import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

rpcs = ["exec_sql", "run_sql", "execute_sql", "query_sql"]

for rpc in rpcs:
    try:
        res = supabase.rpc(rpc, {"sql": "SELECT 1"}).execute()
        print(f"RPC {rpc} exists! Result:", res.data)
        break
    except Exception as e:
        print(f"RPC {rpc} error: {e}")
else:
    # Try calling without parameters or check if we can run psycopg2 directly if we have the password
    print("No standard SQL RPC found.")
