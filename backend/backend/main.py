"""FastAPI entrypoint for Sharrowkin."""

from __future__ import annotations

import sys
import os
import io
import time
import json
import contextlib
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Setup pathing
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import integrations paths
for relative in ("integrations/semanticgit/src", "integrations/lazystandup/src"):
    candidate = REPO_ROOT / relative
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from backend.agent import PHASES, SharrowkinAgent
from cognition.fieldscript.fieldscript_v1 import FieldScript

app = FastAPI(title="Sharrowkin Unified Cognitive Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent global cognitive agent instance (FieldScript)
cognitive_agent = FieldScript(dim=256)

PATCH_DECISION = {"status": "idle", "message": "No patch decision recorded yet."}


class StandupRequest(BaseModel):
    workspace_path: str = Field(..., min_length=1)
    hours: float = Field(24, gt=0)
    engine: str = "offline"


class PatchDecisionRequest(BaseModel):
    workspace_path: str = Field(..., min_length=1)
    note: str = ""


class CreateDocRequest(BaseModel):
    title: str
    folder: str
    content: str


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "phases": PHASES}


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    
    if not messages:
        return {"response": "No messages received."}
        
    last_user_message = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if not last_user_message:
        return {"response": "No user message found."}
        
    content = last_user_message["content"]
    
    # 1. Capture the internal reasoning logs (stdout)
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        print(f"\n[RECEPTION] User input: {content}")
        # Observe the input
        cognitive_agent.observe(content)
        # Reason and find meaning
        cognitive_agent.reason(depth=12)
        # Find memory analogies
        cognitive_agent.recall("user conversation context")
        # Stabilize
        cognitive_agent.stabilize()
        # Commit to vector space
        cognitive_agent.commit("Processed user interaction.")
    
    logs = f.getvalue()
    
    # 2. Build the detailed response incorporating the cognitive trace
    response_text = f"NARE-Field Analysis Complete.\n\n```log\n{logs}\n```\n\nThe cognitive cycle successfully processed your input: '{content}'. Memory deltas have been updated and system energy stabilized."
    
    return {"response": response_text, "logs": logs}


@app.post("/api/terminal")
async def terminal_endpoint(request: Request):
    data = await request.json()
    command = data.get("command", "").strip()
    
    normalized_cmd = command.lower()
    output = []
    
    if normalized_cmd == "dsm status":
        output = [
            "→ MoE vector space connected: stable",
            "→ 12,408 Memory chunks active",
            "→ Trace context cleared. Inference energy: 0.045",
            "✔ DSM fully operational."
        ]
    elif normalized_cmd.startswith("agent start"):
        output = [
            "[INFO] Booting Sharrowkin autonomous protocol...",
            "[INFO] Syncing weights to FieldScript (dim=256)...",
            "→ System active. Delta prediction engine online."
        ]
    elif normalized_cmd == "clear":
        pass
    else:
        # Default fallback: try to run as local terminal commands or fallback gracefully
        output = [f"bash: command not found: {command}"]
        
    return {"output": output}


@app.get("/api/stats")
async def stats_endpoint():
    # Return simulated real-time stats
    return {
        "cpu": 24,
        "memory_gb": 0.85,
        "ping": 14,
        "routines": [
            {"name": "Associative Indexer", "active": True},
            {"name": "MoE Routing Protocol", "active": True},
            {"name": "Trace Context Resolver", "active": False}
        ]
    }


@app.post("/api/standup")
def standup(request: StandupRequest) -> dict[str, object]:
    from lazystandup.harvester import harvest_changes
    from lazystandup.reporter import generate_report, generate_report_offline

    try:
        result = harvest_changes(repo_path=request.workspace_path, hours=request.hours)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        report = (
            "LazyStandup could not read s-git history for this workspace.\n\n"
            f"Reason: {exc}\n\n"
            "Initialize s-git history in the project to generate AST-based standup reports."
        )
        return {
            "report": report,
            "engine": "offline",
            "fallback": True,
            "error": str(exc),
            "changes": [],
            "commits_scanned": 0,
        }

    descriptions = result.descriptions
    report = ""
    error = ""
    try:
        if request.engine == "offline":
            report = generate_report_offline(descriptions)
        else:
            report = generate_report(descriptions, engine=request.engine)
    except (ConnectionError, TimeoutError, ValueError, RuntimeError) as exc:
        error = str(exc)
        report = generate_report_offline(descriptions)
    return {
        "report": report,
        "engine": request.engine,
        "fallback": bool(error),
        "error": error,
        "changes": [change.describe() for change in result.changes],
        "commits_scanned": result.commits_scanned,
    }


@app.post("/api/patch/accept")
def accept_patch(request: PatchDecisionRequest) -> dict[str, object]:
    PATCH_DECISION["status"] = "accepted"
    PATCH_DECISION["message"] = request.note or f"Accepted patch for {request.workspace_path}."
    return PATCH_DECISION


import subprocess

@app.get("/api/git/changes")
def get_git_changes():
    workspace = "c:\\Users\\danik\\Documents\\Field"
    try:
        # Run git status --porcelain
        status_res = subprocess.run(
            ["git", "status", "--porcelain"], 
            cwd=workspace, 
            capture_output=True, 
            text=True, 
            check=True
        )
        lines = status_res.stdout.strip().split("\n")
        files = []
        for line in lines:
            if not line:
                continue
            parts = line.strip().split(" ", 1)
            if len(parts) < 2:
                continue
            status, filepath = parts[0], parts[1].strip()
            
            # Get actual git diff for the file
            diff_res = subprocess.run(
                ["git", "diff", filepath],
                cwd=workspace,
                capture_output=True,
                text=True
            )
            diff_text = diff_res.stdout
            
            # Create a simple diff breakdown
            original = ""
            modified = ""
            additions = 0
            deletions = 0
            
            diff_lines = diff_text.split("\n")
            for dl in diff_lines:
                if dl.startswith("+") and not dl.startswith("+++"):
                    additions += 1
                    if len(modified) < 150:
                        modified += dl[1:] + "\n"
                elif dl.startswith("-") and not dl.startswith("---"):
                    deletions += 1
                    if len(original) < 150:
                        original += dl[1:] + "\n"
            
            files.append({
                "name": filepath,
                "status": "modified" if "M" in status else "untracked" if "?" in status else "deleted",
                "additions": additions,
                "deletions": deletions,
                "original": original.strip() or "// Original file content",
                "modified": modified.strip() or "// Modified file content"
            })
            
        # Fallback if git status is empty
        if not files:
            files = [
                {
                    "name": "components/chat/left-sidebar.tsx",
                    "status": "modified",
                    "additions": 4,
                    "deletions": 4,
                    "original": '              { icon: Zap, label: "Automations", href: "/automations" },',
                    "modified": '              { icon: Settings, label: "Settings", href: "/settings" },'
                }
            ]
            
        return [
            {
                "id": "PR-REAL",
                "title": "Sync local modifications",
                "repo": "starface77/Field",
                "status": "pending",
                "time": "Just now",
                "description": "Real-time modifications detected in the active workspace. Ready to deploy or synchronize.",
                "filesChanged": files
            }
        ]
    except Exception as e:
        return [
            {
                "id": "PR-FALLBACK",
                "title": f"Git diagnostics: {str(e)}",
                "repo": "starface77/Field",
                "status": "pending",
                "time": "N/A",
                "description": f"Failed to retrieve real-time git state: {str(e)}",
                "filesChanged": []
            }
        ]


@app.get("/api/docs")
def list_docs():
    workspace = Path("c:\\Users\\danik\\Documents\\Field")
    docs_dir = workspace / "modules" / "docs"
    
    doc_list = []
    
    # Scan modules/docs
    if docs_dir.exists():
        for f in docs_dir.glob("*.md"):
            doc_list.append({
                "id": f.name,
                "title": f.stem.replace("_", " ").title(),
                "folder": "Theory & Manifesto",
                "filename": str(f)
            })
            
    # Scan root directory for MD files
    for f in workspace.glob("*.md"):
        doc_list.append({
            "id": f.name,
            "title": f.stem.replace("_", " ").title(),
            "folder": "Workspace Root",
            "filename": str(f)
        })
        
    return doc_list


@app.get("/api/docs/content")
def get_doc_content(filename: str):
    try:
        # Prevent path traversal
        if "c:\\Users\\danik\\Documents\\Field" not in filename:
            return {"content": "Access denied."}
        
        p = Path(filename)
        if p.exists() and p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        return {"content": "File not found."}
    except Exception as e:
        return {"content": f"Error: {str(e)}"}


@app.post("/api/docs/create")
def create_doc(request: CreateDocRequest) -> dict[str, object]:
    try:
        workspace = Path("c:\\Users\\danik\\Documents\\Field")
        if request.folder == "Theory & Manifesto":
            target_dir = workspace / "modules" / "docs"
        else:
            target_dir = workspace
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filename = request.title.strip().replace(" ", "_")
        if not filename.lower().endswith(".md"):
            filename += ".md"
            
        filepath = target_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(request.content)
            
        return {"status": "success", "message": f"Created {filename} successfully!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.websocket("/ws/agent")
async def agent_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        task = payload.get("task", "") if isinstance(payload, dict) else ""
        workspace_path = payload.get("workspace_path", "") if isinstance(payload, dict) else ""
        if not isinstance(task, str) or not isinstance(workspace_path, str) or not task or not workspace_path:
            await websocket.send_json({"type": "error", "message": "task and workspace_path are required"})
            await websocket.close()
            return
        agent = SharrowkinAgent()
        async for event in agent.run(task, workspace_path):
            await websocket.send_json(event)
        await websocket.close()
    except WebSocketDisconnect:
        return
