"""FastAPI: the same agents exposed as REST endpoints. Run with: uvicorn api:app --reload"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
from agents.email_agent import triage_email
from agents.schemas import EmailTriage
from agents.task_agent import run_agent
from agents.task_store import TaskStore

app = FastAPI(title="AI Work Assistant API", version="1.0.0")
store = TaskStore()


class TriageRequest(BaseModel):
    email: str
    role: str = "busy professional"
    tone: str = "professional and concise"


class AgentRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/health")
def health():
    return {"status": "ok", "model": config.LLM_MODEL}


@app.post("/triage", response_model=EmailTriage)
def triage(req: TriageRequest):
    if not req.email.strip():
        raise HTTPException(status_code=400, detail="Email text is empty.")
    try:
        return triage_email(req.email, req.role, req.tone)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Triage failed: {e}")


@app.post("/agent")
def agent(req: AgentRequest):
    try:
        res = run_agent(req.message, store, req.history)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent failed: {e}")
    return {"reply": res.reply, "history": res.history, "tool_calls": res.tool_log}


@app.get("/tasks")
def tasks(status: str = "all"):
    return store.list(status)
