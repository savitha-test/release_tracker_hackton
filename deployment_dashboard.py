import streamlit as st
import pandas as pd
from services.eks_service import get_all_services_from_cluster, EKS_HARD_CLUSTER, EKS_HARD_NAMESPACE, EKS_STAGE_CLUSTER, EKS_STAGE_NAMESPACE
from services.at_pipeline_service import get_at_test_result
from utils.config_loader import load_properties

# Load config for branch info
config = load_properties("config/config.properties")
RELEASE_BRANCH = config.get("release.branch", "master")


def deployment_status_dashboard():
    st.title("Stage Deployment Dashboard - May 2026")
    

    # Fetch service versions from EKS clusters
    with st.spinner("Fetching data from EKS clusters..."):
        try:
            # Get all services from ocp-hard cluster
            hard_services = get_all_services_from_cluster(EKS_HARD_CLUSTER, EKS_HARD_NAMESPACE)
            stage_services = get_all_services_from_cluster(EKS_STAGE_CLUSTER, EKS_STAGE_NAMESPACE)
            
            # Combine into the format we need
            service_versions = {}
            all_service_names = set(list(hard_services.keys()) + list(stage_services.keys()))
            
            # Debug info
            print(f"Found {len(hard_services)} services in hard cluster")
            print(f"Found {len(stage_services)} services in stage cluster")
            print(f"Total unique services: {len(all_service_names)}")
            
            for service in all_service_names:
                service_versions[service] = {
                    'ocp-hard': hard_services.get(service, 'N/A'),
                    'ocp-stage': stage_services.get(service, 'N/A')
                }
        except Exception as e:
            st.error(f"❌ Error fetching data from EKS clusters: {str(e)}")
            st.info("""
            **Troubleshooting Steps:**
            1. Verify kubectl is installed: `kubectl version --client`
            2. Check cluster access:
               ```bash
               kubectl get deployments -n hard --context=hard-k8s
               kubectl get deployments -n stage --context=stage-k8s
               ```
            3. Update kubeconfig if needed:
               ```bash
               aws eks update-kubeconfig --region us-east-2 --name hard-k8s
               aws eks update-kubeconfig --region us-east-2 --name stage-k8s
               ```
            """)
            return
    
    # Check if we have any services
    if not service_versions:
        st.warning("⚠️ No services found in EKS clusters. Please verify:")
        st.info("""
        1. kubectl is configured correctly
        2. You have access to the clusters:
           - `kubectl get deployments -n hard --context=hard-k8s`
           - `kubectl get deployments -n stage --context=stage-k8s`
        3. The namespaces 'hard' and 'stage' exist in the respective clusters
        4. Your AWS credentials are set up properly
        """)
        return
    
    # Show progress while preparing data
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Prepare dashboard data
    data = []
    at_results_cache = {}
    total_services = len(service_versions)
    
    for idx, (service_name, versions) in enumerate(service_versions.items()):
        # Update progress
        progress = (idx + 1) / total_services
        progress_bar.progress(progress)
        status_text.text(f"Processing {idx + 1}/{total_services}: {service_name}")
        
        # Determine if service is deployed
        is_deployed_hard = versions['ocp-hard'] != 'N/A'
        is_deployed_stage = versions['ocp-stage'] != 'N/A'
        
        # Get AT test status from Bitbucket pipeline
        # Try to map service name to repo name (handle naming differences)
        repo_name = service_name.replace('_', '-')  # Common conversion
        
        try:
            if repo_name not in at_results_cache:
                at_result = get_at_test_result(repo_name, RELEASE_BRANCH)
                at_results_cache[repo_name] = at_result
            else:
                at_result = at_results_cache[repo_name]
        except Exception as e:
            print(f"Error fetching AT result for {repo_name}: {str(e)}")
            at_result = "🔒 No Access"
        
        # Go/No-go based on AT test results
        if "✅ Passed" in at_result:
            status = "Go"
            approval = "✅"
        else:
            status = "No-go"
            approval = "❌"
        
        data.append({
            "Service": service_name,
            "Image version in hardening": versions['ocp-hard'],
            "Image version in stage": versions['ocp-stage'],
            "AT Test Cases": at_result,
            "Approval": approval,
            "Status": status
        })
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()

    df = pd.DataFrame(data)

    # Check if we have data to display
    if df.empty:
        st.warning("⚠️ No services found in EKS clusters. Please verify:")
        st.info("""
        1. kubectl is configured correctly
        2. You have access to the clusters:
           - `kubectl get deployments -n hard --context=hard-k8s`
           - `kubectl get deployments -n stage --context=stage-k8s`
        3. The namespaces 'hard' and 'stage' exist in the respective clusters
        4. Your AWS credentials are set up properly
        """)
        return
    
    # Show metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📦 Total Services", len(df))
    with col2:
        passed_count = len(df[df['AT Test Cases'].str.contains('✅', na=False)]) if 'AT Test Cases' in df.columns else 0
        st.metric("✅ AT Passed", passed_count)
    with col3:
        failed_count = len(df[df['AT Test Cases'].str.contains('❌', na=False)]) if 'AT Test Cases' in df.columns else 0
        st.metric("❌ AT Failed", failed_count)
    with col4:
        no_access_count = len(df[df['AT Test Cases'].str.contains('🔒', na=False)]) if 'AT Test Cases' in df.columns else 0
        st.metric("🔒 No Access", no_access_count)
    with col5:
        go_count = len(df[df['Status'] == 'Go']) if 'Status' in df.columns else 0
        st.metric("🚀 Ready (Go)", go_count)

    def color_status(val):
        colors = {"Go": "background-color: #d4edda; color: #155724",
                  "No-go": "background-color: #f8d7da; color: #721c24"}
        return colors.get(val, "")

    # Apply styling only if Status column exists
    if "Status" in df.columns:
        styled = df.style.map(color_status, subset=["Status"])
    else:
        styled = df

    st.dataframe(styled, use_container_width=True, hide_index=True)
    
    # Add refresh button
    if st.button("🔄 Refresh from EKS"):
        st.rerun()