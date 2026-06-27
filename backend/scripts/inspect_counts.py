import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
if not url or not key:
    print("Missing Supabase config in env.")
    sys.exit(1)

supabase = create_client(url, key)

tables = [
    "risk_assessments",
    "incident_predictions",
    "training_recommendations",
    "evidence_records",
    "violation_tracking",
    "workers",
    "ppe_associations",
    "knowledge_base"
]

print("=== TABLE COUNTS ===")
for t in tables:
    try:
        res = supabase.table(t).select("id", count="exact").limit(1).execute()
        count = res.count if hasattr(res, 'count') else (len(res.data) if res.data else 0)
        print(f"{t}: {count} rows")
    except Exception as e:
        # Some tables might not have an 'id' column or might need a different count approach
        try:
            res = supabase.table(t).select("*", count="exact").limit(1).execute()
            count = res.count if hasattr(res, 'count') else (len(res.data) if res.data else 0)
            print(f"{t}: {count} rows")
        except Exception as e2:
            print(f"{t} error: {e2}")
