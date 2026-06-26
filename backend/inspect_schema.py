import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SECRET_KEY")
supabase: Client = create_client(url, key)

print("--- Inspecting analysis_jobs table ---")
try:
    # Get one row or try to get column names by selecting a non-existent column or selecting everything
    res = supabase.table("analysis_jobs").select("*").limit(1).execute()
    print("Schema output:")
    if res.data:
        print("Columns:", list(res.data[0].keys()))
        print("Sample data:", res.data[0])
    else:
        print("No data found in analysis_jobs. Let's try inserting/inspecting schema in another way.")
        # We can run a query with postgres if we have RPC or we can just look at what fields exist on a dummy insert.
        # But wait, if we select "*" it returns all columns for empty table too? Actually supabase select("*") with limit(1) returns empty list if no rows.
        # Let's insert a dummy row or select from a Postgres view or use RPC if available.
        # Wait, does the project have a sql RPC or similar? Let's check check_rpc.py
except Exception as e:
    print(f"Error: {e}")
