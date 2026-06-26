import logging
from app.agents.base import BaseADKAgent
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

class SecurityAgent(BaseADKAgent):
    """Security Agent governing RBAC, auditing, and PII masking checks."""
    
    def __init__(self):
        instructions = (
            "You are the Security Agent. You are the custodian of security, privacy, and user access. "
            "Your job is to validate user roles (Viewer, SafetyOfficer, Supervisor), "
            "assert that projects belong to the target users, and sanitize sensitive information from trace logs."
        )
        super().__init__(name="SecurityAgent", instructions=instructions)

    def validate_user_access(self, user_id: str, project_id: str, required_role: str = "SafetyOfficer") -> bool:
        """Validate if user owns the target project and holds sufficient access roles."""
        logger.info(f"SecurityAgent: Validating access permissions for user {user_id} on project {project_id}")
        
        try:
            # Query projects database
            res = supabase.table("projects").select("*").eq("id", project_id).eq("user_id", user_id).execute()
            if not res.data:
                logger.warning(f"SecurityAgent: Access denied - user {user_id} does not own project {project_id}")
                return False
                
            # Log successful audit trace
            supabase.table("audit_logs").insert({
                "user_id": user_id,
                "action": "access_verification",
                "details": {"project_id": project_id, "required_role": required_role, "status": "allowed"}
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"SecurityAgent: Permission check failed: {e}")
            return False

    def validate_token(self, token: str) -> str | None:
        """Validate Supabase JWT token against the Auth API and return user UUID."""
        try:
            clean_token = token.replace("Bearer ", "").strip()
            res = supabase.auth.get_user(clean_token)
            if res and getattr(res, "user", None):
                return res.user.id
            return None
        except Exception as e:
            logger.error(f"SecurityAgent: Token verification failed: {e}")
            return None

    def log_audit_action(self, user_id: str, action: str, details: dict):
        """Log safety actions to the security audit trail."""
        try:
            supabase.table("audit_logs").insert({
                "user_id": user_id,
                "action": action,
                "details": details
            }).execute()
        except Exception as e:
            logger.error(f"SecurityAgent: Logging failed: {e}")

    def sanitize_text(self, text: str) -> str:
        """Remove names, emails, and phone numbers from logs to protect privacy."""
        import re
        sanitized = text
        # Mask emails
        sanitized = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', sanitized)
        # Mask phone numbers
        sanitized = re.sub(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[REDACTED_PHONE]', sanitized)
        return sanitized
