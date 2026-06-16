from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from verdict_sift_server.mock_data import TOOL_OUTPUTS

app = FastAPI(title="VERDICT SIFT MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ToolRequest(BaseModel):
    manifest: dict = {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "verdict-sift-mcp"}


@app.get("/tools")
async def list_tools():
    return {"tools": list(TOOL_OUTPUTS.keys())}


@app.post("/tools/{tool_name}")
async def run_tool(tool_name: str, request: ToolRequest):
    """
    Execute a forensic tool and return results.
    In production: actually invoke SIFT/Volatility/Zeek/etc.
    In demo: return pre-built ransomware scenario data.
    """
    if tool_name not in TOOL_OUTPUTS:
        # Return empty but valid response for unknown tools
        return {
            "tool": tool_name,
            "note": f"Tool {tool_name} not available in mock mode",
            "results": []
        }
    return TOOL_OUTPUTS[tool_name]
