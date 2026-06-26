import asyncio
import json
import logging
from typing import Dict, Callable, Any
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

class MCPServerSSE:
    """Base Class representing an MCP Server communicating over SSE (Server-Sent Events) in FastAPI."""
    
    def __init__(self, name: str):
        self.name = name
        self.router = APIRouter(prefix=f"/mcp/{name}", tags=[f"MCP {name.upper()}"])
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self._register_routes()

    def register_tool(self, name: str, description: str, input_schema: dict, handler: Callable):
        """Register an MCP tool with its handler function and validation schema."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema
        }
        self.tool_handlers[name] = handler
        logger.info(f"Registered tool '{name}' on MCP Server '{self.name}'")

    def _register_routes(self):
        """Register the SSE and message routes under FastAPI."""
        
        @self.router.get("/sse")
        async def sse_endpoint(request: Request):
            """Establishes the SSE message channel with the client agent."""
            async def event_generator():
                try:
                    # Send connection confirmation event
                    yield f"event: endpoint\ndata: /api/mcp/{self.name}/messages\n\n"
                    # Keep connection alive
                    while True:
                        if await request.is_disconnected():
                            break
                        yield ": keep-alive\n\n"
                        await asyncio.sleep(15)
                except asyncio.CancelledError:
                    pass

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        @self.router.post("/messages")
        async def messages_endpoint(request: Request):
            """Receives JSON-RPC 2.0 tool requests from the client agent."""
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON payload")

            # Validate JSON-RPC 2.0
            if body.get("jsonrpc") != "2.0":
                return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": body.get("id")}

            method = body.get("method")
            msg_id = body.get("id")

            # 1. tools/list: List all available tools
            if method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": list(self.tools.values())
                    },
                    "id": msg_id
                }

            # 2. tools/call: Execute a tool
            elif method == "tools/call":
                params = body.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if not tool_name or tool_name not in self.tool_handlers:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {tool_name}"
                        },
                        "id": msg_id
                    }

                # Execute tool handler
                try:
                    handler = self.tool_handlers[tool_name]
                    # Support async/sync handlers
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(**arguments)
                    else:
                        result = handler(**arguments)

                    return {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": msg_id
                    }
                except TypeError as te:
                    logger.error(f"Invalid parameters for tool '{tool_name}': {te}")
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32602,
                            "message": f"Invalid params: {str(te)}"
                        },
                        "id": msg_id
                    }
                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}")
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32000,
                            "message": f"Internal error during execution: {str(e)}"
                        },
                        "id": msg_id
                    }

            # Invalid method
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": msg_id
                }
