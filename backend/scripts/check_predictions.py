import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(url, key)

print("--- INCIDENT PREDICTIONS ---")
res = supabase.table("incident_predictions").select("*").execute()
print(f"Count: {len(res.data)}")
for r in res.data[:3]:
    print(r)

print("\n--- TRAINING RECOMMENDATIONS ---")
res = supabase.table("training_recommendations").select("*").execute()
print(f"Count: {len(res.data)}")
for r in res.data[:3]:
    print(r)
