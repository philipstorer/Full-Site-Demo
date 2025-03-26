import streamlit as st
import pandas as pd
import openai
import json
import os
import re

# -----------------------
# Custom CSS Injection
# -----------------------
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Inject CSS for sidebar, overlay, and footer.
st.markdown(
    """
    <style>
    /* Sidebar custom style: light gray background, narrower width */
    [data-testid="stSidebar"] {
        background-color: #f0f0f0;
        width: 240px;  /* Adjust width as needed */
    }
    /* Footer style */
    .custom-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #444444;
        color: white;
        text-align: center;
        padding: 10px 0;
        font-size: 0.9em;
    }
    .custom-footer a {
        color: #dddddd;
        margin: 0 10px;
        text-decoration: none;
    }
    .custom-footer a:hover {
        color: #ffffff;
    }
    /* Login overlay */
    .login-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.95);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .login-box {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 8px;
        box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
        width: 300px;
        text-align: center;
    }
    .login-box h2 {
        margin-bottom: 20px;
    }
    .login-box input[type="text"], .login-box input[type="password"] {
        width: 100%;
        padding: 10px;
        margin: 10px 0;
        border: 1px solid #ccc;
        border-radius: 4px;
    }
    .login-box button {
        width: 100%;
        padding: 10px;
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        margin-bottom: 10px;
    }
    .login-box button:hover {
        background-color: #2980b9;
    }
    </style>
    """, unsafe_allow_html=True
)

# Optionally load external CSS file if you have additional styling.
if os.path.exists("static/style.css"):
    local_css("static/style.css")

# -----------------------
# Login Overlay Logic
# -----------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def show_login():
    # Create a container that covers the page
    login_html = """
    <div class="login-overlay">
      <div class="login-box">
        <h2>Login</h2>
        <form id="login-form">
          <input type="text" id="username" placeholder="Username" required /><br>
          <input type="password" id="password" placeholder="Password" required /><br>
          <button type="submit">Login</button>
        </form>
        <p>or</p>
        <button onclick="window.parent.postMessage('microsoft-login','*')">Sign in with Microsoft</button>
      </div>
    </div>
    <script>
      const form = document.getElementById('login-form');
      form.addEventListener('submit', function(e) {
          e.preventDefault();
          window.parent.postMessage('login-success','*');
      });
    </script>
    """
    st.markdown(login_html, unsafe_allow_html=True)

# Listen for messages from the frontend (this simulation uses st.experimental_set_query_params)
# (In Streamlit Cloud, you can simulate this by clicking a button.)
if not st.session_state.logged_in:
    show_login()
    # Create a placeholder button to simulate login (this is visible only in dev mode)
    if st.button("Simulate Login"):
        st.session_state.logged_in = True
        st.experimental_rerun()

if not st.session_state.logged_in:
    st.stop()  # Block the rest of the app if not logged in

# -----------------------
# Navigation Pane (Sidebar)
# -----------------------
with st.sidebar:
    # Place the title in the sidebar
    st.markdown("<h2>Pharma AI Brand Manager</h2>", unsafe_allow_html=True)
    # Navigation links (placeholders)
    st.markdown("""
    <ul style="list-style-type: none; padding-left: 0; margin: 0;">
      <li><a href="#" style="text-decoration: none; color: inherit;">Find Real Patients</a></li>
      <li><a href="#" style="text-decoration: none; color: inherit;">Tactical Plans</a></li>
      <li><a href="#" style="text-decoration: none; color: inherit;">Strategic Imperatives</a></li>
      <li><a href="#" style="text-decoration: none; color: inherit;">Landscape Analysis</a></li>
      <li><a href="#" style="text-decoration: none; color: inherit;">Pipeline Outlook</a></li>
      <li><a href="#" style="text-decoration: none; color: inherit;">Create Messaging</a></li>
      <li><a href="#" style="text-decoration: none; color: inherit;">Creative Campaign Concepts</a></li>
    </ul>
    """, unsafe_allow_html=True)

# -----------------------
# Main App Content (Login has already occurred, so hide the title here)
# -----------------------
# Load Criteria from Sheet1 (A–M)
@st.cache_data
def load_criteria(filename):
    try:
        df = pd.read_excel(filename, sheet_name=0, header=0, usecols="A:M")
        if df.shape[1] < 13:
            st.error(f"Excel file has only {df.shape[1]} columns but at least 13 are required. Check file formatting.")
            return None, None, None, None
        role_options = df.columns[1:4].tolist()  # B–D
        role_options = [opt for opt in role_options if opt.lower() != "caregiver"]
        lifecycle_options = df.columns[5:9].tolist()  # F–I
        journey_options = df.columns[9:13].tolist()   # J–M
        matrix_df = df.copy()
        return role_options, lifecycle_options, journey_options, matrix_df
    except Exception as e:
        st.error(f"Error reading the Excel file (Sheet1): {e}")
        return None, None, None, None

role_options, lifecycle_options, journey_options, matrix_df = load_criteria("test.xlsx")
if any(v is None for v in [role_options, lifecycle_options, journey_options, matrix_df]):
    st.stop()

# Define placeholders and disease state options.
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

# -----------------------
# Helper: Filter Strategic Imperatives (Sheet1)
# -----------------------
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

# -----------------------
# Main Criteria Selection (Step 1)
# -----------------------
st.header("Step 1: Select Your Criteria")
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

# -----------------------
# Footer Area
# -----------------------
footer_html = """
<div class="custom-footer">
  <a href="#">Terms of Use</a> |
  <a href="#">Privacy Policy</a> |
  <a href="#">Cookie Settings</a>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
