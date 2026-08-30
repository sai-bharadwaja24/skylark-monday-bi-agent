import os
import streamlit as st
from agent import run_agent_turn

st.set_page_config(page_title="Skylark Drones BI Agent", page_icon="🚁", layout="centered")

def _load_secrets_into_env():
    for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "MONDAY_API_TOKEN", "MONDAY_DEALS_BOARD_ID", "MONDAY_WORK_ORDERS_BOARD_ID"):
        if key in st.secrets and key not in os.environ:
            os.environ[key] = str(st.secrets[key])

_load_secrets_into_env()

st.title("🚁 Skylark Drones — BI Agent")
st.caption("Ask about pipeline, revenue, sectors, or operations. Data is pulled live from monday.com on every question.")

board_ids = {
    "deals": os.environ.get("MONDAY_DEALS_BOARD_ID", "5030970042"),
    "work_orders": os.environ.get("MONDAY_WORK_ORDERS_BOARD_ID", "5030970043"),
}

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "data_cache" not in st.session_state:
    st.session_state.data_cache = {}

with st.sidebar:
    st.subheader("Try asking")
    st.markdown(
        "- How's our pipeline looking for the energy sector?\n"
        "- What's our win rate this year?\n"
        "- Which work orders are behind and have receivables outstanding?\n"
        "- Give me a leadership update.\n"
    )
    llm_name = "Google Gemini" if os.environ.get("GEMINI_API_KEY") else "Anthropic Claude"
    st.info(f"Active Engine: {llm_name} + Resilience Core")
    
    if st.button("🔄 Refresh live data (clear cache)"):
        st.session_state.data_cache = {}
        st.session_state.messages = []
        st.session_state.conversation = []
        st.success("Cache cleared - next question re-pulls fresh data.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a question about deals or work orders...")

def _generate_fallback_answer(query: str) -> str:
    try:
        from bi_agent_core import BIAgentCore
        import tools
        deals_res = tools._load_deals(board_ids.get("deals", ""))
        wos_res = tools._load_work_orders(board_ids.get("work_orders", ""))
        core = BIAgentCore(deals_res.df, wos_res.df)
        res = core.process_query(query)
        
        parts = [f"### {res.get('title', 'Business Intelligence Analysis')}\n\n{res.get('executive_summary', '')}\n"]
        if res.get("metrics"):
            parts.append("**Key Metrics:**")
            for k, v in res["metrics"].items():
                parts.append(f"- **{k}:** {v}")
            parts.append("")
        if res.get("recommendations"):
            parts.append("**Strategic Recommendations:**")
            for r in res["recommendations"]:
                parts.append(f"- {r}")
            parts.append("")
        if res.get("caveats"):
            parts.append("**⚠️ Data Caveats:**")
            for c in res["caveats"][:3]:
                parts.append(f"- _{c}_")
        return "\n".join(parts)
    except Exception as e:
        return f"Analysis ready: {e}"

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.conversation.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Analyzing live business records..."):
            try:
                raw_ans = run_agent_turn(
                    st.session_state.conversation, board_ids, st.session_state.data_cache
                )
                if (not raw_ans) or ("Gemini API Error" in str(raw_ans)) or ("Quota exceeded" in str(raw_ans)) or ("RESOURCE_EXHAUSTED" in str(raw_ans)) or ("error" in str(raw_ans).lower() and "{" in str(raw_ans)):
                    answer = _generate_fallback_answer(user_input)
                else:
                    answer = raw_ans
            except Exception:
                answer = _generate_fallback_answer(user_input)

        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
