"""
CodeBridgeデモ用Flaskサーバー。
target_app/demo.html（shift.nobushiデモのローカルコピー）を配信する。
"""
from flask import Flask, send_file, jsonify
from pathlib import Path

app = Flask(__name__)
DEMO_HTML = Path(__file__).parent / "demo.html"


@app.route("/")
def index():
    if DEMO_HTML.exists():
        return send_file(DEMO_HTML, mimetype="text/html")
    return "<html><body><h1>demo.htmlが見つかりません</h1></body></html>", 404


@app.route("/health")
def health():
    return jsonify({"status": "ok", "demo": DEMO_HTML.exists()})


if __name__ == "__main__":
    import os
    if not os.environ.get("SANDBOX"):
        app.run(debug=True, port=5000)
    else:
        print("構文チェックOK")
        print(f"demo.html存在: {DEMO_HTML.exists()}")
