import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

tables = ["analysis_jobs", "violation_tracking", "evidence_records", "incident_predictions"]

for table in tables:
    try:
        res = supabase.table(table).select("project_id").limit(1).execute()
        print(f"Table {table}: project_id column exists!")
    except Exception as e:
        print(f"Table {table}: error when selecting project_id: {e}")
