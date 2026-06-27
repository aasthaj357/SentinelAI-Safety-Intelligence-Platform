import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from app.api import dashboard, upload, reports, analysis, insights, agents, chat, demo, evidence, approvals, audit
from app.mcp import sop_server, incident_server, evidence_server, reporting_server, memory_server

app = FastAPI(title="Workplace Safety Intelligence Platform API")

# NOTE: allow_origins=["*"] and allow_credentials=True is an invalid CORS combination.
# Browsers reject requests when both are set. Use allow_credentials=False with wildcard
# origin, or specify explicit origins with credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://sentinel-ai-safety-intelligence-pla.vercel.app",
        "https://sentinel-ai-safety-intelligence-platform-7lr96uptk.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=False,  # Fixed: wildcard origin requires credentials=False
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse
from app.agents.security_agent import SecurityAgent

security = SecurityAgent()

# Routes that REQUIRE a valid Supabase JWT (they invoke LLM agents / sensitive ops)
_JWT_REQUIRED_PREFIXES = ("/api/agents", "/api/chat")

# Routes that are fully public / use service-role internally (upload, pipeline, UI data)
_PUBLIC_PREFIXES = (
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/api/demo",
    "/api/upload",
    "/api/analysis",
    "/api/dashboard",
    "/api/reports",
    "/api/evidence",
    "/api/insights",
    "/api/approvals",
    "/api/audit",
    "/api/mcp",
)


@app.middleware("http")
async def security_audit_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path

    # Always skip CORS pre-flight and public routes
    for prefix in _PUBLIC_PREFIXES:
        if path == prefix or path.startswith(prefix):
            # If a token IS present, validate and log it (best-effort)
            token = request.headers.get("Authorization")
            if token:
                try:
                    uid = security.validate_token(token)
                    if uid:
                        security.log_audit_action(uid, request.method, {"path": path})
                        request.state.user_id = uid
                except Exception:
                    pass  # never block public routes on token errors
            return await call_next(request)

    # JWT-enforced routes (agents, chat)
    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: Missing authorization header"},
        )

    user_id = security.validate_token(token)
    if not user_id:
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden: Invalid or expired token"},
        )

    security.log_audit_action(user_id, request.method, {"path": path})
    request.state.user_id = user_id
    return await call_next(request)


app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(insights.router, prefix="/api", tags=["insights"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["evidence"])
app.include_router(demo.router, prefix="/api/demo", tags=["demo"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])

# Register SSE MCP Server Routes
app.include_router(sop_server.router, prefix="/api")
app.include_router(incident_server.router, prefix="/api")
app.include_router(evidence_server.router, prefix="/api")
app.include_router(reporting_server.router, prefix="/api")
app.include_router(memory_server.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to Workplace Safety Intelligence Platform API"}

@app.get("/health")
def health_check():
    """Quick liveness check — visit http://localhost:8000/health to confirm backend is running."""
    return {"status": "ok"}
