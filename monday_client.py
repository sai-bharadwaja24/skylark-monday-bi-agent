"""
monday.com API client.

Design decision (see DECISION_LOG.md): rather than hardcoding monday.com's
internal column IDs (which are opaque, per-account strings like "text_1__1"
and differ every time a board is recreated), we fetch each board's column
*titles* at query time and match on title. This means the exact same code
works against anyone's re-import of the two boards, as long as the column
headers roughly match the source spreadsheets - no redeploy needed if a
board gets rebuilt.

All data is fetched live on every call (no caching across process restarts,
no bundled CSV/JSON snapshot) - satisfies the "must query monday.com
dynamically" requirement.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

MONDAY_API_URL = "https://api.monday.com/v2"
API_VERSION = "2024-01"  # items_page / next_items_page require a recent version


class MondayAPIError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        raise MondayAPIError(
            "MONDAY_API_TOKEN is not set. Set it as an environment variable "
            "or Streamlit secret - never hardcode it in source."
        )
    return token


def _post(query: str, variables: dict | None = None, retries: int = 3) -> dict:
    headers = {
        "Authorization": _token(),
        "Content-Type": "application/json",
        "API-Version": API_VERSION,
    }
    payload = {"query": query, "variables": variables or {}}

    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(MONDAY_API_URL, json=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
            continue

        if resp.status_code == 429:
            # rate limited - back off and retry
            time.sleep(2 * (attempt + 1))
            continue

        if resp.status_code != 200:
            raise MondayAPIError(f"monday.com API HTTP {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        if "errors" in data:
            raise MondayAPIError(f"monday.com API error: {data['errors']}")
        return data["data"]

    raise MondayAPIError(f"monday.com API request failed after {retries} retries: {last_err}")


def get_board_schema(board_id: str) -> dict[str, Any]:
    """Return board name + list of {id, title, type} for its columns."""
    query = """
    query ($boardId: [ID!]) {
      boards(ids: $boardId) {
        id
        name
        columns { id title type }
      }
    }
    """
    data = _post(query, {"boardId": [board_id]})
    boards = data.get("boards") or []
    if not boards:
        raise MondayAPIError(f"Board {board_id} not found or token lacks access.")
    return boards[0]


def get_board_items(board_id: str) -> list[dict[str, Any]]:
    """
    Fetch every item on a board with its column values, resolved to
    {column_title: display_text} dicts. Handles pagination via cursor.
    """
    board = get_board_schema(board_id)
    col_title_by_id = {c["id"]: c["title"] for c in board["columns"]}

    query = """
    query ($boardId: ID!, $cursor: String) {
      boards(ids: [$boardId]) {
        items_page(limit: 100, cursor: $cursor) {
          cursor
          items {
            id
            name
            column_values {
              id
              text
              value
            }
          }
        }
      }
    }
    """

    items: list[dict[str, Any]] = []
    cursor = None
    while True:
        data = _post(query, {"boardId": board_id, "cursor": cursor})
        page = data["boards"][0]["items_page"]
        for raw_item in page["items"]:
            record: dict[str, Any] = {"_item_id": raw_item["id"], "Name": raw_item["name"]}
            for cv in raw_item["column_values"]:
                title = col_title_by_id.get(cv["id"], cv["id"])
                record[title] = cv["text"]
            items.append(record)
        cursor = page.get("cursor")
        if not cursor:
            break

    return items


def list_accessible_boards() -> list[dict[str, str]]:
    """Utility for setup/debugging: list boards the token can see."""
    query = """
    query {
      boards(limit: 100) { id name }
    }
    """
    data = _post(query)
    return data.get("boards", [])
