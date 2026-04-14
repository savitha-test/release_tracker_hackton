import urllib
from datetime import datetime

import requests
import streamlit as st
import pandas as pd
from dateutil.relativedelta import relativedelta

from jira_service import get_jira_issues
from release_summary import generate_release_summary
from utils.config_loader import load_properties
from services.bitbucket_service import fetch_release_data, get_headers

st.set_page_config(layout="wide")
st.title("🚀 Release Dashboard")

config = load_properties("config/config.properties")

workspace = config["bitbucket.workspace"]
username = config["bitbucket.username"]
app_password = config["bitbucket.app_password"]
default_branch = config["release.branch"]
repos = [r.strip() for r in config["repos"].split(",")]


def get_all_branches(workspace, repo, username, app_password):
    query = 'name~"release/"'
    encoded_query = urllib.parse.quote(query)

    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/refs/branches?q={encoded_query}"

    branches_all = []

    while url:
        response = requests.get(url, auth=(username, app_password))
        data = response.json()

        branches_all.extend(data.get("values", []))
        url = data.get("next")  # pagination

    print(f"Found {len(branches_all)} branches")
    return branches_all


def filter_release_branches(branches):
    filtered_rel_branch = []

    for branch in branches:
        name = branch["name"]

        if not name.startswith("release/") or name.count("/") != 1:
            continue

        try:
            date_str = name.split("/")[-1]  # 2026-02-02
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            if date_obj.year == 2026:
                filtered_rel_branch.append(name)

            elif date_obj.year == 2025 and date_obj.month in [11, 12]:
                filtered_rel_branch.append(name)

        except Exception:
            # skip invalid formats
            continue

    return filtered_rel_branch

#==============================================================
branches = get_all_branches(workspace, "ng-platform-ui", username, app_password)

filtered = filter_release_branches(branches)

print('The list of release branches are ',filtered)

#==============================================================
# Sort release branches by date (newest first)
filtered_sorted = sorted(filtered, key=lambda x: datetime.strptime(x.split("/")[-1], "%Y-%m-%d"), reverse=True)

branch = st.selectbox("Release Branch", filtered_sorted)
date_part = branch.split("/")[-1]
print(date_part)
date_obj = datetime.strptime(date_part, "%Y-%m-%d")

one_month_back = date_obj - relativedelta(months=1)

print(one_month_back.strftime("%Y-%m-%d"))
formatted_start_date = one_month_back.strftime("%Y-%m-%dT00:00:00+00:00")

st.info(f"Showing all features/commits in {branch}")

if st.button("Run Analysis"):

    headers = get_headers(username, app_password)
    with st.spinner("Fetching data..."):
        data = fetch_release_data(
            workspace,
            repos,
            branch,
            headers,
            formatted_start_date
        )

    if data:
        df = pd.DataFrame(data)

        st.success(f"Found {len(df)} User Stories")

        col1, col2 = st.columns(2)
        col1.metric("Services", df["repo"].nunique())
        col2.metric("Total US", len(df))

        st.dataframe(df, use_container_width=True)

<<<<<<< HEAD
        st.subheader("US per Service")
        grouped = df.groupby("repo")["us_id"].apply(list).reset_index()
        st.dataframe(grouped)

=======
        st.subheader("US Per Service")
        grouped = df.groupby("repo")["us_id"].apply(list).reset_index()

        st.dataframe(grouped)
        st.subheader("US Per Service")
        grouped = df.groupby("repo")["us_id"].apply(list).reset_index()

        st.dataframe(grouped)

        for repo, us_ids in zip(grouped["repo"], grouped["us_id"]):
            issues = get_jira_issues(us_ids)
            summary = generate_release_summary(issues)

            print(f"Repo: {repo}")
            print(summary)
            st.header(f"Repo: {repo}")
            st.subheader("📊 Release Summary")
            st.markdown(summary)
