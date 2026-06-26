import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

res = supabase.table("analysis_jobs").select("*").execute()
for r in res.data:
    print("Job ID:", r["id"], "status:", r["status"])
    if "result" in r and r["result"] and "agents" in r["result"]:
        agents = r["result"]["agents"]
        for name, info in agents.items():
            print(f"  {info['name']}: {info['status']}")
