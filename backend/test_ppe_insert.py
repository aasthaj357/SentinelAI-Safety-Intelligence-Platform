import os
import sys
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

try:
    # Get a valid worker and frame to avoid FK violations
    w = supabase.table("workers").select("id").limit(1).execute()
    f = supabase.table("frames").select("id").limit(1).execute()
    
    wid = w.data[0]["id"] if w.data else None
    fid = f.data[0]["id"] if f.data else None
    
    print(f"Using worker_id: {wid}, frame_id: {fid}")
    
    res = supabase.table("ppe_associations").insert({
        "worker_id": wid,
        "frame_id": fid,
        "timestamp": 1.0,
        "helmet": True,
        "gloves": True,
        "goggles": True,
        "mask": True,
        "vest": True,
        "shoes": True
    }).execute()
    
    print("Insert success:", res.data)
except Exception as e:
    print("Insert failed:", e)
