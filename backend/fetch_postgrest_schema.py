import os
import httpx
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

print("Fetching OpenAPI schema from PostgREST...")
try:
    resp = httpx.get(f"{url}/rest/v1/", headers=headers, timeout=10)
    print("Status code:", resp.status_code)
    if resp.status_code == 200:
        schema = resp.json()
        print("Schema loaded successfully!")
        
        # Look for RPC paths (which start with /rpc/)
        rpc_paths = [p for p in schema.get("paths", {}).keys() if p.startswith("/rpc/")]
        print("Exposed RPC functions:")
        for path in rpc_paths:
            print("  ", path)
            
        # Let's save the schemas to a local file for inspection
        with open("postgrest_schema.json", "w") as f:
            import json
            json.dump(schema, f, indent=2)
        print("Exposed tables:")
        tables = [p for p in schema.get("paths", {}).keys() if not p.startswith("/rpc/")]
        for table in tables:
            print("  ", table)
    else:
        print("Error content:", resp.text)
except Exception as e:
    print("Error:", e)
