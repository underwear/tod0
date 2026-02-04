#!/usr/bin/env python3
"""Unit tests for the update command (CLI parsing + wrapper)"""

import unittest
from unittest.mock import patch, MagicMock
from todocli.cli import setup_parser
from todocli.graphapi.wrapper import update_task


class TestUpdateCLIParsing(unittest.TestCase):
    """Test argparse setup for the update command"""

    def setUp(self):
        self.parser = setup_parser()

    def test_update_basic(self):
        args = self.parser.parse_args(["update", "Tasks/my task"])
        self.assertEqual(args.task_name, "Tasks/my task")
        self.assertIsNone(args.title)
        self.assertIsNone(args.due)
        self.assertIsNone(args.reminder)
        self.assertFalse(args.important)
        self.assertIsNone(args.recurrence)
        self.assertIsNone(getattr(args, "list", None))

    def test_update_with_title(self):
        args = self.parser.parse_args(["update", "Tasks/old", "--title", "new name"])
        self.assertEqual(args.title, "new name")

    def test_update_with_due(self):
        args = self.parser.parse_args(["update", "Tasks/t", "-d", "15.02.2026"])
        self.assertEqual(args.due, "15.02.2026")

    def test_update_with_all_flags(self):
        args = self.parser.parse_args(
            [
                "update",
                "Tasks/t",
                "--title",
                "renamed",
                "-d",
                "20.02.2026",
                "-r",
                "9:00",
                "-I",
                "-R",
                "daily",
            ]
        )
        self.assertEqual(args.title, "renamed")
        self.assertEqual(args.due, "20.02.2026")
        self.assertEqual(args.reminder, "9:00")
        self.assertTrue(args.important)
        self.assertEqual(args.recurrence, "daily")

    def test_update_with_list_flag(self):
        args = self.parser.parse_args(
            ["update", "my task", "-l", "Work", "--title", "x"]
        )
        self.assertEqual(args.task_name, "my task")
        self.assertEqual(args.list, "Work")
        self.assertEqual(args.title, "x")


class TestUpdateWrapper(unittest.TestCase):
    """Test update_task wrapper function with mocked API"""

    @patch("todocli.graphapi.wrapper.get_oauth_session")
    @patch("todocli.graphapi.wrapper.get_task_id_by_name")
    @patch("todocli.graphapi.wrapper.get_list_id_by_name")
    def test_update_task_title_only(self, mock_list_id, mock_task_id, mock_session):
        mock_list_id.return_value = "lid"
        mock_task_id.return_value = "tid"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = b'{"id": "tid", "title": "new title"}'
        mock_session.return_value.patch.return_value = mock_resp

        task_id, task_title = update_task("Tasks", "my task", title="new title")
        self.assertEqual(task_id, "tid")
        self.assertEqual(task_title, "new title")
        call_kwargs = mock_session.return_value.patch.call_args
        body = call_kwargs.kwargs["json"]
        self.assertEqual(body["title"], "new title")
        self.assertNotIn("dueDateTime", body)

    @patch("todocli.graphapi.wrapper.get_oauth_session")
    @patch("todocli.graphapi.wrapper.get_task_id_by_name")
    @patch("todocli.graphapi.wrapper.get_list_id_by_name")
    def test_update_task_due_only(self, mock_list_id, mock_task_id, mock_session):
        from datetime import datetime

        mock_list_id.return_value = "lid"
        mock_task_id.return_value = "tid"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = b'{"id": "tid", "title": "my task"}'
        mock_session.return_value.patch.return_value = mock_resp

        dt = datetime(2026, 2, 15, 7, 0, 0)
        task_id, task_title = update_task("Tasks", "my task", due_datetime=dt)
        self.assertEqual(task_id, "tid")
        body = mock_session.return_value.patch.call_args.kwargs["json"]
        self.assertIn("dueDateTime", body)
        self.assertNotIn("title", body)

    @patch("todocli.graphapi.wrapper.get_oauth_session")
    @patch("todocli.graphapi.wrapper.get_task_id_by_name")
    @patch("todocli.graphapi.wrapper.get_list_id_by_name")
    def test_update_task_importance(self, mock_list_id, mock_task_id, mock_session):
        mock_list_id.return_value = "lid"
        mock_task_id.return_value = "tid"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = b'{"id": "tid", "title": "my task"}'
        mock_session.return_value.patch.return_value = mock_resp

        task_id, task_title = update_task("Tasks", "my task", important=True)
        self.assertEqual(task_id, "tid")
        body = mock_session.return_value.patch.call_args.kwargs["json"]
        self.assertEqual(body["importance"], "high")

    @patch("todocli.graphapi.wrapper.get_oauth_session")
    @patch("todocli.graphapi.wrapper.get_task_id_by_name")
    @patch("todocli.graphapi.wrapper.get_list_id_by_name")
    def test_update_task_multiple_fields(
        self, mock_list_id, mock_task_id, mock_session
    ):
        from datetime import datetime

        mock_list_id.return_value = "lid"
        mock_task_id.return_value = "tid"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = b'{"id": "tid", "title": "new"}'
        mock_session.return_value.patch.return_value = mock_resp

        dt = datetime(2026, 3, 1, 7, 0, 0)
        task_id, task_title = update_task(
            "Tasks", "t", title="new", due_datetime=dt, important=True
        )
        self.assertEqual(task_id, "tid")
        self.assertEqual(task_title, "new")
        body = mock_session.return_value.patch.call_args.kwargs["json"]
        self.assertEqual(body["title"], "new")
        self.assertIn("dueDateTime", body)
        self.assertEqual(body["importance"], "high")

    @patch("todocli.graphapi.wrapper.get_task_id_by_name")
    @patch("todocli.graphapi.wrapper.get_list_id_by_name")
    def test_update_task_empty_body_raises(self, mock_list_id, mock_task_id):
        mock_list_id.return_value = "lid"
        mock_task_id.return_value = "tid"

        with self.assertRaises(ValueError):
            update_task("Tasks", "t")


if __name__ == "__main__":
    unittest.main()
