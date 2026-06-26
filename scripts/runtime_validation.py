"""Runtime validation script for Workplace Safety Intelligence Platform."""
import json
import os
import sys
import uuid
import urllib.request
import urllib.error

# Load backend .env
env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

# Load frontend .env
f_env_path = os.path.join(os.path.dirname(__file__), "..", "frontend", ".env")
if os.path.exists(f_env_path):
    with open(f_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SECRET = os.environ.get("SUPABASE_SECRET_KEY", "")
SUPABASE_ANON = os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY", "")
BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5173"

results = []

def record(category, test, status, detail=""):
    results.append({"category": category, "test": test, "status": status, "detail": detail})
    icon = "PASS" if status == "PASS" else ("WARN" if status == "WARN" else "FAIL")
    print(f"[{icon}] {category} / {test}: {detail}")

def http_json(method, url, data=None, headers=None):
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {"raw": e.read().decode() if e.fp else str(e)}
        return e.code, payload

def supabase_rest(method, path, data=None, use_service=True):
    key = SUPABASE_SECRET if use_service else SUPABASE_ANON
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    hdrs = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"message": raw}
        return e.code, payload

# --- Servers ---
for name, url in [("Backend", BACKEND), ("Frontend", FRONTEND)]:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            record("Servers", name, "PASS", f"HTTP {resp.status} at {url}")
    except Exception as e:
        record("Servers", name, "FAIL", str(e))

# --- Database tables ---
tables = [
    "projects", "video_uploads", "sop_documents", "violation_tracking",
    "video_transcripts", "risk_assessments", "incident_predictions",
    "generated_reports", "chatbot_conversations", "analysis_jobs",
    "knowledge_base", "training_recommendations",
]
for table in tables:
    code, data = supabase_rest("GET", f"{table}?select=id&limit=1")
    if code == 200:
        record("Database", f"Table {table}", "PASS", "Queryable")
    else:
        msg = data.get("message", str(data)) if isinstance(data, dict) else str(data)
        record("Database", f"Table {table}", "FAIL", msg)

# --- Auth (Supabase) ---
test_email = f"validation_{uuid.uuid4().hex[:8]}@test.local"
test_password = "ValidationTest123!"
code, signup = http_json(
    "POST",
    f"{SUPABASE_URL}/auth/v1/signup",
    {"email": test_email, "password": test_password},
    headers={"apikey": SUPABASE_ANON, "Authorization": f"Bearer {SUPABASE_ANON}"},
)
if code in (200, 201):
    record("Auth", "Registration", "PASS", f"Created {test_email}")
else:
    record("Auth", "Registration", "FAIL", str(signup))

code, login = http_json(
    "POST",
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    {"email": test_email, "password": test_password},
    headers={"apikey": SUPABASE_ANON, "Authorization": f"Bearer {SUPABASE_ANON}"},
)
access_token = None
user_id = None
if code == 200 and login.get("access_token"):
    access_token = login["access_token"]
    user_id = login.get("user", {}).get("id")
    record("Auth", "Login", "PASS", f"User id {user_id}")
else:
    record("Auth", "Login", "FAIL", str(login))

if access_token:
    code, logout = http_json(
        "POST",
        f"{SUPABASE_URL}/auth/v1/logout",
        {},
        headers={"apikey": SUPABASE_ANON, "Authorization": f"Bearer {access_token}"},
    )
    record("Auth", "Logout", "PASS" if code in (200, 204) else "WARN", f"HTTP {code}")

# --- Project create (anon key, simulates frontend) ---
if user_id:
    project_name = f"Project-{user_id}"
    code, proj = supabase_rest("POST", "projects", {"name": project_name}, use_service=False)
    if code in (200, 201) and isinstance(proj, list) and proj:
        project_id = proj[0]["id"]
        record("Database", "Project insert (anon)", "PASS" if code in (200, 201) else "FAIL", f"id={project_id}")
    else:
        # Try service role
        code, proj = supabase_rest("POST", "projects", {"name": project_name}, use_service=True)
        if code in (200, 201) and isinstance(proj, list) and proj:
            project_id = proj[0]["id"]
            record("Database", "Project insert (service)", "PASS", f"id={project_id} (RLS may block anon)")
        else:
            project_id = None
            record("Database", "Project insert", "FAIL", str(proj))
else:
    project_id = None

# --- Demo load with valid UUID ---
demo_project_id = project_id or str(uuid.uuid4())
code, demo = http_json("POST", f"{BACKEND}/api/demo/load", {"project_id": demo_project_id})
if code == 200:
    record("Demo Data", "Load", "PASS", demo.get("message", "OK"))
else:
    record("Demo Data", "Load", "FAIL", str(demo))

# Verify demo data in DB
if code == 200:
    for table, col in [
        ("video_uploads", "project_id"),
        ("risk_assessments", "project_id"),
        ("incident_predictions", "project_id"),
        ("training_recommendations", "project_id"),
        ("knowledge_base", "project_id"),
    ]:
        c, rows = supabase_rest("GET", f"{table}?select=id&{col}=eq.{demo_project_id}&limit=5")
        count = len(rows) if isinstance(rows, list) else 0
        record("Demo Data", f"{table} rows", "PASS" if count > 0 else "FAIL", f"{count} rows")

# --- Demo load with demo-user-123 (frontend demo login) ---
code, demo_bad = http_json("POST", f"{BACKEND}/api/demo/load", {"project_id": "demo-user-123"})
record(
    "Demo Data",
    "Load with demo-user-123",
    "FAIL" if code != 200 else "PASS",
    "Expected FAIL: not a valid UUID" if code != 200 else "Unexpected success",
)

# --- Chat ---
code, chat = http_json(
    "POST",
    f"{BACKEND}/api/chat/",
    {"project_id": demo_project_id, "message": "What risk score was calculated for Sector C?", "history": []},
)
if code == 200 and chat.get("reply"):
    has_sources = bool(chat.get("sources"))
    static_phrases = ["I am currently unavailable", "static", "canned"]
    is_static = any(p.lower() in chat["reply"].lower() for p in static_phrases)
    record(
        "Chatbot",
        "POST /api/chat",
        "PASS" if not is_static else "WARN",
        f"Reply length={len(chat['reply'])}, sources={len(chat.get('sources', []))}, rag={'yes' if has_sources else 'no'}",
    )
    if chat.get("sources"):
        record("Chatbot", "RAG sources returned", "PASS", f"{len(chat['sources'])} sources")
    else:
        record("Chatbot", "RAG sources returned", "WARN", "No sources — match_knowledge may return empty")
else:
    record("Chatbot", "POST /api/chat", "FAIL", str(chat))

# --- Dashboard backend API ---
code, dash = http_json("GET", f"{BACKEND}/api/dashboard/stats")
if code == 200:
    hardcoded = dash.get("ppe_compliance_percent") == 100.0 and dash.get("total_violations") == 0
    record(
        "Dashboard",
        "Backend /api/dashboard/stats",
        "WARN" if hardcoded else "PASS",
        "Returns hardcoded placeholder values (frontend uses Supabase directly)" if hardcoded else "Dynamic",
    )

# --- Demo reset ---
code, reset = http_json("POST", f"{BACKEND}/api/demo/reset", {"project_id": demo_project_id})
record("Demo Data", "Reset", "PASS" if code == 200 else "FAIL", reset.get("message", str(reset)) if isinstance(reset, dict) else str(reset))

# --- Storage buckets (list via service) ---
for bucket in ["videos", "sop-documents", "annotated-videos", "reports"]:
    url = f"{SUPABASE_URL}/storage/v1/bucket/{bucket}"
    req = urllib.request.Request(url, headers={"apikey": SUPABASE_SECRET, "Authorization": f"Bearer {SUPABASE_SECRET}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            record("Storage", f"Bucket {bucket}", "PASS", "Exists")
    except urllib.error.HTTPError as e:
        record("Storage", f"Bucket {bucket}", "FAIL", f"HTTP {e.code}")

# Summary
print("\n=== SUMMARY ===")
passed = sum(1 for r in results if r["status"] == "PASS")
warned = sum(1 for r in results if r["status"] == "WARN")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"PASS: {passed}  WARN: {warned}  FAIL: {failed}  TOTAL: {len(results)}")

out = os.path.join(os.path.dirname(__file__), "..", "RUNTIME_VALIDATION_REPORT.json")
with open(out, "w") as f:
    json.dump({"frontend": FRONTEND, "backend": BACKEND, "results": results, "summary": {"pass": passed, "warn": warned, "fail": failed}}, f, indent=2)
print(f"Report written to {out}")
sys.exit(1 if failed > 0 else 0)
