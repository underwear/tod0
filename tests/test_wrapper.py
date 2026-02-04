#!/usr/bin/env python3
"""Unit tests for graph API wrapper module"""

import unittest
from unittest.mock import patch, MagicMock
from todocli.graphapi.wrapper import (
    ListNotFound,
    TaskNotFoundByName,
    TaskNotFoundByIndex,
    StepNotFoundByIndex,
    StepNotFoundByName,
    BASE_URL,
    BATCH_URL,
    get_task_id_by_name,
    get_step_id,
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
    def test_get_task_id_by_name_with_invalid_index(self, mock_get_list_id, mock_get_tasks):
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


if __name__ == "__main__":
    unittest.main()
