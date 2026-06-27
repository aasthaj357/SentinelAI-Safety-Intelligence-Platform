import os
import time
import requests
from supabase import create_client

url= os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SECRET_KEY"]
supabase = create_client(url, key)

base_url = "http://127.0.0.1:8000"

def run_tests():
    print("1. Registration/Login")
    email = f"test_{int(time.time())}@gmail.com"
    password = "password123!"
    user_id = None
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        print(f"Registered: {email}")
        user_id = res.user.id
        time.sleep(2)
        # Login
        res_login = supabase.auth.sign_in_with_password({"email": email, "password": password})
        print(f"Logged in successfully")
    except Exception as e:
        print("Auth failed:", e)

    print("\n2. Dashboard loading")
    try:
        r = requests.get(f"{base_url}/api/dashboard/stats")
        print(f"Dashboard Stats: {r.status_code} - {r.text}")
    except Exception as e:
        print("Dashboard loading failed:", e)

    print("\n3. Load Demo Data")
    project_id = "11111111-1111-4111-a111-111111111111"
    video_id = None
    try:
        r = requests.post(f"{base_url}/api/demo/load", json={"project_id": project_id, "user_id": user_id or "00000000-0000-4000-a000-000000000001"})
        print(f"Load Demo Data: {r.status_code} - {r.text}")
        if r.status_code == 200:
            data = r.json()
            # video_id is not returned anymore, we'll just ignore it or hardcode for next tests
    except Exception as e:
        print("Load Demo Data failed:", e)

    if not project_id:
        print("Skipping dependent tests due to missing project_id")
        return

    print("\n4. Upload SOP")
    try:
        files = {'file': ('test_sop.pdf', b'fake pdf content', 'application/pdf')}
        data = {'project_id': project_id, 'user_id': user_id or "00000000-0000-4000-a000-000000000001"}
        r = requests.post(f"{base_url}/api/upload/sop", files=files, data=data)
        print(f"Upload SOP: {r.status_code} - {r.text}")
    except Exception as e:
        print("Upload SOP failed:", e)

    print("\n5. Upload Video")
    file_url = None
    try:
        files = {'file': ('test_video.mp4', b'fake video content', 'video/mp4')}
        data = {'project_id': project_id, 'user_id': user_id or "00000000-0000-4000-a000-000000000001"}
        r = requests.post(f"{base_url}/api/upload/video", files=files, data=data)
        print(f"Upload Video: {r.status_code} - {r.text}")
        if r.status_code == 200:
            data = r.json()
            video_id = data.get("video_id")
            file_url = data.get("storage_path")
    except Exception as e:
        print("Upload Video failed:", e)

    print("\n6. Analysis job creation")
    try:
        payload = {
            "video_id": video_id,
            "project_id": project_id,
            "file_url": file_url or "test_video.mp4",
            "user_id": user_id or "00000000-0000-4000-a000-000000000001"
        }
        r = requests.post(f"{base_url}/api/analysis/video", json=payload)
        print(f"Analysis job: {r.status_code} - {r.text}")
    except Exception as e:
        print("Analysis job creation failed:", e)

    print("\n7. Safety Copilot")
    try:
        payload = {
            "project_id": project_id,
            "user_id": user_id or "00000000-0000-4000-a000-000000000001",
            "message": "What is the safety risk?",
            "history": []
        }
        r = requests.post(f"{base_url}/api/chat/", json=payload)
        print(f"Safety Copilot: {r.status_code} - {r.text}")
    except Exception as e:
        print("Safety Copilot failed:", e)

    print("\n8. PDF Export")
    try:
        payload = {
            "project_id": project_id,
            "user_id": user_id or "00000000-0000-4000-a000-000000000001"
        }
        r = requests.post(f"{base_url}/api/reports/generate", json=payload)
        print(f"PDF Export: {r.status_code} - {r.text}")
    except Exception as e:
        print("PDF Export failed:", e)

if __name__ == "__main__":
    time.sleep(2) # wait for server
    run_tests()
