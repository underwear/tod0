#!/usr/bin/env python3
"""Unit tests for task filtering functionality"""

import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import datetime, timedelta

from todocli.cli import lst


def _make_task(title, task_id="tid", importance="normal", due_datetime=None):
    """Create a mock Task."""
    task = MagicMock()
    task.id = task_id
    task.title = title
    task.importance = MagicMock()
    task.importance.value = importance
    task.due_datetime = due_datetime
    return task


def _make_args(**kwargs):
    """Create mock args with defaults."""
    args = MagicMock()
    defaults = {
        "json": False,
        "list_name": "Tasks",
        "no_steps": True,  # Skip steps for faster tests
        "date_format": "eu",
        "due_today": False,
        "overdue": False,
        "important": False,
    }
    for k, v in defaults.items():
        setattr(args, k, v)
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args


class TestTaskFilters(unittest.TestCase):
    """Test task filtering options."""

    @patch("todocli.cli.wrapper")
    def test_filter_due_today(self, mock_wrapper):
        today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        mock_wrapper.get_list_id_by_name.return_value = "lid"
        mock_wrapper.get_tasks.return_value = [
            _make_task("Due today", task_id="t1", due_datetime=today),
            _make_task("Due tomorrow", task_id="t2", due_datetime=tomorrow),
            _make_task("No due date", task_id="t3"),
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args(due_today=True))
            output = mock_stdout.getvalue()

        self.assertIn("Due today", output)
        self.assertNotIn("Due tomorrow", output)
        self.assertNotIn("No due date", output)

    @patch("todocli.cli.wrapper")
    def test_filter_overdue(self, mock_wrapper):
        today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        mock_wrapper.get_list_id_by_name.return_value = "lid"
        mock_wrapper.get_tasks.return_value = [
            _make_task("Overdue task", task_id="t1", due_datetime=yesterday),
            _make_task("Due tomorrow", task_id="t2", due_datetime=tomorrow),
            _make_task("No due date", task_id="t3"),
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args(overdue=True))
            output = mock_stdout.getvalue()

        self.assertIn("Overdue task", output)
        self.assertNotIn("Due tomorrow", output)
        self.assertNotIn("No due date", output)

    @patch("todocli.cli.wrapper")
    def test_filter_important(self, mock_wrapper):
        mock_wrapper.get_list_id_by_name.return_value = "lid"
        mock_wrapper.get_tasks.return_value = [
            _make_task("Important task", task_id="t1", importance="high"),
            _make_task("Normal task", task_id="t2", importance="normal"),
            _make_task("Low priority", task_id="t3", importance="low"),
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args(important=True))
            output = mock_stdout.getvalue()

        self.assertIn("Important task", output)
        self.assertNotIn("Normal task", output)
        self.assertNotIn("Low priority", output)

    @patch("todocli.cli.wrapper")
    def test_no_filter_shows_all(self, mock_wrapper):
        mock_wrapper.get_list_id_by_name.return_value = "lid"
        mock_wrapper.get_tasks.return_value = [
            _make_task("Task 1", task_id="t1", importance="high"),
            _make_task("Task 2", task_id="t2", importance="normal"),
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args())
            output = mock_stdout.getvalue()

        self.assertIn("Task 1", output)
        self.assertIn("Task 2", output)


if __name__ == "__main__":
    unittest.main()
