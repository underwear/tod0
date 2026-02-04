#!/usr/bin/env python3
"""Shared test utilities and mock factories for todocli tests."""

from unittest.mock import MagicMock
from datetime import datetime


def make_mock_task(
    title: str,
    task_id: str = "tid",
    importance: str = "normal",
    status: str = "notStarted",
    due_datetime: datetime = None,
    reminder_datetime: datetime = None,
    created_datetime: datetime = None,
):
    """Create a mock Task object for testing.

    Args:
        title: Task title
        task_id: Task ID (default: "tid")
        importance: "low", "normal", or "high" (default: "normal")
        status: Task status (default: "notStarted")
        due_datetime: Optional due date
        reminder_datetime: Optional reminder datetime
        created_datetime: Creation datetime (default: 2026-01-01 10:00)

    Returns:
        MagicMock configured as a Task
    """
    task = MagicMock()
    task.id = task_id
    task.title = title

    # Mock enum-like importance with .value attribute
    task.importance = MagicMock()
    task.importance.value = importance

    # Mock enum-like status with .value attribute
    task.status = MagicMock()
    task.status.value = status

    task.due_datetime = due_datetime
    task.reminder_datetime = reminder_datetime
    task.created_datetime = created_datetime or datetime(2026, 1, 1, 10, 0, 0)
    task.completed_datetime = None
    task.is_reminder_on = reminder_datetime is not None
    task.last_modified_datetime = task.created_datetime

    # Mock to_dict method
    task.to_dict.return_value = {
        "id": task_id,
        "title": title,
        "status": status,
        "importance": importance,
        "due_datetime": due_datetime.isoformat() if due_datetime else None,
        "reminder_datetime": (
            reminder_datetime.isoformat() if reminder_datetime else None
        ),
        "created_datetime": task.created_datetime.isoformat(),
        "completed_datetime": None,
        "is_reminder_on": task.is_reminder_on,
        "last_modified_datetime": task.created_datetime.isoformat(),
    }

    return task


def make_mock_list(
    display_name: str,
    list_id: str = "lid",
    is_owner: bool = True,
    is_shared: bool = False,
):
    """Create a mock TodoList object for testing.

    Args:
        display_name: List name
        list_id: List ID (default: "lid")
        is_owner: Whether user owns the list (default: True)
        is_shared: Whether list is shared (default: False)

    Returns:
        MagicMock configured as a TodoList
    """
    lst = MagicMock()
    lst.id = list_id
    lst.display_name = display_name
    lst.is_owner = is_owner
    lst.is_shared = is_shared
    lst.well_known_list_name = MagicMock()
    lst.well_known_list_name.value = "none"

    lst.to_dict.return_value = {
        "id": list_id,
        "display_name": display_name,
        "is_owner": is_owner,
        "is_shared": is_shared,
        "well_known_list_name": "none",
    }

    return lst


def make_mock_step(
    name: str,
    step_id: str = "sid",
    is_checked: bool = False,
    created_datetime: datetime = None,
):
    """Create a mock ChecklistItem object for testing.

    Args:
        name: Step/checklist item name
        step_id: Step ID (default: "sid")
        is_checked: Whether step is completed (default: False)
        created_datetime: Creation datetime (default: 2026-01-01 10:00)

    Returns:
        MagicMock configured as a ChecklistItem
    """
    step = MagicMock()
    step.id = step_id
    step.display_name = name
    step.is_checked = is_checked
    step.created_datetime = created_datetime or datetime(2026, 1, 1, 10, 0, 0)
    step.checked_datetime = None

    step.to_dict.return_value = {
        "id": step_id,
        "display_name": name,
        "is_checked": is_checked,
        "created_datetime": step.created_datetime.isoformat(),
        "checked_datetime": None,
    }

    return step


def make_mock_args(**kwargs):
    """Create mock argparse args with sensible defaults.

    Commonly used defaults:
        - json: False
        - list_name: "Tasks"
        - no_steps: False
        - date_format: "eu"
        - due_today: False
        - overdue: False
        - important: False
        - list: None
        - task_names: None
        - yes: False

    Args:
        **kwargs: Override any default values

    Returns:
        MagicMock configured as argparse Namespace
    """
    args = MagicMock()

    defaults = {
        "json": False,
        "list_name": "Tasks",
        "no_steps": False,
        "date_format": "eu",
        "due_today": False,
        "overdue": False,
        "important": False,
        "list": None,
        "task_names": None,
        "yes": False,
        "reminder": None,
        "due": None,
        "recurrence": None,
        "title": None,
    }

    for key, value in defaults.items():
        setattr(args, key, value)

    for key, value in kwargs.items():
        setattr(args, key, value)

    return args
