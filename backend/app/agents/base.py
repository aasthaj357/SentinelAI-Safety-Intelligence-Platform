import os
import json
import logging
import httpx
from app.core.config import settings
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


class BaseADKAgent:
    """Base class for ADK-inspired agents using Groq as the LLM backend.

    Agents are constructed with a system instruction string and an optional
    dict of callable tool handlers.  The ``execute`` method sends a prompt to
    Groq, handles any JSON-encoded tool calls embedded in the response, and
    returns the final text reply.
    """

    def __init__(
        self,
        name: str,
        instructions: str,
        tools: list = None,
        tool_handlers: dict = None,
    ):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.tool_handlers = tool_handlers or {}
        self.api_key = settings.GROQ_API_KEY

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_groq(self, messages: list) -> dict:
        """Send a chat completion request to Groq and return the JSON body."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.1,
        }
        if self.tools:
            payload["tools"] = self.tools
            payload["tool_choice"] = "auto"

        with httpx.Client(timeout=60) as client:
            resp = client.post(GROQ_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    def _log_trace(self, project_id: str, step: str, reasoning: str, context: dict):
        """Persist a decision trace to Supabase (best-effort)."""
        if not project_id:
            return
        try:
            supabase.table("decision_traces").insert(
                {
                    "project_id": project_id,
                    "agent_id": self.name,
                    "step": step,
                    "reasoning": reasoning,
                    "context": context,
                }
            ).execute()
        except Exception as trace_err:
            logger.warning("Trace logging failed: %s", trace_err)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, prompt: str, project_id: str = None) -> str:
        """Run the agent reasoning loop, invoking tools when requested."""
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": prompt},
        ]

        try:
            while True:
                body = self._call_groq(messages)
                choice = body["choices"][0]
                message = choice["message"]

                # Append assistant turn to history
                messages.append(message)

                # If no tool calls → we have the final answer
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    return message.get("content") or ""

                # Process each tool call
                for call in tool_calls:
                    fn_name = call["function"]["name"]
                    try:
                        args = json.loads(call["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}

                    logger.info(
                        "Agent %s: tool '%s' called with args %s",
                        self.name, fn_name, args,
                    )
                    self._log_trace(
                        project_id,
                        f"tool_call_{fn_name}",
                        f"Agent invoked tool '{fn_name}' during execution flow.",
                        {"arguments": args},
                    )

                    if fn_name in self.tool_handlers:
                        try:
                            result = self.tool_handlers[fn_name](**args)
                        except Exception as exc:
                            logger.error("Tool '%s' raised: %s", fn_name, exc)
                            result = {"error": str(exc)}
                    else:
                        result = {"error": f"Tool '{fn_name}' is not registered."}

                    self._log_trace(
                        project_id,
                        f"tool_result_{fn_name}",
                        f"Tool '{fn_name}' returned.",
                        {"result": result},
                    )

                    # Feed tool result back to the conversation
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "name": fn_name,
                            "content": json.dumps(result),
                        }
                    )

        except Exception as exc:
            logger.error("Agent %s execution error: %s", self.name, exc)
            return f"Agent execution error: {exc}"
