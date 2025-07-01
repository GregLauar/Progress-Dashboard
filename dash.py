import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
from PIL import Image
import base64
from io import BytesIO

# st.set_page_config() must be the first Streamlit command.
st.set_page_config(layout="wide", page_title="Dashboard Budget", initial_sidebar_state="auto")

# === CONFIGURATIONS ===
DATA_FOLDER = "data_base"
BUDGET_FILE = "budget_base_tabular.xlsx"
AUM_FILE    = "budget_aum_tabular_novo_approach.xlsx"
OKRS_FILE = "okrs.xlsx"
LOGO_FILE = "logo.png"

START = datetime(2025, 4, 1)
END   = datetime(2026, 3, 31)

# === DATA LOADING FUNCTIONS (CACHE) ===
@st.cache_data
def load_data():
    df_budg = pd.read_excel(f"{DATA_FOLDER}/{BUDGET_FILE}")
    df_aum  = pd.read_excel(f"{DATA_FOLDER}/{AUM_FILE}")
    df_budg['Data'] = pd.to_datetime(df_budg['Data'])
    df_aum['Data'] = pd.to_datetime(df_aum['Data'])
    df_budg = df_budg[(df_budg["Data"] >= START) & (df_budg["Data"] <= END)]
    df_aum  = df_aum[(df_aum["Data"] >= START) & (df_aum["Data"] <= END)]
    mask = df_aum["Categoria"] == "Disbursement"
    df_aum.loc[mask, ["Budget", "Actual/Est"]] *= -1
    return df_budg, df_aum

@st.cache_data
def load_okrs():
    return pd.read_excel(f"{DATA_FOLDER}/{OKRS_FILE}")

def display_logo(width=150):
    """Tries to load and display the logo, resizing it."""
    try:
        logo = Image.open(LOGO_FILE)
        aspect_ratio = logo.width / logo.height
        new_height = int(width / aspect_ratio)
        resized_logo = logo.resize((width, new_height))
        st.image(resized_logo)
    except FileNotFoundError:
        st.warning(f"Logo file '{LOGO_FILE}' not found. Please place it in the same folder as the script.")

# === VISUALIZATION FUNCTIONS ===
def bar_compare(df, categoria, title="", key=None, cumulative=False):
    d = df[df["Categoria"] == categoria].copy()
    budget_data = d.groupby('Data')['Budget'].sum().sort_index()
    actual_data = d[d['Natureza do Dado'] == 'Actual'].groupby('Data')['Actual/Est'].sum().sort_index()
    forecast_data = d[d['Natureza do Dado'] == 'Forecast'].groupby('Data')['Actual/Est'].sum().sort_index()

    if cumulative:
        budget_data = budget_data.cumsum()
        actual_data = actual_data.cumsum()
        forecast_data = forecast_data.cumsum()

    fig = go.Figure()
    if not actual_data.empty:
        fig.add_trace(go.Bar(x=actual_data.index, y=actual_data, name="Actual", marker_color="steelblue"))
    if not forecast_data.empty:
        fig.add_trace(go.Bar(x=forecast_data.index, y=forecast_data, name="Forecast", marker_color="lightblue"))
    if not budget_data.empty:
        fig.add_trace(go.Scatter(x=budget_data.index, y=budget_data, mode="lines", name="Budget", line=dict(color="black", width=2, dash="dash")))
    fig.update_layout(title=title, barmode="overlay", xaxis_title="Month", yaxis_title="Value", xaxis=dict(tickformat="%b/%y"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True, key=key)

def display_okr_view(okr_data):
    """Displays a single OKR with a metric and progress bars (detailed view)."""
    st.metric(label="Overall Average Progress", value=f"{okr_data['average']:.0%}")
    st.progress(okr_data['average'])

    st.markdown("<br>", unsafe_allow_html=True)

    children = okr_data['children'].copy()
    for _, row in children.iterrows():
        kr_name = row["Key Result"]
        kr_progress = row["Progress"]
        st.markdown(f"**{kr_name}**")
        st.progress(kr_progress, text=f"{kr_progress:.0%}")

def display_okr_summary_view(df_okrs):
    """Displays a summary of all OKRs with progress bars."""
    st.markdown("---")
    avg_df = (df_okrs.groupby("Objectives")["Current"].mean().reset_index())

    for _, row in avg_df.iterrows():
        obj = row["Objectives"]
        avg = row["Current"]
        
        st.markdown(f"<h5>{obj}</h5>", unsafe_allow_html=True)
        st.progress(avg, text=f"{avg:.0%}")
        st.markdown("<br>", unsafe_allow_html=True)

# ===================================================================
# INTERACTIVE MODE PAGES
# ===================================================================

def page_dashboard():
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📊 Budget vs Actual/Forecast (FY25)")
    with col2:
        display_logo()

    df_budg, df_aum = load_data()
    st.subheader("🔹 Committed & Disbursement vs Budget (Cumulative) BRLmn")
    c1, c2 = st.columns(2)
    with c1:
        bar_compare(df_aum, "Committed", "Committed FY25 (Cumulative)", key="dash_committed", cumulative=True)
    with c2:
        bar_compare(df_aum, "Disbursement", "Disbursement FY25 (Cumulative)", key="dash_disbursement", cumulative=True)
    
    st.subheader("🔹 AuM at the EoP vs Budget")
    bar_compare(df_aum, "AuM at the EoP", "AuM at the EoP FY25", key="dash_aum")
    st.subheader("🔹 Revenues & Profit Before Tax vs Budget (BRLmn)")
    c5, c6 = st.columns(2)
    with c5:
        bar_compare(df_budg, "Revenues - Net of ECL", "Revenues FY25", key="dash_revenues")
    with c6:
        bar_compare(df_budg, "PROFIT BEFORE TAX", "Profit Before Tax FY25", key="dash_pbt")

def page_okrs():
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🎯 OKRs FY25")
    with col2:
        display_logo()
        
    df_okrs = load_okrs()
    avg_df = (df_okrs.groupby("Objectives")["Current"].mean().reset_index())
    
    st.markdown("Click on an objective to expand and see the Key Results details.")
    st.markdown("---")

    for _, row in avg_df.iterrows():
        obj = row["Objectives"]
        avg = row["Current"]
        
        with st.expander(f"**{obj}** (Progress: {avg:.0%})", expanded=False):
            display_okr_view({
                'average': avg, 
                'children': df_okrs[df_okrs["Objectives"] == obj][["Child Items", "Current"]].rename(columns={"Child Items": "Key Result", "Current": "Progress"})
            })

# ===================================================================
# "TV MODE" PAGE (IMMERSIVE VERSION)
# ===================================================================

def get_image_as_base64(file, width=150):
    """Converts an image file to a base64 string to embed in HTML."""
    try:
        img = Image.open(file)
        aspect_ratio = img.width / img.height
        new_height = int(width / aspect_ratio)
        resized_img = img.resize((width, new_height))
        
        buffered = BytesIO()
        resized_img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except FileNotFoundError:
        return None

def page_tv_mode():
    """Runs the automatic, full-screen presentation mode."""
    
    if st.button("Exit TV Mode", key="exit_tv"):
        st.session_state.tv_mode_on = False
        st.rerun()

    logo_base64 = get_image_as_base64(LOGO_FILE)

    st.markdown(f"""
        <style>
            /* Hide Streamlit UI */
            [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"] {{
                display: none;
            }}
            
            /* Create a full-screen container to prevent scrolling */
            .main .block-container {{
                display: flex;
                flex-direction: column;
                justify-content: center; /* Vertically center content */
                align-items: center;     /* Horizontally center content */
                height: 100vh;           /* Full viewport height */
                width: 100vw;            /* Full viewport width */
                padding: 2rem;
                background-color: #FFFFFF; /* Solid background to hide artifacts */
                box-sizing: border-box;
            }}

            /* Position the exit button */
            div[data-testid="stButton"] > button[kind="secondary"] {{
                position: fixed;
                top: 2rem;
                left: 2rem;
                z-index: 1001;
            }}

            /* Position the logo */
            .logo-container {{
                position: fixed;
                top: 2rem;
                right: 2rem;
                z-index: 1000;
            }}
        </style>
        """, unsafe_allow_html=True)

    if logo_base64:
        st.markdown(f"""
            <div class="logo-container">
                <img src="data:image/png;base64,{logo_base64}">
            </div>
            """, unsafe_allow_html=True)

    DELAY = 15 
    df_budg, df_aum = load_data()
    df_okrs = load_okrs()
    views = []
    views.append({'type': 'chart', 'title': 'Budget: Committed vs Budget (Cumulative) BRLmn', 'params': {'df': df_aum, 'categoria': 'Committed', 'cumulative': True}})
    views.append({'type': 'chart', 'title': 'Budget: Disbursement vs Budget (Cumulative) BRLmn', 'params': {'df': df_aum, 'categoria': 'Disbursement', 'cumulative': True}})
    views.append({'type': 'chart', 'title': 'Budget: AuM at the EoP vs Budget BRLmn', 'params': {'df': df_aum, 'categoria': 'AuM at the EoP'}})
    views.append({'type': 'chart', 'title': 'Budget: Revenues - Net of ECL vs Budget BRLmn', 'params': {'df': df_budg, 'categoria': 'Revenues - Net of ECL'}})
    views.append({'type': 'chart', 'title': 'Budget: PROFIT BEFORE TAX vs Budget BRLmn', 'params': {'df': df_budg, 'categoria': 'PROFIT BEFORE TAX'}})
    views.append({'type': 'okr_summary', 'title': 'Overall OKR Summary', 'params': {'df_okrs': df_okrs}})
        
    if 'view_index' not in st.session_state:
        st.session_state.view_index = 0

    placeholder = st.empty()
    
    iteration_counter = 0
    while True:
        current_view = views[st.session_state.view_index]
        
        with placeholder.container():
            st.title(current_view['title'])
            unique_key = f"tv_view_{st.session_state.view_index}_{iteration_counter}"
            
            if current_view['type'] == 'chart':
                is_cumulative = current_view['params'].get('cumulative', False)
                bar_compare(df=current_view['params']['df'], categoria=current_view['params']['categoria'], key=unique_key, cumulative=is_cumulative)
            elif current_view['type'] == 'okr_summary':
                display_okr_summary_view(df_okrs=current_view['params']['df_okrs'])

        st.session_state.view_index = (st.session_state.view_index + 1) % len(views)
        iteration_counter += 1
        
        time.sleep(DELAY)

# ===================================================================
# MAIN NAVIGATION STRUCTURE
# ===================================================================
PAGES = {
    "Main Dashboard": page_dashboard,
    "OKRs Tracking": page_okrs,
}

if "tv_mode_on" not in st.session_state:
    st.session_state.tv_mode_on = False

if st.session_state.tv_mode_on:
    page_tv_mode()
else:
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))

    if st.sidebar.button("▶️ Start TV Mode"):
        st.session_state.tv_mode_on = True
        st.rerun()
    
    page_function = PAGES[selection]
    page_function()
