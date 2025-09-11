import streamlit as st
from st_components.st_interpreter import setup_interpreter
from src.data.database import save_chat
from src.data.models import Chat
from src.utils.message_processor import message_processor
from src.utils.internal_task_tracker import internal_tracker
# Database
from src.data.database import save_chat, save_lesson
# Message processor for consistency
from src.utils.message_processor import message_processor
import uuid
import re
from src.utils.pdf_parser import parse_pdf_text
from src.utils.pdf_retriever import ensure_pdf_index_built, retrieve_pdf_sections
from src.utils.docker_executor import DockerCodeExecutor


def chat_with_interpreter():

    # GENERATE MESSAGES
    if prompt := st.chat_input(placeholder="What's up?", disabled=not st.session_state['chat_ready']):

        setup_interpreter()

        # Display user message
        with st.chat_message("user"):
            st.markdown(f'<p>{prompt}</p>', True)

        # Internal task management (hidden from user)
        task_id = internal_tracker.auto_manage_task(prompt)

        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        user_chat = Chat(
            st.session_state['current_conversation']["id"], "user", prompt)
        save_chat(user_chat)

        handle_assistant_response(prompt)


def handle_user_message(prompt):
    with st.chat_message("user"):
        st.markdown(f'<p>{prompt}</p>', True)
        st.session_state.messages.append({"role": "user", "content": prompt})
        user_chat = Chat(
            st.session_state['current_conversation']["id"], "user", prompt)
        save_chat(user_chat)


def add_memory(prompt):
    look_back = -2*st.session_state['num_pair_messages_recall']
    memory = '\n'.join(
        [f"{i['role'].capitalize()}: {i['content']}" for i in st.session_state['messages'][look_back:]]
    ).replace('User', '\nUser'
              )
    prompt_with_memory = f"user's request:{prompt}. --- \nBelow is the transcript of your past conversation with the user: {memory} ---\n"
    return prompt_with_memory


def _build_hidden_lessons_context(prompt: str) -> str:
    """Retrieve top lessons and build a compact hidden context block to guide the model.
    This is NOT rendered in the UI; it's appended to the user message sent to the model."""
    try:
        ensure_index_built()
        # You can refine filters based on language/framework selection in the future
        lessons = retrieve(query=prompt, top_k=2)
        if not lessons:
            return ""

        blocks = []
        for i, l in enumerate(lessons, start=1):
            cm = l.get('commit_message', '').strip()
            fp = l.get('file_path', '')
            before = (l.get('before_code') or '')
            after = (l.get('after_code') or '')
            # Trim to keep context light
            before_trim = '\n'.join(before.splitlines()[:20])
            after_trim = '\n'.join(after.splitlines()[:20])

            bullets = []
            if l.get('change_type'):
                bullets.append(f"- change_type: {l['change_type']}")
            if l.get('language'):
                bullets.append(f"- language: {l['language']}")
            if l.get('framework'):
                bullets.append(f"- framework: {l['framework']}")
            bullets_str = '\n'.join(bullets[:3])

            block = (
                f"Lesson {i}:\n"
                f"Commit Message: {cm}\n"
                f"File: {fp}\n"
                f"What changed (summary):\n{bullets_str}\n\n"
                f"Before (Buggy):\n```\n{before_trim}\n```\n\n"
                f"After (Fixed):\n```\n{after_trim}\n```\n"
            )
            blocks.append(block)

        guidance = (
            "\n---\n"
            "Background: prior real-world fixes that may inform a concise answer.\n"
            "Use them only if relevant; do not recap or follow a rigid template.\n"
            + "\n\n".join(blocks)
        )
        return guidance
    except Exception:
        # Fail-safe: never block the main flow
        return ""


def _build_hidden_grep_context(prompt: str) -> str:
    """Lightweight grep across the workspace to surface likely-relevant code lines.
    Injects only when enabled via sidebar toggle. Invisible to the UI.
    """
    try:
        # Quick heuristics to avoid overuse
        p = (prompt or "").lower()
        trigger_terms = [
            'error', 'exception', 'traceback', 'fix', 'undefined', 'import', 'not found', 'hydration', 'ssr'
        ]
        if not any(t in p for t in trigger_terms):
            return ""

        import os, re
        from pathlib import Path

        root = Path('.')
        skip_dirs = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.mypy_cache', '.pytest_cache', '.ruff_cache'}

        # Build simple search terms: top 3 words >= 4 chars
        words = re.findall(r"[A-Za-z0-9_]{4,}", prompt)
        words = words[:3]
        if not words:
            return ""

        snippets = []
        max_files = 8
        max_hits_per_file = 3
        files_scanned = 0

        for dirpath, dirnames, filenames in os.walk(root):
            base = os.path.basename(dirpath)
            if base in skip_dirs:
                dirnames[:] = []
                continue
            for fn in filenames:
                if not fn.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.txt', '.yml', '.yaml', '.toml', '.cfg', '.ini', '.css', '.scss', '.html')):
                    continue
                path = Path(dirpath) / fn
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                except Exception:
                    continue

                hits = []
                for i, line in enumerate(lines, start=1):
                    if all(w.lower() in line.lower() for w in words):
                        start = max(1, i-1)
                        end = min(len(lines), i+1)
                        context = ''.join(lines[start-1:end])
                        hits.append((i, context))
                        if len(hits) >= max_hits_per_file:
                            break

                if hits:
                    snippet_text = []
                    for (ln, ctx) in hits:
                        snippet_text.append(f"{ln}: {ctx}")
                    block = (
                        f"File: {path}\n" +
                        "".join(snippet_text)
                    )
                    snippets.append(block)
                    files_scanned += 1
                    if files_scanned >= max_files:
                        break
            if files_scanned >= max_files:
                break

        if not snippets:
            return ""

        return (
            "\n---\n"
            "Relevant codebase snippets (for debugging).\n" +
            "\n\n".join(snippets[:5])
        )
    except Exception:
        return ""


def handle_assistant_response(prompt):
    with st.chat_message("assistant"):
        # Initialize variables
        full_response = ""
        message_placeholder = st.empty()

        # Skip auto-greeting - let conversation flow naturally
        if message_processor.is_simple_greeting(prompt):
            # Don't return early, let it go through normal processing
            pass

        # Intent: explicit sandbox creation/health check
        pl = (prompt or "").strip().lower()
        if any(kw in pl for kw in ["create a sandbox", "make a sandbox", "start sandbox", "docker sandbox", "check docker"]):
            # Probe Docker
            docker = DockerCodeExecutor()
            available = False
            try:
                available = docker.is_available()
            except Exception:
                available = False
            if available:
                # Tiny smoke test inside Docker (hidden unless user enabled output)
                res = docker.execute_code("print('ok')", language='python')
                if st.session_state.get('show_exec_output', False):
                    st.markdown(f"Docker Sandbox is available. Smoke test output: `{res.strip()}`")
                else:
                    st.markdown("Docker Sandbox is available. Smoke test passed.")
            else:
                st.markdown("Docker Sandbox is unavailable. Start Docker Desktop, then try again. You can also enable 'Prefer Local Execution' to skip Docker.")
            return

        # Build message with memory and system prompt
        message = add_memory(prompt)
        
        # Add system prompt with style guidelines
        system_prompt = message_processor.build_system_prompt()
        message = system_prompt + message
        # Hidden domain context: P6 schedule review instructions, if available
        p6_ctx = st.session_state.get('p6_context')
        if p6_ctx:
            message = ("\n[Domain Context: P6 Schedule Review]\n" + p6_ctx + "\n\n" + message)
        
        # Skip augmentation for simple greetings or if not needed
        if not message_processor.should_use_augmentation(prompt):
            pass  # No additional augmentation needed
        else:
            # Hidden auto-grep augmentation
            if st.session_state.get('use_auto_grep', True):
                grep_block = _build_hidden_grep_context(prompt)
                if grep_block:
                    message = message + grep_block
            
            # Hidden PDF context from uploaded chat files
            if st.session_state.get('use_pdf_context', True):
                try:
                    chat_files = st.session_state.get('chat_files', {})
                    pdfs = [str(p) for p in chat_files.values() if str(p).lower().endswith('.pdf')]
                    if pdfs:
                        # Build/update index if needed
                        ensure_pdf_index_built(pdfs)
                        sections = retrieve_pdf_sections(prompt, top_k=3)
                        if sections:
                            blocks = []
                            total = 0
                            for s in sections:
                                title = s.get('title') or 'Section'
                                body = (s.get('body') or '')[:1200]
                                path = s.get('path') or ''
                                blocks.append(f"PDF: {path}\n# {title}\n{body}\n...")
                                total += len(body)
                                if total > 3500:
                                    break
                            if blocks:
                                message += ("\n---\n"
                                            "Relevant document sections (PDF).\n" +
                                            "\n\n".join(blocks))
                except Exception:
                    pass
            
            # Hidden augmentation: inject lessons behind the scenes
            if st.session_state.get('use_commit_lessons', False):
                hidden = _build_hidden_lessons_context(prompt)
                if hidden:
                    message = message + hidden
        with st.spinner('thinking'):
            for chunk in st.session_state['interpreter'].chat([{"role": "user", "type": "message", "content": message}], display=False, stream=True):
                full_response = format_response(chunk, full_response)

                # Join the formatted messages
                message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)

        # Apply final message processing
        final_response = message_processor.format_final_response(full_response)
        
        st.session_state.messages.append(
            {"role": "assistant", "content": final_response})
        assistant_chat = Chat(
            st.session_state['current_conversation']["id"], "assistant", final_response)
        save_chat(assistant_chat)
        st.session_state['mensajes'] = st.session_state['interpreter'].messages

        # Auto-save successful fix exchanges as lessons (invisible)
        _auto_save_fix_as_lesson(user_prompt=prompt, assistant_reply=final_response)


def format_response(chunk, full_response):
    # Process chunk through message processor
    processed_chunk = message_processor.process_chunk(chunk)
    
    # Skip hidden chunks
    if processed_chunk.get('type') == 'hidden':
        return full_response
    
    # Message - DO NOT filter individual chunks to preserve word spacing
    if processed_chunk['type'] == "message":
        content = processed_chunk.get("content", "")
        if content:
            # Add content directly without filtering chunks (filtering happens at the end)
            full_response += content
        if processed_chunk.get('end', False):
            full_response += "\n"

    # Code (only show if enabled)
    if processed_chunk['type'] == "code":
        if message_processor.should_show_code_output():
            if processed_chunk.get('start', False):
                full_response += "```python\n"
            full_response += processed_chunk.get('content', '')
            if processed_chunk.get('end', False):
                full_response += "\n```\n"

    # Output (only show if enabled)
    if processed_chunk['type'] == "confirmation":
        if message_processor.should_show_code_output():
            if processed_chunk.get('start', False):
                full_response += "```python\n"
            full_response += processed_chunk.get('content', {}).get('code', '')
            if processed_chunk.get('end', False):
                full_response += "```\n"

    # Console (only show if enabled)
    if processed_chunk['type'] == "console":
        if message_processor.should_show_code_output():
            if processed_chunk.get('start', False):
                full_response += "```python\n"
            if processed_chunk.get('format', '') == "active_line":
                console_content = processed_chunk.get('content', '')
                if console_content is None:
                   full_response += "No output available on console."
            if processed_chunk.get('format', '') == "output":
                console_content = processed_chunk.get('content', '')
                full_response += console_content
            if processed_chunk.get('end', False):
                full_response += "\n```\n"

    # Image
    if processed_chunk['type'] == "image":
        if processed_chunk.get('start', False) or processed_chunk.get('end', False):
            full_response += "\n"
        else:
            image_format = processed_chunk.get('format', '')
            if image_format == 'base64.png':
                image_content = processed_chunk.get('content', '')
                if image_content:
                    image = Image.open(
                        BytesIO(base64.b64decode(image_content)))
                    new_image = Image.new("RGB", image.size, "white")
                    new_image.paste(image, mask=image.split()[3])
                    buffered = BytesIO()
                    new_image.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    full_response += f"![Image](data:image/png;base64,{img_str})\n"

    return full_response


def _extract_first_code_block(text: str) -> str:
    """Extract first fenced code block content from text. Supports ```lang ...``` or ``` ... ```"""
    if not text:
        return ""
    fence = re.search(r"```[a-zA-Z0-9_+-]*\n([\s\S]*?)```", text)
    if fence:
        return fence.group(1).strip()
    return ""


def _infer_language_from_code(code: str) -> str:
    if 'import ' in code and '.tsx' in code or '.ts' in code:
        return 'ts'
    if 'import ' in code and '.jsx' in code or '.js' in code:
        return 'js'
    if 'def ' in code or 'import ' in code:
        return 'py'
    return ''


def _infer_framework_from_text(text: str) -> str:
    t = (text or '').lower()
    if 'next.js' in t or 'nextjs' in t:
        return 'nextjs'
    if 'react' in t:
        return 'react'
    if 'flask' in t:
        return 'flask'
    if 'fastapi' in t:
        return 'fastapi'
    return ''


def _infer_change_type(before: str, after: str) -> str:
    b = before.lower()
    a = after.lower()
    if 'import ' in b or 'import ' in a:
        return 'import_fix'
    if 'hydration' in b or 'hydration' in a or 'ssr' in b or 'ssr' in a:
        return 'ssr_hydration'
    if 'cors' in b or 'cors' in a:
        return 'cors'
    if 'csp' in b or 'csp' in a:
        return 'csp'
    if 'proxy' in b or 'proxy' in a:
        return 'proxy'
    return ''


def _auto_save_fix_as_lesson(user_prompt: str, assistant_reply: str):
    try:
        before_code = _extract_first_code_block(user_prompt)
        after_code = _extract_first_code_block(assistant_reply)

        # Require both before and after to consider it a fix exchange
        if not before_code or not after_code:
            return

        # Heuristic: if assistant output still contains Traceback or obvious errors, skip
        if 'Traceback (most recent call last)' in assistant_reply or 'Error:' in assistant_reply:
            return

        lesson = {
            'id': str(uuid.uuid4()),
            'repo': '',
            'file_path': '',
            'branch': '',
            'commit_sha': '',
            'commit_message': 'Auto-learned fix from chat exchange',
            'before_code': before_code,
            'after_code': after_code,
            'tags': 'chat,auto,fix',
            'language': _infer_language_from_code(before_code) or _infer_language_from_code(after_code),
            'framework': _infer_framework_from_text(user_prompt + "\n" + assistant_reply),
            'change_type': _infer_change_type(before_code, after_code),
            'lines_changed': abs(len(after_code.splitlines()) - len(before_code.splitlines())),
            'tokens_changed': abs(len(after_code.split()) - len(before_code.split())),
        }

        save_lesson(lesson)

        # Rebuild retrieval index to include the new lesson (best-effort)
        try:
            from src.utils.lessons_retriever import build_index
            build_index()
        except Exception:
            pass
    except Exception:
        # Never break chat on auto-save issues
        pass
