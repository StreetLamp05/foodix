import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Local logo (fallback to included SVG file)
LOGO_PATH = "fcx_logo.svg"

# Page configuration
st.set_page_config(
    page_title="Inventory Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar configuration
try:
    st.sidebar.image(LOGO_PATH, width=72)
except Exception:
    # ignore if logo missing
    pass

st.sidebar.title("⚙️ Settings")
backend_url = st.sidebar.text_input(
    "Backend URL",
    value=os.getenv("BACKEND_URL", "http://localhost:5000"),
    help="URL of the backend API"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Navigation")
current_page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Analytics", "Usage Predictions", "Inventory"],
    label_visibility="collapsed"
)

# Main header (logo + title)
col_logo, col_title = st.columns([1, 8])
with col_logo:
    try:
        st.image(LOGO_PATH, width=96)
    except Exception:
        pass
with col_title:
    st.title(f"📦 {current_page}")
    st.markdown("Real-time inventory tracking and analytics")


# Sample data (replace with actual API calls)
@st.cache_data
def load_inventory_data():
    # This will be replaced with actual API call to backend
    data = {
        "Product ID": ["PROD001", "PROD002", "PROD003", "PROD004", "PROD005"],
        "Product Name": ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Tool Z"],
        "Current Stock": [150, 75, 200, 45, 320],
        "Min Stock": [50, 30, 100, 20, 100],
        "Max Stock": [500, 300, 600, 200, 800],
        "Category": ["Electronics", "Electronics", "Gadgets", "Gadgets", "Tools"],
        "Last Updated": pd.date_range("2026-01-01", periods=5, freq="D")
    }
    return pd.DataFrame(data)


# Load data
inventory_df = load_inventory_data()
inventory_df = inventory_df.copy()
inventory_df["Utilization %"] = (
    inventory_df["Current Stock"] / inventory_df["Max Stock"] * 100
).round(2)

if current_page == "Dashboard":
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Items",
            value=inventory_df["Current Stock"].sum(),
            delta="+12"
        )

    with col2:
        st.metric(
            label="Low Stock Items",
            value=len(inventory_df[inventory_df["Current Stock"] < inventory_df["Min Stock"]]),
            delta="-2"
        )

    with col3:
        st.metric(
            label="Categories",
            value=inventory_df["Category"].nunique()
        )

    with col4:
        st.metric(
            label="Total Products",
            value=len(inventory_df)
        )

    st.divider()
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Stock Levels by Product")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Current Stock",
            x=inventory_df["Product Name"],
            y=inventory_df["Current Stock"],
            marker_color="lightblue"
        ))
        fig.add_trace(go.Scatter(
            name="Min Stock",
            x=inventory_df["Product Name"],
            y=inventory_df["Min Stock"],
            mode="lines",
            line=dict(color="red", dash="dash")
        ))
        fig.update_layout(
            hovermode="x unified",
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Stock Status")
        for _, row in inventory_df.iterrows():
            status = "🟢" if row["Current Stock"] >= row["Min Stock"] else "🔴"
            st.markdown(f"{status} {row['Product Name']}: {row['Current Stock']}")

elif current_page == "Analytics":
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Stock by Category")
        category_stock = inventory_df.groupby("Category")["Current Stock"].sum()
        fig = go.Figure(data=[
            go.Pie(
                labels=category_stock.index,
                values=category_stock.values,
                hole=0.3
            )
        ])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Stock Utilization")
        fig = go.Figure(data=[
            go.Bar(
                x=inventory_df["Product Name"],
                y=inventory_df["Utilization %"],
                marker_color="mediumpurple"
            )
        ])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

elif current_page == "Usage Predictions":
    st.subheader("AI Analytics Assistant")
    st.markdown(
        "**Ask questions about ingredient usage, inventory levels, or future demand.**\n\n"
        "Example prompts: \"What ingredients are running low?\", \"Predict tomato usage next week\""
    )

    user_query = st.text_area(
        "Your question",
        value="",
        height=120,
        placeholder="Type a question for the AI analytics assistant..."
    )

    if st.button("Analyze") and user_query.strip():
        with st.spinner("Analyzing..."):
            st.info("(This would call the backend/AI service and display results here)")

    st.markdown("---")
    st.subheader("7-Day Usage Forecast (Placeholder)")
    forecast_df = pd.DataFrame({
        "Day": pd.date_range(pd.Timestamp.today().normalize(), periods=7, freq="D"),
        "Predicted Usage": [42, 45, 43, 48, 51, 49, 53]
    })
    forecast_fig = go.Figure(
        data=[go.Scatter(
            x=forecast_df["Day"],
            y=forecast_df["Predicted Usage"],
            mode="lines+markers",
            line=dict(color="#2a9d8f", width=3)
        )]
    )
    forecast_fig.update_layout(height=360)
    st.plotly_chart(forecast_fig, use_container_width=True)

elif current_page == "Inventory":
    st.subheader("Inventory Table")
    edited_df = st.data_editor(
        inventory_df[["Product Name", "Current Stock", "Min Stock", "Max Stock", "Category"]],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("Add Inventory"):
            st.success("Add inventory flow would open here")
    with col2:
        if st.button("Run Reorder"):
            st.success("Reorder process triggered (placeholder)")
    with col3:
        st.metric(
            "Low Stock Items",
            len(inventory_df[inventory_df["Current Stock"] < inventory_df["Min Stock"]])
        )

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: gray; margin-top: 30px;'>
    <small>Inventory Dashboard v1.0 | Connected to Backend: {}</small>
    </div>
""".format(backend_url), unsafe_allow_html=True)
