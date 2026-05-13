import streamlit as st
import pandas as pd


def deployment_status_dashboard():
    st.title("Stage Deployment Dashboard - May 2026")
    data = [
        {"Service": "auth-service", "Hard Version": "v3.4.1", "Stg": "✅", "Prod": "✅", "Tests": "✅",
         "Approval": "✅", "Status": "Go"},
        {"Service": "data-pipeline", "Hard Version": "v2.1.0",  "Stg": "✅", "Prod": "✅", "Tests": "✅",
          "Approval": "✅",   "Status": "Go"},
        {"Service": "notification-svc", "Hard Version": "v1.8.3",  "Stg": "✅", "Prod": "—", "Tests": "✅",
         "Approval": "⏳",   "Status": "No-go"},
        {"Service": "report-engine", "Hard Version": "v4.0.0",   "Stg": "✅", "Prod": "—", "Tests": "❌",
         "Approval": "❌",  "Status": "No-go"},
        {"Service": "tenant-router", "Hard Version": "v3.1.5",   "Stg": "—", "Prod": "—", "Tests": "✅",
          "Approval": "⏳",   "Status": "Hold"},
    ]

    df = pd.DataFrame(data)

    def color_status(val):
        colors = {"Go": "background-color: #d4edda; color: #155724",
                  "No-go": "background-color: #f8d7da; color: #721c24",
                  "Hold": "background-color: #fff3cd; color: #856404"}
        return colors.get(val, "")

    styled = df.style.map(color_status, subset=["Status"])

    st.dataframe(styled, use_container_width=True, hide_index=True)