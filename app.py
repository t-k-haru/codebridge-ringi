import streamlit as st
import os, time, difflib
from datetime import datetime
from dotenv import load_dotenv
from core.orchestrator import run_pipeline, TaskResult
from core.sandbox import read_target_code, apply_code

load_dotenv()

T = {
    "ja": {
        "app_name": "CodeBridge",
        "mode_request": "リクエスト", "mode_engineer": "エンジニア", "mode_settings": "設定",
        "system_label": "対象システム", "system_coming": "近日公開",
        "theme_light": "ライト", "theme_dark": "ダーク", "lang": "EN",
        "request_title": "変更をリクエスト",
        "request_sub": "変えたいことを日本語で伝えるだけで、AIがコードに変換します。",
        "instruction_label": "指示内容",
        "instruction_ph": "例：\n・シフト表のヘッダー背景色を変えたい\n・KPIカードの数字フォントを大きくしたい\n・テーブル行ホバー時にハイライトを追加したい",
        "priority_label": "重要度",
        "priority_low": "低", "priority_mid": "中", "priority_high": "高", "priority_urgent": "緊急",
        "comment_label": "エンジニアへのコメント（任意）",
        "comment_ph": "補足情報や要望があれば記入してください",
        "submit": "AIに送信",
        "submit_ok": "コードを生成しました",
        "submit_ok_sub": "エンジニアが確認中です。承認後に本番環境へ反映されます。",
        "submit_warn": "エンジニアの確認が必要です",
        "submit_warn_sub": "AIは対応を試みましたが、一部に課題があります。",
        "submit_empty": "指示内容を入力してください",
        "deployed_ok": "本番環境への反映が完了しました", "deployed_at": "反映日時",
        "step1": "指示を解析しています", "step2": "コードを生成しています",
        "step3": "サンドボックスで検証しています", "step4": "AIが結果を確認しています",
        "step5": "レポートを作成しています",
        "eng_title": "エンジニアレビュー",
        "eng_sub": "AIが生成した変更内容を確認し、承認または差し戻しを行います。",
        "eng_password": "パスワード", "eng_password_ph": "エンジニア専用",
        "eng_wrong_pw": "パスワードが違います",
        "eng_no_req": "リクエスト画面から指示を送ると、ここにレビュー内容が表示されます",
        "eng_pw_needed": "サイドバーからパスワードを入力してください",
        "sandbox_label": "サンドボックス", "test_ok": "テスト成功", "test_fail": "テスト失敗",
        "debug_label": "デバッグ試行", "lines_label": "変更行数", "times": "回", "lines": "行",
        "user_req": "ユーザーからの指示", "priority_badge": "重要度",
        "eng_comment": "エンジニアへのコメント", "ai_report": "AIレポート",
        "code_diff": "コード変更内容", "tab_diff": "差分", "tab_before": "変更前", "tab_after": "変更後",
        "log_label": "実行ログを確認", "log_none": "出力なし", "decision": "判断",
        "approve_title": "承認してデプロイ",
        "approve_sub": "バックアップを取得した後、本番環境に反映します",
        "approve_btn": "承認", "approve_done": "デプロイが完了しました",
        "reject_title": "差し戻して再生成",
        "reject_sub": "修正コメントを添えてAIに再依頼します",
        "reject_ph": "例：ボタンの色を青ではなく緑にしてください",
        "regen_btn": "再生成", "regen_warn": "修正コメントを入力してください",
        "regen_spin": "再生成しています...",
        "settings_title": "設定", "settings_sub": "CodeBridgeの動作をカスタマイズします。",
        "sys_info_title": "システム情報", "sys_url": "デモURL",
        "sys_source": "ソースファイル", "sys_path": "ファイルパス",
        "theme_title": "外観", "lang_title": "言語",
        "notif_title": "通知・オプション",
        "notif_auto": "承認後に自動でデプロイ通知を表示",
        "notif_history": "リクエスト履歴を保持する件数",
        "history_label": "最近のリクエスト",
    },
    "en": {
        "app_name": "CodeBridge",
        "mode_request": "Request", "mode_engineer": "Engineer", "mode_settings": "Settings",
        "system_label": "Target System", "system_coming": "Coming Soon",
        "theme_light": "Light", "theme_dark": "Dark", "lang": "JA",
        "request_title": "Request Changes",
        "request_sub": "Describe what you want to change. AI will convert it to code.",
        "instruction_label": "Instructions",
        "instruction_ph": "e.g.:\n· Change the header background color\n· Make the KPI numbers larger\n· Add hover highlight to table rows",
        "priority_label": "Priority",
        "priority_low": "Low", "priority_mid": "Medium", "priority_high": "High", "priority_urgent": "Urgent",
        "comment_label": "Comment to Engineer (optional)",
        "comment_ph": "Add any supplementary notes here",
        "submit": "Send to AI",
        "submit_ok": "Code generated",
        "submit_ok_sub": "An engineer is reviewing. Changes will be applied after approval.",
        "submit_warn": "Engineer review required",
        "submit_warn_sub": "AI attempted the task but some issues remain.",
        "submit_empty": "Please enter instructions",
        "deployed_ok": "Successfully deployed to production", "deployed_at": "Deployed at",
        "step1": "Analyzing instructions", "step2": "Generating code",
        "step3": "Validating in sandbox", "step4": "AI verifying results",
        "step5": "Creating report",
        "eng_title": "Engineer Review",
        "eng_sub": "Review AI-generated changes and approve or reject.",
        "eng_password": "Password", "eng_password_ph": "Engineer only",
        "eng_wrong_pw": "Incorrect password",
        "eng_no_req": "Send a request to see review content here",
        "eng_pw_needed": "Enter password in the sidebar",
        "sandbox_label": "Sandbox", "test_ok": "Test Passed", "test_fail": "Test Failed",
        "debug_label": "Debug Attempts", "lines_label": "Lines Changed", "times": "times", "lines": "lines",
        "user_req": "User Instructions", "priority_badge": "Priority",
        "eng_comment": "Comment to Engineer", "ai_report": "AI Report",
        "code_diff": "Code Changes", "tab_diff": "Diff", "tab_before": "Before", "tab_after": "After",
        "log_label": "View Execution Log", "log_none": "No output", "decision": "Decision",
        "approve_title": "Approve & Deploy",
        "approve_sub": "A backup will be taken before deploying to production",
        "approve_btn": "Approve", "approve_done": "Deploy complete",
        "reject_title": "Reject & Regenerate",
        "reject_sub": "Send correction comments and ask AI to regenerate",
        "reject_ph": "e.g.: Make the button green instead of blue",
        "regen_btn": "Regenerate", "regen_warn": "Please enter correction comments",
        "regen_spin": "Regenerating...",
        "settings_title": "Settings", "settings_sub": "Customize CodeBridge behavior.",
        "sys_info_title": "System Information", "sys_url": "Demo URL",
        "sys_source": "Source File", "sys_path": "File Path",
        "theme_title": "Appearance", "lang_title": "Language",
        "notif_title": "Notifications & Options",
        "notif_auto": "Show deploy notification after approval",
        "notif_history": "Number of recent requests to keep",
        "history_label": "Recent Requests",
    }
}

SYSTEMS = {
    "shift_generic": {
        "name_ja": "シフト管理 / 汎用デモ", "name_en": "Shift Management / Generic Demo",
        "url": "http://shift.nobushi.jp/demo-generic/",
        "source": "target_app/demo.html", "path": "/target_app/demo.html", "active": True,
    },
    "shift_food": {
        "name_ja": "シフト管理 / 飲食", "name_en": "Shift Management / F&B",
        "url": "http://shift.nobushi.jp/demo/",
        "source": "target_app/demo_food.html", "path": "/target_app/demo_food.html", "active": False,
    },
    "shift_care": {
        "name_ja": "シフト管理 / 介護医療", "name_en": "Shift Management / Healthcare",
        "url": "http://shift.nobushi.jp/demo-care.php",
        "source": "target_app/demo_care.html", "path": "/target_app/demo_care.html", "active": False,
    },
}

PRIORITY_KEYS = ["low", "mid", "high", "urgent"]

def _esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _build_diff_html(original, new):
    diff = difflib.unified_diff(original.splitlines(), new.splitlines(), lineterm="", n=3)
    lines = []
    for line in diff:
        if line.startswith(("+++","---","@@")): lines.append(f"<span class='d-hdr'>{_esc(line)}</span>")
        elif line.startswith("+"): lines.append(f"<span class='d-add'>{_esc(line)}</span>")
        elif line.startswith("-"): lines.append(f"<span class='d-del'>{_esc(line)}</span>")
        else: lines.append(f"<span class='d-ctx'>{_esc(line)}</span>")
    return "\n".join(lines) if lines else "<span class='d-ctx'>変更なし / No changes</span>"

st.set_page_config(page_title="CodeBridge", layout="wide", initial_sidebar_state="expanded")

defaults = {
    "mode": "request", "theme": "light", "lang": "ja",
    "result": None, "deployed": False, "engineer_auth": False,
    "history": [], "selected_system": "shift_generic",
    "priority": "mid", "notif_auto": True, "history_limit": 10,
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

th = st.session_state.theme
lg = st.session_state.lang
t  = T[lg]
is_dark = th == "dark"

css_vars = f"""
:root {{
  --bg:         {'#1c1c1e' if is_dark else '#f2f2f7'};
  --bg2:        {'#2c2c2e' if is_dark else '#e5e5ea'};
  --surface:    {'rgba(44,44,46,0.92)' if is_dark else 'rgba(255,255,255,0.92)'};
  --surface2:   {'rgba(58,58,60,0.95)' if is_dark else 'rgba(242,242,247,0.98)'};
  --glass-border: {'rgba(255,255,255,0.10)' if is_dark else 'rgba(255,255,255,0.92)'};
  --border:     {'rgba(255,255,255,0.10)' if is_dark else 'rgba(0,0,0,0.08)'};
  --text:       {'#f5f5f7' if is_dark else '#1d1d1f'};
  --text2:      {'#aeaeb2' if is_dark else '#3d3d3f'};
  --text3:      {'#636366' if is_dark else '#8e8e93'};
  --input-bg:   {'rgba(58,58,60,0.98)' if is_dark else '#ffffff'};
  --input-border: {'rgba(255,255,255,0.22)' if is_dark else 'rgba(0,0,0,0.20)'};
  --input-focus: rgba(0,122,255,0.6);
  --accent: #007aff; --accent-hover: #0066d6;
  --green: #34c759; --amber: #ff9500; --red: #ff3b30;
  --shadow: {'0 2px 16px rgba(0,0,0,0.40)' if is_dark else '0 2px 12px rgba(0,0,0,0.07)'};
  --radius: 14px;
}}
"""

st.markdown(f"""<style>
{css_vars}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,[data-testid="stAppViewContainer"]{{
  background:var(--bg)!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',sans-serif;
  color:var(--text);-webkit-font-smoothing:antialiased;
}}
[data-testid="stSidebar"]{{
  background:var(--surface)!important;
  backdrop-filter:saturate(180%) blur(24px)!important;
  border-right:1px solid var(--border)!important;
}}
[data-testid="stSidebar"]>div:first-child{{padding:24px 18px 20px}}
.main .block-container{{padding:28px 36px 48px;max-width:1080px}}
h1{{font-size:26px;font-weight:600;letter-spacing:-.4px;color:var(--text)}}
p,.stMarkdown p{{font-size:15px;line-height:1.65;color:var(--text2)}}
.glass{{
  background:var(--surface);backdrop-filter:saturate(180%) blur(20px);
  -webkit-backdrop-filter:saturate(180%) blur(20px);
  border:1px solid var(--glass-border);border-radius:var(--radius);
  box-shadow:var(--shadow);padding:20px 22px;margin-bottom:14px;
}}
.glass-sm{{
  background:var(--surface);backdrop-filter:blur(16px);
  border:1px solid var(--glass-border);border-radius:11px;
  box-shadow:0 1px 6px rgba(0,0,0,{'0.25' if is_dark else '0.05'});
  padding:11px 14px;margin-bottom:8px;
}}
.accent-blue{{border-left:3px solid var(--accent)}}
.accent-green{{border-left:3px solid var(--green)}}
.accent-amber{{border-left:3px solid var(--amber)}}
.accent-red{{border-left:3px solid var(--red)}}
.metric-card{{
  background:var(--surface);backdrop-filter:blur(16px);
  border:1px solid var(--glass-border);border-radius:13px;
  box-shadow:var(--shadow);padding:16px 18px;text-align:center;
}}
.metric-label{{font-size:10.5px;font-weight:600;color:var(--text3);letter-spacing:.4px;text-transform:uppercase}}
.metric-value{{font-size:30px;font-weight:300;letter-spacing:-1px;color:var(--text);line-height:1.1;margin:5px 0 2px}}
.metric-unit{{font-size:12px;color:var(--text3)}}
.sec{{
  font-size:10.5px;font-weight:600;letter-spacing:.7px;text-transform:uppercase;
  color:var(--text3);margin:22px 0 9px;padding-bottom:7px;
  border-bottom:1px solid var(--border);
}}
.dot{{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px}}
.dot-green{{background:var(--green)}}.dot-red{{background:var(--red)}}
.badge{{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:11.5px;font-weight:600}}
.stButton>button{{
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  font-size:14px!important;font-weight:500!important;border-radius:10px!important;
  padding:9px 18px!important;transition:all .15s ease!important;color:var(--text)!important;
}}
.stButton>button[kind="primary"]{{
  background:var(--accent)!important;border:none!important;
  box-shadow:0 2px 8px rgba(0,122,255,.35)!important;color:#fff!important;
}}
.stButton>button[kind="primary"]:hover{{background:var(--accent-hover)!important;transform:translateY(-1px)!important}}
.stButton>button:not([kind="primary"]){{background:var(--surface2)!important;border:1px solid var(--border)!important}}
.stButton>button:not([kind="primary"]):hover{{background:var(--surface)!important;transform:translateY(-1px)!important}}
.stTextArea textarea,.stTextInput input{{
  background:var(--input-bg)!important;
  border:1.5px solid var(--input-border)!important;
  border-radius:10px!important;font-size:14px!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  color:var(--text)!important;
  box-shadow:0 1px 4px rgba(0,0,0,{'0.3' if is_dark else '0.06'})!important;
  padding:10px 12px!important;
}}
.stTextArea textarea::placeholder,.stTextInput input::placeholder{{color:var(--text3)!important;opacity:1!important}}
.stTextArea textarea:focus,.stTextInput input:focus{{
  border-color:var(--input-focus)!important;
  box-shadow:0 0 0 3px rgba(0,122,255,{'0.22' if is_dark else '0.12'})!important;outline:none!important;
}}
label,[data-testid="stWidgetLabel"]{{color:var(--text2)!important;font-size:13px!important;font-weight:500!important}}
.stProgress>div>div>div{{background:var(--accent)!important;border-radius:4px!important}}
.stProgress>div>div{{background:var(--border)!important;border-radius:4px!important}}
.stTabs [data-baseweb="tab-list"]{{
  background:var(--bg2)!important;border-radius:10px!important;
  padding:3px!important;gap:2px!important;border:none!important;
}}
.stTabs [data-baseweb="tab"]{{
  background:transparent!important;border-radius:8px!important;
  font-size:13px!important;font-weight:500!important;
  color:var(--text3)!important;padding:6px 13px!important;border:none!important;
}}
.stTabs [aria-selected="true"]{{
  background:var(--surface)!important;color:var(--text)!important;
  box-shadow:0 1px 4px rgba(0,0,0,{'0.3' if is_dark else '0.08'})!important;
}}
.stSelectbox>div>div{{background:var(--input-bg)!important;border:1.5px solid var(--input-border)!important;border-radius:10px!important;color:var(--text)!important}}
.stAlert{{border-radius:12px!important;font-size:14px!important;border:none!important}}
.d-add{{background:rgba(52,199,89,.12);color:{'#4cd964' if is_dark else '#1a7a35'};padding:1px 8px;border-left:2px solid var(--green);display:block;font-family:'SF Mono',monospace;font-size:12.5px}}
.d-del{{background:rgba(255,59,48,.10);color:{'#ff453a' if is_dark else '#c0392b'};padding:1px 8px;border-left:2px solid var(--red);display:block;font-family:'SF Mono',monospace;font-size:12.5px}}
.d-ctx{{color:var(--text3);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:12.5px}}
.d-hdr{{color:var(--accent);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:12px;font-weight:600}}
.sys-item{{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:10px;margin-bottom:4px}}
.sys-item.active{{background:rgba(0,122,255,{'0.18' if is_dark else '0.10'})}}
.sys-item.inactive{{opacity:.4}}
.sys-dot{{width:8px;height:8px;border-radius:50%;background:var(--accent);flex-shrink:0}}
.sys-dot.off{{background:var(--text3)}}
.sys-name{{font-size:13px;font-weight:500;color:var(--text)}}
.sys-tag{{font-size:10px;color:var(--text3);margin-left:auto;white-space:nowrap}}
[data-testid="stHorizontalBlock"]{{gap:10px}}
footer{{display:none}}#MainMenu{{visibility:hidden}}[data-testid="stDecoration"]{{display:none}}
hr{{border:none;border-top:1px solid var(--border);margin:14px 0}}
.stCheckbox>label{{color:var(--text2)!important;font-size:14px!important}}
::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}
</style>""", unsafe_allow_html=True)

# ─── サイドバー ───
with st.sidebar:
    c1, c2 = st.columns([3,1])
    with c1:
        st.markdown(f"<div style='font-size:17px;font-weight:700;letter-spacing:-.5px;color:var(--text)'>{t['app_name']}</div>", unsafe_allow_html=True)
    with c2:
        if st.button("◑" if is_dark else "◐", key="theme_toggle"):
            st.session_state.theme = "light" if is_dark else "dark"; st.rerun()
    lc, _ = st.columns([1,2])
    with lc:
        if st.button(t["lang"], key="lang_toggle"):
            st.session_state.lang = "en" if lg=="ja" else "ja"; st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # モード切り替え（3ボタンピル）
    mc1, mc2, mc3 = st.columns(3)
    modes = [("request",t["mode_request"]),("engineer",t["mode_engineer"]),("settings",t["mode_settings"])]
    for col, (k, label) in zip([mc1,mc2,mc3], modes):
        with col:
            if st.button(label, key=f"mode_{k}", use_container_width=True,
                         type="primary" if st.session_state.mode==k else "secondary"):
                st.session_state.mode = k; st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # システム選択
    st.markdown(f"<div class='sec' style='margin-top:4px'>{t['system_label']}</div>", unsafe_allow_html=True)
    for sys_key, sys in SYSTEMS.items():
        name = sys["name_ja"] if lg=="ja" else sys["name_en"]
        is_active_sys = sys["active"] and st.session_state.selected_system == sys_key
        tag = "" if sys["active"] else t["system_coming"]
        dot_cls = "sys-dot" if sys["active"] else "sys-dot off"
        item_cls = "sys-item active" if is_active_sys else ("sys-item" if sys["active"] else "sys-item inactive")
        st.markdown(
            f"<div class='{item_cls}'>"
            f"<div class='{dot_cls}'></div>"
            f"<span class='sys-name'>{name}</span>"
            f"<span class='sys-tag'>{tag}</span></div>",
            unsafe_allow_html=True,
        )
        if sys["active"]:
            if st.button(name, key=f"sys_{sys_key}", use_container_width=True):
                st.session_state.selected_system = sys_key; st.rerun()

    # エンジニアパスワード
    if st.session_state.mode == "engineer" and not st.session_state.engineer_auth:
        st.markdown("<hr>", unsafe_allow_html=True)
        pw = st.text_input(t["eng_password"], type="password", placeholder=t["eng_password_ph"])
        if pw == os.getenv("ENGINEER_PASSWORD","engineer123"):
            st.session_state.engineer_auth = True; st.rerun()
        elif pw:
            st.markdown(f"<div class='glass-sm accent-red' style='margin-top:6px'><span style='font-size:13px;color:var(--red)'>{t['eng_wrong_pw']}</span></div>", unsafe_allow_html=True)

    # 履歴
    if st.session_state.history:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<div class='sec' style='margin-top:4px'>{t['history_label']}</div>", unsafe_allow_html=True)
        for h in st.session_state.history[-st.session_state.history_limit:][::-1][:4]:
            st.markdown(f"<div class='glass-sm'><span style='font-size:11.5px;color:var(--text2);line-height:1.4'>{h}</span></div>", unsafe_allow_html=True)

# ─── リクエスト画面 ───
if st.session_state.mode == "request":
    st.markdown(f"<h1>{t['request_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:6px;margin-bottom:24px'>{t['request_sub']}</p>", unsafe_allow_html=True)

    with st.form("req_form"):
        instruction = st.text_area(t["instruction_label"], placeholder=t["instruction_ph"], height=160)

        # 重要度
        st.markdown(f"<div style='font-size:13px;font-weight:500;color:var(--text2);margin-bottom:4px'>{t['priority_label']}</div>", unsafe_allow_html=True)
        pc1,pc2,pc3,pc4 = st.columns(4)
        prio_cols = [pc1,pc2,pc3,pc4]
        prio_keys = ["low","mid","high","urgent"]
        for col, pk in zip(prio_cols, prio_keys):
            with col:
                if st.form_submit_button(t[f"priority_{pk}"], use_container_width=True):
                    st.session_state.priority = pk

        eng_comment = st.text_area(t["comment_label"], placeholder=t["comment_ph"], height=80)
        submitted = st.form_submit_button(t["submit"], use_container_width=True, type="primary")

    if submitted and instruction.strip():
        st.session_state.deployed = False; st.session_state.result = None
        bar_ph = st.empty(); msg_ph = st.empty()
        steps = [t["step1"],t["step2"],t["step3"],t["step4"],t["step5"]]
        bar = bar_ph.progress(0)
        for i, msg in enumerate(steps):
            msg_ph.markdown(f"<div class='glass-sm' style='margin-top:10px'><span style='font-size:13px;color:var(--text2)'>{msg}...</span></div>", unsafe_allow_html=True)
            bar.progress(int((i+1)/len(steps)*95)); time.sleep(0.35)
        full_instruction = instruction
        if eng_comment.strip():
            full_instruction += f"\n\n[{t['eng_comment']}]\n{eng_comment}"
        result = run_pipeline(full_instruction)
        result._priority = st.session_state.priority
        result._eng_comment = eng_comment
        st.session_state.result = result
        label = instruction[:26]+"…" if len(instruction)>26 else instruction
        st.session_state.history.append(f"{datetime.now().strftime('%H:%M')}  {label}")
        bar_ph.empty(); msg_ph.empty()
        if result.success:
            st.markdown(f"<div class='glass accent-green' style='margin-top:14px'><span style='font-size:14px;font-weight:600;color:var(--green)'>{t['submit_ok']}</span><br><span style='font-size:13px;color:var(--text2);margin-top:4px;display:block'>{t['submit_ok_sub']}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='glass accent-amber' style='margin-top:14px'><span style='font-size:14px;font-weight:600;color:var(--amber)'>{t['submit_warn']}</span><br><span style='font-size:13px;color:var(--text2);margin-top:4px;display:block'>{t['submit_warn_sub']}</span></div>", unsafe_allow_html=True)
    elif submitted:
        st.warning(t["submit_empty"])

    if st.session_state.deployed:
        st.markdown(f"<div class='glass accent-green' style='margin-top:14px'><span style='font-size:14px;font-weight:600;color:var(--green)'>{t['deployed_ok']}</span><br><span style='font-size:12px;color:var(--text3);margin-top:4px;display:block'>{t['deployed_at']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>", unsafe_allow_html=True)

# ─── エンジニア画面 ───
elif st.session_state.mode == "engineer":
    if not st.session_state.engineer_auth:
        st.markdown(f"<div class='glass' style='margin-top:40px;text-align:center;padding:40px'><span style='font-size:15px;color:var(--text2)'>{t['eng_pw_needed']}</span></div>", unsafe_allow_html=True); st.stop()
    result = st.session_state.result
    if result is None:
        st.markdown(f"<div class='glass' style='margin-top:40px;text-align:center;padding:40px'><span style='font-size:15px;color:var(--text2)'>{t['eng_no_req']}</span></div>", unsafe_allow_html=True); st.stop()

    st.markdown(f"<h1>{t['eng_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:6px;margin-bottom:24px'>{t['eng_sub']}</p>", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1:
        dot = "dot-green" if result.success else "dot-red"
        lbl = t["test_ok"] if result.success else t["test_fail"]
        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t['sandbox_label']}</div><div style='margin-top:10px'><span class='dot {dot}'></span><span style='font-size:14px;font-weight:500;color:var(--text)'>{lbl}</span></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t['debug_label']}</div><div class='metric-value'>{result.iterations}</div><div class='metric-unit'>{t['times']}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>{t['lines_label']}</div><div class='metric-value'>{result.changed_lines}</div><div class='metric-unit'>{t['lines']}</div></div>", unsafe_allow_html=True)

    prio = getattr(result, '_priority', 'mid')
    prio_label = t[f"priority_{prio}"]
    prio_c = {"low":"var(--green)","mid":"var(--accent)","high":"var(--amber)","urgent":"var(--red)"}[prio]
    st.markdown(f"<div style='margin:6px 0 14px'><span class='badge' style='background:{prio_c}22;color:{prio_c};border:1px solid {prio_c}55'>{t['priority_badge']}: {prio_label}</span></div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['user_req']}</p>", unsafe_allow_html=True)
    eng_comment_stored = getattr(result, '_eng_comment', '')
    instr_display = result.instruction.split(f"\n\n[{t['eng_comment']}]")[0] if eng_comment_stored else result.instruction
    st.markdown(f"<div class='glass accent-blue'><span style='font-size:14px;line-height:1.65;color:var(--text)'>{_esc(instr_display)}</span></div>", unsafe_allow_html=True)
    if eng_comment_stored:
        st.markdown(f"<div class='glass-sm accent-amber'><span style='font-size:11px;color:var(--text3)'>{t['eng_comment']}</span><br><span style='font-size:14px;color:var(--text2)'>{_esc(eng_comment_stored)}</span></div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['ai_report']}</p>", unsafe_allow_html=True)
    st.markdown(f"<div class='glass accent-amber'>{result.report}</div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['code_diff']}</p>", unsafe_allow_html=True)
    tab1,tab2,tab3 = st.tabs([t["tab_diff"],t["tab_before"],t["tab_after"]])
    with tab1:
        st.markdown(f"<div class='glass' style='padding:14px 16px;overflow-x:auto'>{_build_diff_html(result.original_code,result.new_code)}</div>", unsafe_allow_html=True)
    with tab2: st.code(result.original_code, language="html")
    with tab3: st.code(result.new_code, language="html")

    with st.expander(t["log_label"]):
        if result.test_output: st.code(result.test_output, language="bash")
        else: st.markdown(f"<span style='font-size:13px;color:var(--text3)'>{t['log_none']}</span>", unsafe_allow_html=True)
        if result.test_error: st.code(result.test_error, language="bash")

    st.markdown(f"<p class='sec'>{t['decision']}</p>", unsafe_allow_html=True)
    col_ok,col_ng = st.columns(2)
    with col_ok:
        st.markdown(f"<div class='glass' style='padding:18px 20px'><span style='font-size:14px;font-weight:600;color:var(--text)'>{t['approve_title']}</span><br><span style='font-size:12px;color:var(--text3);display:block;margin-top:4px;margin-bottom:12px'>{t['approve_sub']}</span>", unsafe_allow_html=True)
        if st.button(t["approve_btn"], use_container_width=True, type="primary", key="approve"):
            with st.spinner("..."): apply_code(result.new_code); time.sleep(1.0)
            st.session_state.deployed = True
            st.markdown(f"<div class='glass-sm accent-green' style='margin-top:8px'><span style='font-size:13px;color:var(--green);font-weight:600'>{t['approve_done']}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_ng:
        st.markdown(f"<div class='glass' style='padding:18px 20px'><span style='font-size:14px;font-weight:600;color:var(--text)'>{t['reject_title']}</span><br><span style='font-size:12px;color:var(--text3);display:block;margin-top:4px;margin-bottom:12px'>{t['reject_sub']}</span>", unsafe_allow_html=True)
        feedback = st.text_area(t["reject_ph"], height=88, label_visibility="collapsed", key="fb")
        if st.button(t["regen_btn"], use_container_width=True, key="regen"):
            if feedback.strip():
                with st.spinner(t["regen_spin"]):
                    new_result = run_pipeline(f"{result.instruction}\n\n[修正]\n{feedback}", result.original_code)
                st.session_state.result = new_result; st.rerun()
            else: st.warning(t["regen_warn"])
        st.markdown("</div>", unsafe_allow_html=True)

# ─── 設定画面 ───
elif st.session_state.mode == "settings":
    st.markdown(f"<h1>{t['settings_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:6px;margin-bottom:24px'>{t['settings_sub']}</p>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['sys_info_title']}</p>", unsafe_allow_html=True)
    sys = SYSTEMS[st.session_state.selected_system]
    rows = [
        (t["sys_url"],    f'<a href="{sys["url"]}" target="_blank" style="color:var(--accent);text-decoration:none">{sys["url"]}</a>'),
        (t["sys_source"], f'<code style="font-size:12px;color:var(--text2);background:var(--bg2);padding:2px 6px;border-radius:4px">{sys["source"]}</code>'),
        (t["sys_path"],   f'<code style="font-size:12px;color:var(--text2);background:var(--bg2);padding:2px 6px;border-radius:4px">{sys["path"]}</code>'),
    ]
    rows_html = "".join(
        f"<div style='display:flex;align-items:center;padding:11px 0;border-bottom:1px solid var(--border);gap:16px'>"
        f"<span style='font-size:11px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:.4px;min-width:90px'>{lbl}</span>"
        f"<span style='font-size:13px;color:var(--text2)'>{val}</span></div>"
        for lbl, val in rows
    )
    st.markdown(f"<div class='glass' style='padding:0 18px'>{rows_html}</div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['theme_title']}</p>", unsafe_allow_html=True)
    tc1,tc2 = st.columns(2)
    with tc1:
        if st.button(t["theme_light"], key="set_light", use_container_width=True, type="primary" if not is_dark else "secondary"):
            st.session_state.theme = "light"; st.rerun()
    with tc2:
        if st.button(t["theme_dark"], key="set_dark", use_container_width=True, type="primary" if is_dark else "secondary"):
            st.session_state.theme = "dark"; st.rerun()

    st.markdown(f"<p class='sec'>{t['lang_title']}</p>", unsafe_allow_html=True)
    lc1,lc2 = st.columns(2)
    with lc1:
        if st.button("日本語", key="set_ja", use_container_width=True, type="primary" if lg=="ja" else "secondary"):
            st.session_state.lang = "ja"; st.rerun()
    with lc2:
        if st.button("English", key="set_en", use_container_width=True, type="primary" if lg=="en" else "secondary"):
            st.session_state.lang = "en"; st.rerun()

    st.markdown(f"<p class='sec'>{t['notif_title']}</p>", unsafe_allow_html=True)
    st.markdown("<div class='glass' style='padding:18px 20px'>", unsafe_allow_html=True)
    notif = st.checkbox(t["notif_auto"], value=st.session_state.notif_auto)
    st.session_state.notif_auto = notif
    st.markdown(f"<div style='margin-top:16px;margin-bottom:8px'><span style='font-size:13px;font-weight:500;color:var(--text2)'>{t['notif_history']}</span></div>", unsafe_allow_html=True)
    limit = st.slider("", 5, 50, st.session_state.history_limit, 5, label_visibility="collapsed")
    st.session_state.history_limit = limit
    st.markdown("</div>", unsafe_allow_html=True)
