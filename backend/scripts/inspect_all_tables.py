import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

tables = ["projects", "video_uploads", "sop_documents", "video_transcripts", "risk_assessments", "violation_tracking", "incident_predictions", "generated_reports", "chatbot_conversations", "analysis_jobs", "frames", "workers", "detections", "ppe_associations", "observations"]

for table in tables:
    try:
        res = supabase.table(table).select("*").limit(1).execute()
        if res.data:
            print(f"Table {table}: {list(res.data[0].keys())}")
        else:
            # Let's try inserting a dummy row or just print empty
            print(f"Table {table}: No records to inspect keys.")
    except Exception as e:
        print(f"Table {table} error: {e}")
