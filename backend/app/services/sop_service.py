import json
import logging
import os
import tempfile
import uuid
import pymupdf
from groq import Groq
from app.core.config import settings
from app.core.supabase_client import supabase
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)
client = Groq(api_key=settings.GROQ_API_KEY)

# PPE canonical names for matching
PPE_CANONICAL = {
    "helmet": ["helmet", "hard hat", "hardhat", "head protection"],
    "gloves": ["gloves", "hand protection", "safety gloves"],
    "goggles": ["goggles", "safety glasses", "eye protection", "face shield"],
    "vest": ["vest", "hi-vis", "high visibility", "safety vest", "reflective vest"],
    "shoes": ["safety shoes", "safety boots", "steel toe", "foot protection", "boots"],
    "mask": ["mask", "respirator", "face mask", "dust mask"],
}


def normalize_ppe_list(raw_list: list) -> list:
    """Normalize PPE names to canonical lowercase keys."""
    normalized = []
    for item in raw_list:
        item_lower = str(item).lower()
        matched = False
        for canon, synonyms in PPE_CANONICAL.items():
            if any(syn in item_lower for syn in synonyms):
                if canon not in normalized:
                    normalized.append(canon)
                matched = True
                break
        if not matched and item_lower.strip():
            normalized.append(item_lower.strip())
    return normalized


class SopService:
    def parse_sop(self, pdf_path: str) -> dict:
        """
        Extract text from SOP PDF and use Groq to structure it into a rich JSON schema.
        Schema includes: ppe_requirements, required_procedures, required_sequence,
        forbidden_actions, hazards, recommended_actions, severity_levels, equipment_rules.
        """
        try:
            doc = pymupdf.open(pdf_path)
            raw_text = ""
            for page in doc:
                raw_text += page.get_text() + "\n"
        except Exception as e:
            logger.error("Error reading PDF for structured parsing: %s", e)
            return {"error": str(e)}

        prompt = f"""
You are a safety rules extractor. Extract ALL safety rules from this SOP document.

Return ONLY valid JSON with this exact structure:
{{
  "ppe_requirements": ["helmet", "gloves", "goggles", "safety shoes"],
  "required_procedures": ["list of mandatory steps/actions from the SOP"],
  "required_sequence": ["step 1", "step 2", ...],
  "forbidden_actions": ["list of explicitly prohibited actions"],
  "hazards": ["list of named hazards in the document"],
  "recommended_actions": ["list of recommended but not mandatory actions"],
  "severity_levels": {{"helmet": "critical", "gloves": "high", "goggles": "high"}},
  "equipment_rules": ["list of equipment handling rules"],
  "general_safety": ["list of general safety rules"],
  "sop_sections": ["list of section titles found in the document"]
}}

Rules:
- ppe_requirements MUST list every PPE item explicitly required (use standard names: helmet, gloves, goggles, vest, safety shoes, mask)
- forbidden_actions MUST list every prohibited action mentioned
- hazards MUST list every named hazard or risk
- If a section is missing from the SOP, use an empty list []
- Output ONLY raw valid JSON, no markdown, no explanation

Document text:
{raw_text[:15000]}
"""

        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a safety rules extractor. Output ONLY raw valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0
            )

            content = response.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            structured_rules = json.loads(content)

            # Normalize PPE list to canonical names
            if "ppe_requirements" in structured_rules:
                structured_rules["ppe_requirements"] = normalize_ppe_list(
                    structured_rules["ppe_requirements"]
                )

            return {
                "raw_text": raw_text,
                "structured_rules": structured_rules
            }
        except Exception as e:
            logger.error("Error structuring SOP with Groq: %s", e)
            # Fallback: try basic keyword extraction from raw text
            fallback = _fallback_ppe_extraction(raw_text)
            return {"raw_text": raw_text, "structured_rules": fallback}

    def extract_text(self, pdf_path: str) -> str:
        try:
            doc = pymupdf.open(pdf_path)
            raw_text = ""
            for page in doc:
                raw_text += page.get_text() + "\n"
            return raw_text
        except Exception as e:
            logger.error("Error extracting PDF text from %s: %s", pdf_path, e)
            return ""

    def fetch_latest_sop_document(self, project_id: str) -> dict | None:
        result = supabase.table("sop_documents").select(
            "id, title, file_url, sop_text, sop_structure"
        ).eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
        if getattr(result, 'data', None):
            return result.data[0]
        return None

    def find_sop_section_for_violation(self, violation_label: str, project_id: str) -> dict:
        sop_doc = self.fetch_latest_sop_document(project_id)
        if not sop_doc:
            return {
                "section": "Unknown SOP",
                "excerpt": "No SOP document found for this project."
            }

        text = sop_doc.get("sop_text", "") or ""
        structure = sop_doc.get("sop_structure") or {}
        violation_text = violation_label.lower().replace("_", " ").replace("-", " ")
        keywords = [w for w in violation_text.split() if w and w not in ("no", "missing", "without", "detected")]

        # 1. Match structured SOP sections by keywords
        section_matches = []
        for section_key, entries in structure.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, str):
                    continue
                lower_entry = entry.lower()
                hit_count = sum(1 for kw in keywords if kw in lower_entry)
                if hit_count > 0:
                    section_matches.append((hit_count, section_key, entry))

        section_matches.sort(key=lambda x: (x[0], 0 if "general" in x[1].lower() else 1), reverse=True)

        if section_matches:
            _, best_key, best_entry = section_matches[0]
            return {
                "section": best_key.replace("_", " ").title(),
                "excerpt": best_entry.strip()
            }

        # 2. Fallback: search raw text
        if text:
            lower_text = text.lower()
            best_idx = -1
            for keyword in keywords:
                idx = lower_text.find(keyword)
                if idx >= 0 and (best_idx < 0 or idx < best_idx):
                    best_idx = idx
            if best_idx >= 0:
                start = max(0, best_idx - 150)
                excerpt = text[start:best_idx + 200].strip().replace("\n", " ")
                section_name = "Matched SOP Excerpt"
                preceding = text[max(0, best_idx - 300):best_idx]
                for line in reversed(preceding.split("\n")):
                    line = line.strip()
                    if 5 < len(line) < 80 and (line.isupper() or line.istitle()):
                        section_name = line.title()
                        break
                return {
                    "section": section_name,
                    "excerpt": excerpt
                }

        return {
            "section": "Unknown SOP",
            "excerpt": text.strip().replace("\n", " ")[:250] if text else "No relevant SOP excerpt found."
        }

    def _download_to_temp(self, storage_path: str) -> str | None:
        try:
            content = supabase.storage.from_("sop-documents").download(storage_path)
            if content is None:
                return None

            tmp_dir = tempfile.mkdtemp(prefix="sop_download_")
            local_path = os.path.join(tmp_dir, os.path.basename(storage_path))
            with open(local_path, "wb") as f:
                if isinstance(content, (bytes, bytearray)):
                    f.write(content)
                elif hasattr(content, "read"):
                    f.write(content.read())
                else:
                    f.write(bytes(content))
            return local_path
        except Exception as e:
            logger.warning("Unable to download SOP from storage for background processing: %s", e)
            return None

    def process_sop_upload(self, project_id: str, storage_path: str, tmp_path: str | None, document_id: str, title: str, user_id: str = None):
        logger.info("Starting background SOP processing for document %s", document_id)
        file_path = tmp_path
        if not file_path or not os.path.exists(file_path):
            file_path = self._download_to_temp(storage_path)

        if not file_path:
            logger.warning("No SOP file available for processing for document %s", document_id)
            return

        raw_text = self.extract_text(file_path)
        if not raw_text.strip():
            logger.warning("SOP file %s parsed to empty text for document %s", file_path, document_id)
            return

        structured_result = self.parse_sop(file_path)
        raw_text = structured_result.get("raw_text", raw_text)
        structured_rules = structured_result.get("structured_rules", {}) or {}

        try:
            supabase.table("sop_documents").update({
                "sop_text": raw_text,
                "sop_structure": structured_rules,
            }).eq("id", document_id).execute()
        except Exception as e:
            logger.warning("Unable to update sop_documents with extracted text for %s: %s", document_id, e)

        try:
            rag = get_rag_service()
            rag.embed_and_store(
                project_id=project_id,
                user_id=user_id,
                source_type="sop",
                source_id=document_id,
                content=raw_text,
                metadata={"title": title, "storage_path": storage_path, "document_id": document_id},
            )
            logger.info("SOP embedding completed for document %s", document_id)
        except Exception as e:
            logger.error("Failed to embed SOP into knowledge base for document %s: %s", document_id, e)


def _fallback_ppe_extraction(text: str) -> dict:
    """Extract PPE requirements from raw text using keyword matching as fallback."""
    text_lower = text.lower()
    found_ppe = []
    for canon, synonyms in PPE_CANONICAL.items():
        if any(syn in text_lower for syn in synonyms):
            found_ppe.append(canon)

    forbidden = []
    for line in text.split("\n"):
        line_l = line.lower().strip()
        if any(word in line_l for word in ["must not", "do not", "prohibited", "forbidden", "never"]):
            if line.strip():
                forbidden.append(line.strip())

    hazards = []
    for line in text.split("\n"):
        line_l = line.lower().strip()
        if any(word in line_l for word in ["hazard", "risk", "danger", "caution", "warning"]):
            if line.strip():
                hazards.append(line.strip())

    return {
        "ppe_requirements": found_ppe or ["helmet", "vest"],
        "required_procedures": [],
        "required_sequence": [],
        "forbidden_actions": forbidden[:10],
        "hazards": hazards[:10],
        "recommended_actions": [],
        "severity_levels": {},
        "equipment_rules": [],
        "general_safety": [],
        "sop_sections": [],
    }


sop_service = SopService()

def get_sop_service():
    return sop_service
