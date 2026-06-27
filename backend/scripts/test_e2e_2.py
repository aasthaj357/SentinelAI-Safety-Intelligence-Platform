import os
import time
import requests
from supabase import create_client

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SECRET_KEY"]
supabase = create_client(url, key)

print("1. Testing Registration/Login...")
email = f"johndoe{int(time.time())}@gmail.com"
password = "testpassword123!"

try:
    res = supabase.auth.sign_up({"email": email, "password": password})
    print(f"Registered: {res.user.email}")
    time.sleep(2)
    user = res.user
except Exception as e:
    print("Signup error:", e)
    user = type('obj', (object,), {'id': '11111111-1111-4111-a111-111111111111'})()

print("3. Testing Demo Data Loading (Simulated via backend/DB)...")
project_name = f"Project-{user.id}"
project_res = supabase.table('projects').insert({'name': project_name}).execute()
project_id = project_res.data[0]['id']
print(f"Created project: {project_id}")

video_res = supabase.table('video_uploads').insert({
    'project_id': project_id,
    'title': 'Test Video',
    'file_url': 'http://example.com/vid.mp4'
}).execute()
video_id = video_res.data[0]['id']
print(f"Created video upload: {video_id}")

print("6. Testing Analysis job creation...")
job_res = supabase.table('analysis_jobs').insert({
    'target_id': video_id,
    'job_type': 'trigger_pipeline',
    'status': 'queued'
}).execute()
print(f"Created analysis job: {job_res.data[0]['id']}")

print("7. Testing Safety Copilot (Backend)...")
try:
    chat_payload = {
        "project_id": project_id,
        "message": "What is the safety risk?",
        "history": []
    }
    chat_res = requests.post("http://127.0.0.1:8000/api/chat/", json=chat_payload)
    print("Chat response:", chat_res.json())
except Exception as e:
    print("Chat test failed:", e)

