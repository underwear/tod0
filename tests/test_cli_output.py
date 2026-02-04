#!/usr/bin/env python3
"""Unit tests for confirmation output after mutating CLI commands"""

import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

from todocli.cli import (
    new,
    newl,
    complete,
    rm,
    update,
    new_step,
    complete_step,
    rm_step,
)


def _make_args(**kwargs):
    args = MagicMock()
    for k, v in kwargs.items():
        setattr(args, k, v)
    # Defaults for optional flags
    if "list" not in kwargs:
        args.list = None
    if "reminder" not in kwargs:
        args.reminder = None
    if "due" not in kwargs:
        args.due = None
    if "important" not in kwargs:
        args.important = False
    if "recurrence" not in kwargs:
        args.recurrence = None
    if "title" not in kwargs:
        args.title = None
    if "task_names" not in kwargs:
        args.task_names = None
    if "yes" not in kwargs:
        args.yes = False
    if "json" not in kwargs:
        args.json = False
    if "task_id" not in kwargs:
        args.task_id = None
    return args


class TestConfirmationOutput(unittest.TestCase):

    @patch("todocli.cli.wrapper")
    def test_new_prints_confirmation(self, mock_wrapper):
        mock_wrapper.create_task.return_value = "task-id-123"
        args = _make_args(task_name="buy milk")

        with patch("sys.stdout", new_callable=StringIO) as out:
            new(args)
            self.assertIn("Created task", out.getvalue())
            self.assertIn("buy milk", out.getvalue())

    @patch("todocli.cli.wrapper")
    def test_new_with_steps_prints_confirmation(self, mock_wrapper):
        mock_wrapper.create_task.return_value = "task-id-123"
        mock_wrapper.get_list_id_by_name.return_value = "list-id"
        mock_wrapper.create_checklist_item.return_value = ("step-id-123", "step name")
        args = _make_args(task_name="buy groceries", step=["milk", "eggs"])

        with patch("sys.stdout", new_callable=StringIO) as out:
            new(args)
            output = out.getvalue()
            self.assertIn("Created task", output)
            self.assertIn("buy groceries", output)
            self.assertIn("2 step(s)", output)

        # Verify steps were created
        self.assertEqual(mock_wrapper.create_checklist_item.call_count, 2)

    @patch("todocli.cli.wrapper")
    def test_newl_prints_confirmation(self, mock_wrapper):
        mock_wrapper.create_list.return_value = ("list-id-123", "Shopping")
        args = _make_args(list_name="Shopping")

        with patch("sys.stdout", new_callable=StringIO) as out:
            newl(args)
            self.assertIn("Created list", out.getvalue())
            self.assertIn("Shopping", out.getvalue())

    @patch("todocli.cli.wrapper")
    def test_complete_prints_confirmation(self, mock_wrapper):
        mock_wrapper.complete_task.return_value = ("task-id-123", "buy milk")
        args = _make_args(task_name="Tasks/buy milk")

        with patch("sys.stdout", new_callable=StringIO) as out:
            complete(args)
            self.assertIn("Completed task", out.getvalue())

    @patch("todocli.cli.wrapper")
    def test_rm_prints_confirmation(self, mock_wrapper):
        mock_wrapper.remove_task.return_value = "task-id-123"
        args = _make_args(task_name="Tasks/buy milk", yes=True)

        with patch("sys.stdout", new_callable=StringIO) as out:
            rm(args)
            self.assertIn("Removed task", out.getvalue())

    @patch("todocli.cli.wrapper")
    def test_update_prints_confirmation(self, mock_wrapper):
        mock_wrapper.update_task.return_value = ("task-id-123", "new name")
        args = _make_args(task_name="Tasks/buy milk", title="new name")

        with patch("sys.stdout", new_callable=StringIO) as out:
            update(args)
            self.assertIn("Updated task", out.getvalue())

    @patch("todocli.cli.wrapper")
    def test_new_step_prints_confirmation(self, mock_wrapper):
        mock_wrapper.create_checklist_item.return_value = ("step-id-123", "get eggs")
        args = _make_args(task_name="Tasks/buy milk", step_name="get eggs")

        with patch("sys.stdout", new_callable=StringIO) as out:
            new_step(args)
            self.assertIn("Added step", out.getvalue())
            self.assertIn("get eggs", out.getvalue())

    @patch("todocli.cli.wrapper")
    def test_complete_step_prints_confirmation(self, mock_wrapper):
        mock_wrapper.complete_checklist_item.return_value = ("step-id-123", "get eggs")
        args = _make_args(task_name="Tasks/buy milk", step_name="get eggs")

        with patch("sys.stdout", new_callable=StringIO) as out:
            complete_step(args)
            self.assertIn("Completed step", out.getvalue())

    @patch("todocli.cli.wrapper")
    def test_rm_step_prints_confirmation(self, mock_wrapper):
        mock_wrapper.delete_checklist_item.return_value = "step-id-123"
        args = _make_args(task_name="Tasks/buy milk", step_name="get eggs")

        with patch("sys.stdout", new_callable=StringIO) as out:
            rm_step(args)
            self.assertIn("Removed step", out.getvalue())


if __name__ == "__main__":
    unittest.main()
