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


def _is_json_mode():
    """Check if --json or -j flag is present in sys.argv."""
    return "--json" in sys.argv or "-j" in sys.argv


def _output_error(error_code: str, message: str):
    """Output error as JSON or plain text based on --json flag."""
    if _is_json_mode():
        error_dict = {
            "action": "failed",
            "error": message,
            "code": error_code,
        }
        print(json.dumps(error_dict, indent=2))
    else:
        print(message)


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
        output = {
            "list_id": list_id,
            "list_name": list_name,
            "tasks": [],
        }
        for task in tasks:
            task_dict = task.to_dict()
            task_dict["steps"] = [s.to_dict() for s in steps_map.get(task.id, [])]
            output["tasks"].append(task_dict)
        print(json.dumps(output, indent=2))
    else:
        for i, task in enumerate(tasks):
            if show_id:
                # Show full ID for scripting/agent use
                line = f"[{i}] {task.id}  {task.title}"
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
    note_content = getattr(args, "note", None)

    task_id = wrapper.create_task(
        name,
        list_name=task_list,
        reminder_datetime=reminder_datetime,
        due_datetime=due_datetime,
        important=args.important,
        recurrence=recurrence,
        note=note_content,
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

    link_url = getattr(args, "link", None)
    link_id = None
    if link_url:
        link_id, _, _ = wrapper.create_linked_resource(
            web_url=link_url,
            list_name=task_list,
            task_id=task_id,
        )

    msg = f"Created task '{name}' in '{task_list}'"
    if steps:
        msg += f" with {len(steps)} step(s)"
    if note_content:
        msg += " with note"
    if link_url:
        msg += " with link"

    result = {
        "action": "created",
        "id": task_id,
        "title": name,
        "list": task_list,
        "message": msg,
    }
    if step_ids:
        result["step_ids"] = step_ids
    if note_content:
        result["note"] = note_content
    if link_id:
        result["link_id"] = link_id
        result["link_url"] = link_url

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


def rename_list(args):
    list_id, new_name = wrapper.rename_list(args.old_name, args.new_name)
    result = {
        "action": "renamed",
        "id": list_id,
        "old_name": args.old_name,
        "name": new_name,
        "message": f"Renamed list '{args.old_name}' to '{new_name}'",
    }
    _output_result(args, result)


def rm_list(args):
    use_json = getattr(args, "json", False)
    skip_confirm = getattr(args, "yes", False)

    list_name = args.list_name

    if not skip_confirm:
        confirm = input(f"Delete list '{list_name}' and all its tasks? [y/N]: ")
        if confirm.lower() not in ("y", "yes"):
            if not use_json:
                print("Cancelled")
            return

    list_id = wrapper.delete_list(list_name=list_name)
    result = {
        "action": "removed",
        "id": list_id,
        "name": list_name,
        "message": f"Removed list '{list_name}'",
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
    task_index = getattr(args, "task_index", None)
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
    # If --index is provided, use it as explicit index
    elif task_index is not None:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title = wrapper.complete_task(
            list_name=list_name, task_name=task_index
        )
        results.append(
            {
                "action": "completed",
                "id": returned_id,
                "title": title,
                "list": list_name,
                "message": f"Completed task '{title}' in '{list_name}'",
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
    task_index = getattr(args, "task_index", None)
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
    # If --index is provided, use it as explicit index
    elif task_index is not None:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title = wrapper.uncomplete_task(
            list_name=list_name, task_name=task_index
        )
        results.append(
            {
                "action": "uncompleted",
                "id": returned_id,
                "title": title,
                "list": list_name,
                "message": f"Uncompleted task '{title}' in '{list_name}'",
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
    task_index = getattr(args, "task_index", None)
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
            returned_id, title = wrapper.remove_task(list_name=list_name, task_id=task_id)
            results.append(
                {
                    "action": "removed",
                    "id": returned_id,
                    "title": title,
                    "list": list_name,
                    "message": f"Removed task '{title}' from '{list_name}'",
                }
            )
    # If --index is provided, use it as explicit index
    elif task_index is not None:
        list_name = getattr(args, "list", None) or "Tasks"
        if not confirm_action(
            f"Remove task #{task_index} from '{list_name}'?", skip_confirm
        ):
            skipped_count += 1
            results.append(
                {
                    "action": "skipped",
                    "index": task_index,
                    "list": list_name,
                    "message": f"Skipped task #{task_index} (not confirmed)",
                }
            )
        else:
            returned_id, title = wrapper.remove_task(
                list_name=list_name, task_name=task_index
            )
            results.append(
                {
                    "action": "removed",
                    "id": returned_id,
                    "title": title,
                    "list": list_name,
                    "message": f"Removed task '{title}' from '{list_name}'",
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

            returned_id, title = wrapper.remove_task(
                list_name=task_list, task_name=try_parse_as_int(name)
            )
            results.append(
                {
                    "action": "removed",
                    "id": returned_id,
                    "title": title,
                    "list": task_list,
                    "message": f"Removed task '{title}' from '{task_list}'",
                }
            )

    if use_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(r["message"])

    # Note: skipped tasks are not an error - user explicitly declined


def update(args):
    task_id = getattr(args, "task_id", None)
    task_index = getattr(args, "task_index", None)
    use_json = getattr(args, "json", False)
    list_name = getattr(args, "list", None) or "Tasks"

    due_datetime = None
    if args.due is not None:
        due_datetime = parse_datetime(args.due)

    reminder_datetime = None
    if args.reminder is not None:
        reminder_datetime = parse_datetime(args.reminder)

    recurrence = parse_recurrence(args.recurrence)

    # Handle importance: --important sets True, --no-important sets False, neither is None
    important = None
    if args.important:
        important = True
    elif getattr(args, "no_important", False):
        important = False

    clear_due = getattr(args, "clear_due", False)
    clear_reminder = getattr(args, "clear_reminder", False)
    clear_recurrence = getattr(args, "clear_recurrence", False)

    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    if task_id:
        returned_id, title = wrapper.update_task(
            list_name=list_name,
            task_id=task_id,
            title=args.title,
            due_datetime=due_datetime,
            reminder_datetime=reminder_datetime,
            important=important,
            recurrence=recurrence,
            clear_due=clear_due,
            clear_reminder=clear_reminder,
            clear_recurrence=clear_recurrence,
        )
        result = {
            "action": "updated",
            "id": returned_id,
            "title": title,
            "list": list_name,
            "message": f"Updated task '{title}'",
        }
    # If --index is provided, use it as explicit index
    elif task_index is not None:
        returned_id, title = wrapper.update_task(
            list_name=list_name,
            task_name=task_index,
            title=args.title,
            due_datetime=due_datetime,
            reminder_datetime=reminder_datetime,
            important=important,
            recurrence=recurrence,
            clear_due=clear_due,
            clear_reminder=clear_reminder,
            clear_recurrence=clear_recurrence,
        )
        result = {
            "action": "updated",
            "id": returned_id,
            "title": title,
            "list": list_name,
            "message": f"Updated task '{title}' in '{list_name}'",
        }
    else:
        task_list, name = parse_task_path(args.task_name, getattr(args, "list", None))
        returned_id, title = wrapper.update_task(
            list_name=task_list,
            task_name=try_parse_as_int(name),
            title=args.title,
            due_datetime=due_datetime,
            reminder_datetime=reminder_datetime,
            important=important,
            recurrence=recurrence,
            clear_due=clear_due,
            clear_reminder=clear_reminder,
            clear_recurrence=clear_recurrence,
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
            "task_name": str(task_name),
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
    step_id_arg = getattr(args, "step_id", None)
    use_json = getattr(args, "json", False)

    # If --step-id is provided, use it directly (requires --id for task)
    if step_id_arg:
        if not task_id:
            raise ValueError("--step-id requires --id (task ID) to be specified")
        list_name = getattr(args, "list", None) or "Tasks"
        returned_step_id, step_name = wrapper.complete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_id=step_id_arg,
        )
        result = {
            "action": "completed",
            "id": returned_step_id,
            "name": step_name,
            "task_id": task_id,
            "list": list_name,
            "message": f"Completed step '{step_name}'",
        }
    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    elif task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        # When --id is used, step comes as first positional arg (task_name)
        step_arg = args.step_name if args.step_name else args.task_name
        returned_step_id, step_name = wrapper.complete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_name=try_parse_as_int(step_arg),
        )
        result = {
            "action": "completed",
            "id": returned_step_id,
            "name": step_name,
            "task_id": task_id,
            "list": list_name,
            "message": f"Completed step '{step_name}'",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        returned_step_id, step_name = wrapper.complete_checklist_item(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "completed",
            "id": returned_step_id,
            "name": step_name,
            "task_name": str(task_name),
            "list": task_list,
            "message": f"Completed step '{step_name}' in '{task_name}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def uncomplete_step(args):
    task_id = getattr(args, "task_id", None)
    step_id_arg = getattr(args, "step_id", None)
    use_json = getattr(args, "json", False)

    # If --step-id is provided, use it directly (requires --id for task)
    if step_id_arg:
        if not task_id:
            raise ValueError("--step-id requires --id (task ID) to be specified")
        list_name = getattr(args, "list", None) or "Tasks"
        returned_step_id, step_name = wrapper.uncomplete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_id=step_id_arg,
        )
        result = {
            "action": "uncompleted",
            "id": returned_step_id,
            "name": step_name,
            "task_id": task_id,
            "list": list_name,
            "message": f"Uncompleted step '{step_name}'",
        }
    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    elif task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        # When --id is used, step comes as first positional arg (task_name)
        step_arg = args.step_name if args.step_name else args.task_name
        returned_step_id, step_name = wrapper.uncomplete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_name=try_parse_as_int(step_arg),
        )
        result = {
            "action": "uncompleted",
            "id": returned_step_id,
            "name": step_name,
            "task_id": task_id,
            "list": list_name,
            "message": f"Uncompleted step '{step_name}'",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        returned_step_id, step_name = wrapper.uncomplete_checklist_item(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "uncompleted",
            "id": returned_step_id,
            "name": step_name,
            "task_name": str(task_name),
            "list": task_list,
            "message": f"Uncompleted step '{step_name}' in '{task_name}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def rm_step(args):
    task_id = getattr(args, "task_id", None)
    step_id_arg = getattr(args, "step_id", None)
    use_json = getattr(args, "json", False)

    # If --step-id is provided, use it directly (requires --id for task)
    if step_id_arg:
        if not task_id:
            raise ValueError("--step-id requires --id (task ID) to be specified")
        list_name = getattr(args, "list", None) or "Tasks"
        returned_step_id = wrapper.delete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_id=step_id_arg,
        )
        result = {
            "action": "removed",
            "id": returned_step_id,
            "task_id": task_id,
            "list": list_name,
            "message": f"Removed step (id: {returned_step_id[:8]}...)",
        }
    # If --id is provided, use it directly (-l/--list defaults to "Tasks")
    elif task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        # When --id is used, step comes as first positional arg (task_name)
        step_arg = args.step_name if args.step_name else args.task_name
        returned_step_id = wrapper.delete_checklist_item(
            list_name=list_name,
            task_id=task_id,
            step_name=try_parse_as_int(step_arg),
        )
        result = {
            "action": "removed",
            "id": returned_step_id,
            "task_id": task_id,
            "list": list_name,
            "message": f"Removed step (id: {returned_step_id[:8]}...)",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        returned_step_id = wrapper.delete_checklist_item(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
            step_name=try_parse_as_int(args.step_name),
        )
        result = {
            "action": "removed",
            "id": returned_step_id,
            "task_name": str(task_name),
            "list": task_list,
            "message": f"Removed step from '{task_name}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def note(args):
    """Add or update a note on a task."""
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)
    note_content = args.note_content

    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title, content = wrapper.update_task_note(
            note_content=note_content,
            list_name=list_name,
            task_id=task_id,
        )
        result = {
            "action": "updated",
            "id": returned_id,
            "title": title,
            "note": content,
            "list": list_name,
            "message": f"Updated note on task '{title}'",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        returned_id, title, content = wrapper.update_task_note(
            note_content=note_content,
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
        )
        result = {
            "action": "updated",
            "id": returned_id,
            "title": title,
            "note": content,
            "list": task_list,
            "message": f"Updated note on task '{title}' in '{task_list}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def show_note(args):
    """Display the note of a task."""
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    if task_id:
        task_list = getattr(args, "list", None) or "Tasks"
        task = wrapper.get_task(list_name=task_list, task_id=task_id)
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        task = wrapper.get_task(
            list_name=task_list, task_name=try_parse_as_int(task_name)
        )

    if use_json:
        output = {
            "id": task.id,
            "title": task.title,
            "note": task.note if task.note else None,
            "list": task_list,
        }
        print(json.dumps(output, indent=2))
    else:
        if task.note:
            print(task.note)
        else:
            print(f"No note on task '{task.title}'")


def clear_note(args):
    """Clear the note from a task."""
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title = wrapper.clear_task_note(
            list_name=list_name,
            task_id=task_id,
        )
        result = {
            "action": "cleared",
            "id": returned_id,
            "title": title,
            "list": list_name,
            "message": f"Cleared note from task '{title}'",
        }
    else:
        task_list, task_name = parse_task_path(
            args.task_name, getattr(args, "list", None)
        )
        returned_id, title = wrapper.clear_task_note(
            list_name=task_list,
            task_name=try_parse_as_int(task_name),
        )
        result = {
            "action": "cleared",
            "id": returned_id,
            "title": title,
            "list": task_list,
            "message": f"Cleared note from task '{title}' in '{task_list}'",
        }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def link(args):
    """Add a link (linked resource) to a task."""
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)
    web_url = args.url
    app_name = getattr(args, "app", None)
    display_name = getattr(args, "title", None)

    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        link_id, returned_id, title = wrapper.create_linked_resource(
            web_url=web_url,
            list_name=list_name,
            task_id=task_id,
            application_name=app_name,
            display_name=display_name,
        )
    else:
        task_list, name = parse_task_path(args.task_name, getattr(args, "list", None))
        link_id, returned_id, title = wrapper.create_linked_resource(
            web_url=web_url,
            list_name=task_list,
            task_name=try_parse_as_int(name),
            application_name=app_name,
            display_name=display_name,
        )
        list_name = task_list

    result = {
        "action": "linked",
        "link_id": link_id,
        "task_id": returned_id,
        "title": title,
        "url": web_url,
        "list": list_name,
        "message": f"Added link to task '{title}'",
    }
    if app_name:
        result["app"] = app_name

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def unlink(args):
    """Remove link(s) from a task."""
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)
    link_index = getattr(args, "link_index", None)

    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        returned_id, title, count = wrapper.delete_linked_resource(
            list_name=list_name,
            task_id=task_id,
            link_index=link_index,
        )
    else:
        task_list, name = parse_task_path(args.task_name, getattr(args, "list", None))
        returned_id, title, count = wrapper.delete_linked_resource(
            list_name=task_list,
            task_name=try_parse_as_int(name),
            link_index=link_index,
        )
        list_name = task_list

    if count == 0:
        msg = f"No links to remove from task '{title}'"
    elif count == 1:
        msg = f"Removed 1 link from task '{title}'"
    else:
        msg = f"Removed {count} links from task '{title}'"

    result = {
        "action": "unlinked",
        "task_id": returned_id,
        "title": title,
        "count": count,
        "list": list_name,
        "message": msg,
    }

    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])


def links(args):
    """List all links on a task."""
    task_id = getattr(args, "task_id", None)
    use_json = getattr(args, "json", False)

    if task_id:
        list_name = getattr(args, "list", None) or "Tasks"
        resources = wrapper.get_linked_resources(
            list_name=list_name, task_id=task_id
        )
    else:
        task_list, name = parse_task_path(args.task_name, getattr(args, "list", None))
        resources = wrapper.get_linked_resources(
            list_name=task_list,
            task_name=try_parse_as_int(name),
        )
        list_name = task_list

    if use_json:
        output = {
            "list": list_name,
            "links": [
                {
                    "id": r.get("id", ""),
                    "url": r.get("webUrl", ""),
                    "app": r.get("applicationName", ""),
                    "display_name": r.get("displayName", ""),
                }
                for r in resources
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        if not resources:
            print("No links")
            return
        for i, r in enumerate(resources):
            app = r.get("applicationName", "")
            url = r.get("webUrl", "")
            display = r.get("displayName", "")
            if app and display != url:
                print(f"[{i}] {display} ({app}) - {url}")
            elif app:
                print(f"[{i}] {app} - {url}")
            else:
                print(f"[{i}] {url}")


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

    # Fetch linked resources
    try:
        task_links = wrapper.get_linked_resources(
            list_name=task_list, task_id=task.id
        )
    except Exception:
        task_links = []

    if getattr(args, "json", False):
        output = task.to_dict()
        output["list"] = task_list
        output["steps"] = [s.to_dict() for s in steps]
        output["links"] = [
            {
                "id": r.get("id", ""),
                "url": r.get("webUrl", ""),
                "app": r.get("applicationName", ""),
                "display_name": r.get("displayName", ""),
            }
            for r in task_links
        ]
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
        if task.note:
            print(f"Note:       {task.note}")
        if steps:
            print("Steps:")
            for i, step in enumerate(steps):
                check = "x" if step.is_checked else " "
                print(f"  [{i}] [{check}] {step.display_name}")
        if task_links:
            print("Links:")
            for i, r in enumerate(task_links):
                app = r.get("applicationName", "")
                url = r.get("webUrl", "")
                display = r.get("displayName", "")
                if app and display != url:
                    print(f"  [{i}] {display} ({app}) - {url}")
                elif app:
                    print(f"  [{i}] {app} - {url}")
                else:
                    print(f"  [{i}] {url}")


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


def _add_index_flag(subparser):
    """Add --index flag for explicit task index (avoids auto-detection)."""
    subparser.add_argument(
        "--index",
        dest="task_index",
        type=int,
        help="Task index (0-based, as shown in 'tasks' output). Explicit alternative to positional arg.",
    )


def _add_step_id_flag(subparser):
    """Add --step-id flag for direct step ID access (useful for AI agents)."""
    subparser.add_argument(
        "--step-id",
        dest="step_id",
        help="Step ID (from list-steps --json output). Skips step lookup by name/index.",
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
        subparser.add_argument(
            "-N",
            "--note",
            help="Add a note to the task",
            metavar="TEXT",
        )
        subparser.add_argument(
            "-L",
            "--link",
            help="Attach a link (URL) to the task at creation time",
            metavar="URL",
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

    # 'rename-list' command
    subparser = subparsers.add_parser("rename-list", help="Rename a list")
    subparser.add_argument("old_name", help="Current name of the list")
    subparser.add_argument("new_name", help="New name for the list")
    _add_json_flag(subparser)
    subparser.set_defaults(func=rename_list)

    # 'rm-list' command
    subparser = subparsers.add_parser("rm-list", help="Remove a list and all its tasks")
    subparser.add_argument("list_name", help="Name of the list to remove")
    subparser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt"
    )
    _add_json_flag(subparser)
    subparser.set_defaults(func=rm_list)

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
        _add_index_flag(subparser)
        _add_json_flag(subparser)
        subparser.set_defaults(func=complete)

    # 'uncomplete' command and 'reopen' alias
    for cmd_name in ["uncomplete", "reopen"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help=(
                "Mark completed task(s) as not completed"
                if cmd_name == "uncomplete"
                else argparse.SUPPRESS
            ),
        )
        subparser.add_argument(
            "task_names",
            nargs="*",
            metavar="task",
            help=helptext_task_name,
        )
        _add_list_flag(subparser)
        _add_id_flag(subparser)
        _add_index_flag(subparser)
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
        _add_index_flag(subparser)
        _add_json_flag(subparser)
        subparser.set_defaults(func=rm)

    # 'update' command
    subparser = subparsers.add_parser("update", help="Update an existing task")
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("--title", help="New title for the task")

    # Mutually exclusive: --due vs --clear-due
    due_group = subparser.add_mutually_exclusive_group()
    due_group.add_argument("-d", "--due", help=helptext_due, metavar="DATE")
    due_group.add_argument("--clear-due", action="store_true", help="Remove due date")

    # Mutually exclusive: --reminder vs --clear-reminder
    reminder_group = subparser.add_mutually_exclusive_group()
    reminder_group.add_argument(
        "-r", "--reminder", help=helptext_reminder, metavar="DATETIME"
    )
    reminder_group.add_argument(
        "--clear-reminder", action="store_true", help="Remove reminder"
    )

    # Mutually exclusive: --important vs --no-important
    important_group = subparser.add_mutually_exclusive_group()
    important_group.add_argument(
        "-I", "--important", action="store_true", help="Mark as important"
    )
    important_group.add_argument(
        "--no-important", action="store_true", help="Remove important flag"
    )

    # Mutually exclusive: --recurrence vs --clear-recurrence
    recurrence_group = subparser.add_mutually_exclusive_group()
    recurrence_group.add_argument(
        "-R", "--recurrence", help=helptext_recurrence, metavar="PATTERN"
    )
    recurrence_group.add_argument(
        "--clear-recurrence", action="store_true", help="Remove recurrence"
    )

    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_index_flag(subparser)
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
    subparser.add_argument("step_name", nargs="?", help=helptext_step_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_step_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=complete_step)

    # 'uncomplete-step' command
    subparser = subparsers.add_parser(
        "uncomplete-step", help="Mark a checked step as unchecked"
    )
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("step_name", nargs="?", help=helptext_step_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_step_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=uncomplete_step)

    # 'rm-step' command
    subparser = subparsers.add_parser("rm-step", help="Remove a step from a task")
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("step_name", nargs="?", help=helptext_step_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_step_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=rm_step)

    # 'note' command - add or update a note on a task
    subparser = subparsers.add_parser("note", help="Add or update a note on a task")
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("note_content", help="Note content to add to the task")
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=note)

    # 'show-note' command (primary) and 'sn' alias
    for cmd_name in ["show-note", "sn"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help="Display the note of a task" if cmd_name == "show-note" else argparse.SUPPRESS,
        )
        subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
        _add_list_flag(subparser)
        _add_id_flag(subparser)
        _add_json_flag(subparser)
        subparser.set_defaults(func=show_note)

    # 'clear-note' command (primary) and 'cn' alias
    for cmd_name in ["clear-note", "cn"]:
        subparser = subparsers.add_parser(
            cmd_name,
            help="Clear the note from a task" if cmd_name == "clear-note" else argparse.SUPPRESS,
        )
        subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
        _add_list_flag(subparser)
        _add_id_flag(subparser)
        _add_json_flag(subparser)
        subparser.set_defaults(func=clear_note)

    # 'link' command - add a link (linked resource) to a task
    subparser = subparsers.add_parser(
        "link", help="Add a link (deep link) to a task"
    )
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument("url", help="URL to link to the task")
    subparser.add_argument(
        "--app", help="Application name (e.g. Jira, GitHub, Slack). Defaults to URL domain."
    )
    subparser.add_argument(
        "--title", help="Display name for the link. Defaults to URL."
    )
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=link)

    # 'unlink' command - remove link(s) from a task
    subparser = subparsers.add_parser(
        "unlink", help="Remove link(s) from a task"
    )
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    subparser.add_argument(
        "--index",
        dest="link_index",
        type=int,
        help="Remove only the link at this index (from 'links' output). Omit to remove all.",
    )
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=unlink)

    # 'links' command - list all links on a task
    subparser = subparsers.add_parser(
        "links", help="List all links (deep links) on a task"
    )
    subparser.add_argument("task_name", nargs="?", help=helptext_task_name)
    _add_list_flag(subparser)
    _add_id_flag(subparser)
    _add_json_flag(subparser)
    subparser.set_defaults(func=links)

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
                _output_error("argument_error", f"Argument error: {e}")
                error_occurred = True
            except wrapper.TaskNotFoundByName as e:
                _output_error("task_not_found", e.message)
                error_occurred = True
            except wrapper.ListNotFound as e:
                _output_error("list_not_found", e.message)
                error_occurred = True
            except wrapper.TaskNotFoundByIndex as e:
                _output_error("task_not_found", e.message)
                error_occurred = True
            except wrapper.StepNotFoundByName as e:
                _output_error("step_not_found", e.message)
                error_occurred = True
            except wrapper.StepNotFoundByIndex as e:
                _output_error("step_not_found", e.message)
                error_occurred = True
            except wrapper.LinkNotFoundByIndex as e:
                _output_error("link_not_found", e.message)
                error_occurred = True
            except TimeExpressionNotRecognized as e:
                _output_error("invalid_time", e.message)
                error_occurred = True
            except ErrorParsingTime as e:
                _output_error("invalid_time", e.message)
                error_occurred = True
            except InvalidRecurrenceExpression as e:
                _output_error("invalid_recurrence", e.message)
                error_occurred = True
            except ValueError as e:
                _output_error("value_error", f"Error: {e}")
                error_occurred = True
            except requests.RequestException as e:
                _output_error("network_error", f"Network error: {e}")
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
