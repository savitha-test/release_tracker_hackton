import urllib
import requests
import urllib3
from utils.config_loader import load_properties

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

config = load_properties("config/config.properties")

workspace = config["bitbucket.workspace"]
username = config["bitbucket.username"]
app_password = config["bitbucket.app_password"]
repos = [r.strip() for r in config["repos"].split(",")]

def list_branches(workspace, repo, username, app_password):
    query = 'name~"release/"'
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/refs/branches?q={encoded_query}"
    
    branches = []
    while url:
        response = requests.get(url, auth=(username, app_password), verify=False)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return []
        data = response.json()
        branches.extend(data.get("values", []))
        url = data.get("next")
    
    return branches

print("Listing release branches...\n")
for repo in repos:
    print(f"\n{'='*60}")
    print(f"Repository: {repo}")
    print('='*60)
    branches = list_branches(workspace, repo, username, app_password)
    if branches:
        for branch in branches:
            print(f"  - {branch['name']}")
    else:
        print("  No release branches found or error occurred")
