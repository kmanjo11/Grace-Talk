import streamlit as st
import json
import re
import uuid
import platform
from urllib.parse import urlparse, urljoin
from streamlit.components.v1 import html
from streamlit_extras.add_vertical_space import add_vertical_space

from st_components.st_conversations import conversation_navigation
from src.utils.docker_executor import DockerCodeExecutor
from src.utils.firejail_executor import FirejailCodeExecutor
from src.utils.ubuntu_sandbox import UbuntuSandboxExecutor
from src.utils.python_sandbox import RestrictedEnvironment

import os

OPEN_AI = 'OpenAI'
AZURE_OPEN_AI = 'Azure OpenAI'
OPEN_ROUTER = 'Open Router'
VERTEX_AI = 'Vertex AI'
LOCAL_AI = 'Local LLM'
OPEN_AI_MOCK = 'OpenAI Mock'


def show_sandbox_status():
    """Display sandbox environment status in a modal-like interface"""
    st.subheader("🖥️ Sandbox Environment Status")
    
    # Initialize sandbox executors
    docker_executor = DockerCodeExecutor()
    firejail_executor = FirejailCodeExecutor()
    ubuntu_sandbox = UbuntuSandboxExecutor()
    python_sandbox = RestrictedEnvironment()
    
    # Check availability and get status
    sandboxes = [
        ("🐳 Docker", docker_executor),
        ("🔥 Firejail", firejail_executor), 
        ("🐧 Ubuntu", ubuntu_sandbox),
        ("🐍 Python", python_sandbox)
    ]
    
    st.write("**Available Execution Environments:**")
    
    for name, executor in sandboxes:
        try:
            is_available = executor.is_available()
            status_icon = "✅" if is_available else "❌"
            st.write(f"{status_icon} {name}: {'Available' if is_available else 'Not Available'}")
            
            # Show additional details if available
            if is_available and hasattr(executor, 'get_status'):
                try:
                    status_info = executor.get_status()
                    with st.expander(f"Details for {name}", expanded=False):
                        st.json(status_info)
                except:
                    pass
                    
        except Exception as e:
            st.write(f"❓ {name}: Error checking status ({str(e)[:50]}...)")
    
    # Show current preference
    prefer_local = st.session_state.get('prefer_local_exec', False)
    st.write(f"**Current Execution Preference:** {'Local' if prefer_local else 'Sandboxed'}")
    
    # Show Docker cache status
    docker_available = st.session_state.get('docker_available', False)
    docker_last_check = st.session_state.get('docker_last_check', 0)
    st.write(f"**Docker Cache:** {'Available' if docker_available else 'Unavailable'} (last checked: {docker_last_check})")
    
    # Environment controls
    st.write("**Environment Controls:**")
    
    if st.button("🔄 Refresh Status"):
        # Clear cache to force refresh
        if 'docker_available' in st.session_state:
            del st.session_state['docker_available']
        if 'docker_last_check' in st.session_state:
            del st.session_state['docker_last_check']
        st.rerun()
    
    new_prefer_local = st.checkbox("Prefer Local Execution", value=prefer_local)
    if new_prefer_local != prefer_local:
        st.session_state['prefer_local_exec'] = new_prefer_local
        st.rerun()


def st_sidebar():
    # try:
    with st.sidebar:
        # Commit Lessons (RAG) toggles
        if 'use_commit_lessons' not in st.session_state:
            st.session_state['use_commit_lessons'] = False
        if 'show_lessons_ui' not in st.session_state:
            st.session_state['show_lessons_ui'] = False

        # Sandbox Environment Status
        with st.expander("🖥️ Environment Status", expanded=False):
            if st.button("🔍 Show Sandbox Status", help="View current sandbox environment details"):
                show_sandbox_status()
            if st.button("📺 Live Sandbox View", help="Open live sandbox display window"):
                # Open popup window instead of inline display
                import streamlit.components.v1 as components
                components.html("""
                <script>
                var popup = window.open('', 'sandbox_monitor', 'width=400,height=300,scrollbars=yes,resizable=yes');
                popup.document.write(`
                <html>
                <head><title>Live Sandbox Monitor</title></head>
                <body style="margin:0;padding:20px;font-family:monospace;background:#1e1e1e;color:#00ff00;">
                    <h2>🖥️ Live Sandbox Monitor</h2>
                    <div id="status">🔴 LIVE - Waiting for activity...</div>
                    <div id="output" style="height:300px;overflow-y:scroll;border:1px solid #333;padding:10px;margin-top:10px;background:#000;"></div>
                    <script>
                        setInterval(() => {
                            document.getElementById("status").innerHTML = "🔴 LIVE - " + new Date().toLocaleTimeString();
                        }, 1000);
                    </script>
                </body>
                </html>
                `);
                popup.document.close();
                </script>
                """, height=0)
        
        with st.expander("Knowledge Augmentation", expanded=False):
            st.session_state['use_commit_lessons'] = st.checkbox(
                'Use Commit Lessons (RAG)', value=st.session_state['use_commit_lessons'], help='Augment prompts with retrieved fix patterns behind the scenes.'
            )
            st.session_state['show_lessons_ui'] = st.checkbox(
                'Show related lessons in UI', value=st.session_state['show_lessons_ui'], help='If enabled, shows a collapsible list of related lessons below responses.'
            )
            # PDF context toggle
            if 'use_pdf_context' not in st.session_state:
                st.session_state['use_pdf_context'] = True
            st.session_state['use_pdf_context'] = st.checkbox(
                'Use PDF Context (LlamaParse)', value=st.session_state['use_pdf_context'], help='If enabled, OI extracts text from uploaded PDFs and uses compact excerpts invisibly when relevant.'
            )
            # Knowledge Base toggle
            if 'use_kb' not in st.session_state:
                st.session_state['use_kb'] = True
            st.session_state['use_kb'] = st.checkbox(
                'Use Knowledge Base', value=st.session_state['use_kb'], help='If enabled, OI retrieves relevant sections from your Markdown/Text knowledge base (e.g., DCMA 14 pt.md).'
            )
            # Image OCR toggle
            if 'use_image_ocr' not in st.session_state:
                st.session_state['use_image_ocr'] = True
            st.session_state['use_image_ocr'] = st.checkbox(
                'Use Image OCR (Tesseract)', value=st.session_state['use_image_ocr'], help='If enabled, OI extracts text from uploaded images/screenshots for relevant context (requires system tesseract binary).'
            )
            # Schedule Focus Mode
            if 'schedule_focus_mode' not in st.session_state:
                st.session_state['schedule_focus_mode'] = False
            st.session_state['schedule_focus_mode'] = st.checkbox(
                'Schedule Focus Mode', value=st.session_state['schedule_focus_mode'],
                help='When enabled, OI limits augmentations to P6 context, PDFs, and Knowledge Base. Lessons and auto-grep are suppressed to keep answers on-task.'
            )

        # Execution & dependencies policy
        with st.expander("Execution Policy", expanded=False):
            if 'allow_auto_exec' not in st.session_state:
                st.session_state['allow_auto_exec'] = False
            st.session_state['allow_auto_exec'] = st.checkbox(
                'Allow Auto-Execution (trusted sandbox)', value=st.session_state['allow_auto_exec'],
                help='If enabled, OI may run safe commands/tests/formatters autonomously to diagnose and fix issues.'
            )
            if 'allow_auto_installs' not in st.session_state:
                st.session_state['allow_auto_installs'] = False
            st.session_state['allow_auto_installs'] = st.checkbox(
                'Allow On-Demand Dependency Installs', value=st.session_state['allow_auto_installs'],
                help='If enabled, OI may pip-install missing Python packages when needed to complete a task.'
            )
            if 'prefer_local_exec' not in st.session_state:
                st.session_state['prefer_local_exec'] = False
            st.session_state['prefer_local_exec'] = st.checkbox(
                'Prefer Local Execution (skip Docker/Firejail)', value=st.session_state['prefer_local_exec'],
                help='If enabled, OI will not attempt Docker or Firejail and will execute directly in the local environment.'
            )
            # Show/hide execution console output in chat
            if 'show_exec_output' not in st.session_state:
                st.session_state['show_exec_output'] = False
            st.session_state['show_exec_output'] = st.checkbox(
                'Show Execution Output in Chat', value=st.session_state['show_exec_output'],
                help='If disabled, OI hides command/process output in the chat, showing only a spinner.'
            )

            # Subtle sandbox status indicator
            docker_status = 'available' if st.session_state.get('docker_available') else 'unavailable'
            st.caption(f"Sandbox: Docker {docker_status}")

        # Response style
        with st.expander("Response Style", expanded=False):
            if 'concise_mode' not in st.session_state:
                st.session_state['concise_mode'] = True
            st.session_state['concise_mode'] = st.checkbox(
                'Concise Mode (no meta, no code unless asked)', value=st.session_state['concise_mode'],
                help='Keeps answers short and on-topic. Suppresses apologies, recaps, and code unless explicitly requested.'
            )

        # Global Chat Files Uploader
        with st.expander("Chat Files (upload/browse)", expanded=False):
            if 'chat_files' not in st.session_state:
                st.session_state['chat_files'] = {}
            chat_uploads_dir = os.path.join('.', 'workspace', 'chat_uploads')
            os.makedirs(chat_uploads_dir, exist_ok=True)

            files = st.file_uploader(
                label='Upload files for this workspace (available to all conversations)',
                type=None,
                accept_multiple_files=True,
                key='global_chat_uploader'
            )
            if files:
                for f in files:
                    dest_path = os.path.join(chat_uploads_dir, f.name)
                    try:
                        with open(dest_path, 'wb') as out:
                            out.write(f.getbuffer())
                        st.session_state['chat_files'][f.name] = dest_path
                    except Exception as e:
                        st.warning(f"Could not save {f.name}: {e}")

            if st.session_state['chat_files']:
                st.caption('Available files:')
                for name, path in st.session_state['chat_files'].items():
                    st.write(f"- {name} → {path}")
                if st.button('Clear uploaded file list (keeps files on disk)'):
                    st.session_state['chat_files'] = {}

        # Downloads panel (only artifacts explicitly saved to exports by OI)
        with st.expander("Downloads", expanded=False):
            exports_dir = os.path.join('.', 'workspace', 'exports')
            os.makedirs(exports_dir, exist_ok=True)
            try:
                files = sorted(
                    [f for f in os.listdir(exports_dir) if os.path.isfile(os.path.join(exports_dir, f))]
                )
            except Exception:
                files = []
            if not files:
                st.caption('No exported artifacts yet. When OI saves deliverables to exports/, they will appear here.')
            else:
                for fname in files:
                    fpath = os.path.join(exports_dir, fname)
                    try:
                        with open(fpath, 'rb') as fh:
                            data = fh.read()
                        st.download_button(label=f"Download {fname}", data=data, file_name=fname, key=f"dl_{fname}")
                    except Exception as e:
                        st.write(f"{fname}: unavailable ({e})")

        # Per-conversation Working Folder (documents related to this thread)
        with st.expander("Working Folder (this conversation)", expanded=False):
            # Use conversation-specific directory
            conv_id = None
            try:
                conv_id = st.session_state['current_conversation']['id']
            except Exception:
                pass
            if conv_id:
                conv_dir = os.path.join('.', 'workspace', 'conversations', conv_id)
                os.makedirs(conv_dir, exist_ok=True)
                try:
                    cfiles = sorted(
                        [f for f in os.listdir(conv_dir) if os.path.isfile(os.path.join(conv_dir, f))]
                    )
                except Exception:
                    cfiles = []
                if not cfiles:
                    st.caption('No files yet. When OI or you save per-conversation artifacts, they will appear here.')
                else:
                    for fname in cfiles:
                        fpath = os.path.join(conv_dir, fname)
                        try:
                            with open(fpath, 'rb') as fh:
                                data = fh.read()
                            st.download_button(label=f"Download {fname}", data=data, file_name=fname, key=f"dl_conv_{fname}")
                        except Exception as e:
                            st.write(f"{fname}: unavailable ({e})")
            else:
                st.caption('Conversation not initialized yet.')
        # Select choice of API Server
        api_server = st.selectbox('Your API Server', [
                                  OPEN_AI, AZURE_OPEN_AI, OPEN_ROUTER, VERTEX_AI, LOCAL_AI, OPEN_AI_MOCK])

        # Set credentials based on choice of API Server
        if api_server == OPEN_AI:
            set_open_ai_credentials()
        elif api_server == AZURE_OPEN_AI:
            set_azure_open_ai_credentials()
        elif api_server == OPEN_ROUTER:
            set_open_router_credentials()
        elif api_server == VERTEX_AI:
            set_vertex_ai_credentials()
        elif api_server == LOCAL_AI:
            local_server_credentials()
        elif api_server == OPEN_AI_MOCK:
            st.warning('under construction')

        # Section dedicated to navigate conversations
        conversation_navigation()

        # Section dedicated to About Us
        about_us()

    # except Exception as e:
    #     st.error(e)


# About Us Section
def about_us():
    add_vertical_space(8)
    html_chat = '<center><h5>🤗 Support the project with a donation for the development of new Features 🤗</h5>'
    st.markdown(html_chat, unsafe_allow_html=True)
    button = '<script type="text/javascript" src="https://cdnjs.buymeacoffee.com/1.0.0/button.prod.min.js" data-name="bmc-button" data-slug="blazzmocompany" data-color="#FFDD00" data-emoji=""  data-font="Cookie" data-text="Buy me a coffee" data-outline-color="#000000" data-font-color="#000000" data-coffee-color="#ffffff" ></script>'
    html(button, height=70, width=220)
    iframe = '<style>iframe[width="220"]{position: absolute; top: 50%;left: 50%;transform: translate(-50%, -50%);margin:26px 0}</style>'
    st.markdown(iframe, unsafe_allow_html=True)
    add_vertical_space(2)
    st.write('<center><h6>Made with ❤️ by <a href="mailto:blazzmo.company@gmail.com">BlazzByte</a></h6>',
             unsafe_allow_html=True)
    st.write('<center><h6>Contribution 🤝 by <a href="mailto:tranhoangnguyen03@gmail.com">Sergeant113</a></h6>',
             unsafe_allow_html=True)

# Setup OpenAI


def set_open_ai_credentials():
    with st.expander(label="Settings", expanded=(not st.session_state['chat_ready'])):
        openai_key = st.text_input('OpenAI Key:', type="password")
        os.environ['OPENAI_API_KEY'] = openai_key
        model = st.selectbox(
            label='🔌 models',
            options=list(st.session_state['models']['openai'].keys()),
            index=0,
            # disabled= not st.session_state.openai_key # Comment: Why?
        )
        context_window = st.session_state['models']['openai'][model]['context_window']

        temperature = st.slider('🌡 Tempeture', min_value=0.01, max_value=1.0
                               , value=st.session_state.get('temperature', 0.5), step=0.01)
        max_tokens = st.slider('📝 Max tokens', min_value=1, max_value=2000
                              , value=st.session_state.get('max_tokens', 512), step=1)

        num_pair_messages_recall = st.slider(
            '**Memory Size**: user-assistant message pairs', min_value=1, max_value=10, value=5)

        button_container = st.empty()
        save_button = button_container.button(
            "Save Changes 🚀", key='open_ai_save_model_configs')

        if save_button and openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
            st.session_state['api_choice'] = 'openai'
            st.session_state['openai_key'] = openai_key
            st.session_state['model'] = model
            st.session_state['temperature'] = temperature
            st.session_state['max_tokens'] = max_tokens
            st.session_state['context_window'] = context_window

            st.session_state['num_pair_messages_recall'] = num_pair_messages_recall

            st.session_state['chat_ready'] = True
            button_container.empty()  # Rerun does not allow it
            st.rerun()

# Setup Azure OpenAI


def set_azure_open_ai_credentials():
    with st.expander(label="Settings", expanded=(not st.session_state['chat_ready'])):
        azure_openai_key = st.text_input('Azure OpenAI Key:', type="password")
        azure_endpoint = st.text_input(
            'Azure endpoint', placeholder="https://{your-resource-name}.openai.azure.com")
        deployment_id = st.text_input(
            'deployment-id', help="The deployment name you choose when you deployed the model.")
        api_version = st.text_input(
            'api-version', help="The API version to use for this operation. This follows the YYYY-MM-DD format.")
        temperature = st.slider('🌡 Temperature', min_value=0.01, max_value=1.0
                               , value=st.session_state.get('temperature', 0.5), step=0.01)
        max_tokens = st.slider('📝 Max tokens', min_value=1, max_value=2000
                              , value=st.session_state.get('max_tokens', 512), step=1)
        num_pair_messages_recall = st.slider(
            '**Memory Size**: user-assistant message pairs', min_value=1, max_value=10, value=5)
        button_container = st.empty()
        save_button = button_container.button(
            "Save Changes 🚀", key='open_ai_save_model_configs')

        if save_button and azure_openai_key:
            st.session_state['api_choice'] = 'azure_openai'
            st.session_state['openai_key'] = azure_openai_key
            st.session_state['model'] = f"azure/{deployment_id}"
            st.session_state['azure_endpoint'] = azure_endpoint
            st.session_state['api_version'] = api_version
            st.session_state['temperature'] = temperature
            st.session_state['max_tokens'] = max_tokens
            st.session_state['num_pair_messages_recall'] = num_pair_messages_recall
            st.session_state['chat_ready'] = True
            button_container.empty()
            st.rerun()

# Setup Open Router


def set_open_router_credentials():
    with st.expander(label="Settings", expanded=(not st.session_state['chat_ready'])):
        openrouter_key = st.text_input('Open Router Key:', type="password")
        openrouter_api_base = "https://openrouter.ai/api/v1/chat/completions"
        openrouter_headers = {
            # To identify your app. Can be set to e.g. http://localhost:3000 for testing
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Open-Interpreter Gpt App",  # Optional. Shows on openrouter.ai
        }

        model = st.selectbox(
            label='🔌 models',
            options=list(st.session_state['models']['openrouter'].keys()),
            index=0,
            # disabled= not st.session_state.openai_key # Comment: Why?
        )
        context_window = st.session_state['models']['openrouter'][model]['context_window']

        temperature = st.slider('🌡 Tempeture', min_value=0.01, max_value=1.0
                               , value=st.session_state.get('temperature', 0.5), step=0.01)
        max_tokens = st.slider('📝 Max tokens', min_value=1, max_value=2000
                              , value=st.session_state.get('max_tokens', 512), step=1)

        num_pair_messages_recall = st.slider(
            '**Memory Size**: user-assistant message pairs', min_value=1, max_value=10, value=5)

        button_container = st.empty()
        save_button = button_container.button(
            "Save Changes 🚀", key='open_router_save_model_configs')

        if save_button and openrouter_key:
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
            os.environ["OR_SITE_URL"] = openrouter_headers["HTTP-Referer"]
            os.environ["OR_APP_NAME"] = openrouter_headers["X-Title"]
            st.session_state['api_choice'] = 'openrouter'
            st.session_state['openrouter_key'] = openrouter_key
            st.session_state['openrouter_api_base'] = openrouter_api_base
            st.session_state['openrouter_headers'] = openrouter_headers
            st.session_state['model'] = f'openrouter/{model}'
            st.session_state['temperature'] = temperature
            st.session_state['max_tokens'] = max_tokens
            st.session_state['context_window'] = context_window

            st.session_state['num_pair_messages_recall'] = num_pair_messages_recall

            st.session_state['chat_ready'] = True
            button_container.empty()
            st.rerun()

# Setup Vertex AI


def set_vertex_ai_credentials():

    def validate_json_content(data):
        required_keys = ['project_id', 'private_key', 'client_email']
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            return False, f"The following keys are missing in the JSON file: {', '.join(missing_keys)}"
        else:
            return True, "JSON file contains all necessary elements"

    def save_validated_credentials(data):
        # Define the file path for the new JSON file
        json_file_name = f'{str(uuid.uuid4())}.json'

        output_path = os.path.join(os.getcwd(), json_file_name)
        with open(output_path, 'w', encoding='utf-8') as outfile:
            json.dump(json_dict, outfile, indent=2)

        return output_path

    def delete_json_file(json_file_name):
        try:
            os.remove(json_file_name)
            st.success(f"{json_file_name} has been deleted!")
        except FileNotFoundError:
            st.warning(f"{json_file_name} does not exist.")

    with st.expander(label="Settings", expanded=(not st.session_state['chat_ready'])):
        if 'ruta_saved' not in st.session_state:
            uploaded_file = st.file_uploader("Upload your JSON file credentials", type=["json"])
            if uploaded_file:
                bytes_data = uploaded_file.getvalue()
                json_string = bytes_data.decode('utf-8')
                json_dict = json.loads(json_string)
                # file_contents = uploaded_file.read()
                # json_dict = json.loads(file_contents)
                # Validate the JSON data
                is_valid, message = validate_json_content(json_dict)
                if is_valid:
                    st.write("Validation successful:", message)
                    # Save the loaded JSON under a new filename
                    ruta = save_validated_credentials(data=json_dict)
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ruta
                    os.environ['VERTEXAI_PROJECT'] = json_dict['project_id']
                    st.session_state.ruta_saved = ruta
                    st.rerun()
                else:
                    st.error(f"Validation failed: {message}", icon='⚠️')

        else:
            # Create the Streamlit button to delete the JSON file
            st.success('JSON saved successfully')
            if st.button("Delete JSON file"):
                delete_json_file(json_file_name=st.session_state.ruta_saved)
                os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS')
                os.environ.pop('VERTEXAI_PROJECT')
                if 'VERTEXAI_LOCATION' in os.environ:
                    os.environ.pop('VERTEXAI_LOCATION')
                del st.session_state.ruta_saved
                st.rerun()

        location = st.selectbox(
            label='Select Region',
            options=['Iowa (us-central1)', 'Northern Virginia (us-east4)', 'Oregon (us-west1)', 'Las Vegas (us-west4)', 'Montréal (northamerica-northeast1)', 'Belgium (europe-west1)', 'London (europe-west2)',
                     'Frankfurt (europe-west3)', 'Netherlands (europe-west4)', 'Paris (europe-west9)', 'Tokyo (asia-northeast1)', 'Seoul (asia-northeast3)', 'Singapore (asia-southeast1)'],
            index=0,
            help='The location of your Vertex AI resources.'
        )

        model = st.selectbox(
            label='🔌 models',
            options=list(st.session_state['models']['vertexai'].keys()),
            index=0
        )

        context_window = st.session_state['models']['vertexai'][model]['context_window']

        temperature = st.slider('🌡 Temperature', min_value=0.01, max_value=1.0
                               , value=st.session_state.get('temperature', 0.5), step=0.01)
        max_tokens = st.slider('📝 Max tokens', min_value=1, max_value=2000
                              , value=st.session_state.get('max_tokens', 512), step=1)

        num_pair_messages_recall = st.slider(
            '**Memory Size**: user-assistant message pairs', min_value=1, max_value=10, value=5)

        button_container = st.empty()
        save_button = button_container.button(
            "Save Changes 🚀", key='open_router_save_model_configs')

        if save_button and 'ruta_saved' in st.session_state:

            match = re.search(r'\((.*?)\)', location)
            if match:
                os.environ['VERTEXAI_LOCATION'] = match.group(1)

            st.session_state['api_choice'] = 'vertexai'
            st.session_state['model'] = f'vertex_ai/{model}'
            st.session_state['temperature'] = temperature
            st.session_state['max_tokens'] = max_tokens
            st.session_state['context_window'] = context_window

            st.session_state['num_pair_messages_recall'] = num_pair_messages_recall

            st.session_state['chat_ready'] = True
            button_container.empty()
            st.rerun()


# Setup Local LLM
def local_server_credentials():

    def validate_local_host_link(link):
        prefixes = ['http://localhost', 'https://localhost',
                    'http://127.0.0.1', 'https://127.0.0.1']
        return any(link.startswith(prefix) for prefix in prefixes)

    def validate_provider(link, provider):
        return link if provider != 'Lmstudio' else link + '/v1' if not link.endswith('/v1') else link

    def parse_and_correct_url(url):
        parsed_url = urlparse(url)
        corrected_url = urljoin(parsed_url.geturl(), parsed_url.path)
        return corrected_url

    def submit():
        if platform.system() == 'Linux' and not validate_local_host_link(st.session_state.widget) and st.session_state.widget != '':
            link = validate_provider(
                link=st.session_state.widget, provider=local_provider)
            print('Linux')
            st.session_state.widget = parse_and_correct_url(link)

        else:
            print(platform.system() == 'Linux', validate_local_host_link(
                st.session_state.widget), st.session_state.widget != '')
            if platform.system() != 'Linux' and validate_local_host_link(st.session_state.widget) and st.session_state.widget != '':
                link = validate_provider(link=st.session_state.widget, provider=local_provider)
                print('here')
                st.session_state.widget = parse_and_correct_url(link)
            else:
                print('empty')
                st.session_state.widget = ''

    with st.expander(label="Settings", expanded=(not st.session_state['chat_ready'])):
        local_provider = st.selectbox(
            label='Local Provider',
            options=['Lmstudio', 'Ollama'],
            index=0,
        )
        api_base = st.text_input(
            label='Put here your Api Base Link', 
            value=st.session_state.get('api_base', ''),
            placeholder='http://localhost:1234/v1' if local_provider == 'Lmstudio' else 'http://localhost:11434', 
            key='widget', 
            on_change=submit)

        model = st.text_input(label='Model Name [get here](https://ollama.com/library)' if local_provider == 'Ollama' else 'Model Name [get here](https://huggingface.co/models?pipeline_tag=text-generation)',
                              value=st.session_state.get('model', 'mistral') if local_provider == 'Ollama' else 'openai/x', disabled=False if local_provider == 'Ollama' else True)
        context_window = st.selectbox(
            label='Input/Output token windows',
            options=['512', '1024', '2048', '4096', '8192', '16384', '32768'],
            index=0,
        )

        # context_window = st.slider('Input/Output token window', min_value=512, max_value=32768, value=st.session_state.get('context_window', st.session_state.get('window', 512)), step=st.session_state.get('window', 512)*2, key='window')
        temperature = st.slider('🌡 Temperature', min_value=0.01, max_value=1.0
                               , value=st.session_state.get('temperature', 0.5), step=0.01)
        max_tokens = st.slider('📝 Max tokens', min_value=1, max_value=2000
                              , value=st.session_state.get('max_tokens', 512), step=1)

        num_pair_messages_recall = st.slider(
            '**Memory Size**: user-assistant message pairs', min_value=1, max_value=10, value=5)

        button_container = st.empty()
        save_button = button_container.button("Save Changes 🚀", key='open_ai_save_model_configs')

        if save_button and api_base and model:
            st.session_state['provider'] = local_provider
            st.session_state['api_choice'] = 'local'
            st.session_state['api_base'] = api_base
            st.session_state['model'] = model
            st.session_state['temperature'] = temperature
            st.session_state['max_tokens'] = max_tokens
            st.session_state['context_window'] = context_window

            st.session_state['num_pair_messages_recall'] = num_pair_messages_recall

            st.session_state['chat_ready'] = True
            button_container.empty()
            st.rerun()