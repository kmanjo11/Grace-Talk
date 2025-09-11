import streamlit as st
from src.utils.docker_executor import DockerCodeExecutor
from src.utils.firejail_executor import FirejailCodeExecutor
from src.utils.python_sandbox import RestrictedEnvironment
from src.utils.ubuntu_sandbox import UbuntuSandboxExecutor
from src.utils.deps import ensure_package
import time

def setup_interpreter():
    try:
        st.session_state['interpreter'].reset()
    except:
        pass
        
    st.session_state['interpreter'].conversation_filename = st.session_state['current_conversation']["id"]
    st.session_state['interpreter'].conversation_history = True
    st.session_state['interpreter'].messages = st.session_state.get(
        'messages',
        st.session_state.get('mensajes',[])
    )
    st.session_state['interpreter'].llm.model = st.session_state['model']
    st.session_state['interpreter'].llm.temperature = st.session_state['temperature']
    st.session_state['interpreter'].llm.max_tokens = st.session_state['max_tokens']
    st.session_state['interpreter'].llm.system_message = st.session_state['system_message']
    st.session_state['interpreter'].auto_run = True
    st.session_state['interpreter'].safe_mode = 'off'  # Disable safe mode to enable code execution

    st.session_state['interpreter'].computer.emit_images = True
    st.session_state['interpreter'].computer.offline = False  # Allow internet access
    st.session_state['interpreter'].computer.verbose = True  # Enable verbose output for performance logs
    
    # Integrate sandboxing for code execution (Docker -> Firejail -> Ubuntu -> Python Sandbox -> Local)
    original_run = st.session_state['interpreter'].computer.run
    docker_executor = DockerCodeExecutor()
    firejail_executor = FirejailCodeExecutor()
    ubuntu_sandbox = UbuntuSandboxExecutor()
    python_sandbox = RestrictedEnvironment()

    # Cache Docker health to avoid spamming daemon when it's down
    if 'docker_available' not in st.session_state:
        st.session_state['docker_available'] = False
    if 'docker_last_check' not in st.session_state:
        st.session_state['docker_last_check'] = 0.0

    # Initial non-blocking probe
    try:
        st.session_state['docker_available'] = docker_executor.is_available()
    except Exception:
        st.session_state['docker_available'] = False
    st.session_state['docker_last_check'] = time.time()
    
    def _yield_console(msg: str):
        # Minimal generator yielding a console output chunk compatible with OI
        yield {
            'type': 'console',
            'format': 'output',
            'content': msg,
            'end': True,
        }

    def _is_probable_python_code(cmd: str) -> bool:
        c = (cmd or "").strip()
        # Exclude shell invocations like `python` or `python -V` etc.
        if c.lower() == 'python' or c.lower().startswith('python '):
            return False
        # Consider it code if it contains newlines or common Python syntax
        if "\n" in c:
            return True
        import re as _re
        return bool(_re.match(r"^(from |import |def |class |print\(|for |while |if |try:|#)", c))

    def sandboxed_run(command, *args, **kwargs):
        """Override run method to use sandbox (Docker > Firejail > Ubuntu > Python Sandbox > Local)"""
        try:
            # For Python code, try Docker first
            # Periodically retry Docker availability (every 5 minutes)
            now = time.time()
            if (now - st.session_state.get('docker_last_check', 0)) > 300:
                try:
                    st.session_state['docker_available'] = docker_executor.is_available()
                except Exception:
                    st.session_state['docker_available'] = False
                st.session_state['docker_last_check'] = now

            if _is_probable_python_code(command):
                try:
                    # If user prefers local, skip all sandboxes
                    if st.session_state.get('prefer_local_exec', False):
                        raise RuntimeError('Prefer local execution')
                    
                    # Try Docker first
                    result = docker_executor.execute_code(command, 'python') if st.session_state.get('docker_available', False) else 'Docker not available'
                    # If docker is unavailable, fall through to other sandboxes
                    if isinstance(result, str) and result.strip().lower().startswith('docker not available'):
                        raise RuntimeError('Docker unavailable')
                    return _yield_console("🐳 Docker Sandbox:\n" + (result or ""))
                    
                except Exception as docker_error:
                    # Try Firejail if Docker fails/unavailable and not preferring local
                    if not st.session_state.get('prefer_local_exec', False) and firejail_executor.is_available():
                        try:
                            result = firejail_executor.execute_code(command, 'python')
                            return _yield_console("🔥 Firejail Sandbox:\n" + (result or ""))
                        except Exception as firejail_error:
                            pass
                    
                    # Try Ubuntu sandbox if Firejail fails
                    if not st.session_state.get('prefer_local_exec', False) and ubuntu_sandbox.is_available():
                        try:
                            result = ubuntu_sandbox.execute_code(command, 'python')
                            return _yield_console("🐧 Ubuntu Sandbox:\n" + (result or ""))
                        except Exception as ubuntu_error:
                            pass
                    
                    # Try Python sandbox as final fallback
                    try:
                        result = python_sandbox.execute_code(command, 'python')
                        return _yield_console("🐍 Python Sandbox:\n" + (result or ""))
                    except Exception as python_error:
                        pass
            
            # For other commands or if sandboxes fail, use original method
            return original_run(command, *args, **kwargs)
        except Exception as e:
            # On-demand dependency install and retry if allowed
            allow_install = st.session_state.get('allow_auto_installs', True)
            allow_exec = st.session_state.get('allow_auto_exec', True)
            msg = str(e)
            missing = None
            # Simple parse for missing module
            # e.g., ModuleNotFoundError: No module named 'foo'
            import re
            m = re.search(r"No module named ['\"]([a-zA-Z0-9_\-\.]+)['\"]", msg)
            if m:
                missing = m.group(1)
            if missing and allow_install and allow_exec:
                if ensure_package(missing):
                    try:
                        return original_run(command, *args, **kwargs)
                    except Exception:
                        pass
            # If all else fails, surface the error as a console chunk and then attempt original run
            err_msg = f"Sandbox execution failed: {str(e)}. Falling back.\n"
            def _fallback_chain():
                yield from _yield_console(err_msg)
                try:
                    # original_run is a generator; yield from it directly
                    yield from original_run(command, *args, **kwargs)
                except Exception as ee:
                    yield from _yield_console(f"Local execution failed: {ee}")
            return _fallback_chain()
    
    # Monkey patch the run method
    st.session_state['interpreter'].computer.run = sandboxed_run
    st.session_state['interpreter'].computer.import_computer_api = True  # Import computer API for full functionality

    if st.session_state['api_choice'] == 'openrouter':
        st.session_state['interpreter'].llm.api_key = st.session_state['openrouter_key']
        st.session_state['interpreter'].llm.context_window = st.session_state['context_window']
    elif st.session_state['api_choice'] == 'openai':
        st.session_state['interpreter'].llm.api_key = st.session_state['openai_key']
        st.session_state['interpreter'].llm.context_window = st.session_state['context_window']
    elif st.session_state['api_choice'] == 'azure_openai':
        st.session_state['interpreter'].llm.api_key = st.session_state['openai_key']
        st.session_state['interpreter'].llm.api_base = st.session_state['azure_endpoint']
        st.session_state['interpreter'].llm.api_version = st.session_state['api_version']
    elif st.session_state['api_choice'] == 'vertexai':
        st.session_state['interpreter'].llm.context_window = st.session_state['context_window']
    elif st.session_state['api_choice'] == 'local':
        st.session_state['interpreter'].llm.context_window = st.session_state['context_window']
        st.session_state['interpreter'].offline = True
        if st.session_state['provider']=='Lmstudio':
            st.session_state['interpreter'].llm.model = "openai/x" # Tells OI to send messages in OpenAI's format
            st.session_state['interpreter'].llm.api_key = "fake_key" # LiteLLM, which we use to talk to LM Studio, requires this
            st.session_state['interpreter'].llm.api_base = st.session_state.get('api_base') # Point this at any OpenAI compatible server
        else:
            st.session_state['interpreter'].llm.model = f"ollama_chat/{st.session_state.get('model')}"
            st.session_state['interpreter'].llm.api_base = st.session_state.get('api_base')

    # Debug
    # st.write(interpreter.__dict__)
    # st.write(f'{interpreter.conversation_history_path=}')
    # st.write(f'{interpreter.conversation_filename =}')