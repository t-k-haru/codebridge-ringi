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
CREATE TABLE IF NOT EXISTS positions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT UNIQUE NOT NULL,
    rank      INTEGER NOT NULL,
    is_system INTEGER NOT NULL DEFAULT 0
);
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
    # positions 初期データ（冪等）
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO positions (id,name,rank,is_system) VALUES (1,'管理者',1,1)")
        c.execute("INSERT OR IGNORE INTO positions (id,name,rank,is_system) VALUES (2,'マネージャー',2,0)")
        c.execute("INSERT OR IGNORE INTO positions (id,name,rank,is_system) VALUES (3,'一般',3,0)")
    # users に position_id を追加（ADD COLUMN は IF NOT EXISTS 未サポート → try/except）
    try:
        with _conn() as c:
            c.execute("ALTER TABLE users ADD COLUMN position_id INTEGER DEFAULT NULL")
    except Exception:
        pass
    # 既存ユーザーの position_id を role から移行（NULL のもののみ）
    with _conn() as c:
        c.execute("UPDATE users SET position_id=1 WHERE role='admin'   AND position_id IS NULL")
        c.execute("UPDATE users SET position_id=2 WHERE role='manager' AND position_id IS NULL")
        c.execute("UPDATE users SET position_id=3 WHERE role='staff'   AND position_id IS NULL")
    # 固定ユーザーのシード
    _role_to_pid = {"admin": 1, "manager": 2, "staff": 3}
    with _conn() as c:
        for u in FIXED_USERS:
            exists = c.execute("SELECT 1 FROM users WHERE email=?", (u["email"],)).fetchone()
            if not exists:
                ts = datetime.utcnow().isoformat()
                pid = _role_to_pid.get(u["role"], 3)
                c.execute(
                    "INSERT INTO users (name,email,pw_hash,role,created,position_id) VALUES (?,?,?,?,?,?)",
                    (u["name"], u["email"], _hash(u["password"]), u["role"], ts, pid),
                )


def login(email: str, password: str):
    with _conn() as c:
        row = c.execute(
            """SELECT u.*, p.name AS position_name, p.rank AS position_rank
               FROM users u
               LEFT JOIN positions p ON u.position_id = p.id
               WHERE u.email=? AND u.active=1""",
            (email,),
        ).fetchone()
    if row and row["pw_hash"] == _hash(password):
        return dict(row)
    return None


def list_approvers():
    with _conn() as c:
        rows = c.execute(
            """SELECT u.id, u.name, p.name AS role, p.rank AS position_rank
               FROM users u
               JOIN positions p ON u.position_id = p.id
               WHERE p.rank < (SELECT MAX(rank) FROM positions)
               AND u.active=1
               ORDER BY p.rank, u.id"""
        ).fetchall()
    return [dict(r) for r in rows]


def list_users():
    with _conn() as c:
        rows = c.execute(
            """SELECT u.id, u.name, u.email, u.role, u.active, u.created,
                      u.position_id, p.name AS position_name, p.rank AS position_rank
               FROM users u
               LEFT JOIN positions p ON u.position_id = p.id
               ORDER BY u.id"""
        ).fetchall()
    return [dict(r) for r in rows]


def update_user_role(user_id: int, role: str):
    with _conn() as c:
        c.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))


def update_user_position(user_id: int, position_id: int):
    with _conn() as c:
        c.execute("UPDATE users SET position_id=? WHERE id=?", (position_id, user_id))


def toggle_user_active(user_id: int, active: bool):
    with _conn() as c:
        c.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))


def reset_password(user_id: int) -> str:
    import secrets as sec, string
    chars = string.ascii_letters + string.digits
    temp_pw = "".join(sec.choice(chars) for _ in range(10))
    with _conn() as c:
        c.execute("UPDATE users SET pw_hash=? WHERE id=?", (_hash(temp_pw), user_id))
    return temp_pw


def change_password(user_id: int, new_password: str):
    with _conn() as c:
        c.execute("UPDATE users SET pw_hash=? WHERE id=?", (_hash(new_password), user_id))


def list_users_by_role(role: str) -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, name FROM users WHERE role=? AND active=1 ORDER BY id", (role,)
        ).fetchall()
    return [dict(r) for r in rows]


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


def update_request_extension_data(request_id: int, new_ext: dict, regen_comment: str = None):
    """extension_data を上書きし、再生成履歴を approver_comment に追記する（status は変更しない）"""
    with _conn() as c:
        if regen_comment:
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            row = c.execute("SELECT approver_comment FROM requests WHERE id=?", (request_id,)).fetchone()
            prev = (row["approver_comment"] or "").strip() if row else ""
            entry = f"[{ts}] 再生成指示: {regen_comment}"
            new_comment = f"{prev}\n{entry}" if prev else entry
            c.execute(
                "UPDATE requests SET extension_data=?, approver_comment=? WHERE id=?",
                (json.dumps(new_ext), new_comment, request_id),
            )
        else:
            c.execute(
                "UPDATE requests SET extension_data=? WHERE id=?",
                (json.dumps(new_ext), request_id),
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
                f"""SELECT u.id, u.name FROM users u
                    JOIN positions p ON u.position_id = p.id
                    WHERE p.rank < (SELECT MAX(rank) FROM positions)
                    AND u.id IN ({ph})""",
                list(user_ids),
            ).fetchall()
        else:
            approvers = c.execute(
                """SELECT u.id, u.name FROM users u
                   JOIN positions p ON u.position_id = p.id
                   WHERE p.rank < (SELECT MAX(rank) FROM positions)"""
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


def log_to_csv() -> str:
    rows = get_activity_log(10000)
    lines = ["id,timestamp,user,action,detail,cost_usd"]
    for r in rows:
        detail = str(r.get("detail", "")).replace(",", "，").replace("\n", " ")
        lines.append(f"{r['id']},{r['ts']},{r['user_name']},{r['action']},{detail},{r['cost_usd']:.6f}")
    return "\n".join(lines)


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


# ── 役職管理 ──────────────────────────────────────────────────────────────

def list_positions() -> list:
    with _conn() as c:
        rows = c.execute("SELECT * FROM positions ORDER BY rank").fetchall()
    return [dict(r) for r in rows]


def create_position(name: str, rank: int = None) -> int:
    with _conn() as c:
        if rank is None:
            row = c.execute("SELECT COALESCE(MAX(rank), 0) FROM positions").fetchone()
            rank = row[0] + 1
        cur = c.execute(
            "INSERT INTO positions (name, rank, is_system) VALUES (?, ?, 0)", (name, rank)
        )
        return cur.lastrowid


def update_position(pid: int, name: str, rank: int):
    with _conn() as c:
        pos = c.execute("SELECT * FROM positions WHERE id=?", (pid,)).fetchone()
        if not pos:
            raise ValueError("役職が見つかりません")
        if pos["is_system"]:
            raise ValueError("システム既定の役職は変更できません")
        if rank == 1:
            raise ValueError("順位1は管理者専用です")
        c.execute("UPDATE positions SET name=?, rank=? WHERE id=?", (name, rank, pid))


def reorder_positions(ordered_ids: list) -> None:
    with _conn() as c:
        admin_pos = c.execute(
            "SELECT id FROM positions WHERE is_system=1 ORDER BY rank LIMIT 1"
        ).fetchone()
        if admin_pos and ordered_ids and ordered_ids[0] != admin_pos["id"]:
            raise ValueError("管理者役職は常に先頭である必要があります")
        for i, pid in enumerate(ordered_ids, 1):
            c.execute("UPDATE positions SET rank=? WHERE id=?", (i, pid))


def delete_position(pid: int):
    with _conn() as c:
        pos = c.execute("SELECT * FROM positions WHERE id=?", (pid,)).fetchone()
        if not pos:
            raise ValueError("役職が見つかりません")
        if pos["is_system"]:
            raise ValueError("システム既定の役職は削除できません")
        user_count = c.execute(
            "SELECT COUNT(*) FROM users WHERE position_id=?", (pid,)
        ).fetchone()[0]
        if user_count > 0:
            raise ValueError("ユーザーが存在する役職は削除できません")
        c.execute("DELETE FROM positions WHERE id=?", (pid,))


# ── 可視性・権限ヘルパー ──────────────────────────────────────────────────

def get_visible_user_ids(user_id: int) -> list:
    """自分の rank 以上の rank を持つ全ユーザー ID を返す（自分含む）。
    rank=1(admin)→全員, rank=2→rank>=2, rank=3→rank>=3"""
    with _conn() as c:
        row = c.execute(
            "SELECT p.rank FROM users u JOIN positions p ON u.position_id=p.id WHERE u.id=?",
            (user_id,),
        ).fetchone()
        if not row:
            return [user_id]
        rows = c.execute(
            "SELECT u.id FROM users u JOIN positions p ON u.position_id=p.id WHERE p.rank >= ?",
            (row["rank"],),
        ).fetchall()
    return [r["id"] for r in rows]


def user_can_approve(user_id: int) -> bool:
    """rank < max_rank なら承認者になれる（最低ランク以外）"""
    with _conn() as c:
        row = c.execute(
            """SELECT p.rank, (SELECT MAX(rank) FROM positions) AS max_rank
               FROM users u JOIN positions p ON u.position_id=p.id
               WHERE u.id=?""",
            (user_id,),
        ).fetchone()
    if not row:
        return False
    return row["rank"] < row["max_rank"]


init_db()
