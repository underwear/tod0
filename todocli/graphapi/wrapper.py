"""
For implementation details, refer to this source:
https://docs.microsoft.com/en-us/graph/api/resources/todo-overview?view=graph-rest-1.0
"""

import json
from datetime import datetime
from typing import Union

from todocli.models.todolist import TodoList
from todocli.models.todotask import Task, TaskImportance, TaskStatus
from todocli.models.checklistitem import ChecklistItem
from todocli.graphapi.oauth import get_oauth_session

from todocli.utils.datetime_util import datetime_to_api_timestamp

BASE_API = "https://graph.microsoft.com/v1.0"
BASE_RELATE_URL = "/me/todo/lists"
BASE_URL = f"{BASE_API}{BASE_RELATE_URL}"
BATCH_URL = f"{BASE_API}/$batch"


def _require_list(list_name, list_id):
    """Validate that list_name or list_id is provided."""
    if list_name is None and list_id is None:
        raise ValueError("You must provide list_name or list_id")


def _require_task(task_name, task_id):
    """Validate that task_name or task_id is provided."""
    if task_name is None and task_id is None:
        raise ValueError("You must provide task_name or task_id")


def _require_step(step_name):
    """Validate that step_name is provided."""
    if step_name is None:
        raise ValueError("You must provide step_name")


class ListNotFound(Exception):
    def __init__(self, list_name):
        self.message = "List with name '{}' could not be found".format(list_name)
        super(ListNotFound, self).__init__(self.message)


class TaskNotFoundByName(Exception):
    def __init__(self, task_name, list_name):
        self.message = "Task with name '{}' could not be found in list '{}'".format(
            task_name, list_name
        )
        super(TaskNotFoundByName, self).__init__(self.message)


class TaskNotFoundByIndex(Exception):
    def __init__(self, task_index, list_name):
        self.message = "Task with index '{}' could not be found in list '{}'".format(
            task_index, list_name
        )
        super(TaskNotFoundByIndex, self).__init__(self.message)


class StepNotFoundByName(Exception):
    def __init__(self, step_name, task_name):
        self.message = "Step with name '{}' could not be found in task '{}'".format(
            step_name, task_name
        )
        super(StepNotFoundByName, self).__init__(self.message)


class StepNotFoundByIndex(Exception):
    def __init__(self, step_index, task_name):
        self.message = "Step with index '{}' could not be found in task '{}'".format(
            step_index, task_name
        )
        super(StepNotFoundByIndex, self).__init__(self.message)


def parse_response(response):
    return json.loads(response.content.decode())["value"]


def get_lists():
    session = get_oauth_session()
    response = session.get(BASE_URL)
    response_value = parse_response(response)
    return [TodoList(x) for x in response_value]


def create_list(title: str):
    """Create a new list. Returns (list_id, list_name)."""
    request_body = {"displayName": title}
    session = get_oauth_session()
    response = session.post(BASE_URL, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return data.get("id", ""), data.get("displayName", "")
    response.raise_for_status()


def rename_list(old_title: str, new_title: str):
    """Rename a list. Returns (list_id, new_title)."""
    list_id = get_list_id_by_name(old_title)
    request_body = {"displayName": new_title}
    session = get_oauth_session()
    response = session.patch(f"{BASE_URL}/{list_id}", json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return data.get("id", ""), data.get("displayName", "")
    response.raise_for_status()


def delete_list(list_name: str = None, list_id: str = None):
    """Delete a list. Returns list_id."""
    _require_list(list_name, list_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)

    endpoint = f"{BASE_URL}/{list_id}"
    session = get_oauth_session()
    response = session.delete(endpoint)
    if response.ok:
        return list_id
    response.raise_for_status()


def get_tasks(
    list_name: str = None,
    list_id: str = None,
    num_tasks: int = 100,
    include_completed: bool = False,
    only_completed: bool = False,
):
    """Fetch tasks from a list.

    Args:
        list_name: Name of the list
        list_id: ID of the list (alternative to list_name)
        num_tasks: Maximum number of tasks to return
        include_completed: If True, include completed tasks
        only_completed: If True, return only completed tasks
    """
    _require_list(list_name, list_id)

    # For compatibility with cli
    if list_id is None:
        list_id = get_list_id_by_name(list_name)

    if only_completed:
        endpoint = (
            f"{BASE_URL}/{list_id}/tasks?$filter=status eq 'completed'&$top={num_tasks}"
        )
    elif include_completed:
        endpoint = f"{BASE_URL}/{list_id}/tasks?$top={num_tasks}"
    else:
        endpoint = (
            f"{BASE_URL}/{list_id}/tasks?$filter=status ne 'completed'&$top={num_tasks}"
        )

    session = get_oauth_session()
    response = session.get(endpoint)
    response_value = parse_response(response)
    return [Task(x) for x in response_value]


def create_task(
    task_name: str,
    list_name: str | None = None,
    list_id: str | None = None,
    reminder_datetime: datetime | None = None,
    due_datetime: datetime | None = None,
    important: bool = False,
    recurrence: dict | None = None,
    note: str | None = None,
):
    _require_list(list_name, list_id)

    # For compatibility with cli
    if list_id is None:
        list_id = get_list_id_by_name(list_name)

    # The Graph API requires dueDateTime when recurrence is set
    if due_datetime is None and recurrence is not None:
        due_datetime = datetime.now()

    endpoint = f"{BASE_URL}/{list_id}/tasks"
    request_body = {
        "title": task_name,
        "reminderDateTime": datetime_to_api_timestamp(reminder_datetime),
        "dueDateTime": datetime_to_api_timestamp(due_datetime),
        "importance": TaskImportance.HIGH if important else TaskImportance.NORMAL,
        "recurrence": recurrence,
    }
    if note:
        request_body["body"] = {"content": note, "contentType": "text"}
    session = get_oauth_session()
    response = session.post(endpoint, json=request_body)
    if response.ok:
        return json.loads(response.content.decode())["id"]
    else:
        response.raise_for_status()


def complete_task(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    """Mark a task as completed. Returns (task_id, task_title)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    # For compatibility with cli
    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}"
    request_body = {
        "status": TaskStatus.COMPLETED,
        "completedDateTime": datetime_to_api_timestamp(datetime.now()),
    }
    session = get_oauth_session()
    response = session.patch(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return task_id, data.get("title", "")
    response.raise_for_status()


def uncomplete_task(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    """Mark a completed task as not completed. Returns (task_id, task_title)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}"
    request_body = {
        "status": TaskStatus.NOT_STARTED,
        "completedDateTime": None,
    }
    session = get_oauth_session()
    response = session.patch(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return task_id, data.get("title", "")
    response.raise_for_status()


def complete_tasks(list_id, task_ids=None):
    if task_ids is None:
        task_ids = []
    body = {"requests": []}
    for task_id in task_ids:
        body["requests"].append(
            {
                "id": task_id,
                "method": "PATCH",
                "url": f"{BASE_RELATE_URL}/{list_id}/tasks/{task_id}",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "status": TaskStatus.COMPLETED,
                    "completedDateTime": datetime_to_api_timestamp(datetime.now()),
                },
            }
        )
    session = get_oauth_session()
    response = session.post(BATCH_URL, json=body)
    return True if response.ok else response.raise_for_status()


def remove_task(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    """Delete a task. Returns (task_id, task_title)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    # Fetch task title before deletion
    task = get_task(list_id=list_id, task_id=task_id)
    task_title = task.title

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}"
    session = get_oauth_session()
    response = session.delete(endpoint)
    if response.ok:
        return task_id, task_title
    response.raise_for_status()


def update_task(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
    title: str | None = None,
    due_datetime: datetime | None = None,
    reminder_datetime: datetime | None = None,
    important: bool | None = None,
    recurrence: dict | None = None,
    clear_due: bool = False,
    clear_reminder: bool = False,
    clear_recurrence: bool = False,
):
    """Update a task. Returns (task_id, task_title)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    request_body = {}
    if title is not None:
        request_body["title"] = title
    if clear_due:
        request_body["dueDateTime"] = None
    elif due_datetime is not None:
        request_body["dueDateTime"] = datetime_to_api_timestamp(due_datetime)
    if clear_reminder:
        request_body["reminderDateTime"] = None
        request_body["isReminderOn"] = False
    elif reminder_datetime is not None:
        request_body["reminderDateTime"] = datetime_to_api_timestamp(reminder_datetime)
    if important is not None:
        request_body["importance"] = (
            TaskImportance.HIGH if important else TaskImportance.NORMAL
        )
    if clear_recurrence:
        request_body["recurrence"] = None
    elif recurrence is not None:
        request_body["recurrence"] = recurrence

    if not request_body:
        raise ValueError("No fields to update")

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}"
    session = get_oauth_session()
    response = session.patch(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return task_id, data.get("title", "")
    response.raise_for_status()


def get_list_id_by_name(list_name: str) -> str:
    """Get list ID by exact name match."""
    escaped_name = _escape_odata_string(list_name)
    endpoint = f"{BASE_URL}?$filter=displayName eq '{escaped_name}'"
    session = get_oauth_session()
    response = session.get(endpoint)
    response_value = parse_response(response)
    try:
        return response_value[0]["id"]
    except IndexError:
        raise ListNotFound(list_name)


def _escape_odata_string(value: str) -> str:
    """Escape a string for use in an OData $filter expression embedded in a URL.

    Single quotes are doubled per OData spec.

    Certain characters have special meaning in URLs and are not
    percent-encoded by the HTTP client when they appear in a
    raw query string:
      '#' — fragment identifier (truncates the URL)
      '&' — query-parameter separator
      '+' — interpreted as space in query strings

    These must be double-percent-encoded so that the first decode
    pass (HTTP/transport layer) yields the standard percent-encoded
    form, and the second pass (OData parser) yields the literal
    character.  E.g. '#' → '%2523' → '%23' → '#'.

    Reference: https://learn.microsoft.com/en-us/answers/questions/
    432875/how-do-you-escape-the-octothorpe-number-pound-hashtag-
    symbol-in-a-graph-api-odata-search-string
    """
    return (
        value.replace("'", "''")
        .replace("#", "%2523")
        .replace("&", "%2526")
        .replace("+", "%252B")
    )


def get_task_id_by_name(list_name: str, task_name: str):
    if isinstance(task_name, str):
        try:
            list_id = get_list_id_by_name(list_name)
            escaped_name = _escape_odata_string(task_name)
            endpoint = f"{BASE_URL}/{list_id}/tasks?$filter=title eq '{escaped_name}'"
            session = get_oauth_session()
            response = session.get(endpoint)
            response_value = parse_response(response)
            return [Task(x) for x in response_value][0].id
        except IndexError:
            raise TaskNotFoundByName(task_name, list_name)
    elif isinstance(task_name, int):
        tasks = get_tasks(list_name=list_name)
        try:
            return tasks[task_name].id
        except IndexError:
            raise TaskNotFoundByIndex(task_name, list_name)
    else:
        raise TypeError(f"task_name must be str or int, got {type(task_name).__name__}")


def get_task(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    """Fetch a single task with all details."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}"
    session = get_oauth_session()
    response = session.get(endpoint)
    if response.ok:
        return Task(json.loads(response.content.decode()))
    response.raise_for_status()


def get_checklist_items(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}/checklistItems"
    session = get_oauth_session()
    response = session.get(endpoint)
    response_value = parse_response(response)
    return [ChecklistItem(x) for x in response_value]


BATCH_MAX_REQUESTS = 20


def get_checklist_items_batch(list_id: str, task_ids: list[str]):
    """Fetch checklist items for multiple tasks using $batch API.

    Returns dict mapping task_id -> list[ChecklistItem].
    """
    if not task_ids:
        return {}

    result = {}
    session = get_oauth_session()

    # Chunk into groups of BATCH_MAX_REQUESTS
    for i in range(0, len(task_ids), BATCH_MAX_REQUESTS):
        chunk = task_ids[i : i + BATCH_MAX_REQUESTS]
        body = {
            "requests": [
                {
                    "id": task_id,
                    "method": "GET",
                    "url": f"{BASE_RELATE_URL}/{list_id}/tasks/{task_id}/checklistItems",
                }
                for task_id in chunk
            ]
        }
        response = session.post(BATCH_URL, json=body)
        if not response.ok:
            response.raise_for_status()

        batch_response = json.loads(response.content.decode())
        for resp in batch_response.get("responses", []):
            tid = resp["id"]
            if resp.get("status") == 200:
                items = resp.get("body", {}).get("value", [])
                result[tid] = [ChecklistItem(x) for x in items]
            else:
                result[tid] = []

    return result


def create_checklist_item(
    step_name: str,
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}/checklistItems"
    request_body = {"displayName": step_name}
    session = get_oauth_session()
    response = session.post(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return data.get("id", ""), data.get("displayName", "")
    response.raise_for_status()


def complete_checklist_item(
    list_name: str = None,
    task_name: Union[str, int] = None,
    step_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
    step_id: str = None,
):
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)
    if step_id is None:
        _require_step(step_name)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)
    if step_id is None:
        step_id = get_step_id(
            list_name, task_name, step_name, list_id=list_id, task_id=task_id
        )

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}/checklistItems/{step_id}"
    request_body = {"isChecked": True}
    session = get_oauth_session()
    response = session.patch(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return step_id, data.get("displayName", "")
    response.raise_for_status()


def uncomplete_checklist_item(
    list_name: str = None,
    task_name: Union[str, int] = None,
    step_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
    step_id: str = None,
):
    """Mark a checked step as unchecked."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)
    if step_id is None:
        _require_step(step_name)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)
    if step_id is None:
        step_id = get_step_id(
            list_name, task_name, step_name, list_id=list_id, task_id=task_id
        )

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}/checklistItems/{step_id}"
    request_body = {"isChecked": False}
    session = get_oauth_session()
    response = session.patch(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return step_id, data.get("displayName", "")
    response.raise_for_status()


def delete_checklist_item(
    list_name: str = None,
    task_name: Union[str, int] = None,
    step_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
    step_id: str = None,
):
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)
    if step_id is None:
        _require_step(step_name)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)
    if step_id is None:
        step_id = get_step_id(
            list_name, task_name, step_name, list_id=list_id, task_id=task_id
        )

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}/checklistItems/{step_id}"
    session = get_oauth_session()
    response = session.delete(endpoint)
    if response.ok:
        return step_id
    response.raise_for_status()


def get_step_id(
    list_name: str,
    task_name: Union[str, int],
    step_name: Union[str, int],
    list_id: str = None,
    task_id: str = None,
):
    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    items = get_checklist_items(list_id=list_id, task_id=task_id)

    if isinstance(step_name, int):
        try:
            return items[step_name].id
        except IndexError:
            raise StepNotFoundByIndex(step_name, task_name)
    elif isinstance(step_name, str):
        for item in items:
            if item.display_name == step_name:
                return item.id
        raise StepNotFoundByName(step_name, task_name)
    else:
        raise TypeError(f"step_name must be str or int, got {type(step_name).__name__}")


# --- Note functions ---


def update_task_note(
    note_content: str,
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
    content_type: str = "text",
):
    """Update the note (body) of a task. Returns (task_id, task_title, note_content)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}"
    request_body = {
        "body": {
            "content": note_content,
            "contentType": content_type,
        }
    }
    session = get_oauth_session()
    response = session.patch(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        body = data.get("body", {})
        return task_id, data.get("title", ""), body.get("content", "")
    response.raise_for_status()


def clear_task_note(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    """Clear the note (body) of a task. Returns (task_id, task_title)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}"
    request_body = {
        "body": {
            "content": "",
            "contentType": "text",
        }
    }
    session = get_oauth_session()
    response = session.patch(endpoint, json=request_body)
    if response.ok:
        data = json.loads(response.content.decode())
        return task_id, data.get("title", "")
    response.raise_for_status()


# --- My Day functions ---

MY_DAY_APP_NAME = "microsoft-todo-cli"
MY_DAY_EXTERNAL_ID = "my-day"
MY_DAY_DISPLAY_NAME = "My Day"
MY_DAY_WEB_URL = "todocli://my-day"


def _get_my_day_linked_resource(list_id: str, task_id: str):
    """Check if a task has a My Day linked resource. Returns the resource or None."""
    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}/linkedResources"
    session = get_oauth_session()
    response = session.get(endpoint)
    if response.ok:
        resources = json.loads(response.content.decode()).get("value", [])
        for r in resources:
            if (
                r.get("applicationName") == MY_DAY_APP_NAME
                and r.get("externalId") == MY_DAY_EXTERNAL_ID
            ):
                return r
    return None


def add_to_my_day(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    """Add a task to My Day by creating a linked resource. Returns (task_id, task_title)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    # Check if already in My Day
    existing = _get_my_day_linked_resource(list_id, task_id)
    if existing:
        # Already in My Day, get task title
        task = get_task(list_id=list_id, task_id=task_id)
        return task_id, task.title, True  # already_existed=True

    endpoint = f"{BASE_URL}/{list_id}/tasks/{task_id}/linkedResources"
    request_body = {
        "webUrl": MY_DAY_WEB_URL,
        "applicationName": MY_DAY_APP_NAME,
        "displayName": MY_DAY_DISPLAY_NAME,
        "externalId": MY_DAY_EXTERNAL_ID,
    }
    session = get_oauth_session()
    response = session.post(endpoint, json=request_body)
    if response.ok:
        task = get_task(list_id=list_id, task_id=task_id)
        return task_id, task.title, False  # already_existed=False
    response.raise_for_status()


def remove_from_my_day(
    list_name: str = None,
    task_name: Union[str, int] = None,
    list_id: str = None,
    task_id: str = None,
):
    """Remove a task from My Day by deleting its linked resource. Returns (task_id, task_title)."""
    _require_list(list_name, list_id)
    _require_task(task_name, task_id)

    if list_id is None:
        list_id = get_list_id_by_name(list_name)
    if task_id is None:
        task_id = get_task_id_by_name(list_name, task_name)

    existing = _get_my_day_linked_resource(list_id, task_id)
    task = get_task(list_id=list_id, task_id=task_id)
    if not existing:
        return task_id, task.title, False  # was_in_my_day=False

    lr_id = existing["id"]
    endpoint = (
        f"{BASE_URL}/{list_id}/tasks/{task_id}/linkedResources/{lr_id}"
    )
    session = get_oauth_session()
    response = session.delete(endpoint)
    if response.ok:
        return task_id, task.title, True  # was_in_my_day=True
    response.raise_for_status()


def get_my_day_tasks():
    """Get all tasks marked as My Day across all lists.

    Returns list of (list_id, list_name, task) tuples.
    Uses batch API to check linked resources efficiently.
    """
    session = get_oauth_session()

    # Get all lists
    lists = get_lists()

    my_day_tasks = []

    for lst in lists:
        list_id = lst.id
        list_name = lst.display_name

        # Get incomplete tasks from this list
        tasks = get_tasks(list_id=list_id, include_completed=False)
        if not tasks:
            continue

        # Batch check linked resources for all tasks
        # We need to check each task's linked resources
        for i in range(0, len(tasks), BATCH_MAX_REQUESTS):
            chunk = tasks[i : i + BATCH_MAX_REQUESTS]
            body = {
                "requests": [
                    {
                        "id": task.id,
                        "method": "GET",
                        "url": f"{BASE_RELATE_URL}/{list_id}/tasks/{task.id}/linkedResources",
                    }
                    for task in chunk
                ]
            }
            response = session.post(BATCH_URL, json=body)
            if not response.ok:
                response.raise_for_status()

            batch_response = json.loads(response.content.decode())
            # Build a set of task IDs that have My Day linked resource
            my_day_task_ids = set()
            for resp in batch_response.get("responses", []):
                if resp.get("status") == 200:
                    resources = resp.get("body", {}).get("value", [])
                    for r in resources:
                        if (
                            r.get("applicationName") == MY_DAY_APP_NAME
                            and r.get("externalId") == MY_DAY_EXTERNAL_ID
                        ):
                            my_day_task_ids.add(resp["id"])
                            break

            for task in chunk:
                if task.id in my_day_task_ids:
                    my_day_tasks.append((list_id, list_name, task))

    return my_day_tasks
