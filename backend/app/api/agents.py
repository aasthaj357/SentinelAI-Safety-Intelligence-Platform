from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging
from groq import Groq
from app.core.config import settings
from app.core.supabase_client import supabase
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter()
client = Groq(api_key=settings.GROQ_API_KEY)
rag = get_rag_service()

# --- Shared Utilities ---
def call_groq_json(system_prompt: str, user_prompt: str) -> dict:
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1
        )
        content = response.choices[0].message.content
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        logger.error("Groq Agent Error: %s", e)
        return {"error": str(e)}

# --- Payloads ---
class WorkflowState(BaseModel):
    project_id: str
    user_id: str
    video_id: Optional[str] = None
    data: Dict[str, Any] = {}

# --- 1. Observation Agent ---
@router.post("/observation")
def observation_agent(state: WorkflowState):
    """Analyzes YOLOv8 and Roboflow detections to identify unsafe actions."""
    sys_prompt = "You are the Observation Agent. Output JSON ONLY: {'observations': [{'type', 'description', 'evidence_frame', 'timestamp'}], 'unsafe_actions': []}."
    usr_prompt = f"Analyze these detections: {json.dumps(state.data.get('detections', []))} and violations: {json.dumps(state.data.get('violations', []))}"
    result = call_groq_json(sys_prompt, usr_prompt)
    
    # Store RAG context
    rag.embed_and_store(state.project_id, "observation", state.video_id or "obs", json.dumps(result), user_id=state.user_id)
    
    return {"status": "success", "agent": "Observation", "output": result}

# --- 2. Communication Agent ---
@router.post("/communication")
def communication_agent(state: WorkflowState):
    """Analyzes Whisper transcripts for safety warnings."""
    sys_prompt = "You are the Communication Agent. Output JSON ONLY: {'warnings': [{'quote', 'severity', 'timestamp'}], 'ignored_commands': []}."
    usr_prompt = f"Analyze this transcript: {state.data.get('transcript', '')}"
    result = call_groq_json(sys_prompt, usr_prompt)
    
    rag.embed_and_store(state.project_id, "transcript", state.video_id or "trans", json.dumps(result), user_id=state.user_id)
    return {"status": "success", "agent": "Communication", "output": result}

# --- 3. SOP Compliance Agent ---
@router.post("/sop")
def sop_agent(state: WorkflowState):
    """Analyzes SOP rules and interprets requirements."""
    sys_prompt = "You are the SOP Agent. Output JSON ONLY: {'compliance_requirements': [{'rule', 'category', 'strictness'}], 'restricted_areas': []}."
    usr_prompt = f"Analyze this SOP text: {state.data.get('sop_text', '')}"
    result = call_groq_json(sys_prompt, usr_prompt)
    
    rag.embed_and_store(state.project_id, "sop", "sop_1", json.dumps(result), user_id=state.user_id)
    return {"status": "success", "agent": "SOP Compliance", "output": result}

# --- 4. Compliance Auditor Agent ---
@router.post("/auditor")
def auditor_agent(state: WorkflowState):
    """Compares Observations vs SOP Requirements."""
    sys_prompt = "You are the Compliance Auditor. Compare observed events vs SOP requirements. Output JSON ONLY: {'findings': [{'rule_violated', 'observation', 'evidence', 'explanation'}], 'total_violations': int}."
    usr_prompt = f"Observations: {json.dumps(state.data.get('observations', []))}\nSOP: {json.dumps(state.data.get('sop', []))}"
    result = call_groq_json(sys_prompt, usr_prompt)
    
    rag.embed_and_store(state.project_id, "violation", state.video_id or "auditor", json.dumps(result), user_id=state.user_id)
    return {"status": "success", "agent": "Compliance Auditor", "output": result}

# --- 5. Risk Assessment Agent ---
@router.post("/risk")
def risk_agent(state: WorkflowState):
    """Calculates risk severity and explanations."""
    sys_prompt = "You are the Risk Agent. Analyze findings and calculate risk. Output JSON ONLY: {'risk_score': 0-100, 'risk_level': 'Low/Medium/High/Critical', 'explanation': 'Detailed reasoning citing specific evidence and repeated patterns.'}."
    usr_prompt = f"Findings: {json.dumps(state.data.get('findings', []))}"
    result = call_groq_json(sys_prompt, usr_prompt)
    
    # Store in risk_assessments explicitly with explanation
    supabase.table("risk_assessments").insert({
        "project_id": state.project_id,
        "user_id": state.user_id,
        "score": result.get("risk_score", 0),
        "details": result
    }).execute()
    
    rag.embed_and_store(state.project_id, "risk", "risk_1", json.dumps(result), user_id=state.user_id)
    return {"status": "success", "agent": "Risk Assessment", "output": result}

# --- 6. Incident Prediction Agent ---
@router.post("/prediction")
def prediction_agent(state: WorkflowState):
    """Predicts future incidents based on patterns."""
    sys_prompt = "You are the Incident Prediction Agent. Output JSON ONLY: {'predictions': [{'predicted_incident', 'confidence_score': 0.0-1.0, 'explanation': 'Reasoning referencing historical behavior.'}]}."
    usr_prompt = f"Risk Data: {json.dumps(state.data.get('risk_data', {}))}\nFindings: {json.dumps(state.data.get('findings', []))}"
    result = call_groq_json(sys_prompt, usr_prompt)
    
    for pred in result.get("predictions", []):
        supabase.table("incident_predictions").insert({
            "project_id": state.project_id,
            "prediction_details": pred,
            "probability": pred.get("confidence_score", 0.0)
        }).execute()
        
    rag.embed_and_store(state.project_id, "prediction", "pred_1", json.dumps(result), user_id=state.user_id)
    return {"status": "success", "agent": "Incident Prediction", "output": result}

# --- 7. Training Recommendation Agent ---
@router.post("/training")
def training_agent(state: WorkflowState):
    """Generates prioritized training recommendations."""
    sys_prompt = "You are the Training Recommendation Agent. Output JSON ONLY: {'recommendations': [{'priority': 'Critical|High|Medium|Low', 'module_name', 'justification', 'corrective_actions': []}], 'human_readable_summary': 'Summary of plan'}."
    usr_prompt = f"Findings: {json.dumps(state.data.get('findings', []))}\nPredictions: {json.dumps(state.data.get('predictions', []))}"
    result = call_groq_json(sys_prompt, usr_prompt)
    
    summary = result.get("human_readable_summary", "")
    for rec in result.get("recommendations", []):
        supabase.table("training_recommendations").insert({
            "project_id": state.project_id,
            "user_id": state.user_id,
            "priority": rec.get("priority", "Medium"),
            "recommendation_json": rec,
            "human_readable_summary": summary,
            "explanation": rec.get("justification", "")
        }).execute()
        
    rag.embed_and_store(state.project_id, "training", "train_1", json.dumps(result), user_id=state.user_id)
    return {"status": "success", "agent": "Training Recommendation", "output": result}
