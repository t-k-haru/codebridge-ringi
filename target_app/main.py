from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return """
    <html>
    <head>
      <title>サンプル会社</title>
      <style>
        body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #333; }
        nav a { margin-right: 16px; color: #448aff; text-decoration: none; }
      </style>
    </head>
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
    import os
    if not os.environ.get("SANDBOX"):
        app.run(debug=True, port=5000)
    else:
        print("構文チェックOK: Flaskアプリが正常にインポートできました")
        print(f"定義済みルート: {[str(r) for r in app.url_map.iter_rules()]}")
