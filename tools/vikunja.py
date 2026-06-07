# Based on: Vikunja Task Manager OpenWebUI tool
# Original source: https://openwebui.com/posts/642c2f8b-f3b9-4745-b060-4da040829a04

import os
from datetime import datetime

import httpx

from mcp_server.server import mcp

_API_URL = os.environ.get("VIKUNJA_API_URL", "")
_API_KEY = os.environ.get("VIKUNJA_API_KEY", "")
DEFAULT_LIST_ID = os.environ.get("VIKUNJA_DEFAULT_LIST_ID", "1")

REPEAT_MODE_MAP = {0: "from_start_date", 1: "monthly", 2: "from_done_date"}
REPEAT_MODE_MAP_INV = {v: k for k, v in REPEAT_MODE_MAP.items()}


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=_API_URL,
        headers={"Authorization": f"Bearer {_API_KEY}"},
    )


def _parse_date(s: str | None) -> str | None:
    return s if s else None


def _task(data: dict) -> dict:
    return {k: v for k, v in {
        "id": str(data["id"]),
        "list_id": str(data["project_id"]),
        "title": data.get("title"),
        "description": data.get("description") or None,
        "is_done": data.get("done", False),
        "priority": data.get("priority") or None,
        "percent_done": data.get("percent_done") or None,
        "due_date": _parse_date(data.get("due_date")),
        "start_date": _parse_date(data.get("start_date")),
        "end_date": _parse_date(data.get("end_date")),
        "is_favorite": data.get("is_favorite"),
        "is_archived": data.get("is_archived"),
        "repeat_mode": REPEAT_MODE_MAP.get(data.get("repeat_mode")),
        "repeat_after": data.get("repeat_after") or None,
        "labels": [{"id": l["id"], "title": l["title"]} for l in (data.get("labels") or [])],
        "assignees": [a["username"] for a in (data.get("assignees") or [])],
    }.items() if v is not None}


def _project(data: dict) -> dict:
    return {k: v for k, v in {
        "id": str(data["id"]),
        "title": data.get("title"),
        "description": data.get("description") or None,
        "is_favorite": data.get("is_favorite"),
        "is_archived": data.get("is_archived"),
    }.items() if v is not None}


# --- Lists ---

@mcp.tool()
def list_lists() -> list[dict]:
    """List all projects/lists."""
    with _client() as c:
        r = c.get("/projects")
        r.raise_for_status()
        return [_project(p) for p in r.json()]


@mcp.tool()
def find_list_by_title(title: str) -> list[dict]:
    """Find lists by partial title match (case-insensitive)."""
    with _client() as c:
        r = c.get("/projects")
        r.raise_for_status()
        return [_project(p) for p in r.json() if title.lower() in p["title"].lower()]


@mcp.tool()
def create_list(title: str, description: str | None = None) -> dict:
    """Create a new list/project."""
    with _client() as c:
        r = c.put("/projects", json={"title": title, "description": description})
        r.raise_for_status()
        return _project(r.json())


@mcp.tool()
def delete_list(list_id: str) -> dict:
    """Delete a list and all its tasks."""
    with _client() as c:
        r = c.delete(f"/projects/{list_id}")
        r.raise_for_status()
        return {"id": list_id, "deleted": True}


# --- Labels ---

@mcp.tool()
def list_labels() -> list[dict]:
    """List all available labels/tags."""
    with _client() as c:
        r = c.get("/labels")
        r.raise_for_status()
        return [{"id": l["id"], "title": l["title"], "hex_color": l.get("hex_color")} for l in r.json()]


# --- Tasks ---

@mcp.tool()
def list_tasks(
    list_id: str | None = None,
    search: str | None = None,
    is_done: bool | None = False,
    is_favorite: bool | None = None,
    min_priority: int | None = None,
    sort_by: str | None = None,
    order_by: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> list[dict]:
    """List tasks with optional filters. By default only returns incomplete tasks (is_done=False). Pass is_done=null to get all."""
    params = []
    filter_parts = []

    if list_id:
        filter_parts.append(f"project_id = {list_id}")
    if is_done is not None:
        filter_parts.append(f"done = {'true' if is_done else 'false'}")
    if min_priority is not None:
        filter_parts.append(f"priority >= {min_priority}")
    if filter_parts:
        params.append(("filter", " && ".join(filter_parts)))
    if search:
        params.append(("s", search))
    if sort_by:
        params.append(("sort_by", sort_by))
        params.append(("order_by", order_by or "desc"))
    if page:
        params.append(("page", str(page)))
    if page_size:
        params.append(("per_page", str(page_size)))

    endpoint = f"/projects/{list_id}/tasks" if list_id else "/tasks"
    with _client() as c:
        r = c.get(endpoint, params=params)
        r.raise_for_status()
        tasks = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
        result = [_task(t) for t in tasks]
        if is_favorite is not None:
            result = [t for t in result if t.get("is_favorite") == is_favorite]
        return result


@mcp.tool()
def get_task(task_id: str) -> dict:
    """Get details of a specific task."""
    with _client() as c:
        r = c.get(f"/tasks/{task_id}")
        r.raise_for_status()
        return _task(r.json())


@mcp.tool()
def find_task_by_title(title: str, list_id: str | None = None) -> list[dict]:
    """Find tasks by partial title match. Use this to resolve a task name to an ID."""
    return list_tasks(list_id=list_id, search=title)


@mcp.tool()
def create_task(
    title: str,
    list_id: str | None = None,
    description: str | None = None,
    priority: int | None = None,
    percent_done: float | None = None,
    due_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    is_done: bool = False,
    is_favorite: bool = False,
    label_ids: list[int] | None = None,
) -> dict:
    """
    Create a new task. list_id defaults to VIKUNJA_DEFAULT_LIST_ID.
    Dates must be ISO 8601 with timezone (e.g. 2026-06-01T09:00:00+02:00).
    """
    resolved = list_id or DEFAULT_LIST_ID
    payload: dict = {"title": title, "done": is_done, "is_favorite": is_favorite}
    if description is not None:
        payload["description"] = description
    if priority is not None:
        payload["priority"] = priority
    if percent_done is not None:
        payload["percent_done"] = percent_done
    if due_date:
        payload["due_date"] = due_date
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date

    with _client() as c:
        r = c.put(f"/projects/{resolved}/tasks", json=payload)
        r.raise_for_status()
        created = _task(r.json())
        task_id = created["id"]
        if label_ids:
            for lid in label_ids:
                c.put(f"/tasks/{task_id}/labels", json={"label_id": lid}).raise_for_status()
            created = _task(c.get(f"/tasks/{task_id}").json())
        return created


@mcp.tool()
def update_task(task_id: str, changes: dict) -> dict:
    """
    Update fields of a task. Only provided fields are changed.
    Supports: title, description, is_done, priority, percent_done, due_date,
    start_date, end_date, hex_color, is_favorite, is_archived.
    Pass label_ids (list[int]) to replace all labels.
    Dates must be ISO 8601 with timezone.
    """
    with _client() as c:
        # Fetch current task to avoid clobbering fields
        r = c.get(f"/tasks/{task_id}")
        r.raise_for_status()
        current = r.json()

        label_ids = changes.pop("label_ids", None)

        field_map = {
            "title": "title", "description": "description", "is_done": "done",
            "priority": "priority", "percent_done": "percent_done",
            "due_date": "due_date", "start_date": "start_date", "end_date": "end_date",
            "hex_color": "hex_color", "is_favorite": "is_favorite", "is_archived": "is_archived",
        }
        payload = {
            "title": current["title"],
            "done": current.get("done", False),
            "project_id": current["project_id"],
        }
        for our_key, api_key in field_map.items():
            if our_key in changes:
                payload[api_key] = changes[our_key]

        r = c.post(f"/tasks/{task_id}", json=payload)
        r.raise_for_status()
        updated = _task(r.json())

        if label_ids is not None:
            # Remove existing labels
            existing = c.get(f"/tasks/{task_id}/labels").json()
            for lbl in (existing if isinstance(existing, list) else []):
                c.delete(f"/tasks/{task_id}/labels/{lbl['id']}")
            for lid in label_ids:
                c.put(f"/tasks/{task_id}/labels", json={"label_id": lid}).raise_for_status()
            updated = _task(c.get(f"/tasks/{task_id}").json())

        return updated


@mcp.tool()
def delete_task(task_id: str) -> dict:
    """Delete a task."""
    with _client() as c:
        r = c.delete(f"/tasks/{task_id}")
        r.raise_for_status()
        return {"id": task_id, "deleted": True}
