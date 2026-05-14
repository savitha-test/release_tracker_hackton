"""
AWS EKS Service - Fetch deployed image versions from EKS clusters
"""
import boto3
import subprocess
import re
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.config_loader import load_properties
    config = load_properties("config/config.properties")
    AWS_REGION = config.get('aws.region', 'us-east-1')
    EKS_HARD_CLUSTER = config.get('eks.hard.cluster', 'ocp-hard')
    EKS_HARD_NAMESPACE = config.get('eks.hard.namespace', 'hard')
    EKS_STAGE_CLUSTER = config.get('eks.stage.cluster', 'ocp-stage')
    EKS_STAGE_NAMESPACE = config.get('eks.stage.namespace', 'stage')
except Exception as e:
    print(f"Warning: Could not load config: {e}")
    AWS_REGION = 'us-east-1'
    EKS_HARD_CLUSTER = 'ocp-hard'
    EKS_HARD_NAMESPACE = 'hard'
    EKS_STAGE_CLUSTER = 'ocp-stage'
    EKS_STAGE_NAMESPACE = 'stage'


def get_eks_client(region='us-east-1'):
    """Get boto3 EKS client"""
    return boto3.client('eks', region_name=region)


def get_deployed_services_boto3(cluster_name: str, namespace: str, region='us-east-1') -> Dict[str, str]:
    """
    Fetch deployed services and their image versions from EKS cluster using boto3.
    
    Args:
        cluster_name: EKS cluster name (e.g., 'ocp-hard', 'ocp-stage')
        namespace: Kubernetes namespace
        region: AWS region
    
    Returns:
        Dict mapping service name to image version
    """
    try:
        # Use kubectl to get deployments
        # This requires proper kubeconfig setup
        cmd = f"kubectl get deployments -n {namespace} --context={cluster_name} -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Error fetching deployments from {cluster_name}: {result.stderr}")
            return {}
        
        import json
        data = json.loads(result.stdout)
        
        services = {}
        for item in data.get('items', []):
            service_name = item['metadata']['name']
            containers = item['spec']['template']['spec'].get('containers', [])
            
            if containers:
                image = containers[0]['image']
                # Extract version from image (e.g., myapp:v1.2.3 or myapp@sha256:...)
                version = extract_version_from_image(image)
                services[service_name] = version
        
        return services
    
    except Exception as e:
        print(f"Error getting services from {cluster_name}: {str(e)}")
        return {}


def get_deployed_services_kubectl(cluster_name: str, namespace: str) -> Dict[str, str]:
    """
    Fetch deployed services using kubectl directly.
    Fallback method if boto3 approach doesn't work.
    
    Args:
        cluster_name: EKS cluster name or kubeconfig context
        namespace: Kubernetes namespace
    
    Returns:
        Dict mapping service name to image version
    """
    try:
        cmd = f"""
        kubectl get deployments -n {namespace} --context={cluster_name} \
        -o jsonpath='{{range .items[*]}}{{.metadata.name}},{{.spec.template.spec.containers[0].image}}{{\"\\n\"}}{{end}}'
        """
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"kubectl error: {result.stderr}")
            return {}
        
        services = {}
        for line in result.stdout.strip().split('\n'):
            if not line or ',' not in line:
                continue
            
            parts = line.split(',', 1)
            if len(parts) == 2:
                service_name, image = parts
                version = extract_version_from_image(image)
                services[service_name.strip()] = version
        
        return services
    
    except Exception as e:
        print(f"Error running kubectl: {str(e)}")
        return {}


def extract_version_from_image(image: str) -> str:
    """
    Extract version from container image string.
    
    Examples:
        - 'myrepo/myapp:v1.2.3' -> 'v1.2.3'
        - 'myrepo/myapp:latest' -> 'latest'
        - 'myrepo/myapp@sha256:abc123...' -> 'sha256:abc123...'
        - '123456.dkr.ecr.us-east-1.amazonaws.com/myapp:v2.0.0' -> 'v2.0.0'
    
    Args:
        image: Full container image string
    
    Returns:
        Version string
    """
    # Check for digest format (sha256)
    if '@sha256:' in image:
        digest = image.split('@sha256:')[1][:12]  # First 12 chars of digest
        return f"sha256:{digest}"
    
    # Check for tag format
    if ':' in image:
        # Get everything after the last colon
        version = image.split(':')[-1]
        return version
    
    return 'unknown'


def get_service_versions_from_clusters(service_list: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Get image versions for a list of services from both ocp-hard and ocp-stage clusters.
    
    Args:
        service_list: List of service names to query
    
    Returns:
        Dict with structure:
        {
            'service-name': {
                'ocp-hard': 'v1.2.3',
                'ocp-stage': 'v1.2.2'
            }
        }
    """
    result = {}
    
    # Get versions from ocp-hard (hard/test environment)
    hard_services = get_deployed_services_kubectl(EKS_HARD_CLUSTER, EKS_HARD_NAMESPACE)
    
    # Get versions from ocp-stage (staging environment) 
    stage_services = get_deployed_services_kubectl(EKS_STAGE_CLUSTER, EKS_STAGE_NAMESPACE)
    
    for service in service_list:
        result[service] = {
            'ocp-hard': hard_services.get(service, 'N/A'),
            'ocp-stage': stage_services.get(service, 'N/A')
        }
    
    return result


def get_all_services_from_cluster(cluster_name: str, namespace: str) -> Dict[str, str]:
    """
    Get all deployed services and versions from a specific cluster.
    
    Args:
        cluster_name: EKS cluster name (ocp-hard or ocp-stage)
        namespace: Kubernetes namespace (use 'hard' for ocp-hard, 'stage' for ocp-stage)
    
    Returns:
        Dict mapping service name to image version
    """
    # Try kubectl method (most reliable)
    services = get_deployed_services_kubectl(cluster_name, namespace)
    
    if not services:
        print(f"Warning: No services found in {cluster_name}/{namespace}")
    
    return services


# Mock data for testing when kubectl is not available
def get_mock_service_versions() -> Dict[str, Dict[str, str]]:
    """
    Return mock data for testing purposes.
    Use this when kubectl/EKS access is not available.
    """
    return {
        'auth-service': {
            'ocp-hard': 'v3.4.1',
            'ocp-stage': 'v3.4.0'
        },
        'data-pipeline': {
            'ocp-hard': 'v2.1.0',
            'ocp-stage': 'v2.0.5'
        },
        'notification-svc': {
            'ocp-hard': 'v1.8.3',
            'ocp-stage': 'v1.8.2'
        },
        'report-engine': {
            'ocp-hard': 'v4.0.0',
            'ocp-stage': 'v3.9.5'
        },
        'tenant-router': {
            'ocp-hard': 'v3.1.5',
            'ocp-stage': 'v3.1.4'
        }
    }
