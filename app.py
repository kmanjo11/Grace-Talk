# Principal
import streamlit as st
import interpreter
from dotenv import load_dotenv
import threading

# st components
from st_components.st_init import set_style
from st_components.st_session_states import init_session_states
from st_components.st_sidebar import st_sidebar
from st_components.st_main import st_main

#validation
from litellm import completion
from openai import Model

# lessons auto-update on startup (non-blocking)
from src.data.database import create_tables, get_all_lessons
from src.utils.lessons_miner import mine_default_datasets
from src.utils.lessons_retriever import build_index

load_dotenv()  # Load environment variables from .env if present

set_style()

st.title("💬 Grace")

# Ensure DB tables exist
create_tables()

# Background auto-update of lessons if empty (runs once per session)
def _auto_update_lessons_worker():
    try:
        # Mine a modest number to keep startup light
        mine_default_datasets(limit_per_repo=60)
        build_index()
    except Exception:
        # Never interrupt the app if background update fails
        pass

if 'lessons_auto_update_started' not in st.session_state:
    try:
        existing = get_all_lessons(limit=1)
        if not existing:
            t = threading.Thread(target=_auto_update_lessons_worker, daemon=True)
            t.start()
    finally:
        st.session_state['lessons_auto_update_started'] = True

init_session_states()

st_sidebar()

st_main()
