"""
シフト管理システム — デモアプリ
このファイルがCodeBridgeのAIによる変更対象です。
既存のデータベースには一切接触せず、表示ロジックのみを変更します。
"""
from flask import Flask, jsonify, render_template_string
from datetime import date, timedelta

app = Flask(__name__)

STAFF = [
    {"id": 1, "name": "田中 颯",   "dept": "フロント",    "color": "#007aff"},
    {"id": 2, "name": "鈴木 葵",   "dept": "キッチン",    "color": "#34c759"},
    {"id": 3, "name": "佐藤 陽菜", "dept": "フロント",    "color": "#007aff"},
    {"id": 4, "name": "山田 蓮",   "dept": "キッチン",    "color": "#34c759"},
    {"id": 5, "name": "中村 結衣", "dept": "マネージャー", "color": "#ff9500"},
]

def _generate_shifts():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    patterns = [
        (1,"09:00","17:00"),(2,"11:00","20:00"),(3,"17:00","22:00"),
        (1,"10:00","18:00"),(4,"09:00","15:00"),(5,"09:00","18:00"),
        (2,"12:00","21:00"),(3,"09:00","14:00"),(1,"16:00","22:00"),
        (4,"10:00","19:00"),(5,"10:00","17:00"),(2,"09:00","15:00"),
        (3,"13:00","22:00"),(1,"09:00","18:00"),(4,"16:00","22:00"),
        (5,"09:00","18:00"),(2,"10:00","20:00"),
    ]
    return [{"staff_id":sid,"date":str(monday+timedelta(days=i%7)),"start":s,"end":e}
            for i,(sid,s,e) in enumerate(patterns)]

SHIFTS = _generate_shifts()
DAYS_JP = ["月","火","水","木","金","土","日"]

TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>シフト管理</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;background:#f2f2f7;color:#1d1d1f;-webkit-font-smoothing:antialiased}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px}
header{margin-bottom:28px}
header h1{font-size:24px;font-weight:600;letter-spacing:-.4px}
header p{font-size:14px;color:#8e8e93;margin-top:4px}
.card{background:rgba(255,255,255,.85);border:1px solid rgba(255,255,255,.9);border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,.06);padding:20px 22px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{font-size:11px;font-weight:600;color:#8e8e93;letter-spacing:.4px;text-transform:uppercase;padding:8px 12px;text-align:left;border-bottom:1px solid rgba(0,0,0,.06)}
td{padding:10px 12px;border-bottom:1px solid rgba(0,0,0,.04)}
tr:last-child td{border-bottom:none}
.dept{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:500;padding:3px 9px;border-radius:20px}
.dept-front{background:rgba(0,122,255,.10);color:#0055b3}
.dept-kitchen{background:rgba(52,199,89,.10);color:#1a7a35}
.dept-mgr{background:rgba(255,149,0,.10);color:#7a4a00}
.shift-block{display:inline-block;background:rgba(0,122,255,.08);color:#0055b3;border-radius:6px;padding:2px 8px;font-size:12px}
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.stat{background:rgba(255,255,255,.85);border:1px solid rgba(255,255,255,.9);border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,.05);padding:16px 18px;text-align:center}
.stat-label{font-size:11px;font-weight:500;color:#8e8e93;text-transform:uppercase;letter-spacing:.3px}
.stat-value{font-size:28px;font-weight:300;letter-spacing:-1px;color:#1d1d1f;margin-top:4px}
.section-title{font-size:11px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;color:#8e8e93;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid rgba(0,0,0,.06)}
</style>
</head>
<body>
<div class="wrap">
  <header><h1>シフト管理</h1><p>今週のシフト一覧 — CodeBridgeデモ用</p></header>
  <div class="stat-grid">
    <div class="stat"><div class="stat-label">スタッフ数</div><div class="stat-value">{{ staff_count }}</div></div>
    <div class="stat"><div class="stat-label">今週のシフト</div><div class="stat-value">{{ shift_count }}</div></div>
    <div class="stat"><div class="stat-label">部署数</div><div class="stat-value">{{ dept_count }}</div></div>
  </div>
  <div class="card">
    <p class="section-title">スタッフ一覧</p>
    <table>
      <thead><tr><th>名前</th><th>部署</th><th>今週のシフト数</th></tr></thead>
      <tbody>
      {% for s in staff %}
        <tr>
          <td style="font-weight:500">{{ s.name }}</td>
          <td>{% if s.dept == 'フロント' %}<span class="dept dept-front">{{ s.dept }}</span>{% elif s.dept == 'キッチン' %}<span class="dept dept-kitchen">{{ s.dept }}</span>{% else %}<span class="dept dept-mgr">{{ s.dept }}</span>{% endif %}</td>
          <td>{{ s.shift_count }} 回</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="card">
    <p class="section-title">今週のシフト詳細</p>
    <table>
      <thead><tr><th>日付</th><th>曜日</th><th>スタッフ</th><th>時間</th></tr></thead>
      <tbody>
      {% for sh in shifts %}
        <tr>
          <td>{{ sh.date }}</td><td>{{ sh.day_jp }}曜</td>
          <td style="font-weight:500">{{ sh.staff_name }}</td>
          <td><span class="shift-block">{{ sh.start }} – {{ sh.end }}</span></td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
</body>
</html>"""

@app.route("/")
def index():
    staff_map = {s["id"]:s for s in STAFF}
    shifts_view = []
    for sh in sorted(SHIFTS, key=lambda x:(x["date"],x["start"])):
        s = staff_map[sh["staff_id"]]
        d = date.fromisoformat(sh["date"])
        shifts_view.append({**sh,"staff_name":s["name"],"day_jp":DAYS_JP[d.weekday()]})
    staff_view = [{**s,"shift_count":sum(1 for sh in SHIFTS if sh["staff_id"]==s["id"])} for s in STAFF]
    return render_template_string(TEMPLATE,staff=staff_view,shifts=shifts_view,
        staff_count=len(STAFF),shift_count=len(SHIFTS),dept_count=len(set(s["dept"] for s in STAFF)))

@app.route("/api/staff")
def api_staff():
    return jsonify(STAFF)

@app.route("/api/shifts")
def api_shifts():
    return jsonify(SHIFTS)

if __name__ == "__main__":
    import os
    if not os.environ.get("SANDBOX"):
        app.run(debug=True, port=5000)
    else:
        print("構文チェックOK: シフト管理デモが正常に読み込まれました")
        print(f"スタッフ数: {len(STAFF)}, シフト数: {len(SHIFTS)}")
