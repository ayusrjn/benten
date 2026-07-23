#!/usr/bin/env python3
import os
import sys
import re
import yaml
import requests

# Constants
YAML_FILE = "known_failure.yaml"
MARKER_REGEX = r"<!-- FAILURE_ID:\s*([a-zA-Z0-9-]+)\s*-->"

def log_error_and_exit(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def validate_failures_schema(data):
    """
    Validates that the loaded YAML data conforms to the schema rules.
    If invalid, prints error and exits non-zero.
    """
    if not isinstance(data, dict) or "failures" not in data or not isinstance(data["failures"], list):
        log_error_and_exit("Invalid YAML. Top level must contain a dictionary with a 'failures' list.")

    failures = data["failures"]
    allowed = {
        "severity": {"critical", "high", "medium", "low"},
        "priority": {"p0", "p1", "p2", "p3"},
        "status": {"handled", "unhandled", "fixed"}
    }
    required_fields = [
        "id", "name", "component", "severity", "priority", 
        "status", "category", "triggers", "behavior", "remediation", "labels"
    ]
    seen_ids = set()

    for idx, failure in enumerate(failures):
        if not isinstance(failure, dict):
            log_error_and_exit(f"Failure entry at index {idx} must be a dictionary.")

        # Check required fields
        for field in required_fields:
            if field not in failure or failure[field] is None:
                log_error_and_exit(f"Failure at index {idx} is missing required field: '{field}'")

        fid = failure["id"]
        if fid in seen_ids:
            log_error_and_exit(f"Duplicate failure ID detected: '{fid}'")
        seen_ids.add(fid)

        # Value constraint checks
        for key, allowed_vals in allowed.items():
            val = str(failure[key]).lower()
            if val not in allowed_vals:
                log_error_and_exit(f"Failure '{fid}' has invalid {key} '{failure[key]}'. Allowed: {allowed_vals}")

        # List fields checks
        list_fields = ["triggers", "remediation", "labels"]
        for field in list_fields:
            items = failure[field]
            if not isinstance(items, list):
                log_error_and_exit(f"Failure '{fid}' field '{field}' must be a list.")
            for item in items:
                if not isinstance(item, str) or not item.strip():
                    log_error_and_exit(f"Failure '{fid}' has an empty or invalid item in '{field}'.")

    return failures

def generate_issue_body(failure):
    triggers_markdown = "\n".join(f"- {t}" for t in failure["triggers"])
    remediation_markdown = "\n".join(f"- {r}" for r in failure["remediation"])
    
    component = failure["component"].replace("-", " ").title()
    severity = str(failure["severity"]).title()
    priority = str(failure["priority"]).upper()
    status = str(failure["status"]).title()
    category = failure["category"].replace("-", " ").title()
    
    body = f"""<!-- FAILURE_ID: {failure['id']} -->

## Summary

{failure['name']}

---

### Component

{component}

### Severity

{severity}

### Priority

{priority}

### Status

{status}

### Category

{category}

---

## Triggers

{triggers_markdown}

---

## Current Behavior

{failure['behavior'].strip()}

---

## Suggested Remediation

{remediation_markdown}

---

This issue is automatically generated from
known_failure.yaml.

Do not edit manually."""
    return body.strip()

def fetch_paginated(url, headers, params=None):
    """
    Utility helper to perform a GET request and handle GitHub's Link header pagination.
    """
    results = []
    page = 1
    actual_params = {"per_page": 100}
    if params:
        actual_params.update(params)
    
    while True:
        actual_params["page"] = page
        response = requests.get(url, headers=headers, params=actual_params)
        if response.status_code != 200:
            log_error_and_exit(f"GitHub API fetch failed: {response.status_code} - {response.text}")
        data = response.json()
        if not data:
            break
        results.extend(data)
        if "rel=\"next\"" not in response.headers.get("Link", ""):
            break
        page += 1
    return results

def main():
    # Allow custom YAML file path via command line argument
    yaml_file = sys.argv[1] if len(sys.argv) > 1 else YAML_FILE

    # 1. Load and Validate YAML
    if not os.path.exists(yaml_file):
        log_error_and_exit(f"Known failures YAML file '{yaml_file}' does not exist.")

    try:
        with open(yaml_file, "r") as f:
            yaml_data = yaml.safe_load(f)
    except Exception as e:
        log_error_and_exit(f"Failed to parse YAML file: {e}")

    failures = validate_failures_schema(yaml_data)

    # Allow local dry-run if GitHub context variables are missing
    is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    token = os.environ.get("GITHUB_TOKEN")
    owner_repo = os.environ.get("GITHUB_REPOSITORY")

    if not token or not owner_repo:
        if is_github_actions:
            log_error_and_exit("GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required in GitHub Actions.")
        else:
            print("Running in LOCAL DRY-RUN mode (missing GITHUB_TOKEN or GITHUB_REPOSITORY).")
            print(f"Validation successful. Loaded {len(failures)} failures.")
            sys.exit(0)

    # Setup GitHub HTTP Client parameters
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    api_base = f"https://api.github.com/repos/{owner_repo}"

    # 2. Fetch all repository labels to ensure the required ones exist
    print("Fetching repository labels...")
    lbl_list = fetch_paginated(f"{api_base}/labels", headers)
    existing_labels = {l["name"].lower() for l in lbl_list}

    # 3. Auto-create any missing labels
    required_labels = {lbl for failure in failures for lbl in failure["labels"]}
    required_labels.add("known-failure")

    for label in required_labels:
        if label.lower() not in existing_labels:
            print(f"Label '{label}' does not exist. Creating it...")
            url = f"{api_base}/labels"
            payload = {"name": label, "color": "ededed"}
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 201:
                existing_labels.add(label.lower())
            else:
                print(f"Warning: Could not create label '{label}': {res.status_code} - {res.text}")

    # 4. Fetch all Issues (open and closed)
    print("Fetching repository issues...")
    github_issues = fetch_paginated(f"{api_base}/issues", headers, {"state": "all"})

    # 5. Extract automation-managed issues using marker
    # Format: { failure_id: issue_object }
    managed_issues = {}
    for issue in github_issues:
        if "pull_request" in issue:
            continue
        
        body = issue.get("body") or ""
        match = re.search(MARKER_REGEX, body)
        if match:
            fid = match.group(1)
            # If multiple open issues exist for some reason, we take the one that is currently open (if any)
            if fid in managed_issues:
                existing = managed_issues[fid]
                if existing["state"] == "closed" and issue["state"] == "open":
                    managed_issues[fid] = issue
            else:
                managed_issues[fid] = issue

    # 6. Synchronize
    loaded_count = len(failures)
    created_list = []
    updated_list = []
    closed_list = []
    skipped_count = 0

    yaml_failure_ids = set()

    for failure in failures:
        fid = failure["id"]
        yaml_failure_ids.add(fid)
        
        expected_title = f"[{fid}] {failure['name']}"
        expected_body = generate_issue_body(failure)
        expected_labels = set(failure["labels"])
        status = str(failure["status"]).lower()

        issue = managed_issues.get(fid)

        # Status 'fixed' indicates that it should be closed (if it exists) or skipped (if it doesn't).
        if status == "fixed":
            # If it exists on GitHub and is open, close it.
            if issue and issue["state"] == "open":
                # Comment first
                comm_url = f"{api_base}/issues/{issue['number']}/comments"
                comment_payload = {"body": "Automatically closed because the failure no longer exists in known_failure.yaml."}
                requests.post(comm_url, headers=headers, json=comment_payload)

                # Then PATCH to close
                close_url = f"{api_base}/issues/{issue['number']}"
                requests.patch(close_url, headers=headers, json={"state": "closed"})
                closed_list.append(fid)
            else:
                skipped_count += 1
            continue

        # For handled/unhandled (active) failures:
        if not issue:
            # Create a brand new issue
            print(f"Creating issue for failure {fid}...")
            url = f"{api_base}/issues"
            payload = {
                "title": expected_title,
                "body": expected_body,
                "labels": list(expected_labels)
            }
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code != 201:
                log_error_and_exit(f"Failed to create issue for {fid}: {res.status_code} - {res.text}")
            created_list.append(fid)
        else:
            # Issue exists. Check if we need to update or reopen it.
            issue_labels = {lbl["name"] for lbl in issue.get("labels", [])}
            body_changed = issue.get("body", "").strip() != expected_body.strip()
            title_changed = issue.get("title", "") != expected_title
            labels_changed = issue_labels != expected_labels
            reopen_needed = issue["state"] == "closed"

            if body_changed or title_changed or labels_changed or reopen_needed:
                print(f"Updating issue for failure {fid}...")
                patch_payload = {
                    "title": expected_title,
                    "body": expected_body,
                    "labels": list(expected_labels)
                }
                if reopen_needed:
                    patch_payload["state"] = "open"

                patch_url = f"{api_base}/issues/{issue['number']}"
                res = requests.patch(patch_url, headers=headers, json=patch_payload)
                if res.status_code != 200:
                    log_error_and_exit(f"Failed to update issue for {fid}: {res.status_code} - {res.text}")
                updated_list.append(fid)
            else:
                skipped_count += 1

    # 7. Check for removed failures (issues exists in GitHub under our tracker but not in YAML)
    for fid, issue in managed_issues.items():
        if fid not in yaml_failure_ids and issue["state"] == "open":
            print(f"Closing removed failure issue {fid}...")
            # Comment first
            comm_url = f"{api_base}/issues/{issue['number']}/comments"
            comment_payload = {"body": "Automatically closed because the failure no longer exists in known_failure.yaml."}
            requests.post(comm_url, headers=headers, json=comment_payload)

            # Then PATCH to close
            close_url = f"{api_base}/issues/{issue['number']}"
            requests.patch(close_url, headers=headers, json={"state": "closed"})
            closed_list.append(fid)

    # 8. Print Sync log matching specification
    print(f"\nLoaded {loaded_count} failures\n")
    
    if created_list:
        print("Created:")
        for item in created_list:
            print(f"+ {item}")
        print()
        
    if updated_list:
        print("Updated:")
        for item in updated_list:
            print(f"~ {item}")
        print()
        
    if closed_list:
        print("Closed:")
        for item in closed_list:
            print(f"- {item}")
        print()
        
    print("Skipped:")
    print(f"{skipped_count} unchanged")

if __name__ == "__main__":
    main()
