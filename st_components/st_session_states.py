import streamlit as st
import uuid
import json
import os
from interpreter import interpreter

from src.utils.prompts import PROMPTS


def init_session_states():

    if 'models' not in st.session_state:
        with open("models.json", "r") as file:
            st.session_state['models'] = json.load(file)
    if 'api_choice' not in st.session_state:
        st.session_state['api_choice'] = None
    if 'chat_ready' not in st.session_state:
        st.session_state['chat_ready'] = False
    if 'system_message' not in st.session_state:
        st.session_state['system_message'] = PROMPTS.system_message
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = str(uuid.uuid4())
    if 'interpreter' not in st.session_state:
        st.session_state['interpreter'] = interpreter
    
    # Load persistent API keys from environment variables
    if 'openai_key' not in st.session_state or not st.session_state['openai_key']:
        st.session_state['openai_key'] = os.getenv('OPENAI_API_KEY', '')
    if 'openrouter_key' not in st.session_state or not st.session_state['openrouter_key']:
        st.session_state['openrouter_key'] = os.getenv('OPENROUTER_API_KEY', '')
    if 'api_base' not in st.session_state or not st.session_state['api_base']:
        st.session_state['api_base'] = os.getenv('API_BASE', '')
    if 'azure_endpoint' not in st.session_state or not st.session_state['azure_endpoint']:
        st.session_state['azure_endpoint'] = os.getenv('AZURE_ENDPOINT', '')
    if 'api_version' not in st.session_state or not st.session_state['api_version']:
        st.session_state['api_version'] = os.getenv('API_VERSION', '')

    # If an API key is already present in env, auto-configure a default model and skip the welcome screen
    if not st.session_state.get('chat_ready', False):
        try:
            # Prefer OpenAI
            if st.session_state['openai_key']:
                st.session_state['api_choice'] = 'openai'
                # pick first OpenAI model from models.json
                openai_models = list(st.session_state['models'].get('openai', {}).keys())
                default_model = openai_models[0] if openai_models else 'gpt-4o-mini'
                st.session_state['model'] = default_model
                context_window = st.session_state['models'].get('openai', {}).get(default_model, {}).get('context_window', 4096)
                st.session_state['context_window'] = context_window
                st.session_state['temperature'] = st.session_state.get('temperature', 0.5)
                st.session_state['max_tokens'] = st.session_state.get('max_tokens', 512)
                st.session_state['num_pair_messages_recall'] = st.session_state.get('num_pair_messages_recall', 5)
                st.session_state['chat_ready'] = True
            # Else use OpenRouter if key is present
            elif st.session_state['openrouter_key']:
                st.session_state['api_choice'] = 'openrouter'
                or_models = list(st.session_state['models'].get('openrouter', {}).keys())
                default_model = or_models[0] if or_models else 'openrouter/auto'
                st.session_state['model'] = f'openrouter/{default_model}' if not default_model.startswith('openrouter/') else default_model
                context_window = st.session_state['models'].get('openrouter', {}).get(default_model.replace('openrouter/', ''), {}).get('context_window', 4096)
                st.session_state['context_window'] = context_window
                st.session_state['temperature'] = st.session_state.get('temperature', 0.5)
                st.session_state['max_tokens'] = st.session_state.get('max_tokens', 512)
                st.session_state['num_pair_messages_recall'] = st.session_state.get('num_pair_messages_recall', 5)
                st.session_state['chat_ready'] = True
            # Else if Azure endpoint/version present alongside OpenAI key
            elif st.session_state['azure_endpoint'] and st.session_state['openai_key']:
                st.session_state['api_choice'] = 'azure_openai'
                # choose a placeholder deployment/model name
                st.session_state['model'] = 'azure/deployment'
                st.session_state['context_window'] = st.session_state.get('context_window', 4096)
                st.session_state['temperature'] = st.session_state.get('temperature', 0.5)
                st.session_state['max_tokens'] = st.session_state.get('max_tokens', 512)
                st.session_state['num_pair_messages_recall'] = st.session_state.get('num_pair_messages_recall', 5)
                st.session_state['chat_ready'] = True
        except Exception:
            # Fail-safe: keep normal flow
            pass
