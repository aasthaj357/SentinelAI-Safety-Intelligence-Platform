import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

storage_path = "f0cd8aaf-a17e-4dd9-953b-a5c1a014e8c7/c8dbab42-0c2b-45ac-b6ca-3a4fd4fcad7c-Workplace_safety_inspection_video_202606210151.mp4"

try:
    print("Attempting to download video...")
    res = supabase.storage.from_("videos").download(storage_path)
    print("Download success, length:", len(res))
except Exception as e:
    print("Download failed with exception:", e)
