import httpx

from app.config import settings

_auth = (settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)
_headers = {"Accept": "application/json", "Content-Type": "application/json"}


def _url(path: str) -> str:
    return f"{settings.JIRA_SITE_URL}/rest/api/3{path}"


def get_issue(issue_key: str) -> dict:
    r = httpx.get(_url(f"/issue/{issue_key}"), auth=_auth, headers=_headers)
    r.raise_for_status()
    return r.json()


def add_comment(issue_key: str, text: str) -> dict:
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": text}]}
            ],
        }
    }
    r = httpx.post(_url(f"/issue/{issue_key}/comment"), auth=_auth, headers=_headers, json=body)
    r.raise_for_status()
    return r.json()


def update_labels(issue_key: str, labels: list[str]) -> None:
    body = {"update": {"labels": [{"add": label} for label in labels]}}
    r = httpx.put(_url(f"/issue/{issue_key}"), auth=_auth, headers=_headers, json=body)
    r.raise_for_status()


def assign_issue(issue_key: str, account_id: str | None) -> None:
    body = {"accountId": account_id}
    r = httpx.put(_url(f"/issue/{issue_key}/assignee"), auth=_auth, headers=_headers, json=body)
    r.raise_for_status()


def create_subtask(parent_key: str, project_key: str, summary: str, description: str) -> dict:
    body = {
        "fields": {
            "project": {"key": project_key},
            "parent": {"key": parent_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": description}]}
                ],
            },
            "issuetype": {"name": "Sub-task"},
        }
    }
    r = httpx.post(_url("/issue"), auth=_auth, headers=_headers, json=body)
    r.raise_for_status()
    return r.json()


def create_issue(project_key: str, summary: str, description: str, issue_type: str = "Task") -> dict:
    body = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": description}]}
                ],
            },
            "issuetype": {"name": issue_type},
        }
    }
    r = httpx.post(_url("/issue"), auth=_auth, headers=_headers, json=body)
    r.raise_for_status()
    return r.json()
