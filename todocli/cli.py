import argparse
import json
import shlex
import sys
from datetime import datetime

import requests

import todocli.graphapi.wrapper as wrapper
from todocli.utils.update_checker import check as update_checker
from todocli.utils.datetime_util import (
    parse_datetime,
    format_date,
    TimeExpressionNotRecognized,
    ErrorParsingTime,
)
from todocli.utils.recurrence_util import (
    parse_recurrence,
    InvalidRecurrenceExpression,
)


def parse_task_path(task_input, list_name=None):
    """Parse task input into list name and task name.

    Args:
        task_input: Task name
        list_name: Optional list name from --list flag. Defaults to "Tasks".

    Returns:
        Tuple of (list_name, task_name)
    """
    return (list_name or "Tasks"), task_input


def _output_result(args, result_dict):
    """Output result as JSON or human-readable text."""
    if getattr(args, "json", False):
        print(json.dumps(result_dict, indent=2))
    else:
        # Human readable - just show the message
        print(result_dict.get("message", "Done"))


def print_list(item_list):
    for i, x in enumerate(item_list):
        print(f"[{i}]\t{x}")


def ls(args):
    lists = wrapper.get_lists()
    if getattr(args, "json", False):
        output = [lst.to_dict() for lst in lists]
        print(json.dumps(output, indent=2))
    else:
        lists_names = [lst.display_name for lst in lists]
        print_list(lists_names)


def lst(args):
    date_fmt = getattr(args, "date_format", "eu")
    no_steps = getattr(args, "no_steps", False)
    show_id = getattr(args, "show_id", False)
    include_completed = getattr(args, "all", False)
    only_completed = getattr(args, "completed", False)

    # Support both positional list_name and --list flag
    list_name = getattr(args, "list", None) or getattr(args, "list_name", "Tasks")

    list_id = wrapper.get_list_id_by_name(list_name)
    tasks = wrapper.get_tasks(
        list_id=list_id,
        include_completed=include_completed,
        only_completed=only_completed,
    )

    # Apply filters
    today = datetime.now().date()

    if getattr(args, "due_today", False):
        tasks = [t for t in tasks if t.due_datetime and t.due_datetime.date() == today]

    if getattr(args, "overdue", False):
        tasks = [t for t in tasks if t.due_datetime and t.due_datetime.date() < today]

    if getattr(args, "important", False):
        tasks = [t for t in tasks if _get_enum_value(t.importance) == "high"]

    if not no_steps and tasks:
        steps_map = wrapper.get_checklist_items_batch(list_id, [t.id for t in tasks])
    else:
        steps_map = {}

    if getattr(args, "json", False):
        output = []
        for task in tasks:
            task_dict = task.to_dict()
            task_dict["steps"] = [s.to_dict() for s in steps_map.get(task.id, [])]
            output.append(task_dict)
        print(json.dumps(output, indent=2))
    else:
        for i, task in enumerate(tasks):
            if show_id:
                short_id = task.id[:12] if len(task.id) > 12 else task.id
                line = f"[{i}] {short_id}  {task.title}"
            else:
                line = f"[{i}]\t{task.title}"
            if _get_enum_value(task.importance) == "high":
                line += " !"
            if task.due_datetime is not None:
                line += f" (due: {format_date(task.due_datetime, date_fmt)})"
            print(line)
            for item in steps_map.get(task.id, []):
                check = "x" if item.is_checked else " "
                print(f"    [{check}] {item.display_name}")


def new(args):
    task_list, name = parse_task_path(args.task_name, getattr(args, "list", None))

    reminder_date_time_str = args.reminder
    reminder_datetime = None

    if reminder_date_time_str is not None:
        reminder_datetime = parse_datetime(reminder_date_time_str)

    due_date_time_str = args.due
    due_datetime = None
    if due_date_time_str is not None:
        due_datetime = parse_datetime(due_date_time_str)

    recurrence = parse_recurrence(args.recurrence)

    task_id = wrapper.create_task(
        name,
        list_name=task_list,
        reminder_datetime=reminder_datetime,
        due_datetime=due_datetime,
        important=args.important,
        recurrence=recurrence,
    )

    steps = getattr(args, "step", []) or []
    step_ids = []
    if steps:
        list_id = wrapper.get_list_id_by_name(task_list)
        for step_name in steps:
            step_id, _ = wrapper.create_checklist_item(
                step_name, list_id=list_id, task_id=task_id
            )
            step_ids.append(step_id)

    msg = f"Created task '{name}' in '{task_list}'"
    if steps:
        msg += f" with {len(steps)} step(s)"

    result = {
        "action": "created",
        "id": task_id,
        "title": name,
        "list": task_list,
        "message": msg,
    }
    if step_ids:
        result["step_ids"] = step_ids

    _output_result(args, result)


def newl(args):
    list_id, list_name = wrapper.create_list(args.list_name)
    result = {
        "action": "created",
        "id": list_id,
        "name": list_name,
        "message": f"Created list '{list_name}'",
    }
    _output_result(args, result)


def try_parse_as_int(input_str: str):
    try:
        return int(input_str)
    except ValueError:
        return input_str


def _get_enum_value(enum_or_value):
    """Get value from enum or return as-is if already a string.

    Handles both real enum instances and mock objects in tests.
    """
    return enum_or_value.value if hasattr(enum_or_value, "value") else enum_or_value


def complete(args):
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)
    results = []

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title = wrapper.complete_task(list_name=list_name, task_id=task_id)
        results.append(
            {
                "action": "completed",
                "id": returned_id,
                "title": title,
                "list": list_name,
                "message": f"Completed task '{title}'",
            }
        )
    else:
        task_names = getattr(args, "task_names", None) or [
            getattr(args, "task_name", None)
        ]
        task_names = [t for t in task_names if t is not None]
        for task_name in task_names:
            task_list, name = parse_task_path(task_name, getattr(args, "list", None))
            returned_id, title = wrapper.complete_task(
                list_name=task_list, task_name=try_parse_as_int(name)
            )
            results.append(
                {
                    "action": "completed",
                    "id": returned_id,
                    "title": title,
                    "list": task_list,
                    "message": f"Completed task '{title}' in '{task_list}'",
                }
            )

    if use_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(r["message"])


def uncomplete(args):
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)
    results = []

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title = wrapper.uncomplete_task(
            list_name=list_name, task_id=task_id
        )
        results.append(
            {
                "action": "uncompleted",
                "id": returned_id,
                "title": title,
                "list": list_name,
                "message": f"Uncompleted task '{title}'",
            }
        )
    else:
        task_names = getattr(args, "task_names", None) or [
            getattr(args, "task_name", None)
        ]
        task_names = [t for t in task_names if t is not None]
        for task_name in task_names:
            task_list, name = parse_task_path(task_name, getattr(args, "list", None))
            returned_id, title = wrapper.uncomplete_task(
                list_name=task_list, task_name=try_parse_as_int(name)
            )
            results.append(
                {
                    "action": "uncompleted",
                    "id": returned_id,
                    "title": title,
                    "list": task_list,
                    "message": f"Uncompleted task '{title}' in '{task_list}'",
                }
            )

    if use_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(r["message"])


def rm(args):
    task_id = getattr(args, "task_id", None)
    skip_confirm = getattr(args, "yes", False)
    use_json = getattr(args, "json", False)
    results = []
    skipped_count = 0

    # If --id is provided, use it directly
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        if not confirm_action(f"Remove task (id: {task_id[:8]}...)?", skip_confirm):
            skipped_count += 1
            results.append(
                {
                    "action": "skipped",
                    "id": task_id,
                    "list": list_name,
                    "message": "Skipped (not confirmed)",
                }
            )
        else:
            returned_id = wrapper.remove_task(list_name=list_name, task_id=task_id)
            results.append(
                {
                    "action": "removed",
                    "id": returned_id,
                    "list": list_name,
                    "message": f"Removed task (id: {returned_id[:8]}...)",
                }
            )
    else:
        task_names = getattr(args, "task_names", None) or [
            getattr(args, "task_name", None)
        ]
        task_names = [t for t in task_names if t is not None]

        for task_name in task_names:
            task_list, name = parse_task_path(task_name, getattr(args, "list", None))

            if not confirm_action(
                f"Remove task '{name}' from '{task_list}'?", skip_confirm
            ):
                skipped_count += 1
                results.append(
                    {
                        "action": "skipped",
                        "title": str(name),
                        "list": task_list,
                        "message": f"Skipped '{name}' (not confirmed)",
                    }
                )
                continue

            returned_id = wrapper.remove_task(
                list_name=task_list, task_name=try_parse_as_int(name)
            )
            results.append(
                {
                    "action": "removed",
                    "id": returned_id,
                    "title": str(name),
                    "list": task_list,
                    "message": f"Removed task '{name}' from '{task_list}'",
                }
            )

    if use_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(r["message"])

    # Raise if all tasks were skipped (for non-zero exit code)
    if skipped_count > 0 and skipped_count == len(results):
        raise ValueError("All tasks were skipped (not confirmed)")


def update(args):
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    due_datetime = None
    if args.due is not None:
        due_datetime = parse_datetime(args.due)

    reminder_datetime = None
    if args.reminder is not None:
        reminder_datetime = parse_datetime(args.reminder)

    recurrence = parse_recurrence(args.recurrence)

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title = wrapper.update_task(
            list_name=list_name,
            task_id=task_id,
            title=args.title,
            due_datetime=due_datetime,
            reminder_datetime=reminder_datetime,
            important=True if args.important else None,
            recurrence=recurrence,
        )
        result = {
            "action": "updated",
            "id": returned_id,
            "title": title,
            "list": list_name,
            "message": f"Updated task '{title}'",
        }
    else:
        task_list, name = parse_task_path(args.task_name, getattr(args, "list", None))
        returned_id, title = wrapper.update_task(
            list_name=task_list,
            task_name=try_parse_as_int(name),
            title=args.title,
            due_datetime=due_datetime,
            reminder_datetime=reminder_datetime,
            important=True if args.important else None,
            recurrence=recurrence,
        )
        result = {
            "action": "updated",
            "id": returned_id,
            "title": title,
            "list": task_list,
            "message": f"Updated task '{title}' in '{task_list}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def new_step(args):
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        step_id, step_name = wrapper.create_checklist_item(
            step_name=args.step_name,
            list_name=list_name,
            task_id=task_id,
        )
        result = {
            "action": "created",
            "id": step_id,
            "name": step_name,
            "task_id": task_id,
            "list": list_name,
            "message": f"Added step '{step_name}' to task (id: {task_id[:8]}...)",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        step_id, step_name = wrapper.create_checklist_item(
            step_name=args.step_name,
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
        )
        result = {
            "action": "created",
            "id": step_id,
            "name": step_name,
            "task": str(task_name),
            "list": task_list,
            "message": f"Added step '{step_name}' to '{task_name}' in '{task_list}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def list_steps(args):
    task_id = getattr(args, "task_id", None)

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        items = wrapper.get_checklist_items(list_name=list_name, task_id=task_id)
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        items = wrapper.get_checklist_items(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
        )

    if getattr(args, "json", False):
        output = [item.to_dict() for item in items]
        print(json.dumps(output, indent=2))
    else:
        for i, item in enumerate(items):
            check = "x" if item.is_checked else " "
            print(f"[{i}] [{check}] {item.display_name}")


def complete_step(args):
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        step_id, step_name = wrapper.complete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "completed",
            "id": step_id,
            "name": step_name,
            "task_id": task_id,
            "list": list_name,
            "message": f"Completed step '{step_name}'",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        step_id, step_name = wrapper.complete_checklist_item(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "completed",
            "id": step_id,
            "name": step_name,
            "task": str(task_name),
            "list": task_list,
            "message": f"Completed step '{step_name}' in '{task_name}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def uncomplete_step(args):
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        step_id, step_name = wrapper.uncomplete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "uncompleted",
            "id": step_id,
            "name": step_name,
            "task_id": task_id,
            "list": list_name,
            "message": f"Uncompleted step '{step_name}'",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        step_id, step_name = wrapper.uncomplete_checklist_item(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "uncompleted",
            "id": step_id,
            "name": step_name,
            "task": str(task_name),
            "list": task_list,
            "message": f"Uncompleted step '{step_name}' in '{task_name}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def rm_step(args):
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        step_id = wrapper.delete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "removed",
            "id": step_id,
            "task_id": task_id,
            "list": list_name,
            "message": f"Removed step (id: {step_id[:8]}...)",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        step_id = wrapper.delete_checklist_item(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "removed",
            "id": step_id,
            "task": str(task_name),
            "list": task_list,
            "message": f"Removed step from '{task_name}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def show(args):
    """Display all details of a task."""
    task_id = getattr(args, "task_id", None)
    date_fmt = getattr(args, "date_format", "eu")

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        task_list = getattr(args, "list", None) or "Tasks"
        task = wrapper.get_task(list_name=task_list, task_id=task_id)
        steps = wrapper.get_checklist_items(list_name=task_list, task_id=task_id)
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        task = wrapper.get_task(
            list_name=task_list, task_name=try_parse_as_int(task_name)
        )
        steps = wrapper.get_checklist_items(
            list_name=task_list, task_name=try_parse_as_int(task_name)
        )

    if getattr(args, "json", False):
        output = task.to_dict()
        output["list"] = task_list
        output["steps"] = [s.to_dict() for s in steps]
        print(json.dumps(output, indent=2))
    else:
        print(f"Title:      {task.title}")
        print(f"List:       {task_list}")
        print(f"Status:     {_get_enum_value(task.status)}")
        imp_val = _get_enum_value(task.importance)
        importance_str = "!" if imp_val == "high" else imp_val
        print(f"Importance: {importance_str}")
        if task.due_datetime:
            print(f"Due:        {format_date(task.due_datetime, date_fmt)}")
        if task.reminder_datetime:
            print(f"Reminder:   {task.reminder_datetime.strftime('%Y-%m-%d %H:%M')}")
        print(f"Created:    {format_date(task.created_datetime, date_fmt)}")
        if steps:
            print("Steps:")
            for i, step in enumerate(steps):
                check = "x" if step.is_checked else " "
                print(f"  [{i}] [{check}] {step.display_name}")


def confirm_action(message, skip_confirm=False):
    """Prompt for confirmation. Returns True if confirmed."""
    if skip_confirm:
        return True
    try:
        response = input(f"{message} [y/N]: ")
        return response.lower() in ("y", "yes")
    except EOFError:
        return False


helptext_task_name = (
    "Task name or index number. Use -l/--list to specify a list (default: Tasks)."
)

helptext_step_name = """
        Specify the step (checklist item).
        Can be step_name (string) or step_number (index shown in list-steps output).
        """

helptext_reminder = (
    "Set reminder. Formats: 1h, 30m, 1h30m, 9:30, 5:30pm, "
    "morning (7:00), evening (18:00), tomorrow, 2026-12-24, 24.12.2026"
)

helptext_due = (
    "Set due date. Formats: 2026-12-24, 24.12.2026, 12/24/2026, tomorrow, 1d, 7d"
)

helptext_recurrence = (
    "Set recurrence. Formats: daily, weekly, monthly, yearly, weekdays, "
    "every 2 days, every 3 weeks, weekly:mon,wed,fri"
)


def _add_json_flag(subparser):
    """Add --json flag to a subparser."""
    subparser.add_argument(
        "-j", "--json", action="store_true", help="Output in JSON format"
    )


def _add_date_format_flag(subparser):
    """Add --date-format flag to a subparser."""
    subparser.add_argument(
        "--date-format",
        choices=["eu", "us", "iso"],
        default="eu",
        help="Date display format: eu (DD.MM.YYYY), us (MM/DD/YYYY), iso (YYYY-MM-DD)",
    )


def _add_list_flag(subparser):
    """Add --list flag to a subparser."""
    subparser.add_argument(
        "-l",
        "--list",
        help="Specify the list name explicitly (allows task names with slashes)",
    )


def _add_id_flag(subparser):
    """Add --id flag for direct task ID access (useful for AI agents)."""
    subparser.add_argument(
        "--id",
        dest="task_id",
        help="Task ID (from --json output). List defaults to 'Tasks' if -l not specified.",
    )


def setup_parser():
    parser = argparse.ArgumentParser(
        prog="todo",
        description="Command line interface for Microsoft To-Do",
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Interactive mode"
    )
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers(help="Command to execute")

    # 'lists' command (primary) and 'ls' alias
    for cmd_name in ["lists", "ls"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help="Display all lists" if cmd_name == "lists" else argparse.SUPPRESS,
        )
        _add_json_flag(subparser)
        subparser.set_defaults(func=ls)

    # 'tasks' command (primary) and 'lst'/'t' aliases
    for cmd_name in ["tasks", "lst", "t"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help=(
                "Display tasks from a list"
                if cmd_name == "tasks"
                else argparse.SUPPRESS
            ),
        )
        subparser.add_argument(
            "list_name",
            nargs="?",
            default="Tasks",
            help="List name (default: Tasks)",
        )
        _add_list_flag(subparser)
        subparser.add_argument(
            "--no-steps",
            action="store_true",
            help="Hide checklist items (steps) for faster output",
        )
        subparser.add_argument(
            "--show-id",
            action="store_true",
            help="Show task IDs in output",
        )
        subparser.add_argument(
            "--due-today",
            action="store_true",
            help="Show only tasks due today",
        )
        subparser.add_argument(
            "--overdue",
            action="store_true",
            help="Show only overdue tasks",
        )
        subparser.add_argument(
            "--important",
            action="store_true",
            help="Show only important tasks",
        )
        # Mutually exclusive: --all vs --completed
        completed_group = subparser.add_mutually_exclusive_group()
        completed_group.add_argument(
            "--all",
            action="store_true",
            help="Include completed tasks",
        )
        completed_group.add_argument(
            "--completed",
            action="store_true",
            help="Show only completed tasks",
        )
        _add_json_flag(subparser)
        _add_date_format_flag(subparser)
        subparser.set_defaults(func=lst)

    # 'show' command
    subparser = subparsers.add_parser("show", help="Display all details of a task")
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    _add_date_format_flag(subparser)
    subparser.set_defaults(func=show)

    # 'new' command and 'n' alias
    for cmd_name in ["new", "n"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help="Add a new task" if cmd_name == "new" else argparse.SUPPRESS,
        )
        subparser.add_argument("task_name", help=helptext_task_name)
        subparser.add_argument(
            "-r", "--reminder", help=helptext_reminder, metavar="DATETIME"
        )
        subparser.add_argument("-d", "--due", help=helptext_due, metavar="DATE")
        subparser.add_argument(
            "-I", "--important", action="store_true", help="Mark as important"
        )
        subparser.add_argument(
            "-R", "--recurrence", help=helptext_recurrence, metavar="PATTERN"
        )
        subparser.add_argument(
            "-S",
            "--step",
            action="append",
            default=[],
            help="Add a step (checklist item); can be repeated",
        )
        _add_list_flag(subparser)
        _add_json_flag(subparser)
        subparser.set_defaults(func=new)

    # 'new-list' command (primary) and 'newl' alias
    for cmd_name in ["new-list", "newl"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help="Add a new list" if cmd_name == "new-list" else argparse.SUPPRESS,
        )
        subparser.add_argument("list_name", help="Name of the list to create")
        _add_json_flag(subparser)
        subparser.set_defaults(func=newl)

    # 'complete' command and 'c' alias
    for cmd_name in ["complete", "c"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help="Complete task(s)" if cmd_name == "complete" else argparse.SUPPRESS,
        )
        subparser.add_argument(
            "task_names",
            nargs="*",
            metavar="task",
            help=helptext_task_name,
        )
        _add_list_flag(subparser)
        _add_id_flag(subparser)
        _add_json_flag(subparser)
        subparser.set_defaults(func=complete)

    # 'uncomplete' command
    subparser = subparsers.add_parser(
        "uncomplete", help="Mark completed task(s) as not completed"
    )
    subparser.add_argument(
        "task_names",
        nargs="*",
        metavar="task",
        help=helptext_task_name,
    )
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=uncomplete)

    # 'rm' command and 'd' alias (delete)
    for cmd_name in ["rm", "d"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help="Remove task(s)" if cmd_name == "rm" else argparse.SUPPRESS,
        )
        subparser.add_argument(
            "task_names",
            nargs="*",
            metavar="task",
            help=helptext_task_name,
        )
        subparser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )
        _add_list_flag(subparser)
        _add_id_flag(subparser)
        _add_json_flag(subparser)
        subparser.set_defaults(func=rm)

    # 'update' command
    subparser = subparsers.add_parser("update", help="Update an existing task")
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("--title", help="New title for the task")
    subparser.add_argument(
        "-r", "--reminder", help=helptext_reminder, metavar="DATETIME"
    )
    subparser.add_argument("-d", "--due", help=helptext_due, metavar="DATE")
    subparser.add_argument(
        "-I", "--important", action="store_true", help="Mark as important"
    )
    subparser.add_argument(
        "-R", "--recurrence", help=helptext_recurrence, metavar="PATTERN"
    )
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=update)

    # 'new-step' command
    subparser = subparsers.add_parser(
        "new-step", help="Add a step (checklist item) to a task"
    )
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("step_name", help="Description of the step to create")
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=new_step)

    # 'list-steps' command
    subparser = subparsers.add_parser(
        "list-steps", help="Display steps (checklist items) of a task"
    )
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=list_steps)

    # 'complete-step' command
    subparser = subparsers.add_parser("complete-step", help="Mark a step as checked")
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("step_name", help=helptext_step_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=complete_step)

    # 'uncomplete-step' command
    subparser = subparsers.add_parser(
        "uncomplete-step", help="Mark a checked step as unchecked"
    )
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("step_name", help=helptext_step_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=uncomplete_step)

    # 'rm-step' command
    subparser = subparsers.add_parser("rm-step", help="Remove a step from a task")
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("step_name", help=helptext_step_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=rm_step)

    return parser


def main():
    try:
        parser = setup_parser()
        first_run = True
        interactive = False
        error_occurred = False

        while True:
            try:
                namespace, args = parser.parse_known_args()
                parser.parse_args(args, namespace)

                if namespace.func is not None:
                    namespace.func(namespace)
                else:
                    # No argument was provided
                    parser.print_usage()

                if namespace.interactive and first_run:
                    interactive = True
                    first_run = False

            except argparse.ArgumentError as e:
                print(f"Argument error: {e}")
                error_occurred = True
            except wrapper.TaskNotFoundByName as e:
                print(e.message)
                error_occurred = True
            except wrapper.ListNotFound as e:
                print(e.message)
                error_occurred = True
            except wrapper.TaskNotFoundByIndex as e:
                print(e.message)
                error_occurred = True
            except wrapper.StepNotFoundByName as e:
                print(e.message)
                error_occurred = True
            except wrapper.StepNotFoundByIndex as e:
                print(e.message)
                error_occurred = True
            except TimeExpressionNotRecognized as e:
                print(e.message)
                error_occurred = True
            except ErrorParsingTime as e:
                print(e.message)
                error_occurred = True
            except InvalidRecurrenceExpression as e:
                print(e.message)
                error_occurred = True
            except ValueError as e:
                print(f"Error: {e}")
                error_occurred = True
            except requests.RequestException as e:
                print(f"Network error: {e}")
                error_occurred = True
            finally:
                sys.stdout.flush()
                sys.stderr.flush()

            if not interactive:
                break

            arg = input("\nInput command: ")
            args = shlex.split(arg)
            sys.argv = sys.argv[:1]
            sys.argv += args

        # Exit with non-zero code if an error occurred in non-interactive mode
        if error_occurred and not interactive:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)


if __name__ == "__main__":
    update_checker()
    main()
