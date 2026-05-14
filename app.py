import urllib
from datetime import datetime

import requests
import urllib3
import streamlit as st
import pandas as pd
from dateutil.relativedelta import relativedelta

from jira_service import get_jira_issues
from utils.config_loader import load_properties
from services.bitbucket_service import fetch_release_data, get_headers
from services.eks_service import get_all_services_from_cluster, EKS_STAGE_CLUSTER, EKS_STAGE_NAMESPACE
from style import load_css

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def show_repo_section(repo, us_ids, current_version=None):
    final_df, df_issues = prepare_repo_issues(repo, us_ids)

    with st.expander(f"📦 {repo}", expanded=False):
        # Show current deployed version if available
        if current_version:
            st.info(f"🚀 Currently Deployed in ocp-stage: **{current_version}**")
        
        show_repo_metrics(df_issues)
        st.dataframe(final_df, use_container_width=True,  height=360)



def get_all_branches(workspace, repo, username, app_password):
    query = 'name~"release/"'
    encoded_query = urllib.parse.quote(query)

    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/refs/branches?q={encoded_query}"

    branches_all = []

    while url:
        response = requests.get(url, auth=(username, app_password), verify=False)
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
    # Note: st.set_page_config is called in main.py
    
    branches = get_all_branches(workspace, "ng-platform-ui", username, app_password)
    filtered = filter_release_branches(branches)

    # Sort release branches by date (newest first)
    filtered_sorted = sorted(filtered, key=lambda x: datetime.strptime(x.split("/")[-1], "%Y-%m-%d"), reverse=True)
    col1,col2=st.columns(2)
    with col1:
        branch = st.selectbox("Release Branch", filtered_sorted)
    with col2:
        selected_repo=st.multiselect("Select Repo", repos)

    # Fetch current deployed versions from ocp-stage
    try:
        with st.spinner("Fetching current deployments from ocp-stage..."):
            stage_services = get_all_services_from_cluster(EKS_STAGE_CLUSTER, EKS_STAGE_NAMESPACE)
    except Exception as e:
        st.warning(f"⚠️ Could not fetch EKS data: {str(e)}")
        stage_services = {}
    
    # Display current deployed versions for selected repos
    if selected_repo:
        if stage_services:
            st.subheader("📊 Current Deployments in Stage")
            deployment_data = []
            for repo in selected_repo:
                # Try multiple name variations to match repo name with service name
                # 1. Exact match
                version = stage_services.get(repo)
                
                # 2. Try with underscores replaced by hyphens
                if not version:
                    version = stage_services.get(repo.replace('_', '-'))
                
                # 3. Try with hyphens replaced by underscores
                if not version:
                    version = stage_services.get(repo.replace('-', '_'))
                
                # 4. Try lowercase
                if not version:
                    version = stage_services.get(repo.lower())
                    
                # 5. Try lowercase with hyphen conversion
                if not version:
                    version = stage_services.get(repo.lower().replace('_', '-'))
                
                # If still not found, set as N/A
                if not version:
                    version = 'N/A'
                
                deployment_data.append({
                    "Repository": repo, 
                    "Image version in stage": version
                })
            
            if deployment_data:
                deployment_df = pd.DataFrame(deployment_data)
                st.dataframe(deployment_df, use_container_width=True, hide_index=True)
                
                # Show debug info for services not found
                not_found = [d["Repository"] for d in deployment_data if d["Image version in stage"] == 'N/A']
                if not_found:
                    with st.expander("ℹ️ Service Mapping Info"):
                        st.info(f"""
                        **Services not found in stage cluster:** {', '.join(not_found)}
                        
                        **Available services in stage cluster:** {', '.join(sorted(stage_services.keys()))}
                        
                        **Tip:** Repository names may differ from Kubernetes deployment names.
                        """)
        else:
            st.info("💡 No deployment data available. Ensure kubectl is configured for ocp-stage cluster.")

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



