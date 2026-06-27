import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SECRET_KEY")
supabase: Client = create_client(url, key)

print("--- BUCKETS ---")
try:
    buckets = supabase.storage.list_buckets()
    bucket_names = [b.name for b in buckets]
    print("Existing Buckets:", bucket_names)
    
    required_buckets = ['videos', 'sop-documents', 'annotated-videos', 'reports']
    for rb in required_buckets:
        if rb not in bucket_names:
            print(f"Creating bucket: {rb}")
            supabase.storage.create_bucket(rb, options={"public": True})
except Exception as e:
    print(f"Error checking buckets: {e}")

print("\n--- DB COUNTS ---")
try:
    projects = supabase.table("projects").select("id, name").execute()
    print("Projects:", projects.data)
    
    for p in projects.data:
        pid = p['id']
        name = p['name']
        print(f"\nProject: {name} ({pid})")
        
        # risk_assessments
        risks = supabase.table("risk_assessments").select("*", count="exact").eq("project_id", pid).execute()
        print(f"Risk Assessments: {risks.count}")
        
        # knowledge_base
        kb = supabase.table("knowledge_base").select("*", count="exact").eq("project_id", pid).execute()
        print(f"Knowledge Base: {kb.count}")
except Exception as e:
    print(f"Error checking db: {e}")
