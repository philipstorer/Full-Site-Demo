import streamlit as st
import pandas as pd
import openai
import json
import os
import re

# ------------------------------------
# Inline CSS for Sidebar, Navigation, and Footer
# ------------------------------------
st.markdown(
    """
    <style>
    /* Sidebar (Navigation Pane) */
    [data-testid="stSidebar"] {
        background-color: #f0f0f0;
        width: 240px !important;
        position: relative;
        padding: 10px;
    }
    /* Sidebar Title */
    .sidebar-title {
        font-size: 1rem;
        margin: 0;
        text-align: left;
    }
    /* Navigation Links */
    .custom-nav ul {
        list-style: none;
        margin: 0;
        padding: 0;
    }
    .custom-nav li {
        margin: 0;
        padding: 5px 0;
    }
    .custom-nav li a {
        text-decoration: none;
        color: inherit;
        display: block;
        padding: 5px 10px;
    }
    .custom-nav li.active a {
        background-color: #d3d3d3;
        border-radius: 4px;
        padding: 5px 10px;
        width: 100%;
        box-sizing: border-box;
    }
    /* Sidebar Footer (Bottom Left of Sidebar) */
    .sidebar-footer {
        position: absolute;
        bottom: 10px;
        left: 10px;
        font-size: 0.8rem;
        color: #555;
    }
    /* Main Page Footer (Full Width) */
    .custom-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #444444;
        color: white;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding: 4px 20px;
        font-size: 0.9em;
        z-index: 99999;
    }
    .custom-footer a {
        color: #dddddd;
        margin-left: 10px;
        text-decoration: none;
    }
    .custom-footer a:hover {
        color: #ffffff;
    }
    /* Reduce vertical spacing for select boxes */
    .stSelectbox, .stMultiSelect {
        margin-top: 2px;
        margin-bottom: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------------
# Secure API Key Handling
# ------------------------------------
if "openai" in st.secrets and "api_key" in st.secrets["openai"]:
    openai.api_key = st.secrets["openai"]["api_key"]
else:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        st.error("OpenAI API key not found. Please set it in .streamlit/secrets.toml or as an environment variable.")
        st.stop()
    openai.api_key = openai_api_key

# ------------------------------------
# Load Criteria from Excel (Sheet1)
# ------------------------------------
@st.cache_data
def load_criteria(filename):
    try:
        df = pd.read_excel(filename, sheet_name=0, header=0, usecols="A:M")
        if df.shape[1] < 13:
            st.error(f"Excel file has only {df.shape[1]} columns but at least 13 are required. Check file formatting.")
            return None, None, None, None
        # Extract options:
        role_options = df.columns[1:4].tolist()  # Columns B-D
        role_options = [opt for opt in role_options if opt.lower() != "caregiver"]
        lifecycle_options = df.columns[5:9].tolist()  # Columns F-I
        journey_options = df.columns[9:13].tolist()   # Columns J-M
        matrix_df = df.copy()
        return role_options, lifecycle_options, journey_options, matrix_df
    except Exception as e:
        st.error(f"Error reading the Excel file (Sheet1): {e}")
        return None, None, None, None

role_options, lifecycle_options, journey_options, matrix_df = load_criteria("test.xlsx")
if any(v is None for v in [role_options, lifecycle_options, journey_options, matrix_df]):
    st.stop()

# ------------------------------------
# Define Placeholders and Disease State Options
# ------------------------------------
role_placeholder = "Audience"
lifecycle_placeholder = "Product Life Cycle"
journey_placeholder = "Customer Journey Focus"
disease_placeholder = "Disease State"

role_dropdown_options = [role_placeholder] + role_options
lifecycle_dropdown_options = [lifecycle_placeholder] + lifecycle_options
journey_dropdown_options = [journey_placeholder] + journey_options

disease_states = [
    "Diabetes", "Hypertension", "Asthma", "Depression", "Arthritis",
    "Alzheimer's", "COPD", "Obesity", "Cancer", "Stroke"
]
disease_dropdown_options = [disease_placeholder] + disease_states

# ------------------------------------
# Helper: Filter Strategic Imperatives from Matrix (Sheet1)
# ------------------------------------
def filter_strategic_imperatives(df, role, lifecycle, journey):
    if role not in df.columns or lifecycle not in df.columns or journey not in df.columns:
        st.error("The Excel file's columns do not match the expected names for filtering.")
        return []
    try:
        filtered = df[
            (df[role].astype(str).str.lower() == 'x') &
            (df[lifecycle].astype(str).str.lower() == 'x') &
            (df[journey].astype(str).str.lower() == 'x')
        ]
        return filtered["Strategic Imperative"].dropna().tolist()
    except Exception as e:
        st.error(f"Error filtering strategic imperatives: {e}")
        return []

# ------------------------------------
# Helper: Generate Tactical Recommendation via OpenAI API
# ------------------------------------
def generate_ai_output(tactic_text, selected_differentiators):
    differentiators_text = ", ".join(selected_differentiators) if selected_differentiators else "None"
    prompt = f"""
You are an expert pharmaceutical marketing strategist.
Given the following tactic: "{tactic_text}"
and considering the selected product differentiators: "{differentiators_text}",
explain in 2-3 sentences how implementing this tactic will deliver on the strategic imperative,
detailing how its unique aspects align with and leverage these differentiators.
Also, provide an estimated cost range in USD and an estimated timeframe in months for implementation.
Return ONLY a JSON object with exactly the following keys: "description", "cost", "timeframe". Do not include any additional text.
    """
    try:
        with st.spinner("Generating tactical recommendation..."):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert pharmaceutical marketing strategist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
        content = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            st.error("No valid JSON object found in the response.")
            return {"description": "N/A", "cost": "N/A", "timeframe": "N/A"}
        try:
            output = json.loads(json_str)
        except json.JSONDecodeError:
            st.error("Error decoding the JSON object. Please try again.")
            output = {"description": "N/A", "cost": "N/A", "timeframe": "N/A"}
        return output
    except Exception as e:
        st.error(f"Error generating tactical recommendation: {e}")
        return {"description": "N/A", "cost": "N/A", "timeframe": "N/A"}

# ------------------------------------
# Sidebar Navigation Pane
# ------------------------------------
with st.sidebar:
    st.markdown("<h2 class='sidebar-title'>Pharma AI Brand Manager</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="custom-nav">
          <ul>
            <li><a href="#">Find Real Patients</a></li>
            <li class="active"><a href="#" style="display:block; padding: 5px 10px;">Tactical Plans</a></li>
            <li><a href="#">Strategic Imperatives</a></li>
            <li><a href="#">Landscape Analysis</a></li>
            <li><a href="#">Pipeline Outlook</a></li>
            <li><a href="#">Create Messaging</a></li>
            <li><a href="#">Creative Campaign Concepts</a></li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<div class='sidebar-footer'>© Philip Storer 2025</div>", unsafe_allow_html=True)

# ------------------------------------
# Main Content Area
# ------------------------------------
st.header("Step 1: Customize Your Tactical Plan")
role_selected = st.selectbox("", role_dropdown_options)
lifecycle_selected = st.selectbox("", lifecycle_dropdown_options)
journey_selected = st.selectbox("", journey_dropdown_options)
disease_selected = st.selectbox("", disease_dropdown_options)

if (role_selected != role_placeholder and lifecycle_selected != lifecycle_placeholder and
    journey_selected != journey_placeholder and disease_selected != disease_placeholder):

    st.header("Step 2: Select Strategic Imperatives")
    strategic_options = filter_strategic_imperatives(matrix_df, role_selected, lifecycle_selected, journey_selected)
    if not strategic_options:
        st.warning("No strategic imperatives found for these selections. Please try different options.")
    else:
        selected_strategics = st.multiselect("Select up to 3 Strategic Imperatives", options=strategic_options, max_selections=3)
    
    if selected_strategics and len(selected_strategics) > 0:
        st.header("Step 3: Select Product Differentiators")
        try:
            sheet2 = pd.read_excel("test.xlsx", sheet_name=1, header=0)
        except Exception as e:
            st.error(f"Error reading Sheet2: {e}")
            st.stop()
        if "Differentiator" not in sheet2.columns:
            st.error("Sheet2 must have a column named 'Differentiator'.")
            st.stop()
        product_diff_options = sheet2["Differentiator"].dropna().unique().tolist()
        selected_differentiators = st.multiselect("Select up to 3 Product Differentiators", options=product_diff_options, max_selections=3)
        
        if selected_differentiators and len(selected_differentiators) > 0:
            st.markdown("### Additional Actions")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                gen_plan_pressed = st.button("Generate Strategic Plan", key="gen_plan")
            with col2:
                st.button("Competitive Landscape", key="comp_landscape")
            with col3:
                st.button("Generate Campaign", key="gen_campaign")
            with col4:
                st.button("Create Messaging", key="create_messaging")
            st.button("Creative Campaign Concepts", key="creative_campaign")
            
            if gen_plan_pressed:
                st.header("Tactical Recommendations")
                try:
                    sheet3 = pd.read_excel("test.xlsx", sheet_name=2, header=0)
                except Exception as e:
                    st.error(f"Error reading Sheet3: {e}")
                    st.stop()
                required_cols = ["Strategic Imperative", "Patient & Caregiver", "HCP Engagement"]
                if not all(col in sheet3.columns for col in required_cols):
                    st.error("Sheet3 must have columns named 'Strategic Imperative', 'Patient & Caregiver', and 'HCP Engagement'.")
                    st.stop()
                for imperative in selected_strategics:
                    row = sheet3[sheet3["Strategic Imperative"] == imperative]
                    if row.empty:
                        st.info(f"No tactic found for strategic imperative: {imperative}")
                        continue
                    if role_selected == "HCP":
                        tactic = row["HCP Engagement"].iloc[0]
                    else:
                        tactic = row["Patient & Caregiver"].iloc[0]
                    ai_output = generate_ai_output(tactic, selected_differentiators)
                    st.subheader(f"{imperative}: {tactic}")
                    st.write(ai_output.get("description", "No description available."))
                    st.write(f"**Estimated Cost:** {ai_output.get('cost', 'N/A')}")
                    st.write(f"**Estimated Timeframe:** {ai_output.get('timeframe', 'N/A')}")
        else:
            st.info("Please select at least one product differentiator to proceed.")
    else:
        st.info("Please select at least one strategic imperative to proceed.")
else:
    st.info("Please complete all criteria selections in Step 1 to proceed.")

# ------------------------------------
# Full-Width Footer (Main Page)
# ------------------------------------
footer_html = """
<div class="custom-footer">
  <a href="#">Terms of Use</a> |
  <a href="#">Privacy Policy</a> |
  <a href="#">Cookie Settings</a> |
  <a href="#">Contact Us</a>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
