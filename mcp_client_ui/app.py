from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import traceback

from mcp_orchestrator.orchestrator import choose_and_call_async


app = FastAPI(title="MCP Client UI")

app.mount("/static", StaticFiles(directory="./mcp_client_ui/static"), name="static")


class QueryModel(BaseModel):
    query: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return FileResponse('./mcp_client_ui/templates/index.html')


@app.post("/ask")
async def ask(q: QueryModel):
    try:
        tool_name, result = await choose_and_call_async(q.query)
        return JSONResponse({"tool": tool_name, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e), "trace": traceback.format_exc()}, status_code=500)
