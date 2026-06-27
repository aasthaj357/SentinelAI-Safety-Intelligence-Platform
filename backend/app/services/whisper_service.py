import os
import logging
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

class WhisperService:
    def transcribe_audio(self, audio_file_path: str) -> dict:
        """
        Transcribe audio using Groq's whisper-large-v3 model.
        Returns the transcript text and segments (if supported by Groq API).
        """
        try:
            with open(audio_file_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(audio_file_path, file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json"
                )

            # Verbose JSON provides segments with timestamps
            text = getattr(transcription, "text", "")
            segments = getattr(transcription, "segments", [])

            return {
                "text": text,
                "segments": segments
            }
        except Exception as e:
            logger.error("Whisper transcription error: %s", e)
            return {"text": "", "segments": []}

    def analyze_safety_communications(self, transcript_text: str) -> list:
        """
        Analyze transcript for warnings, commands, and safety instructions using Groq LLM.
        """
        if not transcript_text.strip():
            return []

        prompt = f"""
        Analyze the following transcript from a workplace environment.
        Extract any safety warnings, commands, or safety instructions.
        Format the output as a JSON list of objects with keys: "type" (warning/command/instruction), "quote", and "severity" (low/medium/high).
        
        Transcript:
        {transcript_text}
        """
        
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a safety officer AI. Output ONLY raw valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0
            )
        except Exception as e:
            logger.error("Whisper communication analysis error: %s", e)
            return []
        
        # Parse JSON
        import json
        try:
            content = response.choices[0].message.content
            # Cleanup Markdown backticks if present
            content = content.replace("```json", "").replace("```", "").strip()
            findings = json.loads(content)
            return findings
        except Exception as e:
            logger.error("Error parsing safety communications: %s", e)
            return []

whisper_service = WhisperService()

def get_whisper_service():
    return whisper_service
