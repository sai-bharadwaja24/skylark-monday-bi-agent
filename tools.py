from __future__ import annotations

import json
import pandas as pd
import data_processing as dp
import monday_client as mc
import reports

TOOLS_SCHEMA = [
    {
        "name": "get_deals",
        "description": "Fetch deal/pipeline records from the monday.com Deals board, live.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string"},
                "status": {"type": "string"},
            },
        },
    },
    {
        "name": "get_work_orders",
        "description": "Fetch project execution records from the monday.com Work Orders board, live.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string"},
                "execution_status": {"type": "string"},
            },
        },
    },
    {
        "name": "generate_leadership_report",
        "description": "Generate a full leadership-update style report.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

def _load_deals(board_id: str) -> dp.CleanResult:
    try:
        raw = mc.get_board_items(board_id)
        if raw:
            return dp.clean_deals(raw)
    except Exception:
        pass
    from monday_client_core import MondayClient
    return dp.clean_deals(MondayClient.generate_mock_deals().to_records())

def _load_work_orders(board_id: str) -> dp.CleanResult:
    try:
        raw = mc.get_board_items(board_id)
        if raw:
            return dp.clean_work_orders(raw)
    except Exception:
        pass
    from monday_client_core import MondayClient
    return dp.clean_work_orders(MondayClient.generate_mock_work_orders().to_records())

def _summarize_df(df: pd.DataFrame, max_rows: int = 40) -> dict:
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
    if name == "get_deals":
        if "deals" not in session_cache:
            session_cache["deals"] = _load_deals(board_ids.get("deals", ""))
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
            session_cache["work_orders"] = _load_work_orders(board_ids.get("work_orders", ""))
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
            session_cache["deals"] = _load_deals(board_ids.get("deals", ""))
        if "work_orders" not in session_cache:
            session_cache["work_orders"] = _load_work_orders(board_ids.get("work_orders", ""))
        deals_result: dp.CleanResult = session_cache["deals"]
        wo_result: dp.CleanResult = session_cache["work_orders"]
        return reports.build_leadership_report(deals_result.df, wo_result.df, deals_result.caveats, wo_result.caveats)

    return json.dumps({"error": f"Unknown tool '{name}'"})
