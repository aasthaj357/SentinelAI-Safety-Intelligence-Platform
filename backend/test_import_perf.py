import time
import sys

modules = [
    "app.core.supabase_client",
    "app.services.yolov8_service",
    "app.services.roboflow_service",
    "app.services.sop_service",
    "app.services.rag_service",
    "app.api.dashboard",
    "app.api.upload",
    "app.api.reports",
    "app.api.analysis",
    "app.api.insights",
    "app.api.agents",
    "app.api.chat",
    "app.api.demo",
    "app.api.evidence",
    "app.api.approvals",
    "app.api.audit",
    "app.mcp.sop_server",
    "app.mcp.incident_server",
    "app.mcp.evidence_server",
    "app.mcp.reporting_server",
    "app.mcp.memory_server"
]

print("Starting import timing...", flush=True)
for mod in modules:
    t0 = time.time()
    try:
        __import__(mod)
        dt = time.time() - t0
        print(f"Import {mod}: {dt:.3f}s", flush=True)
    except Exception as e:
        print(f"Failed to import {mod}: {e}", flush=True)

print("Done timing imports.", flush=True)
