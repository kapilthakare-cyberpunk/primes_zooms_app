import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from csv_processor import load_inventory, get_item_details, search_items
from ai_agents import RentalConsultant, PricingAssistant
import os

# --- Configuration --- #
PRICELIST_PATH = os.path.join(os.path.dirname(__file__), "Pricelist_20260703.csv")
try:
    _secret_key = st.secrets.get("GROQ_API_KEY")
except Exception:
    _secret_key = None
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", _secret_key or "")

# --- Streamlit UI --- #
st.set_page_config(page_title="Primes & Zooms AI Assistant", layout="wide")
st.title("Primes & Zooms AI Assistant")

# Sidebar for settings
st.sidebar.header("Settings")

# Groq API Key Input
groq_api_key_input = st.sidebar.text_input(
    "Enter your Groq API Key", type="password", value=GROQ_API_KEY
)
if groq_api_key_input:
    os.environ["GROQ_API_KEY"] = groq_api_key_input
    st.sidebar.success("Groq API Key set!")
else:
    st.sidebar.warning("Please enter your Groq API Key to use the AI features.")

# Auto-load pricelist
st.sidebar.header("Inventory")
if os.path.exists(PRICELIST_PATH):
    st.session_state["inventory_df"] = load_inventory(PRICELIST_PATH)
    if st.session_state["inventory_df"] is not None:
        st.sidebar.success(
            f"Loaded {len(st.session_state['inventory_df'])} items from pricelist."
        )
    else:
        st.sidebar.error("Failed to load pricelist CSV. Check format.")
else:
    st.sidebar.error(f"Pricelist not found: {PRICELIST_PATH}")
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
        "Choose AI Mode:", ("Rental Consultant", "Pricing Assistant"), horizontal=True
    )

    if prompt := st.chat_input("Ask me anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            if mode == "Rental Consultant":
                consultant = RentalConsultant(
                    groq_api_key_input, st.session_state["inventory_df"]
                )
                full_response = consultant.consult(prompt)
            elif mode == "Pricing Assistant":
                # For simplicity, let's assume the prompt for pricing assistant includes the item name
                # A more robust solution would involve parsing the prompt or having separate input fields
                pricing_assistant = PricingAssistant(
                    groq_api_key_input, st.session_state["inventory_df"]
                )
                full_response = pricing_assistant.suggest_pricing(
                    prompt
                )  # Assuming prompt is item name for now

            message_placeholder.markdown(full_response)
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )
else:
    st.info("Please enter your Groq API Key and upload an inventory CSV file to start.")

# --- New Item Pricing Band Calculator --- #
st.markdown("---")
st.header("New Item Pricing Band Calculator")

st.markdown("""
Generate rental pricing bands for new inventory items based on:
- **Existing pricelist patterns** (learned from 1300+ items)
""")

# Initialize pricing results in session state
if "pricing_results" not in st.session_state:
    st.session_state.pricing_results = []

# Input form
col1, col2 = st.columns(2)

with col1:
    new_sku = st.text_input("SKU", placeholder="e.g., C2470F28RF")
    new_name = st.text_input(
        "Item Name", placeholder="e.g., Canon RF 24-70mm f/2.8L IS USM"
    )
    new_brand = st.selectbox(
        "Brand",
        [
            "",
            "Canon",
            "Sony",
            "Nikon",
            "Fujifilm",
            "Panasonic",
            "Sigma",
            "Tamron",
            "Other",
        ],
    )

with col2:
    new_mrp = st.number_input(
        "Purchase Cost / MRP (₹)",
        min_value=0,
        step=1000,
        help="Leave 0 for auto OEM lookup",
    )
    new_type = st.selectbox(
        "Type", ["Lens", "Body", "Accessory", "Lighting", "Audio", "Storage", "Support"]
    )
    new_category = st.selectbox(
        "Category",
        [
            "Mid Range",
            "Tele",
            "Wide Angle",
            "Super Tele",
            "Macro",
            "Full Frame",
            "Crop Sensor",
            "High-end Super-tele",
            "Video Cameras",
            "Other",
        ],
    )

# Generate button
if st.button("Generate Pricing Bands", type="primary"):
    if not new_name:
        st.error("Please enter an item name")
    else:
        with st.spinner("Generating pricing bands..."):
            from pricing_engine import generate_pricing_band

            result, error = generate_pricing_band(
                item_name=new_name,
                sku=new_sku or f"NEW-{len(st.session_state.pricing_results) + 1:03d}",
                mrp=new_mrp if new_mrp > 0 else None,
                brand=new_brand if new_brand else None,
                item_type=new_type,
                res_grp=new_category,
            )

            if error:
                st.error(error)
            else:
                st.session_state.pricing_results.append(result)
                st.success("Pricing band generated!")

                # Display result
                st.markdown(f"""
                ### Generated Pricing Band

                | Field | Value |
                |-------|-------|
                | **SKU** | `{result["sku"]}` |
                | **Item** | {result["item_name"]} |
                | **MRP** | ₹{result["mrp"]:,} |
                | **Category** | {result["item_type"]} / {result["res_grp"]} |
                | **Pricing Band** | `{result["bands_str"]}` |
                | **Source** | {result["source"]} |
                """)

# Display accumulated results
if st.session_state.pricing_results:
    st.markdown("---")
    st.subheader("Generated Pricing Bands")

    # Create dataframe for display
    results_df = pd.DataFrame(
        [
            {
                "Sr No": i + 1,
                "SKU": r["sku"],
                "Item Name": r["item_name"],
                "Date": r["date"],
                "Pricing Band": r["bands_str"],
            }
            for i, r in enumerate(st.session_state.pricing_results)
        ]
    )

    st.dataframe(results_df, use_container_width=True)

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Save to CSV", type="secondary"):
            from pricing_engine import save_to_csv

            csv_path = save_to_csv(st.session_state.pricing_results)
            st.success(f"Saved to `{csv_path}`")

    with col2:
        if st.button("Push to GitHub", type="secondary"):
            from pricing_engine import push_to_github

            with st.spinner("Pushing to GitHub..."):
                success, msg = push_to_github()
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    with col3:
        if st.button("Clear Results", type="secondary"):
            st.session_state.pricing_results = []
            st.rerun()

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
