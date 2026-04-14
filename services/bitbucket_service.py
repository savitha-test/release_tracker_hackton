import base64
import requests
from datetime import datetime

from services.parser import extract_us_ids


def get_headers(username, app_password):
    auth_str = f"{username}:{app_password}"
    auth_bytes = base64.b64encode(auth_str.encode()).decode()
    return {
        "Authorization": f"Basic {auth_bytes}",
        "Content-Type": "application/json"
    }


def fetch_release_data(workspace, repos, current_branch, headers, start_date):
    print(f"Fetching data for {current_branch} from {start_date}...")
    results = []

    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))

    for repo in repos:

        url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/commits/{current_branch}?pagelen=100&fields=values.hash,values.date,values.message"
        print(f"Fetching data for repo {repo}...")
        print(url)


        while url:
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print(f"Error for repo {repo}: {response.status_code}")
                break

            data = response.json()
            stop_pagination = False

            for commit in data.get("values", []):
                commit_dt = datetime.fromisoformat(commit["date"].replace("Z", "+00:00"))

                # Stop when we go past start_date
                if commit_dt < start_dt:
                    stop_pagination = True
                    break

                us_ids = extract_us_ids(commit.get("message", ""))

                for us in us_ids:
                    results.append({
                        "repo": repo,
                        "us_id": us,
                        "commit": commit.get("hash"),
                        "date": commit.get("date"),
                        "release": current_branch
                    })

            if stop_pagination:
                print(f"Reached start_date, stopping pagination for {repo}")
                break

            url = data.get("next")

    # -------- Deduplicate --------
    unique = {(r["repo"], r["us_id"]): r for r in results}.values()
    print(f"Fetched {len(unique)} results for {current_branch}...")
    return list(unique)