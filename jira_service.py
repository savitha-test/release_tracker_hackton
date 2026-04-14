import requests
from requests.auth import HTTPBasicAuth

from release_summary import generate_release_summary
from utils.config_loader import load_properties

config = load_properties("config/config.properties")
JIRA_BASE_URL = config["jira.domain"]
EMAIL = config["jira.userid"]
API_TOKEN = config["jira.api_token"]

def get_jira_issues(issue_keys):
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"

    jql = f'key in ("' + '","'.join(issue_keys) + '")'
    print(jql)

    response = requests.post(
        url,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        json={  # ✅ IMPORTANT
            "jql": jql,
            "maxResults": 100,
            "fields": [
                "summary",
                "description",
                "issuetype",
                "status",
                "customfield_10057"  # acceptance criteria
            ]
        },
        params={"jql": jql},
        auth=HTTPBasicAuth(EMAIL, API_TOKEN)
    )
    print(response.status_code)
    data = response.json()

    issues = []
    for issue in data.get("issues", []):
        fields = issue["fields"]
        print("type " ,fields.get("issuetype", {}).get("name") )
        issue_type=fields.get("issuetype", {}).get("name")
        if issue_type == "Bug" or issue_type == "Story":
         issues.append({
            "id": issue["key"],
            "title": fields.get("summary"),
            "description": extract_adf_text(fields.get("description")),
            "acceptance_criteria": extract_adf_text(fields.get("customfield_10057")),
            "type": fields.get("issuetype", {}).get("name"),
            "status": fields.get("status", {}).get("name"),
         })

    return issues



def extract_adf_text(node):
    text_parts = []

    if isinstance(node, dict):
        if node.get("type") == "text":
            text_parts.append(node.get("text", ""))

        elif node.get("type") in ["paragraph", "listItem"]:
            text_parts.append("\n")

        for child in node.get("content", []):
            text_parts.append(extract_adf_text(child))

    elif isinstance(node, list):
        for item in node:
            text_parts.append(extract_adf_text(item))

    return "".join(text_parts)


if __name__ == "__main__":
    ids = "CE-9672,CORE-23275,POC-49284,POC-23275,POC-47851,POC-9685,DAP-9685,DAP-10034,DAP-9865,DAP-9887"
    issue_list = ids.split(",")
    print(len(issue_list))
    data=get_jira_issues(issue_list)
    print(len(data))
    summary = generate_release_summary(data)
    print('AI', summary)