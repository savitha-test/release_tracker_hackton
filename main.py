import streamlit as st

from deployment_dashboard import deployment_status_dashboard
from style import load_css
from app import show_release_dashboard


st.set_page_config(
    page_title="Release Intelligence Dashboard",
    page_icon="🚀",
    layout="wide"
)

load_css()

st.title("🚀 Release Intelligence Platform")
st.caption("AI-powered release and deployment insights")

tab1, tab2 = st.tabs([
    "🚦 Staging Deployment Readiness",
    "🚀 Release Dashboard"
])

with tab1:
    deployment_status_dashboard()

with tab2:
    show_release_dashboard()