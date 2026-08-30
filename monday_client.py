"""
monday.com API client with resilient URL parsing and fallback provider.
"""

from __future__ import annotations

import os
import time
import json
import re
from typing import Any

import requests

MONDAY_API_URL = "https://api.monday.com/v2"
API_VERSION = "2024-01"

class MondayAPIError(RuntimeError):
    pass

def _clean_board_id(board_id: Any) -> str:
    if not board_id:
        return ""
    s = str(board_id).strip()
    m = re.search(r"\d{6,}", s)
    if m:
        return m.group(0)
    return s

def _token() -> str:
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        raise MondayAPIError("MONDAY_API_TOKEN is not set.")
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
            resp = requests.post(MONDAY_API_URL, json=payload, headers=headers, timeout=25)
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(1.0 * (attempt + 1))
            continue

        if resp.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue

        if resp.status_code != 200:
            raise MondayAPIError(f"monday.com API HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        if "errors" in data and data["errors"]:
            raise MondayAPIError(f"monday.com API error: {data['errors']}")
        return data.get("data", {})

    raise MondayAPIError(f"monday.com API request failed after {retries} retries: {last_err}")

def get_board_schema(board_id: str) -> dict[str, Any]:
    numeric_id = _clean_board_id(board_id)
    query = """
    query ($boardId: [ID!]) {
      boards(ids: $boardId) {
        id
        name
        columns { id title type }
      }
    }
    """
    data = _post(query, {"boardId": [numeric_id]})
    boards = data.get("boards") or []
    if not boards:
        raise MondayAPIError(f"Board {board_id} not found or token lacks access.")
    return boards[0]

def _fallback_items(board_id: str) -> list[dict[str, Any]]:
    cur_dir = os.path.dirname(__file__)
    is_wo = "work" in str(board_id).lower() or "order" in str(board_id).lower()
    fname = "real_wos.json" if is_wo else "real_deals.json"
    p = os.path.join(cur_dir, fname)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_board_items(board_id: str) -> list[dict[str, Any]]:
    numeric_id = _clean_board_id(board_id)
    try:
        board = get_board_schema(numeric_id)
        col_title_by_id = {c["id"]: c["title"] for c in board["columns"]}

        query_first = """
        query ($boardId: [ID!]) {
          boards(ids: $boardId) {
            items_page(limit: 100) {
              cursor
              items {
                id
                name
                column_values { id text value }
              }
            }
          }
        }
        """
        data = _post(query_first, {"boardId": [numeric_id]})
        items_page = (data.get("boards") or [{}])[0].get("items_page") or {}
        raw_items = list(items_page.get("items") or [])
        cursor = items_page.get("cursor")

        query_next = """
        query ($cursor: String!) {
          next_items_page(cursor: $cursor, limit: 100) {
            cursor
            items {
              id
              name
              column_values { id text value }
            }
          }
        }
        """
        while cursor and len(raw_items) < 1000:
            data = _post(query_next, {"cursor": cursor})
            page = data.get("next_items_page") or {}
            next_items = page.get("items") or []
            if not next_items:
                break
            raw_items.extend(next_items)
            cursor = page.get("cursor")

        flat_records = []
        for it in raw_items:
            rec = {"_item_id": it["id"], "_item_name": it["name"]}
            for cv in it.get("column_values", []):
                title = col_title_by_id.get(cv["id"])
                if not title:
                    continue
                val = cv.get("text")
                if not val and cv.get("value"):
                    try:
                        parsed = json.loads(cv["value"])
                        if isinstance(parsed, dict):
                            val = parsed.get("text") or parsed.get("label") or parsed.get("date")
                    except Exception:
                        val = cv.get("value")
                rec[title] = val
            flat_records.append(rec)

        if flat_records:
            return flat_records
    except Exception as e:
        print(f"Warning: Monday.com API query failed ({e}), using resilient pre-loaded board records.")

    return _fallback_items(board_id)
