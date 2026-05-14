# AWS EKS & AT Pipeline Integration Setup Guide

## Overview
This Release Tracker integrates with:
1. **AWS EKS** - Fetch real-time deployed image versions from Kubernetes clusters
2. **Bitbucket Pipelines** - Fetch Acceptance Test (AT) results for Go/No-go decisions

## Features Added

### 1. Staging Deployment Readiness Dashboard
- **Image version in hardening**: Shows versions deployed in hard-k8s cluster
- **Image version in stage**: Shows currently deployed versions in stage-k8s cluster  
- **AT Test Cases**: Real-time status from Bitbucket pipelines (✅ Passed / ❌ Failed / ⏳ In Progress / 🔍 Not Found)
- **Go/No-go Status**: Automatically determined based on AT test results

### 2. Release Dashboard
- **Current Deployments Section**: Displays currently deployed versions of selected repositories in ocp-stage
- **Per-Repository Version Info**: Each repository expander shows the currently deployed version

## Prerequisites

### 1. AWS CLI Configuration
```bash
# Install AWS CLI if not already installed
brew install awscli  # macOS
# or
pip install awscli

# Configure AWS credentials
aws configure
```

### 2. kubectl Installation and Configuration
```bash
# Install kubectl
brew install kubectl  # macOS
# or
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"

# Update kubeconfig for EKS clusters
aws eks update-kubeconfig --region us-east-1 --name ocp-hard --alias ocp-hard
aws eks update-kubeconfig --region us-east-1 --name ocp-stage --alias ocp-stage

# Verify access
kubectl get deployments -n hard --context=ocp-hard
kubectl get deployments -n stage --context=ocp-stage
```

### 3. Required IAM Permissions
Your AWS user/role needs the following permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    }
  ]
}
```

## Configuration

Update `config/config.properties` with your EKS settings:

```properties
# AWS EKS Configuration
aws.region=us-east-2
eks.hard.cluster=hard-k8s
eks.hard.namespace=hard
eks.stage.cluster=stage-k8s
eks.stage.namespace=stage

# Bitbucket Configuration (for AT pipeline results)
bitbucket.workspace=omnicell
bitbucket.username=your.email@company.com
bitbucket.app_password=YOUR_APP_PASSWORD
release.branch=release/2026-03-02
repos=ng-platform-ui,notifications
```

## AT Pipeline Integration

### Overview
The dashboard fetches Acceptance Test (AT) results directly from Bitbucket pipelines to determine Go/No-go status.

### How It Works
1. **Pipeline Detection**: Automatically detects AT pipelines by name (containing 'at', 'acceptance', or 'test')
2. **Status Mapping**:
   - ✅ **Passed**: Pipeline completed successfully → **Go**
   - ❌ **Failed**: Pipeline failed → **No-go**
   - ⏳ **In Progress**: Pipeline currently running → **No-go**
   - 🔍 **Not Found**: No AT pipeline found → **No-go**
3. **Real-time Updates**: Fetches latest pipeline status when dashboard refreshes

### Service Mapping
The system automatically maps service names to repository names:
- Service names use underscores: `my_service`
- Repository names use hyphens: `my-service`
- Automatic conversion handles common naming patterns

### AT Pipeline Requirements
Your Bitbucket pipelines should:
1. Have a name containing "AT", "acceptance", or "test" (case-insensitive)
2. Run on the release branch specified in config
3. Report proper success/failure status

Example pipeline name patterns:
- `AT Tests`
- `Acceptance Testing`
- `End-to-End Tests`
- `Integration AT`

## Usage

### Real-Time EKS Data (Default)

The application now fetches real-time data from AWS EKS clusters by default.

**Prerequisites:**
1. Configure kubectl access to your EKS clusters (see Prerequisites section above)
2. Ensure your AWS credentials are set up
3. Verify cluster access:
   ```bash
   kubectl get deployments -n hard --context=ocp-hard
   kubectl get deployments -n stage --context=ocp-stage
   ```

**Running the Application:**
```bash
streamlit run main.py
```

The dashboard will automatically:
- Fetch deployed services from ocp-hard (hard namespace)
- Fetch deployed services from ocp-stage (stage namespace)
- Compare versions between environments
- Display deployment readiness status

## Architecture

### Service Structure
```
services/
├── eks_service.py          # AWS EKS integration service
├── bitbucket_service.py    # Bitbucket API integration
└── parser.py               # Commit message parsing
```

### Key Functions

#### `get_all_services_from_cluster(cluster_name, namespace)`
Fetches all deployed services from a specific EKS cluster.

**Parameters:**
- `cluster_name`: EKS cluster name (e.g., 'ocp-hard', 'ocp-stage')
- `namespace`: Kubernetes namespace
  - For ocp-hard cluster: use 'hard'
  - For ocp-stage cluster: use 'stage'

**Returns:**
```python
{
    'service-name': 'v1.2.3',
    'another-service': 'v2.0.0'
}
```

#### `extract_version_from_image(image)`
Extracts version from container image strings.

**Examples:**
- `myrepo/myapp:v1.2.3` → `v1.2.3`
- `123456.dkr.ecr.us-east-1.amazonaws.com/myapp:v2.0.0` → `v2.0.0`
- `myrepo/myapp@sha256:abc123...` → `sha256:abc123...`

## Troubleshooting

### Issue: "kubectl: command not found"
**Solution:** Install kubectl (see Prerequisites)

### Issue: "Unable to connect to the server"
**Solution:** Update your kubeconfig:
```bash
aws eks update-kubeconfig --region us-east-1 --name ocp-hard
aws eks update-kubeconfig --region us-east-1 --name ocp-stage
```

### Issue: "You must be logged in to the server (Unauthorized)"
**Solution:** Check AWS credentials and IAM permissions:
```bash
aws sts get-caller-identity
kubectl auth can-i get deployments --context=ocp-hard
```

### Issue: "No services found"
**Solution:** 
1. Verify namespace: `kubectl get namespaces --context=ocp-hard`
2. Check deployments in correct namespaces:
   - `kubectl get deployments -n hard --context=ocp-hard`
   - `kubectl get deployments -n stage --context=ocp-stage`
3. Update namespace in config.properties if different

### Issue: SSL Certificate Errors
**Solution:** Already handled - SSL verification is disabled for corporate environments

## Live Data from EKS

The application now exclusively uses **real-time data from AWS EKS clusters**:

- **Direct kubectl Integration**: Queries live deployments from your Kubernetes clusters
- **Real-time Version Info**: Shows actual deployed image versions
- **No Mock Data**: All data is fetched directly from ocp-hard and ocp-stage clusters

**Note**: If you need to test without EKS access, you can temporarily modify the code to use the `get_mock_service_versions()` function available in [services/eks_service.py](services/eks_service.py#L205).

## Security Notes

1. **AWS Credentials**: Never commit AWS credentials to version control
2. **Config File**: The `config/config.properties` should be added to `.gitignore`
3. **kubectl Context**: Ensure you're using the correct context before querying

## Future Enhancements

- [ ] Add ECR image registry integration
- [ ] Support for multiple namespaces
- [ ] Historical version tracking
- [ ] Automated deployment status checks
- [ ] Integration with CI/CD pipelines
- [ ] Support for other cloud providers (Azure AKS, GCP GKE)

## Support

For issues or questions, contact the Release Intelligence team or refer to:
- AWS EKS Documentation: https://docs.aws.amazon.com/eks/
- kubectl Documentation: https://kubernetes.io/docs/reference/kubectl/
