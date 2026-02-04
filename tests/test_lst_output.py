#!/usr/bin/env python3
"""Unit tests for lst command output (due date and importance display)"""

import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import datetime, timezone

from todocli.cli import lst


def _make_task(title, importance="normal", due_datetime=None):
    task = MagicMock()
    task.title = title
    task.importance = importance
    task.due_datetime = due_datetime
    return task


def _make_args(list_name="Tasks", steps=False):
    args = MagicMock()
    args.list_name = list_name
    args.steps = steps
    return args


class TestLstOutput(unittest.TestCase):

    @patch("todocli.cli.wrapper")
    def test_lst_shows_due_date(self, mock_wrapper):
        dt = datetime(2026, 2, 15, 7, 0, 0)
        mock_wrapper.get_tasks.return_value = [_make_task("Buy milk", due_datetime=dt)]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args())
            output = mock_stdout.getvalue()

        self.assertIn("(due: 15.02.2026)", output)
        self.assertIn("Buy milk", output)

    @patch("todocli.cli.wrapper")
    def test_lst_no_due_date(self, mock_wrapper):
        mock_wrapper.get_tasks.return_value = [_make_task("Buy milk")]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args())
            output = mock_stdout.getvalue()

        self.assertNotIn("(due:", output)
        self.assertIn("Buy milk", output)

    @patch("todocli.cli.wrapper")
    def test_lst_shows_importance(self, mock_wrapper):
        mock_wrapper.get_tasks.return_value = [
            _make_task("Important task", importance="high")
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args())
            output = mock_stdout.getvalue()

        self.assertIn("Important task !", output)

    @patch("todocli.cli.wrapper")
    def test_lst_normal_importance_no_marker(self, mock_wrapper):
        mock_wrapper.get_tasks.return_value = [
            _make_task("Normal task", importance="normal")
        ]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args())
            output = mock_stdout.getvalue()

        self.assertNotIn("!", output)

    @patch("todocli.cli.wrapper")
    def test_lst_with_steps(self, mock_wrapper):
        dt = datetime(2026, 3, 1, 7, 0, 0)
        mock_wrapper.get_tasks.return_value = [
            _make_task("Task with steps", importance="high", due_datetime=dt)
        ]
        step = MagicMock()
        step.is_checked = False
        step.display_name = "Step 1"
        mock_wrapper.get_checklist_items.return_value = [step]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            lst(_make_args(steps=True))
            output = mock_stdout.getvalue()

        self.assertIn("Task with steps !", output)
        self.assertIn("(due: 01.03.2026)", output)
        self.assertIn("[ ] Step 1", output)


if __name__ == "__main__":
    unittest.main()
