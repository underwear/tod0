#!/usr/bin/env python3
"""Unit tests for JSON output functionality"""

import json
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import datetime

from todocli.cli import ls, lst, list_steps, show


def _make_list(display_name, list_id="lid", is_owner=True, is_shared=False):
    """Create a mock TodoList."""
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


def _make_task(
    title,
    task_id="tid",
    importance="normal",
    status="notStarted",
    due_datetime=None,
):
    """Create a mock Task."""
    task = MagicMock()
    task.id = task_id
    task.title = title
    task.importance = MagicMock()
    task.importance.value = importance
    task.status = MagicMock()
    task.status.value = status
    task.due_datetime = due_datetime
    task.reminder_datetime = None
    task.created_datetime = datetime(2026, 1, 1, 10, 0, 0)
    task.completed_datetime = None
    task.is_reminder_on = False
    task.last_modified_datetime = datetime(2026, 1, 1, 10, 0, 0)
    task.to_dict.return_value = {
        "id": task_id,
        "title": title,
        "status": status,
        "importance": importance,
        "due_datetime": due_datetime.isoformat() if due_datetime else None,
        "reminder_datetime": None,
        "created_datetime": "2026-01-01T10:00:00",
        "completed_datetime": None,
        "is_reminder_on": False,
        "last_modified_datetime": "2026-01-01T10:00:00",
    }
    return task


def _make_step(name, step_id="sid", is_checked=False):
    """Create a mock ChecklistItem."""
    step = MagicMock()
    step.id = step_id
    step.display_name = name
    step.is_checked = is_checked
    step.created_datetime = datetime(2026, 1, 1, 10, 0, 0)
    step.checked_datetime = None
    step.to_dict.return_value = {
        "id": step_id,
        "display_name": name,
        "is_checked": is_checked,
        "created_datetime": "2026-01-01T10:00:00",
        "checked_datetime": None,
    }
    return step


def _make_args(**kwargs):
    """Create mock args with defaults."""
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
    }
    for k, v in defaults.items():
        setattr(args, k, v)
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args


class TestJsonOutputLs(unittest.TestCase):
    """Test JSON output for ls (lists) command."""

    @patch("todocli.cli.wrapper")
    def test_ls_json_output(self, mock_wrapper):
        mock_wrapper.get_lists.return_value = [
            _make_list("Tasks"),
            _make_list("Work", list_id="lid2"),
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            ls(_make_args(json=True))
            output = mock_stdout.getvalue()

        data = json.loads(output)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["display_name"], "Tasks")
        self.assertEqual(data[1]["display_name"], "Work")

    @patch("todocli.cli.wrapper")
    def test_ls_text_output(self, mock_wrapper):
        mock_wrapper.get_lists.return_value = [_make_list("Tasks")]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            ls(_make_args(json=False))
            output = mock_stdout.getvalue()

        self.assertIn("[0]", output)
        self.assertIn("Tasks", output)


class TestJsonOutputLst(unittest.TestCase):
    """Test JSON output for lst (tasks) command."""

    @patch("todocli.cli.wrapper")
    def test_lst_json_output(self, mock_wrapper):
        mock_wrapper.get_list_id_by_name.return_value = "lid"
        mock_wrapper.get_tasks.return_value = [
            _make_task("Buy milk", task_id="t1"),
            _make_task("Call mom", task_id="t2", importance="high"),
        ]
        mock_wrapper.get_checklist_items_batch.return_value = {}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args(json=True))
            output = mock_stdout.getvalue()

        data = json.loads(output)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["title"], "Buy milk")
        self.assertEqual(data[1]["title"], "Call mom")
        self.assertEqual(data[1]["importance"], "high")

    @patch("todocli.cli.wrapper")
    def test_lst_json_with_steps(self, mock_wrapper):
        task = _make_task("Groceries", task_id="t1")
        mock_wrapper.get_list_id_by_name.return_value = "lid"
        mock_wrapper.get_tasks.return_value = [task]
        mock_wrapper.get_checklist_items_batch.return_value = {
            "t1": [_make_step("Milk"), _make_step("Eggs", is_checked=True)]
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args(json=True))
            output = mock_stdout.getvalue()

        data = json.loads(output)
        self.assertEqual(len(data[0]["steps"]), 2)
        self.assertEqual(data[0]["steps"][0]["display_name"], "Milk")
        self.assertTrue(data[0]["steps"][1]["is_checked"])


class TestJsonOutputListSteps(unittest.TestCase):
    """Test JSON output for list-steps command."""

    @patch("todocli.cli.wrapper")
    def test_list_steps_json_output(self, mock_wrapper):
        mock_wrapper.get_checklist_items.return_value = [
            _make_step("Step 1"),
            _make_step("Step 2", is_checked=True),
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            list_steps(_make_args(task_name="Test task", json=True))
            output = mock_stdout.getvalue()

        data = json.loads(output)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["display_name"], "Step 1")
        self.assertTrue(data[1]["is_checked"])


class TestJsonOutputShow(unittest.TestCase):
    """Test JSON output for show command."""

    @patch("todocli.cli.wrapper")
    def test_show_json_output(self, mock_wrapper):
        task = _make_task("Important task", importance="high")
        mock_wrapper.get_task.return_value = task
        mock_wrapper.get_checklist_items.return_value = [_make_step("Step 1")]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            show(_make_args(task_name="Important task", json=True))
            output = mock_stdout.getvalue()

        data = json.loads(output)
        self.assertEqual(data["title"], "Important task")
        self.assertEqual(data["importance"], "high")
        self.assertEqual(data["list"], "Tasks")
        self.assertEqual(len(data["steps"]), 1)


if __name__ == "__main__":
    unittest.main()
