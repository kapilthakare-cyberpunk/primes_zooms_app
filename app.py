
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from csv_processor import load_inventory, get_item_details, search_items
from ai_agents import RentalConsultant, PricingAssistant
import os

# --- Configuration --- #
try:
    _secret_key = st.secrets.get("GROQ_API_KEY")
except Exception:
    _secret_key = None
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", _secret_key or "")

# --- Streamlit UI --- #
st.set_page_config(page_title="Primes & Zooms AI Assistant", layout="wide")
st.title("Primes & Zooms AI Assistant")

# Sidebar for settings and file upload
st.sidebar.header("Settings")

# Groq API Key Input
groq_api_key_input = st.sidebar.text_input("Enter your Groq API Key", type="password", value=GROQ_API_KEY)
if groq_api_key_input:
    os.environ["GROQ_API_KEY"] = groq_api_key_input
    st.sidebar.success("Groq API Key set!")
else:
    st.sidebar.warning("Please enter your Groq API Key to use the AI features.")

# CSV File Upload
st.sidebar.header("Inventory Management")
uploaded_file = st.sidebar.file_uploader("Upload your CSV Inventory File", type=["csv"])

if uploaded_file is not None:
    st.sidebar.success("CSV file uploaded successfully!")
    st.session_state["inventory_df"] = load_inventory(uploaded_file)
    if st.session_state["inventory_df"] is not None:
        st.sidebar.write(f"Loaded {len(st.session_state["inventory_df"])} items.")
    else:
        st.sidebar.error("Failed to load inventory. Please check CSV format.")
else:
    st.session_state["inventory_df"] = None

# Main content area
st.header("AI Assistant Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if groq_api_key_input and st.session_state.get("inventory_df") is not None:
    mode = st.radio(
        "Choose AI Mode:",
        ("Rental Consultant", "Pricing Assistant"),
        horizontal=True
    )

    if prompt := st.chat_input("Ask me anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            if mode == "Rental Consultant":
                consultant = RentalConsultant(groq_api_key_input, st.session_state["inventory_df"])
                full_response = consultant.consult(prompt)
            elif mode == "Pricing Assistant":
                # For simplicity, let's assume the prompt for pricing assistant includes the item name
                # A more robust solution would involve parsing the prompt or having separate input fields
                pricing_assistant = PricingAssistant(groq_api_key_input, st.session_state["inventory_df"])
                full_response = pricing_assistant.suggest_pricing(prompt) # Assuming prompt is item name for now
            
            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
else:
    st.info("Please enter your Groq API Key and upload an inventory CSV file to start.")

# --- PageAgent: In-page GUI Copilot --- #
if groq_api_key_input:
    # Inject PageAgent into the page (runs in component iframe)
    # Note: Streamlit renders components in iframes. Page-agent controls the
    # iframe's own DOM. For full page control, use the Chrome Extension or MCP Server.
    components.html(
        f"""
        <script type="module">
        import {{ PageAgent }} from 'https://cdn.jsdelivr.net/npm/page-agent@1.10.0/dist/esm/page-agent.js';

        window._pageAgentStatus = 'loading';
        try {{
            window._pageAgent = new PageAgent({{
                model: 'llama-3.3-70b-versatile',
                baseURL: 'https://api.groq.com/openai/v1',
                apiKey: '{groq_api_key_input}',
                language: 'en-US',
                autoInit: false,
            }});
            window._pageAgentStatus = 'ready';
        }} catch(e) {{
            window._pageAgentStatus = 'error: ' + e.message;
        }}
        </script>
        """,
        height=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.header("Page Agent Copilot")
    st.sidebar.caption("Control this page with natural language")

    copilot_prompt = st.sidebar.text_input(
        "Command",
        placeholder="e.g. Click the Rental Consultant radio button",
        key="copilot_input",
    )

    if copilot_prompt:
        with st.sidebar:
            with st.spinner("Page Agent working..."):
                result_holder = st.empty()
                components.html(
                    f"""
                    <script type="module">
                    async function runAgent() {{
                        try {{
                            if (!window.parent._pageAgent) {{
                                window.parent.postMessage({{
                                    type: 'page-agent-result',
                                    success: false,
                                    error: 'PageAgent not initialized'
                                }}, '*');
                                return;
                            }}
                            const result = await window.parent._pageAgent.execute({repr(copilot_prompt)});
                            window.parent.postMessage({{
                                type: 'page-agent-result',
                                success: true,
                                result: result
                            }}, '*');
                        }} catch(e) {{
                            window.parent.postMessage({{
                                type: 'page-agent-result',
                                success: false,
                                error: e.message
                            }}, '*');
                        }}
                    }}
                    runAgent();
                    </script>
                    """,
                    height=0,
                )
            result_holder.success("Command sent to Page Agent")
else:
    st.sidebar.markdown("---")
    st.sidebar.header("Page Agent Copilot")
    st.sidebar.info("Enter your Groq API Key to enable the Page Agent copilot.")
