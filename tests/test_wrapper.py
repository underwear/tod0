#!/usr/bin/env python3
"""Unit tests for graph API wrapper module"""

import unittest
from unittest.mock import patch, MagicMock
import json
from todocli.graphapi.wrapper import (
    ListNotFound,
    TaskNotFoundByName,
    TaskNotFoundByIndex,
    StepNotFoundByIndex,
    StepNotFoundByName,
    BASE_URL,
    BATCH_URL,
    BATCH_MAX_REQUESTS,
    get_task_id_by_name,
    get_step_id,
    get_checklist_items_batch,
)


class TestWrapperExceptions(unittest.TestCase):
    """Test custom exception classes"""

    def test_list_not_found_exception(self):
        """Test ListNotFound exception message"""
        list_name = "NonExistentList"
        exc = ListNotFound(list_name)

        self.assertIn(list_name, exc.message)
        self.assertIn("could not be found", exc.message)

    def test_task_not_found_by_name_exception(self):
        """Test TaskNotFoundByName exception message"""
        task_name = "NonExistentTask"
        list_name = "Personal"
        exc = TaskNotFoundByName(task_name, list_name)

        self.assertIn(task_name, exc.message)
        self.assertIn(list_name, exc.message)
        self.assertIn("could not be found", exc.message)

    def test_task_not_found_by_index_exception(self):
        """Test TaskNotFoundByIndex exception message"""
        task_index = 999
        list_name = "Personal"
        exc = TaskNotFoundByIndex(task_index, list_name)

        self.assertIn(str(task_index), exc.message)
        self.assertIn(list_name, exc.message)
        self.assertIn("could not be found", exc.message)


class TestWrapperConstants(unittest.TestCase):
    """Test API endpoint URL constants"""

    def test_base_url_format(self):
        """Test BASE_URL is correctly formatted"""
        self.assertTrue(BASE_URL.startswith("https://graph.microsoft.com"))
        self.assertIn("/me/todo/lists", BASE_URL)

    def test_batch_url_format(self):
        """Test BATCH_URL is correctly formatted"""
        self.assertTrue(BATCH_URL.startswith("https://graph.microsoft.com"))
        self.assertIn("/$batch", BATCH_URL)


class TestGetTaskIdByName(unittest.TestCase):
    """Test get_task_id_by_name with int index and invalid types"""

    @patch("todocli.graphapi.wrapper.get_tasks")
    @patch("todocli.graphapi.wrapper.get_list_id_by_name")
    def test_get_task_id_by_name_with_int_index(self, mock_get_list_id, mock_get_tasks):
        mock_get_list_id.return_value = "list-id-123"
        task0 = MagicMock()
        task0.id = "task-id-0"
        task1 = MagicMock()
        task1.id = "task-id-1"
        mock_get_tasks.return_value = [task0, task1]

        result = get_task_id_by_name("Tasks", 1)
        self.assertEqual(result, "task-id-1")
        mock_get_tasks.assert_called_once_with(list_name="Tasks")

    @patch("todocli.graphapi.wrapper.get_tasks")
    @patch("todocli.graphapi.wrapper.get_list_id_by_name")
    def test_get_task_id_by_name_with_invalid_index(
        self, mock_get_list_id, mock_get_tasks
    ):
        mock_get_list_id.return_value = "list-id-123"
        mock_get_tasks.return_value = []

        with self.assertRaises(TaskNotFoundByIndex):
            get_task_id_by_name("Tasks", 5)

    def test_get_task_id_by_name_with_invalid_type(self):
        with self.assertRaises(TypeError):
            get_task_id_by_name("Tasks", 3.14)


class TestGetStepId(unittest.TestCase):
    """Test get_step_id with invalid types"""

    @patch("todocli.graphapi.wrapper.get_checklist_items")
    def test_get_step_id_with_invalid_type(self, mock_get_items):
        with self.assertRaises(TypeError):
            get_step_id("Tasks", "my task", 3.14, list_id="lid", task_id="tid")


class TestGetChecklistItemsBatch(unittest.TestCase):
    """Test get_checklist_items_batch using $batch API"""

    @patch("todocli.graphapi.wrapper.get_oauth_session")
    def test_batch_single_task(self, mock_session):
        batch_response = {
            "responses": [
                {
                    "id": "tid-1",
                    "status": 200,
                    "body": {
                        "value": [
                            {
                                "id": "step-1",
                                "displayName": "Buy eggs",
                                "isChecked": False,
                                "checkedDateTime": None,
                                "createdDateTime": "2026-01-01T00:00:00.0000000Z",
                            }
                        ]
                    },
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = json.dumps(batch_response).encode()
        mock_session.return_value.post.return_value = mock_resp

        result = get_checklist_items_batch("lid-1", ["tid-1"])
        self.assertIn("tid-1", result)
        self.assertEqual(len(result["tid-1"]), 1)
        self.assertEqual(result["tid-1"][0].display_name, "Buy eggs")

        # Verify batch request format
        call_args = mock_session.return_value.post.call_args
        self.assertEqual(call_args.args[0], BATCH_URL)
        req_body = call_args.kwargs["json"]
        self.assertEqual(len(req_body["requests"]), 1)
        self.assertEqual(req_body["requests"][0]["method"], "GET")

    def test_batch_empty_tasks(self):
        result = get_checklist_items_batch("lid-1", [])
        self.assertEqual(result, {})

    @patch("todocli.graphapi.wrapper.get_oauth_session")
    def test_batch_chunking(self, mock_session):
        task_ids = [f"tid-{i}" for i in range(25)]

        def make_batch_response(chunk_ids):
            return {
                "responses": [
                    {"id": tid, "status": 200, "body": {"value": []}}
                    for tid in chunk_ids
                ]
            }

        call_count = [0]

        def mock_post(url, json=None):
            resp = MagicMock()
            resp.ok = True
            chunk_ids = [r["id"] for r in json["requests"]]
            resp.content = (
                __import__("json").dumps(make_batch_response(chunk_ids)).encode()
            )
            call_count[0] += 1
            return resp

        mock_session.return_value.post.side_effect = mock_post

        result = get_checklist_items_batch("lid-1", task_ids)

        # Should have made 2 calls: 20 + 5
        self.assertEqual(call_count[0], 2)
        self.assertEqual(len(result), 25)
        for tid in task_ids:
            self.assertIn(tid, result)


if __name__ == "__main__":
    unittest.main()
