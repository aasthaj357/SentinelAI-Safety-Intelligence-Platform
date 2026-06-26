import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

project_id = "69eb99ee-8c0e-496c-8e4e-be93fa0061bf"
user_id = "4201f1d0-237d-4fd5-a82a-55947ab106eb"

try:
    # Query violation_tracking joining video_uploads and filtering by video_uploads' project_id
    res = supabase.table("violation_tracking")\
        .select("*, video_uploads!inner(project_id, user_id)")\
        .eq("video_uploads.project_id", project_id)\
        .eq("video_uploads.user_id", user_id)\
        .execute()
    print("Join success! Number of rows:", len(res.data))
    if res.data:
        print("Row keys:", list(res.data[0].keys()))
except Exception as e:
    print("Join error:", e)
