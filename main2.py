from utils.config_loader import load_properties
from services.bitbucket_service import fetch_release_data, get_headers
import csv

def run():
    config = load_properties("config/config.properties")

    workspace = config["bitbucket.workspace"]
    username = config["bitbucket.username"]
    app_password = config["bitbucket.app_password"]
    branch = config["release.branch"]
    repos = [r.strip() for r in config["repos"].split(",")]

    headers = get_headers(username, app_password)

    data = fetch_release_data(workspace, repos, branch, headers)

    for r in data:
        print(f"{r['repo']} | {r['us_id']} | {r['date']}")

    with open("release_report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["repo", "us_id", "commit", "date", "release"])
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    run()
