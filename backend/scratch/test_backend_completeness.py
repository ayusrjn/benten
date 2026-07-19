import sys
import os
import requests
import time
import uuid

# Set target backend URL
BACKEND_URL = "http://localhost:8000/api/v1"

# Generate a unique user email to prevent registration conflicts
random_suffix = uuid.uuid4().hex[:6]
TEST_USER = {
    "email": f"test_user_{random_suffix}@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
}

def verify_endpoints():
    print("=== Starting Backend Completeness Verification ===")
    
    # 1. Register / Login
    print("\n[Auth] Registering or logging in test user...")
    register_url = f"{BACKEND_URL}/auth/register"
    reg_resp = requests.post(register_url, json=TEST_USER)
    
    login_url = f"{BACKEND_URL}/auth/login"
    login_payload = {
        "username": TEST_USER["email"],
        "password": TEST_USER["password"]
    }
    login_resp = requests.post(login_url, data=login_payload)
    if login_resp.status_code != 200:
        print(f"FAILED: Login response: {login_resp.status_code} - {login_resp.text}")
        return False
        
    token_data = login_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        print("FAILED: No access token found in login response")
        return False
    print(f"SUCCESS: Logged in. Token starts with: {access_token[:15]}...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 2. Get Organization Stats
    print("\n[Organization] Fetching stats...")
    org_resp = requests.get(f"{BACKEND_URL}/organization", headers=headers)
    if org_resp.status_code != 200:
        print(f"FAILED: Organization stats response: {org_resp.status_code} - {org_resp.text}")
        return False
    org_data = org_resp.json()
    print(f"SUCCESS: Org: {org_data['name']}, Members: {org_data['membersCount']}, Projects: {org_data['projectsCount']}")
    
    # Get Organization Members
    print("[Organization] Fetching members...")
    members_resp = requests.get(f"{BACKEND_URL}/organization/members", headers=headers)
    if members_resp.status_code != 200:
        print(f"FAILED: Members response: {members_resp.status_code}")
        return False
    print(f"SUCCESS: Members count from headers: {members_resp.headers.get('x-total-count')}")
    
    # 3. Create a Project
    print("\n[Projects] Creating a new project...")
    proj_payload = {"name": f"Verification Project {random_suffix}"}
    create_proj_resp = requests.post(f"{BACKEND_URL}/projects", json=proj_payload, headers=headers)
    if create_proj_resp.status_code != 201:
        print(f"FAILED: Create project: {create_proj_resp.status_code} - {create_proj_resp.text}")
        return False
    project_data = create_proj_resp.json()
    project_id = project_data["id"]
    print(f"SUCCESS: Created Project: {project_data['name']} (ID: {project_id})")

    # 4. Create an Agent under this Project
    print("\n[Agents] Registering a new agent...")
    agent_payload = {
        "projectId": project_id,
        "name": "Verification Sales Agent",
        "provider": "vapi"
    }
    create_agent_resp = requests.post(f"{BACKEND_URL}/agents", json=agent_payload, headers=headers)
    if create_agent_resp.status_code != 201:
        print(f"FAILED: Register agent: {create_agent_resp.status_code} - {create_agent_resp.text}")
        return False
    agent_data = create_agent_resp.json()
    agent_id = agent_data["id"]
    print(f"SUCCESS: Registered Agent: {agent_data['name']} (ID: {agent_id})")

    # 5. Trigger call ingestion (will run Celery worker tasks)
    print("\n[Conversations] Triggering background call ingestion...")
    ingest_payload = {
        "projectId": project_id,
        "provider": "vapi",
        "providerCallId": "mock_verification_call_123"
    }
    ingest_resp = requests.post(f"{BACKEND_URL}/conversations", json=ingest_payload, headers=headers)
    if ingest_resp.status_code != 202:
        print(f"FAILED: Trigger ingestion: {ingest_resp.status_code} - {ingest_resp.text}")
        return False
    print(f"SUCCESS: Ingestion task accepted: {ingest_resp.json()}")

    # Wait for Celery worker to finish processing the call
    print("Waiting 4 seconds for Celery processing to complete...")
    time.sleep(4)

    # 6. Fetch Conversations List
    print("\n[Conversations] Listing conversations...")
    convs_resp = requests.get(f"{BACKEND_URL}/conversations?projectId={project_id}", headers=headers)
    if convs_resp.status_code != 200:
        print(f"FAILED: Conversations list: {convs_resp.status_code}")
        return False
    convs = convs_resp.json()
    print(f"SUCCESS: Found {len(convs)} conversations.")
    if len(convs) == 0:
        print("FAILED: Ingestion failed, no conversations found in project.")
        return False
        
    conv_id = convs[0]["id"]
    print(f"SUCCESS: Ingested call ID: {conv_id}, Status: {convs[0]['status']}, Health Score: {convs[0]['score']}")
    
    # Fetch details of the conversation (with segments)
    print("\n[Conversations] Fetching detailed conversation...")
    detail_resp = requests.get(f"{BACKEND_URL}/conversations/{conv_id}", headers=headers)
    if detail_resp.status_code != 200:
        print(f"FAILED: Conversation detail: {detail_resp.status_code}")
        return False
    detail = detail_resp.json()
    print(f"SUCCESS: Agent: {detail['agentName']}, segments count: {len(detail['segments'])}")
    if len(detail['segments']) == 0:
        print("FAILED: No transcript speech segments saved for conversation")
        return False
    
    # 7. Create Alert Rule
    print("\n[Alerts] Creating an alert rule...")
    rule_payload = {
        "projectId": project_id,
        "metric": "Latency",
        "threshold": "> 900ms",
        "duration": "1m",
        "action": "Slack Alert"
    }
    create_rule_resp = requests.post(f"{BACKEND_URL}/alert_rules", json=rule_payload, headers=headers)
    if create_rule_resp.status_code != 201:
        print(f"FAILED: Create alert rule: {create_rule_resp.status_code}")
        return False
    rule_data = create_rule_resp.json()
    print(f"SUCCESS: Created alert rule: {rule_data['metric']} {rule_data['threshold']} (ID: {rule_data['id']})")
    
    # Fetch alert rules list
    rules_resp = requests.get(f"{BACKEND_URL}/alert_rules?projectId={project_id}", headers=headers)
    if rules_resp.status_code != 200:
        print(f"FAILED: Alert rules list: {rules_resp.status_code}")
        return False
    print(f"SUCCESS: Found {len(rules_resp.json())} rules.")
    
    # 8. Fetch Dashboard Metrics
    print("\n[Dashboard] Fetching metrics...")
    dash_resp = requests.get(f"{BACKEND_URL}/dashboard/metrics?projectId={project_id}", headers=headers)
    if dash_resp.status_code != 200:
        print(f"FAILED: Dashboard metrics: {dash_resp.status_code} - {dash_resp.text}")
        return False
    dash_data = dash_resp.json()
    print(f"SUCCESS: Conversations: {dash_data['conversationsCount']}, Avg Latency: {dash_data['latencyAvg']}ms")
    print(f"SUCCESS: Sparkline Trends - Latency: {dash_data['latencyTrend']}, Volume: {dash_data['volumeTrend']}")
    
    print("\n=== All Backend Endpoints Successfully Verified! ===")
    return True

if __name__ == "__main__":
    if not verify_endpoints():
        sys.exit(1)
