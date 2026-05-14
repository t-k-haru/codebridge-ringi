"""
生成されたコードを安全に実行するサンドボックスモジュール。
subprocess + タイムアウトで隔離実行し、stdout/stderr を返す。
"""
import subprocess
import tempfile
import os
import shutil
from pathlib import Path

TARGET_PATH = Path(__file__).parent.parent / "target_app" / "main.py"
BACKUP_PATH = Path(__file__).parent.parent / "target_app" / "main.backup.py"

BLOCKED_PATTERNS = [
    "os.system", "subprocess", "__import__('os')",
    "shutil.rmtree", "open('/etc", "open('/proc",
    "socket.connect", "urllib.request.urlopen",
]

TIMEOUT_SECONDS = 10


def execute_code(code: str) -> tuple[str, str]:
    """
    コードを一時ファイルに書き込み、subprocess で実行。
    (stdout, stderr) のタプルを返す。
    """
    # 安全性チェック
    safety_error = _check_safety(code)
    if safety_error:
        return "", f"[安全性チェック失敗] {safety_error}"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "SANDBOX": "1"},  # サンドボックスフラグ
        )
        return result.stdout.strip(), result.stderr.strip()

    except subprocess.TimeoutExpired:
        return "", f"[タイムアウト] {TIMEOUT_SECONDS}秒以内に完了しませんでした"

    except Exception as e:
        return "", f"[実行エラー] {str(e)}"

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def read_target_code() -> str:
    """ターゲットアプリのコードを読み込む。"""
    if TARGET_PATH.exists():
        return TARGET_PATH.read_text(encoding="utf-8")
    return _default_target_code()


def apply_code(new_code: str) -> None:
    """
    バックアップを取得した上で、ターゲットアプリを新しいコードに差し替える。
    """
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)

    # バックアップ
    if TARGET_PATH.exists():
        shutil.copy2(TARGET_PATH, BACKUP_PATH)

    # 適用
    TARGET_PATH.write_text(new_code, encoding="utf-8")


def _check_safety(code: str) -> str:
    """危険なパターンが含まれていればエラーメッセージを返す。"""
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return f"禁止パターンが検出されました: `{pattern}`"
    return ""


def _default_target_code() -> str:
    """デモ用のデフォルトターゲットコード（Flask アプリ）。"""
    return '''from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return """
    <html>
    <head><title>サンプル会社</title></head>
    <body>
      <h1>サンプル株式会社</h1>
      <p>ようこそ。私たちは最高のサービスを提供します。</p>
      <nav>
        <a href="/">ホーム</a>
      </nav>
    </body>
    </html>
    """

@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "version": "1.0.0"})

if __name__ == "__main__":
    # サンドボックスモードでは起動せず構文チェックのみ
    import os
    if not os.environ.get("SANDBOX"):
        app.run(debug=True, port=5000)
    else:
        print("構文チェックOK: Flaskアプリが正常にインポートできました")
        print(f"定義済みルート: {[str(r) for r in app.url_map.iter_rules()]}")
'''
