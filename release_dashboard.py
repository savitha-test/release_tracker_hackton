import urllib
from datetime import datetime

import requests
import urllib3
import streamlit as st
import pandas as pd
from dateutil.relativedelta import relativedelta

from jira_service import get_jira_issues
from release_summary import generate_release_summary
from utils.config_loader import load_properties
from services.bitbucket_service import fetch_release_data, get_headers
from services.eks_service import get_all_services_from_cluster, EKS_STAGE_CLUSTER, EKS_STAGE_NAMESPACE

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ❌ Removed: load_css() — already called in main.py; calling it here runs
#    it at module-import time, outside any tab context, which causes the
#    tab layout to break on every rerun.

config = load_properties("config/config.properties")
workspace = config["bitbucket.workspace"]
username = config["bitbucket.username"]
app_password = config["bitbucket.app_password"]
default_branch = config["release.branch"]
repos = [r.strip() for r in config["repos"].split(",")]

if "allJira_issues" not in st.session_state:
    st.session_state.allJira_issues = []


def prepare_repo_issues(repo, us_ids):
    issues = get_jira_issues(us_ids)
    st.session_state.allJira_issues.extend(issues)

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


def show_repo_section(repo, us_ids, current_version=None):
    final_df, df_issues = prepare_repo_issues(repo, us_ids)
    
    # Create header with version info
    if current_version:
        header = f"📦 {repo} — 🚀 Stage: {current_version}"
    else:
        header = f"📦 {repo}"

    with st.expander(header, expanded=False):
        show_repo_metrics(df_issues)
        st.dataframe(final_df, use_container_width=True, height=360)


# ✅ Fix: cache this so it only hits the Bitbucket API once per session,
#    not on every widget interaction / Streamlit rerun.
@st.cache_data(show_spinner=False)
def get_all_branches(workspace, repo, username, app_password):
    query = 'name~"release/"'
    encoded_query = urllib.parse.quote(query)

    url = (
        f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}"
        f"/refs/branches?q={encoded_query}"
    )

    branches_all = []

    while url:
        response = requests.get(url, auth=(username, app_password), verify=False)
        data = response.json()
        branches_all.extend(data.get("values", []))
        url = data.get("next")

    print(f"Found {len(branches_all)} branches")
    return branches_all


def filter_release_branches(branches):
    filtered_rel_branch = []

    for branch in branches:
        name = branch["name"]

        if not name.startswith("release/") or name.count("/") != 1:
            continue

        try:
            date_str = name.split("/")[-1]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            if date_obj.year == 2026:
                filtered_rel_branch.append(name)
            elif date_obj.year == 2025 and date_obj.month in [11, 12]:
                filtered_rel_branch.append(name)

        except Exception:
            continue

    return filtered_rel_branch


# ==============================================================

def show_release_dashboard():
    # Fetch current deployed versions from stage cluster
    try:
        with st.spinner("Fetching current deployments from stage..."):
            stage_services = get_all_services_from_cluster(EKS_STAGE_CLUSTER, EKS_STAGE_NAMESPACE)
    except Exception as e:
        st.warning(f"⚠️ Could not fetch EKS stage data: {str(e)}")
        stage_services = {}
    
    branches = get_all_branches(workspace, "ng-platform-ui", username, app_password)
    filtered = filter_release_branches(branches)

    filtered_sorted = sorted(
        filtered,
        key=lambda x: datetime.strptime(x.split("/")[-1], "%Y-%m-%d"),
        reverse=True,
    )

    # ✅ st.form batches all widget interactions — no rerun (no blur) until
    #    the user clicks "Run Analysis". Without this, every selectbox /
    #    multiselect change triggers a full Streamlit rerun and the blur overlay.
    with st.form(key="release_form"):
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            branch = st.selectbox("Release Branch", filtered_sorted)
        with filter_col2:
            selected_repo = st.multiselect("Select Repo", repos)

        _, center_col, _ = st.columns([3, 2, 3])
        with center_col:
            submitted = st.form_submit_button("🚀 Run Analysis", use_container_width=True)

    if submitted:
        date_part = branch.split("/")[-1]
        date_obj = datetime.strptime(date_part, "%Y-%m-%d")
        one_month_back = date_obj - relativedelta(months=1)
        formatted_start_date = one_month_back.strftime("%Y-%m-%dT00:00:00+00:00")

        st.session_state.allJira_issues = []
        headers = get_headers(username, app_password)

        with st.spinner("Fetching data..."):
            data = fetch_release_data(
                workspace,
                selected_repo,
                branch,
                headers,
                formatted_start_date,
            )

        if data:
            df = pd.DataFrame(data)
            grouped = (
                df.groupby("Repository")["User Stories"]
                .apply(list)
                .reset_index()
            )

            metric_col1, metric_col2, _ = st.columns(3)
            metric_col1.metric("📦 Repositories", len(grouped))
            metric_col2.metric("📘 Total Jira Issues", len(df))

            for repo, us_ids in zip(grouped["Repository"], grouped["User Stories"]):
                # Get current version for this repo with robust name matching
                current_version = None
                
                # Try multiple name variations
                current_version = stage_services.get(repo)
                if not current_version:
                    current_version = stage_services.get(repo.replace('_', '-'))
                if not current_version:
                    current_version = stage_services.get(repo.replace('-', '_'))
                if not current_version:
                    current_version = stage_services.get(repo.lower())
                if not current_version:
                    current_version = stage_services.get(repo.lower().replace('_', '-'))
                
                show_repo_section(repo, us_ids, current_version)

        var = st.divider()
        summary = generate_release_summary(st.session_state.allJira_issues)
        #print(summary)
        st.markdown(summary, unsafe_allow_html=True)