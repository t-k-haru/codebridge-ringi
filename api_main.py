# -*- coding: utf-8 -*-
"""
CodeBridge FastAPI バックエンド
Azure App Service で動作する。
"""
import os, secrets, time
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import core.auth as auth
from core.orchestrator import run_pipeline
from core.sandbox import apply_code

app = FastAPI(title="CodeBridge API")

# CORS: Static Web Apps のドメインを許可
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── セッショントークン（簡易インメモリ、本番はRedis等に移行） ──────────────────
_sessions: dict[str, dict] = {}

def _make_token(user: dict) -> str:
    tok = secrets.token_hex(32)
    _sessions[tok] = user
    return tok

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")
    tok = authorization.split(" ", 1)[1]
    user = _sessions.get(tok)
    if not user:
        raise HTTPException(401, "Session expired")
    return user

def require_roles(*roles):
    def dep(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return dep

# ── モデル ─────────────────────────────────────────────────────────────────────
class LoginReq(BaseModel):
    email: str
    password: str

class PipelineReq(BaseModel):
    instruction: str
    priority: str = "mid"
    eng_comment: str = ""

class ApproveReq(BaseModel):
    new_code: str
    instruction: str

class RejectReq(BaseModel):
    instruction: str
    original_code: str
    feedback: str

class CreateUserReq(BaseModel):
    name: str
    email: str
    password: str
    role: str

class UpdateRoleReq(BaseModel):
    role: str

class ChangePwReq(BaseModel):
    old_password: str
    new_password: str

# ── 認証 ───────────────────────────────────────────────────────────────────────
@app.post("/api/login")
def login(req: LoginReq):
    user = auth.login(req.email, req.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token = _make_token(user)
    return {"token": token, "user": {
        "id": user["id"], "name": user["name"],
        "email": user["email"], "role": user["role"],
    }}

@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        tok = authorization.split(" ", 1)[1]
        _sessions.pop(tok, None)
    return {"ok": True}

@app.get("/api/me")
def me(user=Depends(get_current_user)):
    return {"id": user["id"], "name": user["name"],
            "email": user["email"], "role": user["role"]}

@app.post("/api/change-password")
def change_password(req: ChangePwReq, user=Depends(get_current_user)):
    if not auth.login(user["email"], req.old_password):
        raise HTTPException(400, "Current password incorrect")
    if len(req.new_password) < 8:
        raise HTTPException(400, "Password too short")
    auth.change_password(user["id"], req.new_password)
    auth.log_action(user["id"], user["name"], "change_password", "")
    return {"ok": True}

# ── AI パイプライン ─────────────────────────────────────────────────────────────
@app.post("/api/pipeline")
def pipeline(req: PipelineReq, user=Depends(get_current_user)):
    full = req.instruction
    if req.eng_comment.strip():
        full += f"\n\n[Comment]\n{req.eng_comment}"
    result = run_pipeline(full)
    auth.log_action(user["id"], user["name"], "request", req.instruction[:200], result.cost_usd)
    auth.log_cost(user["id"], req.instruction, result.input_tokens, result.output_tokens, result.cost_usd)
    return {
        "success": result.success,
        "original_code": result.original_code,
        "new_code": result.new_code,
        "report": result.report,
        "iterations": result.iterations,
        "changed_lines": result.changed_lines,
        "test_output": result.test_output,
        "test_error": result.test_error,
        "cost_usd": result.cost_usd,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }

@app.post("/api/approve")
def approve(req: ApproveReq, user=Depends(require_roles("engineer","admin"))):
    apply_code(req.new_code)
    auth.log_action(user["id"], user["name"], "approve", req.instruction[:100])
    return {"ok": True}

@app.post("/api/reject")
def reject(req: RejectReq, user=Depends(require_roles("engineer","admin"))):
    full = req.instruction + f"\n\n[Correction]\n{req.feedback}"
    result = run_pipeline(full, req.original_code)
    auth.log_action(user["id"], user["name"], "reject_regen", req.feedback[:100], result.cost_usd)
    auth.log_cost(user["id"], req.feedback, result.input_tokens, result.output_tokens, result.cost_usd)
    return {
        "success": result.success,
        "original_code": result.original_code,
        "new_code": result.new_code,
        "report": result.report,
        "iterations": result.iterations,
        "changed_lines": result.changed_lines,
        "test_output": result.test_output,
        "test_error": result.test_error,
        "cost_usd": result.cost_usd,
    }

# ── ユーザー管理（admin） ────────────────────────────────────────────────────────
@app.get("/api/users")
def list_users(user=Depends(require_roles("admin"))):
    return auth.list_users()

@app.post("/api/users")
def create_user(req: CreateUserReq, user=Depends(require_roles("admin"))):
    ok, msg = auth.create_user(req.name, req.email, req.password, req.role)
    if not ok:
        raise HTTPException(400, msg)
    auth.log_action(user["id"], user["name"], "create_user", req.email)
    return {"ok": True}

@app.put("/api/users/{uid}/role")
def update_role(uid: int, req: UpdateRoleReq, user=Depends(require_roles("admin"))):
    auth.update_user_role(uid, req.role)
    auth.log_action(user["id"], user["name"], "role_change", f"uid={uid} → {req.role}")
    return {"ok": True}

@app.post("/api/users/{uid}/reset-password")
def reset_password(uid: int, user=Depends(require_roles("admin"))):
    tmp = auth.reset_password(uid)
    auth.log_action(user["id"], user["name"], "reset_pw", f"uid={uid}")
    return {"temp_password": tmp}

@app.put("/api/users/{uid}/active")
def toggle_active(uid: int, active: bool, user=Depends(require_roles("admin"))):
    auth.toggle_user_active(uid, active)
    auth.log_action(user["id"], user["name"], "toggle_user", f"uid={uid} active={active}")
    return {"ok": True}

@app.delete("/api/users/{uid}")
def delete_user(uid: int, user=Depends(require_roles("admin"))):
    auth.delete_user(uid)
    auth.log_action(user["id"], user["name"], "delete_user", f"uid={uid}")
    return {"ok": True}

# ── ログ・コスト ────────────────────────────────────────────────────────────────
@app.get("/api/logs")
def get_logs(user=Depends(require_roles("engineer","admin"))):
    return auth.get_activity_log(500)

@app.get("/api/logs/csv")
def get_logs_csv(user=Depends(require_roles("admin"))):
    from fastapi.responses import Response
    csv = auth.log_to_csv()
    return Response(content=csv, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=activity_log.csv"})

@app.get("/api/cost")
def get_cost(user=Depends(require_roles("engineer","admin"))):
    return {
        "monthly": auth.get_monthly_cost(),
        "history": auth.get_cost_history(30),
    }

# ── ヘルスチェック ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}

# ── 本番用: frontendフォルダのSPA配信 ──────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        idx = os.path.join(frontend_dir, "index.html")
        if os.path.exists(idx):
            return FileResponse(idx)
        return {"error": "not found"}
