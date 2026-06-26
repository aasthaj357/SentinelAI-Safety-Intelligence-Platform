import requests

base_url = "http://127.0.0.1:8000"
project_id = "f0cd8aaf-a17e-4dd9-953b-a5c1a014e8c7"
user_id = "00000000-0000-4000-a000-000000000001"

print(f"Triggering demo load for project: {project_id}...")
try:
    r = requests.post(f"{base_url}/api/demo/load", json={"project_id": project_id, "user_id": user_id})
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Request failed: {e}")
