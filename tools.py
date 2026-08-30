"""
Tool layer between the Claude agent and the data sources.

Every tool call re-fetches from monday.com (via monday_client) unless a
fetch already happened earlier in the *same Streamlit session* - in which
case we reuse that session's copy so a multi-turn conversation doesn't
refetch the whole board on every message. Nothing is cached across
sessions or written to disk, so "dynamic query, no hardcoded data" holds:
restart the app and it pulls fresh from monday.com again.
"""

from __future__ import annotations

import json

import pandas as pd

import data_processing as dp
import monday_client as mc
import reports


TOOLS_SCHEMA = [
    {
        "name": "get_deals",
        "description": (
            "Fetch deal/pipeline records from the monday.com Deals board, live. "
            "Optionally filter by sector, deal status (Open/Won/Dead/On Hold), "
            "or deal stage. Returns cleaned records plus data-quality caveats. "
            "Use this for any question about sales pipeline, revenue, win rate, "
            "sectors, deal owners, or closure probability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "Filter to this Sector/service value, e.g. 'Mining'. Omit for all sectors."},
                "status": {"type": "string", "description": "Filter to this Deal Status: Open, Won, Dead, or On Hold. Omit for all."},
            },
        },
    },
    {
        "name": "get_work_orders",
        "description": (
            "Fetch project execution / work order records from the monday.com "
            "Work Orders board, live. Optionally filter by sector or execution "
            "status. Returns cleaned records plus data-quality caveats. Use this "
            "for any question about operations, delivery status, billing, "
            "invoicing, or receivables."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "Filter to this Sector value. Omit for all sectors."},
                "execution_status": {"type": "string", "description": "Filter to this Execution Status value. Omit for all."},
            },
        },
    },
    {
        "name": "generate_leadership_report",
        "description": (
            "Generate a full leadership-update style markdown report covering "
            "sales/pipeline, top wins, high-conviction deals, operations health, "
            "outstanding receivables, and data quality caveats, computed live "
            "from both boards. Use this when the user asks for a leadership "
            "update, executive summary, board update, or similar."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _load_deals(board_id: str) -> dp.CleanResult:
    raw = mc.get_board_items(board_id)
    return dp.clean_deals(raw)


def _load_work_orders(board_id: str) -> dp.CleanResult:
    raw = mc.get_board_items(board_id)
    return dp.clean_work_orders(raw)


def _summarize_df(df: pd.DataFrame, max_rows: int = 40) -> dict:
    """Trim a dataframe to something reasonable to hand back to the LLM
    as tool output - full stats, a capped sample of rows."""
    if df.empty:
        return {"row_count": 0, "sample_rows": [], "note": "No matching records."}
    sample = df.head(max_rows).copy()
    for col in sample.columns:
        if pd.api.types.is_datetime64_any_dtype(sample[col]):
            sample[col] = sample[col].dt.strftime("%Y-%m-%d").where(sample[col].notna(), None)
    return {
        "row_count": len(df),
        "sample_rows": json.loads(sample.to_json(orient="records")),
        "truncated": len(df) > max_rows,
    }


def run_tool(name: str, tool_input: dict, board_ids: dict, session_cache: dict) -> str:
    """Dispatch a tool call. board_ids = {'deals': ..., 'work_orders': ...}.
    session_cache is a plain dict (e.g. st.session_state) used to avoid
    refetching the same board twice within one conversation."""

    if name == "get_deals":
        if "deals" not in session_cache:
            session_cache["deals"] = _load_deals(board_ids["deals"])
        result: dp.CleanResult = session_cache["deals"]
        df = result.df
        if tool_input.get("sector") and "Sector/service" in df.columns:
            df = df[df["Sector/service"] == tool_input["sector"]]
        if tool_input.get("status") and "Deal Status" in df.columns:
            df = df[df["Deal Status"] == tool_input["status"]]
        out = _summarize_df(df)
        out["data_quality_caveats"] = result.caveats
        return json.dumps(out, default=str)

    if name == "get_work_orders":
        if "work_orders" not in session_cache:
            session_cache["work_orders"] = _load_work_orders(board_ids["work_orders"])
        result: dp.CleanResult = session_cache["work_orders"]
        df = result.df
        if tool_input.get("sector") and "Sector" in df.columns:
            df = df[df["Sector"] == tool_input["sector"]]
        if tool_input.get("execution_status") and "Execution Status" in df.columns:
            df = df[df["Execution Status"] == tool_input["execution_status"]]
        out = _summarize_df(df)
        out["data_quality_caveats"] = result.caveats
        return json.dumps(out, default=str)

    if name == "generate_leadership_report":
        if "deals" not in session_cache:
            session_cache["deals"] = _load_deals(board_ids["deals"])
        if "work_orders" not in session_cache:
            session_cache["work_orders"] = _load_work_orders(board_ids["work_orders"])
        deals_result: dp.CleanResult = session_cache["deals"]
        wo_result: dp.CleanResult = session_cache["work_orders"]
        report_md = reports.build_leadership_report(
            deals_result.df, wo_result.df, deals_result.caveats, wo_result.caveats
        )
        return report_md

    return json.dumps({"error": f"Unknown tool '{name}'"})
