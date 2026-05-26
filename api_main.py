# -*- coding: utf-8 -*-
"""
CodeBridge Ringi — FastAPI バックエンド
"""
import os, secrets, json
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
from core.ringi_orchestrator import analyze_request
from core.orchestrator import run_pipeline
from core.sandbox import apply_code, read_target_code

app = FastAPI(title="CodeBridge Ringi API")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, dict] = {}


def _make_token(user: dict) -> str:
    tok = secrets.token_hex(32)
    _sessions[tok] = user
    return tok


def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")
    user = _sessions.get(authorization.split(" ", 1)[1])
    if not user:
        raise HTTPException(401, "Session expired")
    return user


def require_roles(*roles):
    def dep(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return dep


def require_admin():
    def dep(user=Depends(get_current_user)):
        if user.get("position_rank", 999) != 1:
            raise HTTPException(403, "Forbidden")
        return user
    return dep


def require_approver():
    def dep(user=Depends(get_current_user)):
        if not auth.user_can_approve(user["id"]):
            raise HTTPException(403, "Forbidden")
        return user
    return dep


class LoginReq(BaseModel):
    email: str
    password: str

class AnalyzeReq(BaseModel):
    raw_input: str

class SubmitReq(BaseModel):
    raw_input: str
    approval_type: str
    draft_title: str
    draft_body: str
    approver_id: int
    approver_name: str
    extension_type: Optional[str] = None
    extension_data: Optional[dict] = None
    auto_deploy: bool = True

class ResolveReq(BaseModel):
    comment: Optional[str] = None

class ApproverSettingsReq(BaseModel):
    auto_route_rules: dict
    notes: str = ""

class RoleUpdateReq(BaseModel):
    role: str

class ActiveUpdateReq(BaseModel):
    active: bool

class ChangePasswordReq(BaseModel):
    current_password: str
    new_password: str

class PositionCreateReq(BaseModel):
    name: str
    rank: Optional[int] = None

class PositionUpdateReq(BaseModel):
    name: str

class PositionsReorderReq(BaseModel):
    ordered_ids: list

class PositionAssignReq(BaseModel):
    position_id: int


@app.post("/api/login")
def login(req: LoginReq):
    user = auth.login(req.email, req.password)
    if not user:
        raise HTTPException(401, "メールアドレスまたはパスワードが正しくありません")
    token = _make_token(user)
    auth.log_action(user["id"], user["name"], "login", "")
    return {"token": token, "user": {
        "id": user["id"], "name": user["name"],
        "email": user["email"], "role": user["role"],
        "position_rank": user.get("position_rank"),
        "position_name": user.get("position_name"),
    }}


@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        _sessions.pop(authorization.split(" ", 1)[1], None)
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(get_current_user)):
    return {"id": user["id"], "name": user["name"],
            "email": user["email"], "role": user["role"],
            "position_rank": user.get("position_rank"),
            "position_name": user.get("position_name")}


@app.post("/api/me/password")
def change_my_password(req: ChangePasswordReq, user=Depends(get_current_user)):
    if not auth.login(user["email"], req.current_password):
        raise HTTPException(400, "現在のパスワードが正しくありません")
    if len(req.new_password) < 8:
        raise HTTPException(400, "新しいパスワードは8文字以上で入力してください")
    if req.current_password == req.new_password:
        raise HTTPException(400, "新しいパスワードが現在のパスワードと同じです")
    auth.change_password(user["id"], req.new_password)
    auth.log_action(user["id"], user["name"], "change_password_self", "")
    return {"ok": True}


@app.post("/api/requests/analyze")
def analyze(req: AnalyzeReq, user=Depends(get_current_user)):
    approvers = auth.list_approvers()
    draft = analyze_request(req.raw_input, user["name"], approvers)
    extension_data = None
    if draft.extension_type == "code_deploy":
        try:
            pipeline_result = run_pipeline(req.raw_input)
            extension_data = {
                "original_code": pipeline_result.original_code,
                "new_code": pipeline_result.new_code,
                "changed_lines": pipeline_result.changed_lines,
                "diff_summary": pipeline_result.report,
                "auto_deploy": True,
            }
        except Exception as e:
            extension_data = {"error": str(e), "auto_deploy": False}
    auth.log_action(user["id"], user["name"], "analyze", req.raw_input[:100], draft.cost_usd)
    auth.log_cost(user["id"], req.raw_input, draft.input_tokens, draft.output_tokens, draft.cost_usd)
    return {
        "approval_type": draft.approval_type,
        "draft_title": draft.draft_title,
        "draft_body": draft.draft_body,
        "suggested_approver_id": draft.suggested_approver_id,
        "suggested_approver_name": draft.suggested_approver_name,
        "suggested_approver_reason": draft.suggested_approver_reason,
        "extension_type": draft.extension_type,
        "extension_data": extension_data,
        "risk_level": draft.risk_level,
        "key_points": draft.key_points,
        "cost_usd": draft.cost_usd,
    }


@app.post("/api/requests/submit")
def submit(req: SubmitReq, user=Depends(get_current_user)):
    ext_data = req.extension_data
    if ext_data and req.extension_type == "code_deploy":
        ext_data["auto_deploy"] = req.auto_deploy
    request_id = auth.create_request(
        requester_id=user["id"], requester_name=user["name"],
        raw_input=req.raw_input, approval_type=req.approval_type,
        draft_title=req.draft_title, draft_body=req.draft_body,
        approver_id=req.approver_id, approver_name=req.approver_name,
        extension_type=req.extension_type, extension_data=ext_data,
    )
    auth.log_action(user["id"], user["name"], "submit",
                    f"request_id={request_id} title={req.draft_title[:50]}")
    return {"ok": True, "request_id": request_id, "approver_name": req.approver_name}


@app.get("/api/requests/mine")
def my_requests(user=Depends(get_current_user)):
    return auth.get_requests_by_requester(user["id"])


@app.get("/api/requests/inbox")
def inbox(user=Depends(require_approver())):
    return auth.get_requests_inbox(user["id"])


@app.get("/api/requests/{request_id}")
def get_request(request_id: int, user=Depends(get_current_user)):
    req = auth.get_request(request_id)
    if not req:
        raise HTTPException(404, "Not found")
    if user["role"] == "staff" and req["requester_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return req


@app.post("/api/requests/{request_id}/approve")
def approve(request_id: int, req: ResolveReq, user=Depends(require_approver())):
    ringi = auth.get_request(request_id)
    if not ringi:
        raise HTTPException(404, "Not found")
    if ringi["approver_id"] != user["id"]:
        raise HTTPException(403, "この申請の承認者ではありません")
    if ringi["status"] != "pending":
        raise HTTPException(400, "既に処理済みです")
    auth.resolve_request(request_id, "approved", req.comment)
    _execute_extension(ringi)
    auth.log_action(user["id"], user["name"], "approve",
                    f"request_id={request_id} title={ringi.get('draft_title','')[:50]}")
    return {"ok": True}


@app.post("/api/requests/{request_id}/reject")
def reject(request_id: int, req: ResolveReq, user=Depends(require_approver())):
    ringi = auth.get_request(request_id)
    if not ringi:
        raise HTTPException(404, "Not found")
    if ringi["approver_id"] != user["id"]:
        raise HTTPException(403, "この申請の承認者ではありません")
    if ringi["status"] != "pending":
        raise HTTPException(400, "既に処理済みです")
    if not req.comment:
        raise HTTPException(400, "差し戻しにはコメントが必要です")
    auth.resolve_request(request_id, "rejected", req.comment)
    auth.log_action(user["id"], user["name"], "reject",
                    f"request_id={request_id} comment={req.comment[:50]}")
    return {"ok": True}


def _execute_extension(ringi: dict):
    if ringi.get("extension_type") == "code_deploy" and ringi.get("extension_data"):
        try:
            ext = json.loads(ringi["extension_data"]) if isinstance(ringi["extension_data"], str) else ringi["extension_data"]
            if ext.get("auto_deploy") and ext.get("new_code"):
                apply_code(ext["new_code"])
        except Exception:
            pass
    # 将来追加予定:
    # elif ringi.get("extension_type") == "amazon_purchase": ...
    # elif ringi.get("extension_type") == "slack_invite": ...


@app.get("/api/phase3/stats")
def phase3_stats(user=Depends(get_current_user)):
    ids = auth.get_visible_user_ids(user["id"])
    return auth.get_phase3_stats(user_ids=ids)


@app.get("/api/phase3/approver/{uid}")
def approver_stats(uid: int, user=Depends(get_current_user)):
    allowed = auth.get_visible_user_ids(user["id"])
    if uid not in allowed:
        raise HTTPException(403, "Forbidden")
    return auth.get_approver_detail_stats(uid)


@app.get("/api/users/by_role/{role}")
def users_by_role(role: str, user=Depends(require_admin())):
    return auth.list_users_by_role(role)


@app.get("/api/admin/positions")
def list_positions(user=Depends(require_admin())):
    return auth.list_positions()


@app.post("/api/admin/positions")
def create_position(req: PositionCreateReq, user=Depends(require_admin())):
    try:
        pid = auth.create_position(req.name, req.rank)
    except Exception as e:
        raise HTTPException(400, str(e))
    auth.log_action(user["id"], user["name"], "create_position", f"name={req.name}")
    return {"id": pid}


# ⚠️ /reorder は /{pid} より先に定義すること（FastAPI のルート優先順）
@app.put("/api/admin/positions/reorder")
def reorder_positions(req: PositionsReorderReq, user=Depends(require_admin())):
    auth.reorder_positions(req.ordered_ids)
    auth.log_action(user["id"], user["name"], "reorder_positions", str(req.ordered_ids))
    return {"ok": True}


@app.put("/api/admin/positions/{pid}")
def update_position(pid: int, req: PositionUpdateReq, user=Depends(require_admin())):
    auth.update_position_name(pid, req.name)
    auth.log_action(user["id"], user["name"], "update_position_name", f"id={pid} name={req.name}")
    return {"ok": True}


@app.delete("/api/admin/positions/{pid}")
def delete_position(pid: int, user=Depends(require_admin())):
    try:
        auth.delete_position(pid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    auth.log_action(user["id"], user["name"], "delete_position", f"id={pid}")
    return {"ok": True}


@app.get("/api/admin/users")
def list_all_users(user=Depends(require_admin())):
    return auth.list_users()


@app.put("/api/admin/users/{user_id}/role")
def update_user_role(user_id: int, req: RoleUpdateReq, user=Depends(require_admin())):
    if user_id == user["id"]:
        raise HTTPException(400, "自分自身の役職は変更できません")
    if req.role not in ("admin", "manager", "staff"):
        raise HTTPException(400, "Invalid role")
    auth.update_user_role(user_id, req.role)
    auth.log_action(user["id"], user["name"], "update_role",
                    f"target_user_id={user_id} new_role={req.role}")
    return {"ok": True}


@app.put("/api/admin/users/{user_id}/position")
def update_user_position(user_id: int, req: PositionAssignReq, user=Depends(require_admin())):
    if user_id == user["id"]:
        # 自分が rank=1 の唯一のユーザーなら変更不可
        rank1_count = sum(1 for u in auth.list_users() if u.get("position_rank") == 1)
        target = next((u for u in auth.list_users() if u["id"] == user_id), None)
        if target and target.get("position_rank") == 1 and rank1_count <= 1:
            raise HTTPException(400, "最後の管理者の役職は変更できません")
    positions = {p["id"]: p for p in auth.list_positions()}
    if req.position_id not in positions:
        raise HTTPException(400, "Invalid position_id")
    auth.update_user_position(user_id, req.position_id)
    auth.log_action(user["id"], user["name"], "update_position",
                    f"target_user_id={user_id} position_id={req.position_id}")
    return {"ok": True}


@app.put("/api/admin/users/{user_id}/active")
def toggle_user_active(user_id: int, req: ActiveUpdateReq, user=Depends(require_admin())):
    if user_id == user["id"]:
        raise HTTPException(400, "自分自身を無効化できません")
    auth.toggle_user_active(user_id, req.active)
    auth.log_action(user["id"], user["name"], "toggle_active",
                    f"target_user_id={user_id} active={req.active}")
    return {"ok": True}


@app.post("/api/admin/users/{user_id}/reset_password")
def reset_password_endpoint(user_id: int, user=Depends(require_admin())):
    temp_pw = auth.reset_password(user_id)
    auth.log_action(user["id"], user["name"], "reset_password",
                    f"target_user_id={user_id}")
    return {"temp_password": temp_pw}


@app.get("/api/phase3/settings/{uid}")
def get_settings(uid: int, user=Depends(require_admin())):
    return auth.get_approver_settings(uid)


@app.put("/api/phase3/settings/{uid}")
def update_settings(uid: int, req: ApproverSettingsReq, user=Depends(require_admin())):
    auth.update_approver_settings(uid, req.auto_route_rules, req.notes)
    auth.log_action(user["id"], user["name"], "update_settings", f"uid={uid}")
    return {"ok": True}


@app.get("/api/logs")
def get_logs(user=Depends(require_admin())):
    return auth.get_activity_log(500)


@app.get("/api/cost")
def get_cost(user=Depends(require_admin())):
    return {"monthly": auth.get_monthly_cost(), "history": auth.get_cost_history(30)}


@app.get("/api/approvers")
def get_approvers(user=Depends(get_current_user)):
    return auth.list_approvers()


@app.get("/api/health")
def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        idx = os.path.join(frontend_dir, "index.html")
        if os.path.exists(idx):
            return FileResponse(idx)
        return {"error": "not found"}
