"""
Streamlit version of the web UI, used for deploying on Streamlit Community Cloud.
Run locally with:  streamlit run streamlit_app.py
"""
import os
import streamlit as st
from ui_content import (
    EXAMPLES, HEADER_HTML, WELCOME_HTML, FOOTER_HTML, BRAND_CSS,
    program_card_html, tips_card_html,
)


st.set_page_config(page_title="IITM BS Degree Assistant", page_icon="🎓", layout="wide")

USER_AVATAR = "🧑‍🎓"
BOT_AVATAR = "🎓"

STREAMLIT_CSS = """
.block-container { max-width: 1100px; padding-top: 3.5rem; }  /* clear Streamlit's toolbar */
[data-testid="stSidebar"] .iitm-card { margin-bottom: 12px; }
div[data-testid="stButton"] button {
  justify-content: flex-start; text-align: left; min-height: 56px;
  border-radius: 10px; border: 1px solid #E7DFD5; background: #FFFFFF;
}
div[data-testid="stButton"] button:hover { border-color: #8B1E1E; color: #8B1E1E; }
"""


# --- LOADING THE CHATBOT ---
def _load_secrets_into_env():
    """
    On Streamlit Cloud the API keys are stored in st.secrets. llm_providers.py reads
    them from environment variables, so copy them over. Locally .env is used instead.
    """
    try:
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:
        pass  # no secrets.toml, which is normal when running locally


@st.cache_resource(show_spinner="Loading the knowledge base... the first start can take a minute.")
def load_chatbot():
    """
    Imported once per server and shared by all visitors. The first import loads
    the embedding model and builds the handbook database if it doesn't exist yet.
    """
    _load_secrets_into_env()
    import chatbot
    return chatbot


# --- PAGE ---
st.markdown(f"<style>{BRAND_CSS}{STREAMLIT_CSS}</style>", unsafe_allow_html=True)
st.markdown(HEADER_HTML, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(program_card_html(), unsafe_allow_html=True)
    st.markdown(tips_card_html(), unsafe_allow_html=True)
    if st.button("🗨️ New chat", width="stretch"):
        st.session_state.messages = []
        st.rerun()

bot = load_chatbot()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show the conversation so far
for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Empty chat: welcome message and suggested questions
suggested_question = None
if not st.session_state.messages:
    st.markdown(WELCOME_HTML, unsafe_allow_html=True)
    columns = st.columns(2)
    for i, example in enumerate(EXAMPLES):
        if columns[i % 2].button(example, key=f"example_{i}", width="stretch"):
            suggested_question = example

typed_question = st.chat_input("Ask about courses, exams, fees, eligibility...")
question = typed_question or suggested_question

if question:
    history = list(st.session_state.messages)

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(question)

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Looking through the handbook and course documents..."):
            answer = bot.answer_question(question, history)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    # Rerun so the suggested questions disappear after the first message
    if suggested_question:
        st.rerun()

st.markdown(FOOTER_HTML, unsafe_allow_html=True)
