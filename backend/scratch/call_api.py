import requests

login_url = "http://localhost:8000/api/v1/auth/login"
response = requests.post(login_url, data={"username": "user@example.com", "password": "password123"})
print("Login status:", response.status_code)
token = response.json().get("access_token")
print("Token:", token[:15] + "...")

headers = {"Authorization": f"Bearer {token}"}
resp = requests.get("http://localhost:8000/api/v1/integrations", headers=headers)
print("GET integrations status:", resp.status_code)
print("GET integrations headers:", dict(resp.headers))
print("GET integrations body:", resp.json())
