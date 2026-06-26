import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

with open("dump.txt", "w", encoding="utf-8") as out:
    def write(msg):
        out.write(str(msg) + "\n")
        print(msg)

    write("--- PROJECTS ---")
    res = supabase.table("projects").select("*").execute()
    for r in res.data:
        write(r)

    write("\n--- VIDEO UPLOADS ---")
    res = supabase.table("video_uploads").select("*").execute()
    for r in res.data:
        write(r)

    write("\n--- ANALYSIS JOBS ---")
    res = supabase.table("analysis_jobs").select("*").execute()
    for r in res.data:
        write(f"ID: {r['id']} | type: {r['job_type']} | status: {r['status']}")
        if "result" in r and r["result"] and "agents" in r["result"]:
            agents = r["result"]["agents"]
            for name, info in agents.items():
                write(f"  {info['name']}: {info['status']}")
        else:
            write("  No result/agents in job record.")

    write("\n--- RISK ASSESSMENTS ---")
    res = supabase.table("risk_assessments").select("*").execute()
    for r in res.data:
        write(f"ID: {r['id']} | score: {r['score']}")

    try:
        write("\n--- APPROVAL REQUESTS ---")
        res = supabase.table("approval_requests").select("*").execute()
        for r in res.data:
            write(r)
    except Exception as e:
        write(f"Error querying approval_requests: {e}")
