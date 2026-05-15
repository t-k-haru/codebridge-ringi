# -*- coding: utf-8 -*-
"""
CodeBridge 認証・ユーザー管理・アクティビティログ・コスト追跡
SQLite で永続化。
"""
import sqlite3, hashlib, secrets, os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "codebridge.db"

def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    email    TEXT UNIQUE NOT NULL,
    pw_hash  TEXT NOT NULL,
    role     TEXT NOT NULL DEFAULT 'requester',
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
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    user_id      INTEGER,
    request_text TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd     REAL DEFAULT 0
);
""")
    # 管理者アカウントがなければ作る
    with _conn() as c:
        exists = c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone()
        if not exists:
            _create_user("Admin", "admin@codebridge.ai", "Admin1234!", "admin", c)

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _create_user(name, email, password, role, conn=None):
    ts = datetime.utcnow().isoformat()
    h  = _hash(password)
    db = conn or _conn()
    db.execute("INSERT INTO users (name,email,pw_hash,role,created) VALUES (?,?,?,?,?)",
               (name, email, h, role, ts))
    if conn is None:
        db.commit()

# ── 認証 ────────────────────────────────────────────────────────────────────
def login(email: str, password: str):
    """返り値: Row (id, name, email, role) or None"""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM users WHERE email=? AND active=1", (email,)
        ).fetchone()
    if row and row["pw_hash"] == _hash(password):
        return dict(row)
    return None

def change_password(user_id: int, new_pw: str):
    with _conn() as c:
        c.execute("UPDATE users SET pw_hash=? WHERE id=?", (_hash(new_pw), user_id))

def reset_password(user_id: int) -> str:
    """ランダムパスワードを生成して返す"""
    tmp = secrets.token_urlsafe(10)
    change_password(user_id, tmp)
    return tmp

# ── ユーザー管理 (admin) ─────────────────────────────────────────────────────
def list_users():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM users ORDER BY created")]

def create_user(name, email, password, role):
    try:
        _create_user(name, email, password, role)
        return True, ""
    except sqlite3.IntegrityError:
        return False, "このメールアドレスはすでに登録されています"

def update_user_role(user_id: int, role: str):
    with _conn() as c:
        c.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))

def toggle_user_active(user_id: int, active: bool):
    with _conn() as c:
        c.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))

def delete_user(user_id: int):
    with _conn() as c:
        c.execute("DELETE FROM users WHERE id=?", (user_id,))

# ── アクティビティログ ────────────────────────────────────────────────────────
def log_action(user_id, user_name, action, detail="", cost_usd=0.0):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "INSERT INTO activity_log (ts,user_id,user_name,action,detail,cost_usd) VALUES (?,?,?,?,?,?)",
            (ts, user_id, user_name, action, detail, cost_usd)
        )

def get_activity_log(limit=200):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

def log_to_csv() -> str:
    rows = get_activity_log(10000)
    lines = ["id,timestamp,user,action,detail,cost_usd"]
    for r in rows:
        detail = str(r.get("detail","")).replace(",","，").replace("\n"," ")
        lines.append(f"{r['id']},{r['ts']},{r['user_name']},{r['action']},{detail},{r['cost_usd']:.6f}")
    return "\n".join(lines)

# ── コストログ ────────────────────────────────────────────────────────────────
def log_cost(user_id, request_text, input_tokens, output_tokens, cost_usd):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "INSERT INTO cost_log (ts,user_id,request_text,input_tokens,output_tokens,cost_usd) VALUES (?,?,?,?,?,?)",
            (ts, user_id, request_text[:200], input_tokens, output_tokens, cost_usd)
        )

def get_monthly_cost():
    month = datetime.utcnow().strftime("%Y-%m")
    with _conn() as c:
        row = c.execute(
            "SELECT SUM(cost_usd) as total, SUM(input_tokens) as inp, SUM(output_tokens) as out "
            "FROM cost_log WHERE ts LIKE ?", (f"{month}%",)
        ).fetchone()
    return dict(row) if row else {"total":0,"inp":0,"out":0}

def get_cost_history(limit=50):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM cost_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

# o4-mini の概算料金 (2025年時点)
# Input: $1.10 / 1M tokens, Output: $4.40 / 1M tokens
def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * 1.10 + output_tokens * 4.40) / 1_000_000

init_db()
