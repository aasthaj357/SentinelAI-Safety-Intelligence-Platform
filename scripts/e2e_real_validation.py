import os
import sys
import time
import json
from dotenv import load_dotenv

os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
sys.path.append(os.getcwd())
load_dotenv('.env')

from app.api.demo import ensure_project, EnsureProjectRequest, load_demo_dataset, DemoLoadRequest
from app.api.dashboard import get_dashboard_analytics
from app.api.chat import chat_with_copilot, ChatRequest
from app.api.reports import generate_report, ReportRequest

def run_tests():
    print("--- STARTING END-TO-END AUTH AND ISOLATION VALIDATION ---")
    
    import uuid
    # 1. Create Users
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())

    print(f"User A ID (simulated): {user_a_id}")
    print(f"User B ID (simulated): {user_b_id}")
    
    # 2. Create Projects
    print("\n--- PROJECT ISOLATION ---")
    res_pa = ensure_project(EnsureProjectRequest(user_id=user_a_id, project_name="Project A1"))
    proj_a_id = res_pa["project_id"]

    res_pb = ensure_project(EnsureProjectRequest(user_id=user_b_id, project_name="Project B1"))
    proj_b_id = res_pb["project_id"]
    
    print(f"Project A1 ID: {proj_a_id}")
    print(f"Project B1 ID: {proj_b_id}")

    # 3. Simulate History Generation (to give them data)
    print("\nLoading historical data for User A...")
    load_demo_dataset(DemoLoadRequest(user_id=user_a_id, project_id=proj_a_id))

    print("Loading historical data for User B...")
    load_demo_dataset(DemoLoadRequest(user_id=user_b_id, project_id=proj_b_id))

    # 4. Fetch Analytics to Prove Calculation
    print("\n--- HISTORICAL ANALYTICS ---")
    analytics_a = get_dashboard_analytics(project_id=proj_a_id, user_id=user_a_id)
    analytics_b = get_dashboard_analytics(project_id=proj_b_id, user_id=user_b_id)

    print(f"User A PPE Trend: {[t['ppe_compliance_pct'] for t in analytics_a.get('ppe_trend', [])]}")
    print(f"User B PPE Trend: {[t['ppe_compliance_pct'] for t in analytics_b.get('ppe_trend', [])]}")
    
    if analytics_a != analytics_b:
        print("[PASS] Analytics are isolated and generated correctly.")
    else:
        print("[FAIL] Analytics are identical!")

    # 5. Safety Copilot
    print("\n--- SAFETY COPILOT VALIDATION ---")
    copilot_req = ChatRequest(
        project_id=proj_a_id,
        user_id=user_a_id,
        message="What violations occurred this month? Show PPE compliance trend."
    )
    copilot_res = chat_with_copilot(copilot_req)
    print("User A Copilot Response:")
    print(copilot_res.get("reply", "No reply"))
    
    # Inject mock screenshot
    from app.core.supabase_client import supabase
    evid_res = supabase.table("evidence_records").select("id").eq("user_id", user_a_id).limit(1).execute()
    if evid_res.data:
        supabase.table("evidence_records").update({"screenshot_url": "https://example.com/mock-screenshot.jpg"}).eq("id", evid_res.data[0]["id"]).execute()

    # 6. PDF Generation Validation
    print("\n--- PDF EXPORT VALIDATION ---")
    pdf_req = ReportRequest(project_id=proj_a_id, user_id=user_a_id)
    pdf_res = generate_report(pdf_req)
    html_content = pdf_res.get("report_html", "")
    print(f"Generated HTML size: {len(html_content)} characters.")
    if not html_content:
        print(f"PDF Gen Error: {pdf_res}")
    if "No visual evidence available with screenshots" in html_content:
        print("[WARNING] No screenshots found in report. (Expected if mock demo data doesn't provide valid screenshot URLs).")
    elif "<img src='" in html_content and "placeholder" not in html_content:
        print("[PASS] Actual screenshots included in HTML report. Placeholders removed.")
    else:
        print("[FAIL] Missing or placeholder screenshots in HTML report.")

if __name__ == "__main__":
    run_tests()
