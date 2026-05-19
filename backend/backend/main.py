"""FastAPI entrypoint for Sharrowkin."""

from __future__ import annotations

import sys
import os
import subprocess
import shlex

# Fix stdout encoding
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import io
import time
import json
import contextlib
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import psutil
except ImportError:
    psutil = None

# Setup pathing — BACKEND_DIR is the directory containing this file
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import integrations & memory paths (they live inside BACKEND_DIR)
for relative in (
    "integrations/semanticgit/src",
    "integrations/lazystandup/src",
    "memory/rld/src",
    "memory/dsm/src",
):
    candidate = BACKEND_DIR / relative
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from backend.agent import PHASES, SharrowkinAgent
from backend.personas import get_persona_manager, activate_persona, deactivate_persona, get_agent_name

try:
    from cognition.fieldscript.fieldscript_v1 import FieldScript
except ImportError:
    FieldScript = None

app = FastAPI(title="Sharrowkin Unified Cognitive Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent global cognitive agent instance (FieldScript)
cognitive_agent = FieldScript(dim=256) if FieldScript is not None else None

PATCH_DECISION = {"status": "idle", "message": "No patch decision recorded yet."}


# Default workspace: env var > home directory
_DEFAULT_WORKSPACE = os.getenv("WORKSPACE_PATH", str(Path.home()))


class SettingsState:
    workspace_path: str = _DEFAULT_WORKSPACE
    github_username: str = ""
    github_token: str = ""
    connected_repos: list[dict] = []


SETTINGS = SettingsState()


class StandupRequest(BaseModel):
    workspace_path: str = Field(..., min_length=1)
    hours: float = Field(24, gt=0)
    engine: str = "offline"


class PatchDecisionRequest(BaseModel):
    workspace_path: str = Field(..., min_length=1)
    note: str = ""


class ConnectRepoRequest(BaseModel):
    username: str
    token: str = ""
    repo_url: str = ""


class SettingsUpdateRequest(BaseModel):
    workspace_path: str


@app.get("/api/settings")
def get_settings():
    return {
        "workspace_path": SETTINGS.workspace_path,
        "github_username": SETTINGS.github_username,
        "connected_repos": SETTINGS.connected_repos
    }


@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    if not os.path.exists(req.workspace_path):
        return {"status": "error", "message": f"Path '{req.workspace_path}' does not exist on disk."}
    SETTINGS.workspace_path = req.workspace_path
    return {"status": "success", "workspace_path": SETTINGS.workspace_path}


import urllib.parse as _urllib_parse


@app.post("/api/git/connect")
def connect_git(req: ConnectRepoRequest):
    SETTINGS.github_username = req.username
    if req.token:
        SETTINGS.github_token = req.token
        
    if not req.repo_url:
        return {
            "status": "success",
            "message": f"GitHub connected as {req.username} successfully.",
            "workspace_path": SETTINGS.workspace_path
        }
        
    try:
        repo_url = req.repo_url.strip()
        if not repo_url.startswith("http://") and not repo_url.startswith("https://") and not repo_url.startswith("git@"):
            # e.g., "starface77/NareCLI"
            repo_url = f"https://github.com/{repo_url}.git"
            
        parts = repo_url.rstrip("/").split("/")
        repo_name = parts[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
            
        target_dir = Path(SETTINGS.workspace_path) / "projects" / repo_name
        
        # Build authenticated URL
        clone_url = repo_url
        if req.token:
            parsed = urllib.parse.urlparse(repo_url)
            if parsed.scheme == "https" and "github.com" in parsed.netloc:
                netloc = f"{req.username}:{req.token}@github.com" if req.username else f"{req.token}@github.com"
                clone_url = parsed._replace(netloc=netloc).geturl()
                
        # Run git clone if it doesn't exist
        if not (target_dir / ".git").exists():
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            res = subprocess.run(
                ["git", "clone", clone_url, str(target_dir)],
                capture_output=True,
                text=True
            )
            if res.returncode != 0:
                err = res.stderr
                if req.token:
                    err = err.replace(req.token, "********")
                return {"status": "error", "message": f"Git clone failed: {err}"}
                
        SETTINGS.workspace_path = str(target_dir)
        repo_info = {"name": repo_name, "url": req.repo_url, "path": str(target_dir)}
        if repo_info not in SETTINGS.connected_repos:
            SETTINGS.connected_repos.append(repo_info)
            
        return {
            "status": "success",
            "message": f"Cloned and connected repository '{repo_name}' successfully!",
            "workspace_path": SETTINGS.workspace_path,
            "repo": repo_info
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



class CreateDocRequest(BaseModel):
    title: str
    folder: str
    content: str


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "phases": PHASES}


# --- Persona API Endpoints ---
@app.get("/api/personas")
def list_personas():
    """Get all available personas."""
    manager = get_persona_manager()
    personas = manager.list_personas()

    return {
        "personas": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "colors": p.colors,
                "tags": p.tags,
                "audio_enabled": p.audio_enabled,
            }
            for p in personas
        ],
        "active_persona": manager.active_persona.id if manager.active_persona else None,
    }


@app.get("/api/personas/active")
def get_active_persona():
    """Get the currently active persona."""
    manager = get_persona_manager()

    if manager.active_persona:
        return {
            "id": manager.active_persona.id,
            "name": manager.active_persona.name,
            "description": manager.active_persona.description,
            "colors": manager.active_persona.colors,
        }

    return {"id": None, "name": "Default", "description": "Standard Sharrowkin agent"}


class PersonaActivateRequest(BaseModel):
    persona_id: str


@app.post("/api/personas/activate")
def activate_persona_endpoint(request: PersonaActivateRequest):
    """Activate a persona."""
    success = activate_persona(request.persona_id)

    if not success:
        return {"status": "error", "message": f"Persona '{request.persona_id}' not found"}

    return {
        "status": "success",
        "message": f"Persona '{request.persona_id}' activated",
        "persona_id": request.persona_id,
    }


@app.post("/api/personas/deactivate")
def deactivate_persona_endpoint():
    """Deactivate the current persona."""
    deactivate_persona()

    return {
        "status": "success",
        "message": "Persona deactivated, using default agent",
    }


@app.get("/api/personas/agent-name")
def get_agent_name_endpoint():
    """Get the current agent name based on active persona."""
    return {
        "agent_name": get_agent_name()
    }


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    model = data.get("model", "")

    if not messages:
        return {"response": "No messages received."}

    last_user_message = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if not last_user_message:
        return {"response": "No user message found."}

    content = last_user_message["content"]

    # Run through the cognitive agent if available
    logs = ""
    if cognitive_agent is not None:
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            print(f"\n[RECEPTION] User input: {content}")
            cognitive_agent.observe(content)
            cognitive_agent.reason(depth=12)
            cognitive_agent.recall("user conversation context")
            cognitive_agent.stabilize()
            cognitive_agent.commit("Processed user interaction.")
        logs = f.getvalue()

    # Generate an actual LLM response via the agent's Gemini client
    from backend.agent import SharrowkinAgent
    try:
        agent = SharrowkinAgent()
        response_text = agent.gemini.generate_text(
            content,
            "You are Sharrowkin, a helpful AI coding assistant. "
            "Respond concisely and helpfully. Use markdown for code. "
            "Answer in the same language the user writes in."
        )
    except Exception as exc:
        response_text = f"LLM error: {exc}"

    return {"response": response_text, "logs": logs}


# Dangerous commands that must never be executed
_BLOCKED_COMMANDS = {"rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:", "shutdown", "reboot", "halt", "poweroff"}


@app.post("/api/terminal")
async def terminal_endpoint(request: Request):
    data = await request.json()
    command = data.get("command", "").strip()

    if not command:
        return {"output": []}

    normalized_cmd = command.lower()
    if normalized_cmd == "clear":
        return {"output": []}

    # Safety check
    for blocked in _BLOCKED_COMMANDS:
        if blocked in normalized_cmd:
            return {"output": [f"⛔ Command blocked for safety: {command}"]}

    workspace = Path(SETTINGS.workspace_path)
    if not workspace.exists():
        workspace = Path.home()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(workspace),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        if result.returncode != 0:
            lines.append(f"[exit code {result.returncode}]")
        return {"output": lines}
    except subprocess.TimeoutExpired:
        return {"output": [f"⏰ Command timed out after 60s: {command}"]}
    except Exception as e:
        return {"output": [f"❌ Error: {e}"]}


@app.get("/api/stats")
async def stats_endpoint():
    if psutil is not None:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        memory_gb = round(mem.used / (1024 ** 3), 2)
    else:
        cpu = 0
        memory_gb = 0.0

    # Measure network latency to Gemini API (simple proxy for "ping")
    ping_ms = 0
    try:
        import urllib.request
        start = time.time()
        urllib.request.urlopen("https://generativelanguage.googleapis.com", timeout=3)
        ping_ms = int((time.time() - start) * 1000)
    except Exception:
        ping_ms = -1

    return {
        "cpu": cpu,
        "memory_gb": memory_gb,
        "ping": ping_ms,
        "routines": [
            {"name": "LLM Client", "active": True},
            {"name": "Memory Bridge (DSM/RLD)", "active": True},
            {"name": "Workspace Scanner", "active": True},
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


@app.get("/api/git/changes")
def get_git_changes():
    workspace = SETTINGS.workspace_path
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
    workspace = Path(SETTINGS.workspace_path)
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
        if SETTINGS.workspace_path not in filename:
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
        workspace = Path(SETTINGS.workspace_path)
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
        model = payload.get("model", "") if isinstance(payload, dict) else ""

        print(f"[WS] Received: task={task!r}, workspace_path={workspace_path!r}, model={model!r}")

        # Use configured workspace if none provided or if a Windows path is sent
        if not workspace_path or workspace_path.startswith("c:\\") or workspace_path.startswith("C:\\"):
            workspace_path = SETTINGS.workspace_path

        if not isinstance(task, str) or not task:
            await websocket.send_json({"type": "error", "message": "task is required"})
            await websocket.close()
            return

        # Ensure workspace exists
        ws_path = Path(workspace_path)
        if not ws_path.exists():
            ws_path.mkdir(parents=True, exist_ok=True)

        print(f"[WS] Using workspace: {workspace_path}")

        try:
            global _GLOBAL_AGENT
            if '_GLOBAL_AGENT' not in globals():
                _GLOBAL_AGENT = SharrowkinAgent()
            async for event in _GLOBAL_AGENT.run(task, workspace_path):
                await websocket.send_json(event)
        except Exception as exc:
            print(f"[WS] Agent error: {exc}")
            try:
                await websocket.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass

        try:
            await websocket.close()
        except Exception:
            pass
    except WebSocketDisconnect:
        return
    except Exception as exc:
        print(f"[WS] Unhandled error: {exc}")
        try:
            await websocket.send_json({"type": "error", "message": f"Server error: {exc}"})
            await websocket.close()
        except Exception:
            pass
