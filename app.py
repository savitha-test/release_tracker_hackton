import urllib
from datetime import datetime

import requests
import streamlit as st
import pandas as pd
from dateutil.relativedelta import relativedelta

from jira_service import get_jira_issues
from utils.config_loader import load_properties
from services.bitbucket_service import fetch_release_data, get_headers
from style import load_css

load_css()

config = load_properties("config/config.properties")
workspace = config["bitbucket.workspace"]
username = config["bitbucket.username"]
app_password = config["bitbucket.app_password"]
default_branch = config["release.branch"]
repos = [r.strip() for r in config["repos"].split(",")]



def prepare_repo_issues(repo, us_ids):
    issues = get_jira_issues(us_ids)
    df_issues = pd.DataFrame(issues)

    repo_df = pd.DataFrame({
        "Repository": [repo] * len(us_ids),
        "User Stories": us_ids
    })

    merged_df = repo_df.merge(
        df_issues,
        left_on="User Stories",
        right_on="id",
        how="left"
    )

    final_df = merged_df[
        ["Repository", "User Stories", "description", "type", "priority"]
    ].copy()

    final_df.index = range(1, len(final_df) + 1)

    return final_df, df_issues


def show_repo_metrics(df_issues):
    type_counts = df_issues["type"].value_counts()

    story_count = type_counts.get("Story", 0)
    bug_count = type_counts.get("Bug", 0)
    total_count = story_count + bug_count

    col1, col2, col3 = st.columns(3)
    col1.metric("📘 User Stories", story_count)
    col2.metric("🐞 Bugs", bug_count)
    col3.metric("📊 Total", total_count)


def show_repo_section(repo, us_ids):
    final_df, df_issues = prepare_repo_issues(repo, us_ids)

    with st.expander(f"📦 {repo}", expanded=False):
        show_repo_metrics(df_issues)
        st.dataframe(final_df, use_container_width=True,  height=360)



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

def show_release_dashboard():
    st.set_page_config(layout="wide")
    branches = get_all_branches(workspace, "ng-platform-ui", username, app_password)
    filtered = filter_release_branches(branches)

    # Sort release branches by date (newest first)
    filtered_sorted = sorted(filtered, key=lambda x: datetime.strptime(x.split("/")[-1], "%Y-%m-%d"), reverse=True)
    col1,col2=st.columns(2)
    with col1:
        branch = st.selectbox("Release Branch", filtered_sorted)
    with col2:
        selected_repo=st.multiselect("Select Repo", repos)


    date_part = branch.split("/")[-1]

    date_obj = datetime.strptime(date_part, "%Y-%m-%d")

    one_month_back = date_obj - relativedelta(months=1)

    print(one_month_back.strftime("%Y-%m-%d"))
    formatted_start_date = one_month_back.strftime("%Y-%m-%dT00:00:00+00:00")
    all_issues = []


    if st.button("Run Analysis"):
        headers = get_headers(username, app_password)
        with st.spinner("Fetching data..."):
            data = fetch_release_data(
                workspace,
                selected_repo,
                branch,
                headers,
                formatted_start_date
            )

        if data:
            df = pd.DataFrame(data)
            grouped = (
                df.groupby("Repository")["User Stories"]
                .apply(list)
                .reset_index()
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("📦 Repositories", len(grouped))
            col2.metric("📘 Total Jira Issues", len(df))


            for repo, us_ids in zip(grouped["Repository"], grouped["User Stories"]):
                show_repo_section(repo, us_ids)



