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

has_llm_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
has_monday_token = bool(os.environ.get("MONDAY_API_TOKEN"))
has_boards = bool(os.environ.get("MONDAY_DEALS_BOARD_ID") and os.environ.get("MONDAY_WORK_ORDERS_BOARD_ID"))

if not has_llm_key or not has_monday_token or not has_boards:
    missing = []
    if not has_llm_key:
        missing.append("GEMINI_API_KEY (or ANTHROPIC_API_KEY)")
    if not has_monday_token:
        missing.append("MONDAY_API_TOKEN")
    if not os.environ.get("MONDAY_DEALS_BOARD_ID"):
        missing.append("MONDAY_DEALS_BOARD_ID")
    if not os.environ.get("MONDAY_WORK_ORDERS_BOARD_ID"):
        missing.append("MONDAY_WORK_ORDERS_BOARD_ID")

    st.error(
        "Missing required configuration: " + ", ".join(missing) +
        ". Set these in Streamlit Cloud's app secrets (Settings → Secrets) "
        "or in .streamlit/secrets.toml. See README.md."
    )
    st.stop()

board_ids = {
    "deals": os.environ["MONDAY_DEALS_BOARD_ID"],
    "work_orders": os.environ["MONDAY_WORK_ORDERS_BOARD_ID"],
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
    st.info(f"Active LLM: {llm_name}")
    
    if st.button("🔄 Refresh live data (clear cache)"):
        st.session_state.data_cache = {}
        st.success("Cache cleared - next question re-pulls from monday.com.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a question about deals or work orders...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.conversation.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Pulling live data from monday.com and thinking..."):
            try:
                answer = run_agent_turn(
                    st.session_state.conversation, board_ids, st.session_state.data_cache
                )
            except Exception as exc:
                answer = f"Something went wrong talking to monday.com or AI: {exc}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
