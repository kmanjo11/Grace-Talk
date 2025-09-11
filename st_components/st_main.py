import streamlit as st

from st_components.st_conversations import init_conversations
from st_components.st_messages import chat_with_interpreter
from st_components.st_live_sandbox import show_live_sandbox_window
from st_components.st_p6 import p6_panel
from st_components.st_grep import grep_panel

# Database
from src.data.database import get_chats_by_conversation_id, save_conversation
from src.data.models import Conversation
import uuid



def st_main():
        
    # try:
        if not st.session_state['chat_ready']:
            
            introduction()
        
        else:    

            init_conversations()
            create_or_get_current_conversation()
            
            # Fixed top panels - always visible at top
            render_fixed_top_panels()
            
            # Display messages in clean flow
            render_messages()
            
            # Chat input at bottom
            chat_with_interpreter()
    
    # except Exception as e:
    #     st.error(e)

def render_fixed_top_panels():
    """
    Render fixed top panels that don't interfere with chat flow
    """
    # Create two columns for the panels
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("P6 Schedule Review Setup", expanded=False):
            p6_panel()
    
    with col2:
        with st.expander("Code Search (grep)", expanded=False):
            grep_panel()
    
    # Add separator line
    st.divider()

def create_or_get_current_conversation():
    """
    CRITICAL: Ensure conversations and messages persist across page refreshes
    Safari-specific fixes included for session state persistence
    """
    # Safari fix: Force initialize messages if not present or None
    if 'messages' not in st.session_state or st.session_state["messages"] is None:
        st.session_state["messages"] = []
    
    # Safari fix: Check for None as well as missing key
    if 'current_conversation' not in st.session_state or st.session_state['current_conversation'] is None:
        conversations, conversation_options = init_conversations()
        if conversations:
            # Load the most recent conversation
            st.session_state['current_conversation'] = conversations[0]
            # Safari fix: Store conversation ID for persistence tracking
            st.session_state['safari_conversation_id'] = conversations[0]['id']
            # CRITICAL: Load messages from database immediately
            loaded_messages = get_chats_by_conversation_id(st.session_state['current_conversation']["id"])
            st.session_state["messages"] = loaded_messages if loaded_messages else []
        else:
            # Create new conversation if none exist
            conversation_id = str(uuid.uuid4())
            new_conversation = Conversation(conversation_id, st.session_state.user_id, f"Conversation {len(conversations) + 1}")
            save_conversation(new_conversation)
            st.session_state['current_conversation'] = new_conversation.__dict__
            st.session_state["messages"] = []
            st.rerun()
    else:
        # Safari fix: Double-check conversation persistence
        current_conv_id = st.session_state['current_conversation'].get('id') if st.session_state['current_conversation'] else None
        safari_conv_id = st.session_state.get('safari_conversation_id')
        
        # If Safari cleared the conversation but we have a backup ID, restore it
        if not current_conv_id and safari_conv_id:
            conversations, _ = init_conversations()
            for conv in conversations:
                if conv['id'] == safari_conv_id:
                    st.session_state['current_conversation'] = conv
                    current_conv_id = conv['id']
                    break
        
        # CRITICAL: Always reload messages from database to ensure persistence
        if current_conv_id:
            loaded_messages = get_chats_by_conversation_id(current_conv_id)
            if loaded_messages:
                st.session_state["messages"] = loaded_messages
            # If no messages in database but some in session, keep session messages
            elif not st.session_state.get("messages"):
                st.session_state["messages"] = []

def render_messages():
    """
    Render Messages:
    Render chat-message when generated.
    """
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message(msg["role"]).markdown(f'<p>{msg["content"]}</p>', True)
        elif msg["role"] == "assistant":
            st.chat_message(msg["role"]).markdown(msg["content"])

def introduction():
    """
    Introduction:
    Display introductory messages for the user.
    """
    st.info("👋 Hey, we're very happy to see you here. 🤗")
    st.info("👉 Set your OpenAI api key, to be able to run code while you generate it 🚀")
    st.error("👉 The objective of this project is to show an easy implementation of the use of Open Interpreter 🤗")
