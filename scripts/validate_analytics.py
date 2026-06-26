import os
import sys
import uuid

# Change working directory to backend so config picks up .env
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv('.env')

from app.core.supabase_client import supabase
from app.services.analytics_service import get_analytics_service

def validate():
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    project_a = str(uuid.uuid4())
    project_b = str(uuid.uuid4())
    
    print(f"User A: {user_a}")
    print(f"User B: {user_b}")

    # The demo load endpoint will create projects and historical records
    # We will simulate the demo load logic here to avoid spinning up the server
    import app.api.demo as demo_api
    from pydantic import BaseModel
    class Req(BaseModel):
        project_id: str
        user_id: str

    print("Generating history for User A...")
    demo_api.load_demo_dataset(Req(project_id=project_a, user_id=user_a))
    
    print("Generating history for User B...")
    demo_api.load_demo_dataset(Req(project_id=project_b, user_id=user_b))
    
    analytics = get_analytics_service()
    
    print("\n--- User A Analytics ---")
    monthly_a = analytics.get_violation_trend_by_type(user_a, project_a, 90)
    print("Monthly Violations:", monthly_a)
    
    risk_a = analytics.get_risk_score_trend(user_a, project_a, 90, "month")
    print("Risk Trend:", risk_a)
    
    ppe_a = analytics.get_ppe_compliance_trend(user_a, project_a, 90, "month")
    print("PPE Trend:", ppe_a)
    
    print("\n--- User B Analytics ---")
    monthly_b = analytics.get_violation_trend_by_type(user_b, project_b, 90)
    print("Monthly Violations:", monthly_b)
    
    # Verify isolation
    viol_a_count = supabase.table("violation_tracking").select("*", count="exact").eq("user_id", user_a).execute().count
    viol_b_count = supabase.table("violation_tracking").select("*", count="exact").eq("user_id", user_b).execute().count
    
    print(f"\nUser A total violations in DB: {viol_a_count}")
    print(f"User B total violations in DB: {viol_b_count}")
    
    if monthly_a != monthly_b:
        print("\n[SUCCESS] Analytics are distinct and isolated.")
    else:
        print("\n[WARNING] Analytics are identical (random chance or isolation failure).")
        
    # Cleanup
    demo_api.reset_all_user_data(demo_api.ResetUserRequest(user_id=user_a))
    demo_api.reset_all_user_data(demo_api.ResetUserRequest(user_id=user_b))
    print("\nCleanup complete.")

if __name__ == "__main__":
    validate()
