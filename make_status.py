# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pyyaml",
#     "requests",
# ]
# ///
import os
from datetime import datetime
from typing import Dict, List, Optional
from yaml import load, dump, Loader
import requests

with open("dashboard.yml") as f:
    config = load(f, Loader=Loader)

session = requests.Session()
session.headers.update(
    {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ome-status-dashboard",
    }
)

# Set via https://github.com/settings/personal-access-tokens
token = os.getenv("GITHUB_TOKEN")
if token:
    session.headers["Authorization"] = f"Bearer {token}"


def format_date(iso_timestamp: str) -> str:
    return (
        datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00")).date().isoformat()
    )


def fetch_last_commit_info(owner: str, repo: str, session: requests.Session) -> dict:
    """
    Fetch latest commit from the GitHub API.
    """
    base_url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    latest_resp = session.get(base_url, params={"per_page": 1})
    if latest_resp.status_code == 404:
        return

    commits = latest_resp.json()

    last_commit = commits[0]
    url = last_commit.get("html_url")
    author_block = last_commit["commit"]["author"]
    date = format_date(author_block.get("date"))
    author = last_commit["author"]["login"]
    return {
        "url": url,
        "date": date,
        "author": author,
    }


def fetch_repo_info(owner: str, repo: str, session: requests.Session) -> Optional[dict]:
    """
    Fetch repository metadata from the GitHub API.
    """
    resp = session.get(f"https://api.github.com/repos/{owner}/{repo}")
    if resp.status_code == 404:
        return
    info = resp.json()
    return {
        "created_at": info.get("created_at"),
        "updated_at": info.get("updated_at"),
        "open_issues": info.get("open_issues_count"),
        "description": info.get("description"),
        "topics": info.get("topics", []),
        "size": info.get("size"),
    }


for section in config:
    for package in section["packages"]:
        package["user"], package["name"] = package["repo"].split("/")

        repo_info = fetch_repo_info(package["user"], package["name"], session)
        if repo_info:
            package["repo_info"] = repo_info
        else:
            package["error"] = True

        last_commit_info = fetch_last_commit_info(
            package["user"], package["name"], session
        )
        if last_commit_info:
            package["last_commit"] = last_commit_info

snapshot = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "sections": config,
}

with open("generated.yml", "w") as generated_output:
    dump(snapshot, generated_output)
