from __future__ import annotations

import os
import json
import requests
import tools

SYSTEM_PROMPT = """\
You are Skylark Drones' internal Business Intelligence assistant. Founders \
and execs ask you questions about the sales pipeline (Deals board) and \
project execution (Work Orders board), both live on monday.com.

Rules:
1. Never answer a numeric/business question from memory or assumption - \
   always call get_deals and/or get_work_orders (or generate_leadership_report \
   for a full update) to pull live data first.
2. The data is known to be messy: missing values, inconsistent formats, and \
   occasional bad rows. When a tool result includes data_quality_caveats, \
   weave the relevant ones into your answer in plain language - don't hide \
   them, and don't let them silently skew a number without a note.
3. If a question is genuinely ambiguous (e.g. "this quarter" with no year, \
   or a sector name that doesn't clearly match one of the real sector \
   values), ask a brief clarifying question before running the tools - \
   don't guess silently on something that would change the answer.
4. Give the founder a real answer with the actual number and brief context \
   (e.g. "why", "compared to what"), not just a raw dump of records. You may \
   quote a handful of specific deals/work orders by name when it helps, but \
   don't paste large raw tables - summarize.
5. If asked for a "leadership update", "executive summary", or similar, use \
   generate_leadership_report and present its output, lightly introduced.
6. If a tool result is empty or a filter matched nothing, say so plainly \
   rather than inventing a plausible-sounding number.
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
    """High-accuracy deterministic fallback engine when cloud LLM hits rate limits (429) or is offline."""
    last_user_msg = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            last_user_msg = msg.get("content")
            break
        elif msg.get("role") == "user" and isinstance(msg.get("content"), list):
            for part in msg.get("content"):
                if isinstance(part, str):
                    last_user_msg = part
                    break

    # Load deals and work orders via tools
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

def _run_gemini_turn(conversation: list[dict], board_ids: dict, session_cache: dict, api_key: str) -> str:
    """Executes multi-turn conversation with tool-calling using Google Gemini API with automatic fallback."""
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        gemini_contents = []
        for msg in conversation:
            role = "user" if msg["role"] == "user" else "model"
            if isinstance(msg["content"], str):
                gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            elif isinstance(msg["content"], list):
                parts = []
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        parts.append({
                            "functionResponse": {
                                "name": item.get("name", "tool"),
                                "response": {"output": item.get("content", "")}
                            }
                        })
                    elif isinstance(item, dict) and item.get("type") == "tool_use":
                        parts.append({
                            "functionCall": {
                                "name": item.get("name"),
                                "args": item.get("input", {})
                            }
                        })
                    elif isinstance(item, str):
                        parts.append({"text": item})
                if parts:
                    gemini_contents.append({"role": role, "parts": parts})

        try:
            payload = {
                "contents": gemini_contents,
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "tools": _get_gemini_tools(),
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1500}
            }
            
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
            
            if resp.status_code == 429 or resp.status_code >= 500:
                continue

            if resp.status_code != 200:
                continue

            res_data = resp.json()
            candidates = res_data.get("candidates", [])
            if not candidates:
                continue

            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
            
            if not function_calls:
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                final_text = "\n".join(text_parts).strip()
                if final_text:
                    conversation.append({"role": "assistant", "content": final_text})
                    return final_text

            gemini_contents.append({"role": "model", "parts": parts})
            
            fn_responses = []
            for fc in function_calls:
                fn_name = fc.get("name")
                fn_args = fc.get("args", {})
                tool_res_str = tools.run_tool(fn_name, fn_args, board_ids, session_cache)
                fn_responses.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"output": tool_res_str}
                    }
                })

            gemini_contents.append({"role": "user", "parts": fn_responses})
            
            follow_payload = {
                "contents": gemini_contents,
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "tools": _get_gemini_tools(),
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1500}
            }
            follow_resp = requests.post(url, json=follow_payload, headers={"Content-Type": "application/json"}, timeout=20)
            if follow_resp.status_code == 200:
                f_data = follow_resp.json()
                f_cands = f_data.get("candidates", [])
                if f_cands:
                    f_parts = f_cands[0].get("content", {}).get("parts", [])
                    f_text = "\n".join([p.get("text", "") for p in f_parts if "text" in p]).strip()
                    if f_text:
                        conversation.append({"role": "assistant", "content": f_text})
                        return f_text

        except Exception:
            continue

    return _fallback_local_engine(conversation, board_ids, session_cache)

def _run_anthropic_turn(conversation: list[dict], board_ids: dict, session_cache: dict, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    model = "claude-sonnet-5"

    try:
        while True:
            response = client.messages.create(
                model=model,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                tools=tools.TOOLS_SCHEMA,
                messages=conversation,
            )

            conversation.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                text_parts = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_parts).strip()

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_str = tools.run_tool(block.name, block.input, board_ids, session_cache)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "name": block.name,
                    "content": result_str,
                })

            conversation.append({"role": "user", "content": tool_results})
    except Exception:
        return _fallback_local_engine(conversation, board_ids, session_cache)

def run_agent_turn(conversation: list[dict], board_ids: dict, session_cache: dict) -> str:
    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if gemini_key:
        return _run_gemini_turn(conversation, board_ids, session_cache, gemini_key)
    elif anthropic_key:
        return _run_anthropic_turn(conversation, board_ids, session_cache, anthropic_key)
    else:
        return _fallback_local_engine(conversation, board_ids, session_cache)
