"""
AT Pipeline Service - Fetch Acceptance Test results from Bitbucket/Codefresh
"""
import requests
import urllib3
import random
from typing import Dict, Optional
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import config
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.config_loader import load_properties
    config = load_properties("config/config.properties")
    
    BITBUCKET_WORKSPACE = config.get('bitbucket.workspace', '')
    BITBUCKET_USERNAME = config.get('bitbucket.username', '')
    BITBUCKET_APP_PASSWORD = config.get('bitbucket.app_password', '')
except Exception as e:
    print(f"Warning: Could not load config: {e}")
    BITBUCKET_WORKSPACE = ''
    BITBUCKET_USERNAME = ''
    BITBUCKET_APP_PASSWORD = ''


def get_latest_commit_builds(repo_slug: str, branch: str = "master") -> Optional[Dict]:
    """
    Get the build statuses from the latest commit on a branch.
    Each commit in Bitbucket has a Builds section where AT tests are listed.
    
    Args:
        repo_slug: Repository name (e.g., 'authentication')
        branch: Branch name to check (default: 'master')
    
    Returns:
        Dict with AT build info or None if not found
        {
            'status': 'SUCCESSFUL' | 'FAILED' | 'INPROGRESS' | 'STOPPED',
            'name': 'Build name',
            'key': 'Build key',
            'url': 'Build URL',
            'state': 'Build state',
            'error': '403' if access denied
        }
    """
    if not BITBUCKET_WORKSPACE or not BITBUCKET_USERNAME:
        return {'error': '403'}  # Credentials not configured
    
    try:
        # Step 1: Get the latest commit on the branch
        commits_url = f"https://api.bitbucket.org/2.0/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/commits/{branch}"
        commits_response = requests.get(
            commits_url,
            auth=(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD),
            verify=False,
            timeout=10,
            params={'pagelen': 1}  # Only get the most recent commit
        )
        
        if commits_response.status_code != 200:
            if commits_response.status_code == 403:
                return {'error': '403'}
            print(f"Error fetching commits for {repo_slug}: {commits_response.status_code}")
            return None
        
        commits_data = commits_response.json()
        commits = commits_data.get('values', [])
        
        if not commits:
            print(f"No commits found for {repo_slug} on branch {branch}")
            return None
        
        latest_commit = commits[0]
        commit_hash = latest_commit.get('hash')
        
        # Step 2: Get build statuses for this commit
        builds_url = f"https://api.bitbucket.org/2.0/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/commit/{commit_hash}/statuses/build"
        builds_response = requests.get(
            builds_url,
            auth=(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD),
            verify=False,
            timeout=10
        )
        
        if builds_response.status_code != 200:
            if builds_response.status_code == 403:
                return {'error': '403'}
            print(f"Error fetching builds for {repo_slug} commit {commit_hash}: {builds_response.status_code}")
            return None
        
        builds_data = builds_response.json()
        builds = builds_data.get('values', [])
        
        if not builds:
            print(f"No builds found for {repo_slug} commit {commit_hash}")
            return None
        
        # Step 3: Look for AT build with naming convention: "{repo_slug} - Acceptance"
        expected_at_name = f"{repo_slug} - Acceptance".lower()
        
        for build in builds:
            build_name = build.get('name', '').lower()
            build_key = build.get('key', '').lower()
            
            # Check if this is the AT build
            if expected_at_name in build_name or expected_at_name in build_key or '- acceptance' in build_name:
                return {
                    'status': build.get('state', 'UNKNOWN').upper(),
                    'name': build.get('name', ''),
                    'key': build.get('key', ''),
                    'url': build.get('url', ''),
                    'state': build.get('state', ''),
                    'description': build.get('description', '')
                }
        
        # If no AT build found
        print(f"No AT build found for {repo_slug}. Expected build name: '{repo_slug} - Acceptance'")
        return None
        
    except Exception as e:
        print(f"Error fetching build status for {repo_slug}: {str(e)}")
        return None


def get_at_test_result(repo_slug: str, branch: str = "master") -> str:
    """
    Get AT test result for a repository from commit builds.
    Looks for build with naming convention: "{repo_slug} - Acceptance" in the latest commit's builds section.
    
    Args:
        repo_slug: Repository name
        branch: Branch to check
    
    Returns:
        "✅ Passed" | "❌ Failed" | "⏳ In Progress" | "🔍 Not Found" | "🔒 No Access"
        
    Examples:
        - Repository "authentication" → Looks for "authentication - Acceptance" build in latest commit
        - Green/SUCCESSFUL status → "✅ Passed"
        - Failed status → "❌ Failed"
    """
    # TEMPORARILY COMMENTED OUT - FOR TESTING WITH RANDOM RESULTS
    # build_info = get_latest_commit_builds(repo_slug, branch)
    # 
    # if not build_info:
    #     # No AT build found
    #     return "🔍 Not Found"
    # 
    # # Check if it's an access error
    # if build_info.get('error') == '403':
    #     return "🔒 No Access"
    # 
    # status = build_info.get('status', '').upper()
    # state = build_info.get('state', '').upper()
    # 
    # # Bitbucket build statuses: SUCCESSFUL, FAILED, INPROGRESS, STOPPED
    # if status == 'SUCCESSFUL' or state == 'SUCCESSFUL':
    #     return "✅ Passed"
    # elif status == 'FAILED' or state == 'FAILED':
    #     return "❌ Failed"
    # elif status in ['INPROGRESS', 'IN_PROGRESS', 'PENDING', 'RUNNING'] or state in ['INPROGRESS', 'PENDING']:
    #     return "⏳ In Progress"
    # elif status in ['STOPPED', 'ERROR'] or state in ['STOPPED', 'ERROR']:
    #     return "❌ Failed"
    # 
    # # Unknown status
    # return "🔍 Not Found"
    
    # TEMPORARY: Return random pass/fail for testing
    random.seed(hash(repo_slug))  # Use repo_slug as seed for consistent results
    result = random.choice(["✅ Passed", "❌ Failed"])
    return result


def get_all_at_results(repos: list, branch: str = "master") -> Dict[str, str]:
    """
    Get AT test results for multiple repositories.
    
    Args:
        repos: List of repository names
        branch: Branch to check
    
    Returns:
        Dict mapping repo name to AT test result
    """
    results = {}
    for repo in repos:
        result = get_at_test_result(repo, branch)
        results[repo] = result
        print(f"AT Result for {repo}: {result}")
    
    return results


# For testing
if __name__ == "__main__":
    # Test with a sample repo
    test_repos = ['ng-platform-ui', 'notifications']
    results = get_all_at_results(test_repos)
    print("\n=== AT Test Results ===")
    for repo, result in results.items():
        print(f"{repo}: {result}")
