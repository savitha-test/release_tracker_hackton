
import streamlit as st

def load_css():

    st.markdown("""
    <style>

    /* =========================
       APP BACKGROUND
    ========================= */
    .stApp {
        background: linear-gradient(
            180deg,
            #F8FAFC 0%,
            #FDFDFD 100%
        );
        color: #1E293B;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* =========================
       HEADERS
    ========================= */
    h1 {
        color: #1E293B !important;
        font-weight: 800 !important;
        font-size: 3rem !important;
    }

    h2, h3 {
        color: #334155 !important;
        font-weight: 700 !important;
    }

    p, label {
        color: #64748B !important;
    }

    /* =========================
       TABS
    ========================= */

    .stTabs [data-baseweb="tab-list"] {
        gap: 14px;
        background: transparent;
        padding: 10px 0px;
        border-bottom: none;
    }

    .stTabs [data-baseweb="tab"] {
        background: white;
        border: 1px solid #DBEAFE;
        border-radius: 14px;
        color: #64748B !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        padding: 14px 26px !important;
        transition: all 0.2s ease;
        box-shadow: 0 2px 10px rgba(148, 163, 184, 0.08);
    }

    .stTabs [data-baseweb="tab"]:hover {
        border-color: #93C5FD;
        transform: translateY(-1px);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(
            135deg,
            #DBEAFE,
            #FEF3C7
        ) !important;

        color: #1E293B !important;
        border: 1px solid #93C5FD !important;

        box-shadow:
            0 4px 14px rgba(96, 165, 250, 0.15);
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* =========================
       SELECTBOX / MULTISELECT
    ========================= */

    .stSelectbox label,
    .stMultiSelect label {
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }

    .stSelectbox div[data-baseweb="select"],
    .stMultiSelect div[data-baseweb="select"] {

        background: white !important;
        border: 1px solid #DBEAFE !important;
        border-radius: 14px !important;

        box-shadow:
            0 2px 10px rgba(148,163,184,0.08);

        min-height: 52px;
    }

    /* Selected tags */
    .stMultiSelect [data-baseweb="tag"] {

        background: #FEF3C7 !important;
        border: 1px solid #FCD34D !important;
        color: #92400E !important;

        border-radius: 10px !important;

        font-weight: 600 !important;
    }

    /* =========================
       BUTTONS
    ========================= */

    .stButton > button {

        background: linear-gradient(
            135deg,
            #60A5FA,
            #93C5FD
        ) !important;

        color: white !important;

        border: none !important;

        border-radius: 14px !important;

        padding: 14px 26px !important;

        font-size: 15px !important;
        font-weight: 700 !important;

        box-shadow:
            0 4px 14px rgba(96,165,250,0.25);

        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        opacity: 0.95;
    }

    /* =========================
       METRIC CARDS
    ========================= */

    [data-testid="metric-container"] {

        background: white !important;

        border: 1px solid #DBEAFE !important;

        border-radius: 18px !important;

        padding: 24px !important;

        box-shadow:
            0 4px 20px rgba(148,163,184,0.08);
    }

    [data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-size: 15px !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricValue"] {
        color: #1E293B !important;
        font-size: 36px !important;
        font-weight: 800 !important;
    }

    /* =========================
       EXPANDERS
    ========================= */

    [data-testid="stExpander"] {

        background: white !important;

        border: 1px solid #DBEAFE !important;

        border-radius: 18px !important;

        box-shadow:
            0 4px 20px rgba(148,163,184,0.08);

        overflow: hidden !important;

        margin-bottom: 24px !important;
    }

    [data-testid="stExpander"] details summary {

        background:
            linear-gradient(
                135deg,
                #F8FAFC,
                #FEF3C7
            ) !important;

        padding: 16px 20px !important;

        font-size: 18px !important;
        font-weight: 800 !important;

        color: #1E293B !important;

        border-bottom: 1px solid #DBEAFE;
    }

    /* =========================
       DATAFRAMES
    ========================= */

    [data-testid="stDataFrame"] {

        border-radius: 16px !important;

        overflow: hidden !important;

        border: 1px solid #DBEAFE !important;

        box-shadow:
            0 4px 20px rgba(148,163,184,0.08);
    }

    /* =========================
       ALERTS
    ========================= */

    .stAlert {

        background: #FEFCE8 !important;

        border: 1px solid #FDE68A !important;

        border-radius: 14px !important;

        color: #92400E !important;
    }

    </style>
    """, unsafe_allow_html=True)

