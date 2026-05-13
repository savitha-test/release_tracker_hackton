import streamlit as st
from PIL import Image
from deployment_dashboard import deployment_status_dashboard
from style import load_css
from release_dashboard import show_release_dashboard


st.set_page_config(
    page_title="Release Intelligence Dashboard",
    page_icon="🚀",
    layout="wide"
)

load_css()
img=Image.open("./images/logo.png").convert("RGBA")
imgCol, titleCol = st.columns([1, 6])
with imgCol:
    st.image(img, width=80)
with titleCol:
    st.title("Release Intelligence Platform")
#st.title(img,"Release Intelligence Platform")
st.caption("AI-powered release and deployment insights")

tab1, tab2 = st.tabs([
    "🚦 Staging Deployment Readiness",
    "🚀 Release Dashboard"
])

with tab1:
    with st.container():
     deployment_status_dashboard()

with tab2:
    with st.container():
        show_release_dashboard()