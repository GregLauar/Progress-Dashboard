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
# The script now expects data files to be inside a subfolder named "data_base".
DATA_FOLDER = "data_base"
BUDGET_FILE = "budget_base_tabular.xlsx"
AUM_FILE    = "budget_aum_tabular_novo_approach.xlsx"
LOGO_FILE = "logo.png" # The logo should be in the main folder, along with the script.

START = datetime(2025, 4, 1)
END   = datetime(2026, 3, 31)

# === DATA LOADING FUNCTIONS (CACHE) ===
@st.cache_data
def load_data():
    # Paths are adjusted to use the 'data_base' subfolder.
    df_budg = pd.read_excel(f"{DATA_FOLDER}/{BUDGET_FILE}")
    df_aum  = pd.read_excel(f"{DATA_FOLDER}/{AUM_FILE}")
    df_budg['Data'] = pd.to_datetime(df_budg['Data'])
    df_aum['Data'] = pd.to_datetime(df_aum['Data'])
    df_budg = df_budg[(df_budg["Data"] >= START) & (df_budg["Data"] <= END)]
    df_aum  = df_aum[(df_aum["Data"] >= START) & (df_aum["Data"] <= END)]
    
    aum_mask = df_aum["Categoria"] == "AuM at the EoP"
    df_aum.loc[aum_mask, ["Budget", "Actual/Est"]] *= 1000000

    mask = df_aum["Categoria"] == "Disbursement"
    df_aum.loc[mask, ["Budget", "Actual/Est"]] *= -1
    return df_budg, df_aum

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
def format_number(num):
    """Formats a number into a compact string (e.g., 1.5M, 500K)."""
    if abs(num) >= 1_000_000:
        return f'{num / 1_000_000:.1f}M'
    if abs(num) >= 1_000:
        return f'{num / 1_000:.0f}K'
    return f'{num:.0f}'

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
        actual_text = [format_number(x) for x in actual_data]
        fig.add_trace(go.Bar(x=actual_data.index, y=actual_data, name="Actual", marker_color="steelblue", text=actual_text, textposition='inside'))
    
    if not forecast_data.empty:
        forecast_text = [format_number(x) for x in forecast_data]
        fig.add_trace(go.Bar(x=forecast_data.index, y=forecast_data, name="Forecast", marker_color="lightblue", text=forecast_text, textposition='inside'))
    
    if not budget_data.empty:
        fig.add_trace(go.Scatter(x=budget_data.index, y=budget_data, mode="lines", name="Budget", line=dict(color="black", width=2, dash="dash")))
    
    fig.update_layout(
        title=title, 
        barmode="overlay", 
        xaxis_title="", 
        yaxis_title="", 
        xaxis=dict(tickformat="%b/%y"), 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # <<< MUDANÇA: O seletor garante que o estilo de texto seja aplicado APENAS aos gráficos de barra. >>>
    fig.update_traces(textangle=0, insidetextanchor='middle', textfont=dict(color='white', size=14), selector=dict(type='bar'))
    st.plotly_chart(fig, use_container_width=True, key=key)

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
    
    st.subheader("🔹 Balance Sheet Statistics")
    bar_compare(df_aum, "AuM at the EoP", "AuM (BRL)", key="dash_aum")
    
    st.subheader("🔹 Income Statement Statistics")
    c5, c6 = st.columns(2)
    with c5:
        bar_compare(df_budg, "Revenues - Net of ECL", "Revenues (BRL)", key="dash_revenues")
    with c6:
        bar_compare(df_budg, "PROFIT BEFORE TAX", "Profit (BRL)", key="dash_pbt")

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
    
    views = []
    views.append({'type': 'chart', 'title': 'AuM (BRL)', 'params': {'df': df_aum, 'categoria': 'AuM at the EoP'}})
    views.append({'type': 'chart', 'title': 'Revenues (BRL)', 'params': {'df': df_budg, 'categoria': 'Revenues - Net of ECL'}})
    views.append({'type': 'chart', 'title': 'Profit (BRL)', 'params': {'df': df_budg, 'categoria': 'PROFIT BEFORE TAX'}})
        
    if 'view_index' not in st.session_state:
        st.session_state.view_index = 0

    placeholder = st.empty()
    
    iteration_counter = 0
    while True:
        current_view = views[st.session_state.view_index]
        
        with placeholder.container():
            st.title(current_view['title'])
            unique_key = f"tv_view_{st.session_state.view_index}_{iteration_counter}"
            
            is_cumulative = current_view['params'].get('cumulative', False)
            bar_compare(df=current_view['params']['df'], categoria=current_view['params']['categoria'], title="", key=unique_key, cumulative=is_cumulative)

        st.session_state.view_index = (st.session_state.view_index + 1) % len(views)
        iteration_counter += 1
        
        time.sleep(DELAY)

# ===================================================================
# MAIN NAVIGATION STRUCTURE
# ===================================================================
if "tv_mode_on" not in st.session_state:
    st.session_state.tv_mode_on = False

if st.session_state.tv_mode_on:
    page_tv_mode()
else:
    st.sidebar.title("Navigation")

    if st.sidebar.button("▶️ Start TV Mode"):
        st.session_state.tv_mode_on = True
        st.rerun()
    
    page_dashboard()
