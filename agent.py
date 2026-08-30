from __future__ import annotations

import os
import json
import requests
import tools

SYSTEM_PROMPT = """\
You are Skylark Drones' internal Business Intelligence assistant. Founders \
and execs ask you questions about the sales pipeline (Deals board) and \
project execution (Work Orders board), both live on monday.com.
"""

def _get_gemini_tools():
    declarations = []
    for t in tools.TOOLS_SCHEMA:
        declarations.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"]
        })
    return [{"function_declarations": declarations}]

def _fallback_local_engine(conversation: list[dict], board_ids: dict, session_cache: dict) -> str:
    last_user_msg = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            last_user_msg = msg.get("content")
            break

    if "deals" not in session_cache:
        session_cache["deals"] = tools._load_deals(board_ids.get("deals", ""))
    if "work_orders" not in session_cache:
        session_cache["work_orders"] = tools._load_work_orders(board_ids.get("work_orders", ""))

    from bi_agent_core import BIAgentCore
    core = BIAgentCore(session_cache["deals"].df, session_cache["work_orders"].df)
    res = core.process_query(last_user_msg)

    out = []
    out.append(f"### {res.get('title', 'Business Intelligence Snapshot')}\n")
    out.append(res.get("executive_summary", ""))

    if res.get("metrics"):
        out.append("\n**Key Metrics:**")
        for k, v in res["metrics"].items():
            out.append(f"- **{k}:** {v}")

    if res.get("recommendations"):
        out.append("\n**Strategic Recommendations:**")
        for r in res["recommendations"]:
            out.append(f"- {r}")

    if res.get("caveats"):
        out.append("\n**⚠️ Data Caveats:**")
        for c in res["caveats"][:3]:
            out.append(f"- _{c}_")

    final_str = "\n".join(out)
    conversation.append({"role": "assistant", "content": final_str})
    return final_str

def run_agent_turn(conversation: list[dict], board_ids: dict, session_cache: dict) -> str:
    return _fallback_local_engine(conversation, board_ids, session_cache)
