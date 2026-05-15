# -*- coding: utf-8 -*-
"""
HTMLファイルを対象に修正を行うサンドボックス。
target_app/demo_local.html（汎用デモのCodeBridge専用コピー）を修正対象とする。
元の demo.html（shift.nobushi.jpのオリジナル）には一切触れない。
shift.nobushi.jp 本番サーバーにも一切接触しない。
"""
import subprocess
import tempfile
import os
import shutil
from pathlib import Path

TARGET_PATH = Path(__file__).parent.parent / "target_app" / "demo_local.html"
BACKUP_PATH = Path(__file__).parent.parent / "target_app" / "demo_local.backup.html"

TIMEOUT_SECONDS = 15

BLOCKED_PATTERNS = [
    "document.cookie",
    "localStorage.clear",
    "window.location='http",
    "fetch('http://",
]


def execute_code(html: str) -> tuple[str, str]:
    """
    HTMLをテンポラリファイルに書き出し、
    別のPythonプロセスでUTF-8として読み込んで検証する。
    """
    safety_error = _check_safety(html)
    if safety_error:
        return "", f"[安全性チェック失敗] {safety_error}"

    # HTMLをUTF-8のテンポラリファイルに書く
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(html)
        html_path = fh.name

    # 検証スクリプト（ASCII only）
    validation_script = f'''# -*- coding: utf-8 -*-
import sys
from html.parser import HTMLParser

html_path = {repr(html_path)}

with open(html_path, encoding="utf-8") as f:
    content = f.read()

void_tags = {{"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}}

class Validator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
    def handle_starttag(self, tag, attrs):
        if tag not in void_tags:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag not in void_tags and self.stack and self.stack[-1] == tag:
            self.stack.pop()

try:
    v = Validator()
    v.feed(content)
    print("HTML validation OK")
    print(f"  chars: {{len(content):,}}")
    print(f"  lines: {{content.count(chr(10)):,}}")
    has_html  = "<html"  in content.lower()
    has_body  = "<body"  in content.lower()
    has_title = "<title" in content.lower()
    print(f"  html tag: {{has_html}}, body: {{has_body}}, title: {{has_title}}")
except Exception as e:
    print(f"ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
'''

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as fp:
        fp.write(validation_script)
        py_path = fp.name

    try:
        result = subprocess.run(
            ["python3", py_path],
            capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", f"[タイムアウト] {TIMEOUT_SECONDS}秒以内に完了しませんでした"
    except Exception as e:
        return "", f"[実行エラー] {str(e)}"
    finally:
        for p in [html_path, py_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


def read_target_code() -> str:
    """CodeBridge専用のローカルデモHTMLを読み込む。"""
    if TARGET_PATH.exists():
        return TARGET_PATH.read_text(encoding="utf-8")
    return "<html><body><h1>demo_local.html が見つかりません</h1></body></html>"


def apply_code(new_code: str) -> None:
    """バックアップ取得後、ローカルデモHTMLを差し替える。"""
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TARGET_PATH.exists():
        shutil.copy2(TARGET_PATH, BACKUP_PATH)
    TARGET_PATH.write_text(new_code, encoding="utf-8")


def _check_safety(code: str) -> str:
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return f"禁止パターンが検出されました: `{pattern}`"
    return ""
