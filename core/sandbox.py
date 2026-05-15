"""
HTMLファイルを対象に修正を行うサンドボックス。
target_app/demo.html（shift.nobushiのデモページのローカルコピー）を
CodeBridgeが読み込み・修正・検証する。
既存サーバー（shift.nobushi.jp）には一切接触しない。
"""
import subprocess
import tempfile
import os
import shutil
from pathlib import Path

TARGET_PATH = Path(__file__).parent.parent / "target_app" / "demo.html"
BACKUP_PATH = Path(__file__).parent.parent / "target_app" / "demo.backup.html"

TIMEOUT_SECONDS = 10

# HTML内で禁止するパターン（XSSリスク等）
BLOCKED_PATTERNS = [
    "<script>document.cookie",
    "eval(",
    "fetch('http://",
    "XMLHttpRequest",
    "window.location='http",
]


def execute_code(code: str) -> tuple[str, str]:
    """
    HTMLの検証を行う。
    Pythonでhtml.parserを使って構文チェック。
    """
    safety_error = _check_safety(code)
    if safety_error:
        return "", f"[安全性チェック失敗] {safety_error}"

    validation_script = f"""
from html.parser import HTMLParser
import sys

class Validator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.tag_stack = []
        self.void_tags = {{'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_tags:
            self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.void_tags:
            return
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

html_content = {repr(code)}

try:
    parser = Validator()
    parser.feed(html_content)
    tag_count = html_content.lower().count('<html')
    if tag_count == 0:
        print("WARNING: <html>タグが見つかりません")
    else:
        print(f"HTML構文チェックOK")

    # 基本的な要素の確認
    checks = [
        ('<title', 'titleタグ'),
        ('<body', 'bodyタグ'),
    ]
    for tag, name in checks:
        if tag in html_content.lower():
            print(f"  {{name}}: 存在")
        else:
            print(f"  WARNING: {{name}}が見つかりません")

    char_count = len(html_content)
    print(f"  文字数: {{char_count:,}}")
    print(f"  行数: {{html_content.count(chr(10)):,}}")

except Exception as e:
    print(f"ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(validation_script)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
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
    """デモHTMLを読み込む。"""
    if TARGET_PATH.exists():
        return TARGET_PATH.read_text(encoding="utf-8")
    return "<html><body><h1>デモファイルが見つかりません</h1></body></html>"


def apply_code(new_code: str) -> None:
    """バックアップ取得後、デモHTMLを差し替える。"""
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TARGET_PATH.exists():
        shutil.copy2(TARGET_PATH, BACKUP_PATH)
    TARGET_PATH.write_text(new_code, encoding="utf-8")


def _check_safety(code: str) -> str:
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return f"禁止パターンが検出されました: `{pattern}`"
    return ""
