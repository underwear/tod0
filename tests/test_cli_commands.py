#!/usr/bin/env python3
"""Unit tests for CLI command parsing and argument handling"""

import unittest
from todocli.cli import (
    setup_parser,
    parse_task_path,
    try_parse_as_int,
)


class TestCLIArgumentParsing(unittest.TestCase):
    """Test argparse setup for all commands"""

    def setUp(self):
        self.parser = setup_parser()

    def test_ls_command(self):
        """Test 'ls' command parsing"""
        args = self.parser.parse_args(["ls"])
        self.assertTrue(hasattr(args, "func"))
        self.assertIsNotNone(args.func)

    def test_lst_command_with_list(self):
        """Test 'lst' command with list name"""
        args = self.parser.parse_args(["lst", "personal"])
        self.assertEqual(args.list_name, "personal")

    def test_lst_command_default_list(self):
        """Test 'lst' command defaults to 'Tasks'"""
        args = self.parser.parse_args(["lst"])
        self.assertEqual(args.list_name, "Tasks")

    def test_new_command_basic(self):
        """Test 'new' command with task name"""
        args = self.parser.parse_args(["new", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertIsNone(args.reminder)
        self.assertIsNone(getattr(args, "list", None))

    def test_new_command_with_reminder(self):
        """Test 'new' command with -r flag"""
        args = self.parser.parse_args(["new", "-r", "9:00", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.reminder, "9:00")

    def test_new_command_with_list_flag(self):
        """Test 'new' command with --list flag"""
        args = self.parser.parse_args(["new", "--list", "personal", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.list, "personal")

    def test_new_command_with_short_list_flag(self):
        """Test 'new' command with -l flag"""
        args = self.parser.parse_args(["new", "-l", "work", "task"])
        self.assertEqual(args.task_name, "task")
        self.assertEqual(args.list, "work")

    def test_new_command_with_all_flags(self):
        """Test 'new' command with both -l and -r flags"""
        args = self.parser.parse_args(
            ["new", "-l", "personal", "-r", "9:00", "buy milk"]
        )
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.list, "personal")
        self.assertEqual(args.reminder, "9:00")

    def test_new_command_with_important(self):
        """Test 'new' command with -I flag"""
        args = self.parser.parse_args(["new", "-I", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertTrue(args.important)

    def test_new_command_with_important_long(self):
        """Test 'new' command with --important flag"""
        args = self.parser.parse_args(["new", "--important", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertTrue(args.important)

    def test_new_command_without_important(self):
        """Test 'new' command defaults important to False"""
        args = self.parser.parse_args(["new", "buy milk"])
        self.assertFalse(args.important)

    def test_new_command_with_due(self):
        """Test 'new' command with -d flag"""
        args = self.parser.parse_args(["new", "-d", "tomorrow", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.due, "tomorrow")

    def test_new_command_with_due_long(self):
        """Test 'new' command with --due flag"""
        args = self.parser.parse_args(["new", "--due", "2026-01-15", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.due, "2026-01-15")

    def test_new_command_with_recurrence(self):
        """Test 'new' command with -R flag"""
        args = self.parser.parse_args(["new", "-R", "daily", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.recurrence, "daily")

    def test_new_command_with_recurrence_long(self):
        """Test 'new' command with --recurrence flag"""
        args = self.parser.parse_args(["new", "--recurrence", "weekly", "buy milk"])
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.recurrence, "weekly")

    def test_new_command_without_recurrence(self):
        """Test 'new' command defaults recurrence to None"""
        args = self.parser.parse_args(["new", "buy milk"])
        self.assertIsNone(args.recurrence)

    def test_new_command_with_step_flag(self):
        """Test 'new' command with -S flag (repeatable)"""
        args = self.parser.parse_args(
            ["new", "-S", "milk", "-S", "eggs", "buy groceries"]
        )
        self.assertEqual(args.task_name, "buy groceries")
        self.assertEqual(args.step, ["milk", "eggs"])

    def test_new_command_with_step_long_flag(self):
        """Test 'new' command with --step flag"""
        args = self.parser.parse_args(["new", "--step", "milk", "buy groceries"])
        self.assertEqual(args.step, ["milk"])

    def test_new_command_without_steps(self):
        """Test 'new' command defaults step to empty list"""
        args = self.parser.parse_args(["new", "buy milk"])
        self.assertEqual(args.step, [])

    def test_new_command_with_all_flags(self):
        """Test 'new' command with all flags"""
        args = self.parser.parse_args(
            [
                "new",
                "-l",
                "personal",
                "-r",
                "9:00",
                "-d",
                "tomorrow",
                "-I",
                "-R",
                "daily",
                "buy milk",
            ]
        )
        self.assertEqual(args.task_name, "buy milk")
        self.assertEqual(args.list, "personal")
        self.assertEqual(args.reminder, "9:00")
        self.assertEqual(args.due, "tomorrow")
        self.assertTrue(args.important)
        self.assertEqual(args.recurrence, "daily")

    def test_newl_command(self):
        """Test 'newl' command for creating lists"""
        args = self.parser.parse_args(["newl", "shopping"])
        self.assertEqual(args.list_name, "shopping")

    def test_new_list_command(self):
        """Test 'new-list' command (primary name for creating lists)"""
        args = self.parser.parse_args(["new-list", "work"])
        self.assertEqual(args.list_name, "work")

    def test_new_with_json_flag(self):
        """Test 'new' command with --json flag"""
        args = self.parser.parse_args(["new", "--json", "buy milk"])
        self.assertTrue(args.json)

    def test_complete_with_json_flag(self):
        """Test 'complete' command with --json flag"""
        args = self.parser.parse_args(["complete", "-j", "task"])
        self.assertTrue(args.json)

    def test_rm_with_json_flag(self):
        """Test 'rm' command with --json flag"""
        args = self.parser.parse_args(["rm", "--json", "-y", "task"])
        self.assertTrue(args.json)

    def test_update_with_json_flag(self):
        """Test 'update' command with --json flag"""
        args = self.parser.parse_args(["update", "-j", "task", "--title", "new"])
        self.assertTrue(args.json)

    def test_complete_command_basic(self):
        """Test 'complete' command"""
        args = self.parser.parse_args(["complete", "task"])
        self.assertEqual(args.task_names, ["task"])
        self.assertIsNone(getattr(args, "list", None))

    def test_complete_command_with_list(self):
        """Test 'complete' command with --list flag"""
        args = self.parser.parse_args(["complete", "--list", "personal", "task"])
        self.assertEqual(args.task_names, ["task"])
        self.assertEqual(args.list, "personal")

    def test_complete_command_multiple_tasks(self):
        """Test 'complete' command with multiple tasks"""
        args = self.parser.parse_args(["complete", "task1", "task2", "task3"])
        self.assertEqual(args.task_names, ["task1", "task2", "task3"])

    def test_rm_command_basic(self):
        """Test 'rm' command"""
        args = self.parser.parse_args(["rm", "task"])
        self.assertEqual(args.task_names, ["task"])

    def test_rm_command_with_list(self):
        """Test 'rm' command with -l flag"""
        args = self.parser.parse_args(["rm", "-l", "work", "task"])
        self.assertEqual(args.task_names, ["task"])
        self.assertEqual(args.list, "work")

    def test_rm_command_multiple_tasks(self):
        """Test 'rm' command with multiple tasks"""
        args = self.parser.parse_args(["rm", "task1", "task2"])
        self.assertEqual(args.task_names, ["task1", "task2"])

    def test_rm_command_yes_flag(self):
        """Test 'rm' command with -y/--yes flag"""
        args = self.parser.parse_args(["rm", "-y", "task"])
        self.assertTrue(args.yes)

        args = self.parser.parse_args(["rm", "--yes", "task"])
        self.assertTrue(args.yes)

    def test_interactive_flag(self):
        """Test -i/--interactive flag"""
        args = self.parser.parse_args(["-i", "ls"])
        self.assertTrue(args.interactive)

        args = self.parser.parse_args(["--interactive", "ls"])
        self.assertTrue(args.interactive)

    def test_lst_date_format_flag(self):
        """Test lst command with --date-format flag"""
        args = self.parser.parse_args(["lst", "--date-format", "iso"])
        self.assertEqual(args.date_format, "iso")

        args = self.parser.parse_args(["lst", "--date-format", "us"])
        self.assertEqual(args.date_format, "us")

        args = self.parser.parse_args(["lst", "--date-format", "eu"])
        self.assertEqual(args.date_format, "eu")

    def test_lst_date_format_default(self):
        """Test lst command defaults date-format to eu"""
        args = self.parser.parse_args(["lst"])
        self.assertEqual(args.date_format, "eu")

    def test_complete_with_id_flag(self):
        """Test 'complete' command with --id flag"""
        args = self.parser.parse_args(["complete", "--id", "AAMkABC123"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertEqual(args.task_names, [])

    def test_complete_with_id_and_list_flag(self):
        """Test 'complete' command with --id and -l flags"""
        args = self.parser.parse_args(["complete", "--id", "AAMkABC123", "-l", "Work"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertEqual(args.list, "Work")

    def test_rm_with_id_flag(self):
        """Test 'rm' command with --id flag"""
        args = self.parser.parse_args(["rm", "--id", "AAMkABC123", "-y"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertTrue(args.yes)

    def test_show_with_id_flag(self):
        """Test 'show' command with --id flag"""
        args = self.parser.parse_args(["show", "--id", "AAMkABC123"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertIsNone(args.task_name)

    def test_update_with_id_flag(self):
        """Test 'update' command with --id flag"""
        args = self.parser.parse_args(
            ["update", "--id", "AAMkABC123", "--title", "New"]
        )
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertEqual(args.title, "New")

    def test_list_steps_with_id_flag(self):
        """Test 'list-steps' command with --id flag"""
        args = self.parser.parse_args(["list-steps", "--id", "AAMkABC123"])
        self.assertEqual(args.task_id, "AAMkABC123")

    def test_new_step_with_id_flag(self):
        """Test 'new-step' command with --id flag"""
        args = self.parser.parse_args(["new-step", "--id", "AAMkABC123", "Step 1"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertEqual(args.step_name, "Step 1")

    def test_complete_step_with_id_flag(self):
        """Test 'complete-step' command with --id flag"""
        args = self.parser.parse_args(["complete-step", "--id", "AAMkABC123", "0"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertEqual(args.step_name, "0")

    def test_rm_step_with_id_flag(self):
        """Test 'rm-step' command with --id flag"""
        args = self.parser.parse_args(["rm-step", "--id", "AAMkABC123", "0"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertEqual(args.step_name, "0")

    def test_tasks_all_flag(self):
        """Test 'tasks' command with --all flag"""
        args = self.parser.parse_args(["tasks", "--all"])
        self.assertTrue(args.all)

    def test_tasks_completed_flag(self):
        """Test 'tasks' command with --completed flag"""
        args = self.parser.parse_args(["tasks", "--completed"])
        self.assertTrue(args.completed)

    def test_uncomplete_command_basic(self):
        """Test 'uncomplete' command"""
        args = self.parser.parse_args(["uncomplete", "task"])
        self.assertEqual(args.task_names, ["task"])

    def test_uncomplete_with_id_flag(self):
        """Test 'uncomplete' command with --id flag"""
        args = self.parser.parse_args(["uncomplete", "--id", "AAMkABC123"])
        self.assertEqual(args.task_id, "AAMkABC123")

    def test_uncomplete_step_command_basic(self):
        """Test 'uncomplete-step' command"""
        args = self.parser.parse_args(["uncomplete-step", "task", "0"])
        self.assertEqual(args.task_name, "task")
        self.assertEqual(args.step_name, "0")

    def test_uncomplete_step_with_id_flag(self):
        """Test 'uncomplete-step' command with --id flag"""
        args = self.parser.parse_args(["uncomplete-step", "--id", "AAMkABC123", "0"])
        self.assertEqual(args.task_id, "AAMkABC123")
        self.assertEqual(args.step_name, "0")


class TestParseTaskPath(unittest.TestCase):
    """Test parse_task_path function"""

    def test_simple_task_name(self):
        """Test task name without list defaults to 'Tasks'"""
        list_name, task_name = parse_task_path("buy milk")
        self.assertEqual(list_name, "Tasks")
        self.assertEqual(task_name, "buy milk")

    def test_task_with_explicit_list(self):
        """Test task with explicit list_name parameter"""
        list_name, task_name = parse_task_path("buy milk", list_name="work")
        self.assertEqual(list_name, "work")
        self.assertEqual(task_name, "buy milk")

    def test_task_with_slashes_no_autoparsing(self):
        """Test that slashes are NOT auto-parsed as list separator"""
        list_name, task_name = parse_task_path("personal/buy milk")
        self.assertEqual(list_name, "Tasks")
        self.assertEqual(task_name, "personal/buy milk")

    def test_url_as_task_name(self):
        """Test URL as task name works without special handling"""
        list_name, task_name = parse_task_path("https://www.google.com/")
        self.assertEqual(list_name, "Tasks")
        self.assertEqual(task_name, "https://www.google.com/")

    def test_url_with_explicit_list(self):
        """Test URL task name with explicit list"""
        list_name, task_name = parse_task_path(
            "https://example.com/path/to/page", list_name="work"
        )
        self.assertEqual(list_name, "work")
        self.assertEqual(task_name, "https://example.com/path/to/page")

    def test_empty_task_name(self):
        """Test empty task name"""
        list_name, task_name = parse_task_path("")
        self.assertEqual(list_name, "Tasks")
        self.assertEqual(task_name, "")

    def test_special_characters_in_task_name(self):
        """Test task names with special characters"""
        list_name, task_name = parse_task_path("check A/B testing")
        self.assertEqual(list_name, "Tasks")
        self.assertEqual(task_name, "check A/B testing")


class TestTryParseAsInt(unittest.TestCase):
    """Test try_parse_as_int helper function"""

    def test_valid_integer_string(self):
        """Test parsing valid integer string"""
        result = try_parse_as_int("42")
        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)

    def test_zero(self):
        """Test parsing zero"""
        result = try_parse_as_int("0")
        self.assertEqual(result, 0)

    def test_negative_integer(self):
        """Test parsing negative integer"""
        result = try_parse_as_int("-5")
        self.assertEqual(result, -5)

    def test_non_integer_string(self):
        """Test that non-integer strings are returned as-is"""
        result = try_parse_as_int("buy milk")
        self.assertEqual(result, "buy milk")
        self.assertIsInstance(result, str)

    def test_float_string(self):
        """Test that float strings are returned as-is"""
        result = try_parse_as_int("3.14")
        self.assertEqual(result, "3.14")
        self.assertIsInstance(result, str)

    def test_empty_string(self):
        """Test empty string"""
        result = try_parse_as_int("")
        self.assertEqual(result, "")

    def test_mixed_alphanumeric(self):
        """Test mixed alphanumeric string"""
        result = try_parse_as_int("task123")
        self.assertEqual(result, "task123")


if __name__ == "__main__":
    unittest.main()
