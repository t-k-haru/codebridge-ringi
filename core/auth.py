# -*- coding: utf-8 -*-
"""
CodeBridge Ringi — 認証・ユーザー管理・稟議・アクティビティログ・コスト追跡
3アカウント固定。ユーザー追加機能なし。
"""
import sqlite3, hashlib, json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ringi.db"

FIXED_USERS = [
    {"name": "田中 太郎", "email": "admin@codebridge.ai",   "password": "Admin1234!",   "role": "admin"},
    {"name": "山田 花子", "email": "manager@codebridge.ai", "password": "Manager1234!", "role": "manager"},
    {"name": "佐藤 一郎", "email": "staff@codebridge.ai",   "password": "Staff1234!",   "role": "staff"},
]


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def init_db():
    with _conn() as c:
        c.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    email    TEXT UNIQUE NOT NULL,
    pw_hash  TEXT NOT NULL,
    role     TEXT NOT NULL DEFAULT 'staff',
    created  TEXT NOT NULL,
    active   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS activity_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    user_id   INTEGER,
    user_name TEXT,
    action    TEXT NOT NULL,
    detail    TEXT,
    cost_usd  REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cost_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    user_id       INTEGER,
    request_text  TEXT,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd      REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS requests (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                TEXT NOT NULL,
    requester_id      INTEGER NOT NULL,
    requester_name    TEXT NOT NULL,
    raw_input         TEXT NOT NULL,
    approval_type     TEXT NOT NULL,
    draft_title       TEXT,
    draft_body        TEXT,
    approver_id       INTEGER,
    approver_name     TEXT,
    extension_type    TEXT DEFAULT NULL,
    extension_data    TEXT DEFAULT NULL,
    status            TEXT DEFAULT 'pending',
    approver_comment  TEXT DEFAULT NULL,
    resolved_at       TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS approver_settings (
    user_id           INTEGER PRIMARY KEY,
    auto_route_rules  TEXT DEFAULT NULL,
    notes             TEXT DEFAULT NULL
);
""")
    with _conn() as c:
        for u in FIXED_USERS:
            exists = c.execute("SELECT 1 FROM users WHERE email=?", (u["email"],)).fetchone()
            if not exists:
                ts = datetime.utcnow().isoformat()
                c.execute(
                    "INSERT INTO users (name,email,pw_hash,role,created) VALUES (?,?,?,?,?)",
                    (u["name"], u["email"], _hash(u["password"]), u["role"], ts),
                )


def login(email: str, password: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
    if row and row["pw_hash"] == _hash(password):
        return dict(row)
    return None


def list_approvers():
    with _conn() as c:
        rows = c.execute(
            "SELECT id, name, role FROM users WHERE role IN ('manager','admin') AND active=1"
        ).fetchall()
    return [dict(r) for r in rows]


def list_users():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT id,name,email,role,created FROM users ORDER BY id")]


def create_request(requester_id, requester_name, raw_input, approval_type,
                   draft_title, draft_body, approver_id, approver_name,
                   extension_type=None, extension_data=None):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO requests
               (ts,requester_id,requester_name,raw_input,approval_type,
                draft_title,draft_body,approver_id,approver_name,
                extension_type,extension_data,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,'pending')""",
            (ts, requester_id, requester_name, raw_input, approval_type,
             draft_title, draft_body, approver_id, approver_name,
             extension_type,
             json.dumps(extension_data) if extension_data else None),
        )
        return cur.lastrowid


def get_requests_by_requester(user_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM requests WHERE requester_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_requests_inbox(approver_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM requests WHERE approver_id=? AND status='pending' ORDER BY id DESC",
            (approver_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_request(request_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
    return dict(row) if row else None


def resolve_request(request_id, status, comment=None):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "UPDATE requests SET status=?, approver_comment=?, resolved_at=? WHERE id=?",
            (status, comment, ts, request_id),
        )


def get_approver_settings(user_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM approver_settings WHERE user_id=?", (user_id,)).fetchone()
    if row:
        r = dict(row)
        r["auto_route_rules"] = json.loads(r["auto_route_rules"]) if r["auto_route_rules"] else {}
        return r
    return {"user_id": user_id, "auto_route_rules": {}, "notes": ""}


def update_approver_settings(user_id, auto_route_rules, notes):
    with _conn() as c:
        c.execute(
            """INSERT INTO approver_settings (user_id, auto_route_rules, notes)
               VALUES (?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 auto_route_rules=excluded.auto_route_rules,
                 notes=excluded.notes""",
            (user_id, json.dumps(auto_route_rules), notes),
        )


def get_user_ids_for_manager(manager_id: int) -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT id FROM users WHERE role = 'staff' OR id = ?", (manager_id,)
        ).fetchall()
    return [r["id"] for r in rows]


def get_visible_approver_ids_for_role(role: str, user_id: int) -> list:
    """ロールに応じて表示可能なユーザーIDリストを返す。
    admin: 全ユーザー / manager: 自分 + staff / staff: 自分のみ"""
    with _conn() as c:
        if role == "admin":
            rows = c.execute("SELECT id FROM users").fetchall()
        elif role == "manager":
            rows = c.execute(
                "SELECT id FROM users WHERE role = 'staff' OR id = ?", (user_id,)
            ).fetchall()
        else:
            return [user_id]
    return [r["id"] for r in rows]


def get_phase3_stats(user_ids=None):
    def _req_filter(base_sql, params):
        if user_ids:
            ph = ",".join("?" * len(user_ids))
            return f"{base_sql} AND requester_id IN ({ph})", params + list(user_ids)
        return base_sql, params

    with _conn() as c:
        # user_ids が指定された場合は承認者リストも同じ範囲に絞る
        if user_ids:
            ph = ",".join("?" * len(user_ids))
            approvers = c.execute(
                f"SELECT id, name FROM users WHERE role IN ('manager','admin') AND id IN ({ph})",
                list(user_ids),
            ).fetchall()
        else:
            approvers = c.execute(
                "SELECT id, name FROM users WHERE role IN ('manager','admin')"
            ).fetchall()
        by_approver = []
        for a in approvers:
            sql, params = _req_filter(
                "SELECT status, ts, resolved_at FROM requests WHERE approver_id=?", [a["id"]]
            )
            rows = c.execute(sql, params).fetchall()
            total = len(rows)
            approved = sum(1 for r in rows if r["status"] == "approved")
            times = []
            for r in rows:
                if r["resolved_at"] and r["ts"]:
                    try:
                        t1 = datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")
                        t2 = datetime.strptime(r["resolved_at"], "%Y-%m-%d %H:%M:%S")
                        times.append((t2 - t1).total_seconds() / 3600)
                    except Exception:
                        pass
            avg_h = round(sum(times) / len(times), 1) if times else 0
            rate = round(approved / total * 100) if total > 0 else 0
            by_approver.append({
                "approver_id": a["id"],
                "approver_name": a["name"],
                "avg_hours": avg_h,
                "approval_rate": rate,
                "total": total,
                "approved": approved,
            })
        type_sql, type_params = _req_filter(
            "SELECT approval_type, ts, resolved_at FROM requests WHERE status='approved'", []
        )
        type_rows = c.execute(type_sql, type_params).fetchall()
        auto_sql, auto_params = _req_filter(
            "SELECT COUNT(*) FROM requests WHERE approval_type='confirm' AND status='approved'", []
        )
        automation_count = c.execute(auto_sql, auto_params).fetchone()[0]
    type_stats: dict = {}
    for r in type_rows:
        t = r["approval_type"]
        if r["resolved_at"] and r["ts"]:
            try:
                t1 = datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")
                t2 = datetime.strptime(r["resolved_at"], "%Y-%m-%d %H:%M:%S")
                hours = (t2 - t1).total_seconds() / 3600
                type_stats.setdefault(t, []).append(hours)
            except Exception:
                pass
    type_avg = {k: round(sum(v) / len(v), 1) for k, v in type_stats.items()}
    return {"by_approver": by_approver, "by_type": type_avg, "automation_candidates": automation_count}


def get_approver_detail_stats(user_id):
    with _conn() as c:
        rows = c.execute("SELECT * FROM requests WHERE approver_id=? ORDER BY id DESC", (user_id,)).fetchall()
    data = [dict(r) for r in rows]
    total = len(data)
    return {
        "total": total,
        "approved": sum(1 for r in data if r["status"] == "approved"),
        "rejected": sum(1 for r in data if r["status"] == "rejected"),
        "pending":  sum(1 for r in data if r["status"] == "pending"),
        "requests": data,
    }


def log_action(user_id, user_name, action, detail="", cost_usd=0.0):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "INSERT INTO activity_log (ts,user_id,user_name,action,detail,cost_usd) VALUES (?,?,?,?,?,?)",
            (ts, user_id, user_name, action, detail, cost_usd),
        )


def get_activity_log(limit=200):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def log_cost(user_id, request_text, input_tokens, output_tokens, cost_usd):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "INSERT INTO cost_log (ts,user_id,request_text,input_tokens,output_tokens,cost_usd) VALUES (?,?,?,?,?,?)",
            (ts, user_id, request_text[:200], input_tokens, output_tokens, cost_usd),
        )


def get_monthly_cost():
    month = datetime.utcnow().strftime("%Y-%m")
    with _conn() as c:
        row = c.execute(
            "SELECT SUM(cost_usd) as total, SUM(input_tokens) as inp, SUM(output_tokens) as out "
            "FROM cost_log WHERE ts LIKE ?", (f"{month}%",)
        ).fetchone()
    return dict(row) if row else {"total": 0, "inp": 0, "out": 0}


def get_cost_history(limit=50):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM cost_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * 1.10 + output_tokens * 4.40) / 1_000_000


init_db()
