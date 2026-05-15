# -*- coding: utf-8 -*-
import streamlit as st
import os, time, difflib
from datetime import datetime
from dotenv import load_dotenv
from core.orchestrator import run_pipeline
from core.sandbox import read_target_code, apply_code

load_dotenv()

# ── i18n ──────────────────────────────────────────────────────────────────────
T = {
    "ja": {
        "app_name": "CodeBridge",
        "mode_request": "リクエスト", "mode_engineer": "エンジニア", "mode_settings": "設定",
        "system_label": "対象システム", "system_coming": "近日公開",
        "theme_light": "ライト", "theme_dark": "ダーク", "lang_toggle": "EN",
        "request_title": "変更をリクエスト",
        "request_sub": "変えたいことを日本語で伝えるだけで、AIがコードに変換します。",
        "instruction_label": "指示内容",
        "instruction_ph": "例：\n・シフト表のヘッダー色を変えたい\n・KPIの数字フォントを大きくしたい\n・テーブル行ホバー時にハイライトを追加したい",
        "priority_label": "重要度",
        "prio_low": "低", "prio_mid": "中", "prio_high": "高", "prio_urgent": "緊急",
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
        "step3": "サンドボックスで検証しています", "step4": "結果を確認しています",
        "step5": "レポートを作成しています",
        "eng_title": "エンジニアレビュー",
        "eng_sub": "AIが生成した変更内容を確認し、承認または差し戻しを行います。",
        "eng_pass": "パスワード", "eng_pass_ph": "エンジニア専用",
        "eng_wrong": "パスワードが違います",
        "eng_no_req": "リクエスト画面から指示を送ると、ここにレビュー内容が表示されます",
        "eng_need_pw": "サイドバーからパスワードを入力してください",
        "sandbox": "サンドボックス", "test_ok": "テスト成功", "test_fail": "テスト失敗",
        "debug": "デバッグ試行", "lines": "変更行数", "times": "回", "lines_u": "行",
        "user_req": "ユーザーからの指示", "prio_badge": "重要度",
        "eng_cmt": "エンジニアへのコメント", "ai_report": "AIレポート",
        "code_diff": "コード変更内容", "tab_diff": "差分", "tab_before": "変更前", "tab_after": "変更後",
        "log": "実行ログを確認", "log_none": "出力なし", "decision": "判断",
        "approve_title": "承認してデプロイ",
        "approve_sub": "バックアップを取得した後、本番環境に反映します",
        "approve_btn": "承認", "approve_done": "デプロイが完了しました",
        "reject_title": "差し戻して再生成",
        "reject_sub": "修正コメントを添えてAIに再依頼します",
        "reject_ph": "例：ボタンの色を青ではなく緑にしてください",
        "regen_btn": "再生成", "regen_warn": "修正コメントを入力してください",
        "settings_title": "設定", "settings_sub": "CodeBridgeの動作をカスタマイズします。",
        "sys_info": "システム情報", "sys_url": "デモURL",
        "sys_source": "ソースファイル", "sys_path": "ファイルパス",
        "theme_sec": "外観", "lang_sec": "言語",
        "notif_sec": "オプション", "notif_auto": "承認後にデプロイ通知を表示",
        "hist_limit": "履歴の保持件数",
        "history_label": "最近のリクエスト",
    },
    "en": {
        "app_name": "CodeBridge",
        "mode_request": "Request", "mode_engineer": "Engineer", "mode_settings": "Settings",
        "system_label": "Target System", "system_coming": "Coming Soon",
        "theme_light": "Light", "theme_dark": "Dark", "lang_toggle": "JA",
        "request_title": "Request Changes",
        "request_sub": "Describe what you want to change. AI will convert it to code.",
        "instruction_label": "Instructions",
        "instruction_ph": "e.g.:\n· Change the header background color\n· Make KPI numbers larger\n· Add row hover highlight to the table",
        "priority_label": "Priority",
        "prio_low": "Low", "prio_mid": "Medium", "prio_high": "High", "prio_urgent": "Urgent",
        "comment_label": "Comment to Engineer (optional)",
        "comment_ph": "Add any supplementary notes here",
        "submit": "Send to AI",
        "submit_ok": "Code generated",
        "submit_ok_sub": "An engineer is reviewing. Changes will be applied after approval.",
        "submit_warn": "Engineer review required",
        "submit_warn_sub": "AI attempted the task but some issues remain.",
        "submit_empty": "Please enter instructions",
        "deployed_ok": "Successfully deployed to production", "deployed_at": "Deployed at",
        "step1": "Analyzing", "step2": "Generating code",
        "step3": "Validating in sandbox", "step4": "Verifying results",
        "step5": "Creating report",
        "eng_title": "Engineer Review",
        "eng_sub": "Review AI-generated changes and approve or reject.",
        "eng_pass": "Password", "eng_pass_ph": "Engineer only",
        "eng_wrong": "Incorrect password",
        "eng_no_req": "Send a request to see review content here",
        "eng_need_pw": "Enter password in the sidebar",
        "sandbox": "Sandbox", "test_ok": "Test Passed", "test_fail": "Test Failed",
        "debug": "Debug Attempts", "lines": "Lines Changed", "times": "times", "lines_u": "lines",
        "user_req": "User Instructions", "prio_badge": "Priority",
        "eng_cmt": "Engineer Comment", "ai_report": "AI Report",
        "code_diff": "Code Changes", "tab_diff": "Diff", "tab_before": "Before", "tab_after": "After",
        "log": "View Execution Log", "log_none": "No output", "decision": "Decision",
        "approve_title": "Approve & Deploy",
        "approve_sub": "A backup will be taken before deploying",
        "approve_btn": "Approve", "approve_done": "Deploy complete",
        "reject_title": "Reject & Regenerate",
        "reject_sub": "Send correction comments and ask AI to regenerate",
        "reject_ph": "e.g.: Make the button green instead of blue",
        "regen_btn": "Regenerate", "regen_warn": "Please enter correction comments",
        "settings_title": "Settings", "settings_sub": "Customize CodeBridge.",
        "sys_info": "System Information", "sys_url": "Demo URL",
        "sys_source": "Source File", "sys_path": "File Path",
        "theme_sec": "Appearance", "lang_sec": "Language",
        "notif_sec": "Options", "notif_auto": "Show deploy notification after approval",
        "hist_limit": "History limit",
        "history_label": "Recent Requests",
    }
}

SYSTEMS = {
    "shift_generic": {
        "name_ja": "シフト管理 / 汎用デモ", "name_en": "Shift Mgmt / Generic",
        "url": "http://shift.nobushi.jp/demo-generic/",
        "source": "target_app/demo_local.html",
        "path": "/target_app/demo_local.html", "active": True,
    },
    "shift_food": {
        "name_ja": "シフト管理 / 飲食", "name_en": "Shift Mgmt / F&B",
        "url": "http://shift.nobushi.jp/demo/",
        "source": "target_app/demo_food.html",
        "path": "/target_app/demo_food.html", "active": False,
    },
    "shift_care": {
        "name_ja": "シフト管理 / 介護医療", "name_en": "Shift Mgmt / Healthcare",
        "url": "http://shift.nobushi.jp/demo-care.php",
        "source": "target_app/demo_care.html",
        "path": "/target_app/demo_care.html", "active": False,
    },
}

PRIO_KEYS = ["low","mid","high","urgent"]
PRIO_COLORS = {
    "low":    "#34c759",
    "mid":    "#1d1d1f",
    "high":   "#ff9500",
    "urgent": "#ff3b30",
}
PRIO_COLORS_DARK = {
    "low":    "#34c759",
    "mid":    "#f5f5f7",
    "high":   "#ff9f0a",
    "urgent": "#ff453a",
}

def _esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _diff_html(a, b):
    diff = difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=3)
    out = []
    for ln in diff:
        if ln.startswith(("+++","---","@@")): out.append(f"<span class='dh'>{_esc(ln)}</span>")
        elif ln.startswith("+"): out.append(f"<span class='da'>{_esc(ln)}</span>")
        elif ln.startswith("-"): out.append(f"<span class='dd'>{_esc(ln)}</span>")
        else: out.append(f"<span class='dc'>{_esc(ln)}</span>")
    return "\n".join(out) or "<span class='dc'>変更なし / No changes</span>"

st.set_page_config(page_title="CodeBridge", layout="wide", initial_sidebar_state="expanded")

# ── query_params でテーマ/言語を永続化 ─────────────────────────────────────────
qp = st.query_params
defaults = {
    "mode":"request","theme": qp.get("theme","light"),"lang": qp.get("lang","ja"),
    "result":None,"deployed":False,"engineer_auth":False,
    "history":[],"selected_system":"shift_generic",
    "priority":"mid","notif_auto":True,"history_limit":10,
}
for k,v in defaults.items():
    if k not in st.session_state: st.session_state[k]=v

th = st.session_state.theme
lg = st.session_state.lang
t  = T[lg]
D  = (th=="dark")
pc = PRIO_COLORS_DARK if D else PRIO_COLORS

# ── CSS ────────────────────────────────────────────────────────────────────────
BG  = "#1c1c1e" if D else "#f2f2f7"
BG2 = "#2c2c2e" if D else "#e5e5ea"
SFC = "rgba(44,44,46,0.93)" if D else "rgba(255,255,255,0.93)"
SFC2= "rgba(58,58,60,0.96)" if D else "rgba(242,242,247,0.98)"
GLB = "rgba(255,255,255,0.10)" if D else "rgba(255,255,255,0.93)"
BRD = "rgba(255,255,255,0.11)" if D else "rgba(0,0,0,0.09)"
TXT = "#f5f5f7" if D else "#1d1d1f"
TX2 = "#aeaeb2" if D else "#3d3d3f"
TX3 = "#636366" if D else "#8e8e93"
INB = "rgba(60,60,62,0.98)" if D else "#ffffff"
INR = "rgba(255,255,255,0.24)" if D else "rgba(0,0,0,0.22)"
SHD = "0 2px 16px rgba(0,0,0,0.42)" if D else "0 2px 12px rgba(0,0,0,0.07)"
PRIM= "#f5f5f7" if D else "#1d1d1f"   # primary button = white(dark) / black(light)
PTXT= "#1d1d1f" if D else "#f5f5f7"   # primary button text

st.markdown(f"""<style>
:root{{
  --bg:{BG};--bg2:{BG2};--sfc:{SFC};--sfc2:{SFC2};
  --glb:{GLB};--brd:{BRD};
  --txt:{TXT};--tx2:{TX2};--tx3:{TX3};
  --inb:{INB};--inr:{INR};--shd:{SHD};
  --prim:{PRIM};--ptxt:{PTXT};
  --grn:#34c759;--amb:#ff9500;--red:#ff3b30;
  --acc:#1d1d1f;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,[data-testid="stAppViewContainer"]{{
  background:var(--bg)!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',sans-serif;
  color:var(--txt);-webkit-font-smoothing:antialiased;
}}
[data-testid="stSidebar"]{{
  background:var(--sfc)!important;
  backdrop-filter:saturate(180%) blur(24px)!important;
  border-right:1px solid var(--brd)!important;
}}
[data-testid="stSidebar"]>div:first-child{{padding:22px 16px 20px}}
.main .block-container{{padding:24px 32px 48px;max-width:1060px}}
@media(max-width:768px){{
  .main .block-container{{padding:16px 12px 32px!important}}
  [data-testid="stSidebar"]>div:first-child{{padding:16px 12px!important}}
}}
h1{{font-size:24px;font-weight:600;letter-spacing:-.4px;color:var(--txt)}}
p,.stMarkdown p{{font-size:15px;line-height:1.65;color:var(--tx2)}}
.glass{{
  background:var(--sfc);backdrop-filter:saturate(180%) blur(20px);
  border:1px solid var(--glb);border-radius:14px;
  box-shadow:var(--shd);padding:18px 20px;margin-bottom:12px;
}}
.glass-sm{{
  background:var(--sfc);backdrop-filter:blur(16px);
  border:1px solid var(--glb);border-radius:11px;
  box-shadow:0 1px 6px rgba(0,0,0,{'0.25' if D else '0.05'});
  padding:10px 13px;margin-bottom:7px;
}}
.al{{border-left:3px solid #1d1d1f}}
.ag{{border-left:3px solid var(--grn)}}
.aa{{border-left:3px solid var(--amb)}}
.ar{{border-left:3px solid var(--red)}}
.mc{{
  background:var(--sfc);backdrop-filter:blur(16px);
  border:1px solid var(--glb);border-radius:13px;
  box-shadow:var(--shd);padding:14px 16px;text-align:center;
}}
.ml{{font-size:10px;font-weight:600;color:var(--tx3);letter-spacing:.4px;text-transform:uppercase}}
.mv{{font-size:28px;font-weight:300;letter-spacing:-1px;color:var(--txt);line-height:1.1;margin:4px 0 2px}}
.mu{{font-size:12px;color:var(--tx3)}}
.sec{{font-size:10px;font-weight:600;letter-spacing:.7px;text-transform:uppercase;
  color:var(--tx3);margin:20px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--brd)}}
.dot{{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:4px}}
.dg{{background:var(--grn)}}.dr{{background:var(--red)}}
.badge{{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600}}
/* buttons */
.stButton>button{{
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  font-size:14px!important;font-weight:500!important;border-radius:10px!important;
  padding:10px 18px!important;transition:all .15s ease!important;
  min-height:44px!important;
}}
.stButton>button[kind="primary"]{{
  background:var(--prim)!important;border:none!important;
  color:var(--ptxt)!important;
  box-shadow:0 2px 8px rgba(0,0,0,{'0.35' if D else '0.18'})!important;
}}
.stButton>button[kind="primary"]:hover{{opacity:.85!important;transform:translateY(-1px)!important}}
.stButton>button:not([kind="primary"]){{
  background:var(--sfc2)!important;border:1px solid var(--brd)!important;
  color:var(--txt)!important;
}}
.stButton>button:not([kind="primary"]):hover{{background:var(--sfc)!important;transform:translateY(-1px)!important}}
/* inputs */
.stTextArea textarea,.stTextInput input{{
  background:var(--inb)!important;
  border:1.5px solid var(--inr)!important;
  border-radius:10px!important;font-size:14px!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  color:var(--txt)!important;
  box-shadow:0 1px 4px rgba(0,0,0,{'0.30' if D else '0.07'})!important;
  padding:10px 12px!important;
  min-height:44px!important;
}}
.stTextArea textarea::placeholder,.stTextInput input::placeholder{{color:var(--tx3)!important;opacity:1!important}}
.stTextArea textarea:focus,.stTextInput input:focus{{
  border-color:rgba({'255,255,255,0.5' if D else '0,0,0,0.5'})!important;
  box-shadow:0 0 0 3px rgba({'255,255,255,0.10' if D else '0,0,0,0.08'})!important;outline:none!important;
}}
label,[data-testid="stWidgetLabel"]{{color:var(--tx2)!important;font-size:13px!important;font-weight:500!important}}
/* progress */
.stProgress>div>div>div{{background:var(--prim)!important;border-radius:4px!important}}
.stProgress>div>div{{background:var(--brd)!important;border-radius:4px!important}}
/* tabs */
.stTabs [data-baseweb="tab-list"]{{background:var(--bg2)!important;border-radius:10px!important;padding:3px!important;gap:2px!important;border:none!important}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;border-radius:8px!important;font-size:13px!important;font-weight:500!important;color:var(--tx3)!important;padding:6px 12px!important;border:none!important;min-height:36px!important}}
.stTabs [aria-selected="true"]{{background:var(--sfc)!important;color:var(--txt)!important;box-shadow:0 1px 4px rgba(0,0,0,{'0.3' if D else '0.08'})!important}}
/* alert */
.stAlert{{border-radius:12px!important;font-size:14px!important;border:none!important}}
/* diff */
.da{{background:rgba(52,199,89,.12);color:{'#4cd964' if D else '#1a7a35'};padding:1px 8px;border-left:2px solid var(--grn);display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dd{{background:rgba(255,59,48,.10);color:{'#ff453a' if D else '#c0392b'};padding:1px 8px;border-left:2px solid var(--red);display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dc{{color:var(--tx3);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dh{{color:var(--tx2);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:11px;font-weight:600}}
/* system list */
.si{{display:flex;align-items:center;gap:9px;padding:9px 11px;border-radius:10px;margin-bottom:3px}}
.si.on{{background:rgba({'255,255,255,0.12' if D else '0,0,0,0.07'})}}
.si.off{{opacity:.38}}
.sdot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.sdot.a{{background:var(--grn)}}.sdot.i{{background:var(--tx3)}}
.sname{{font-size:12.5px;font-weight:500;color:var(--txt)}}
.stag{{font-size:10px;color:var(--tx3);margin-left:auto;white-space:nowrap}}
/* misc */
[data-testid="stHorizontalBlock"]{{gap:8px}}
footer{{display:none}}#MainMenu{{visibility:hidden}}[data-testid="stDecoration"]{{display:none}}
hr{{border:none;border-top:1px solid var(--brd);margin:13px 0}}
.stCheckbox>label{{color:var(--tx2)!important;font-size:14px!important}}
::-webkit-scrollbar{{width:4px;height:4px}}
::-webkit-scrollbar-thumb{{background:var(--brd);border-radius:3px}}
@media(max-width:640px){{
  h1{{font-size:20px!important}}
  .mc{{padding:10px 12px!important}}
  .mv{{font-size:22px!important}}
  .glass{{padding:14px 14px!important}}
}}
</style>""", unsafe_allow_html=True)

# ── サイドバー ─────────────────────────────────────────────────────────────────
with st.sidebar:
    r1c1, r1c2 = st.columns([3,1])
    with r1c1:
        st.markdown(f"<div style='font-size:17px;font-weight:700;letter-spacing:-.5px;color:var(--txt)'>{t['app_name']}</div>", unsafe_allow_html=True)
    with r1c2:
        icon = "◑" if D else "◐"
        if st.button(icon, key="theme_btn", help=t["theme_dark"] if not D else t["theme_light"]):
            new_th = "light" if D else "dark"
            st.session_state.theme = new_th
            st.query_params["theme"] = new_th
            st.rerun()
    lc, _ = st.columns([1,2])
    with lc:
        if st.button(t["lang_toggle"], key="lang_btn"):
            new_lg = "en" if lg=="ja" else "ja"
            st.session_state.lang = new_lg
            st.query_params["lang"] = new_lg
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # モード切り替え（3ボタン）
    mc1,mc2,mc3 = st.columns(3)
    for col,(k,lbl) in zip([mc1,mc2,mc3],[("request",t["mode_request"]),("engineer",t["mode_engineer"]),("settings",t["mode_settings"])]):
        with col:
            active = st.session_state.mode==k
            if st.button(lbl,key=f"m_{k}",use_container_width=True,type="primary" if active else "secondary"):
                st.session_state.mode=k; st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # システム選択
    st.markdown(f"<div class='sec' style='margin-top:2px'>{t['system_label']}</div>", unsafe_allow_html=True)
    for sk, sv in SYSTEMS.items():
        nm = sv["name_ja"] if lg=="ja" else sv["name_en"]
        is_sel = (st.session_state.selected_system==sk)
        tag = "" if sv["active"] else t["system_coming"]
        dot = "a" if sv["active"] else "i"
        item_cls = ("si on" if is_sel else "si") if sv["active"] else "si off"
        st.markdown(
            f"<div class='{item_cls}'><div class='sdot {dot}'></div>"
            f"<span class='sname'>{nm}</span><span class='stag'>{tag}</span></div>",
            unsafe_allow_html=True,
        )
        if sv["active"]:
            btn_type = "primary" if is_sel else "secondary"
            if st.button(nm, key=f"s_{sk}", use_container_width=True, type=btn_type):
                st.session_state.selected_system=sk; st.rerun()

    if st.session_state.mode=="engineer" and not st.session_state.engineer_auth:
        st.markdown("<hr>", unsafe_allow_html=True)
        pw = st.text_input(t["eng_pass"], type="password", placeholder=t["eng_pass_ph"])
        if pw==os.getenv("ENGINEER_PASSWORD","engineer123"):
            st.session_state.engineer_auth=True; st.rerun()
        elif pw:
            st.markdown(f"<div class='glass-sm ar' style='margin-top:6px'><span style='font-size:13px;color:var(--red)'>{t['eng_wrong']}</span></div>", unsafe_allow_html=True)

    if st.session_state.history:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<div class='sec' style='margin-top:2px'>{t['history_label']}</div>", unsafe_allow_html=True)
        for h in st.session_state.history[-st.session_state.history_limit:][::-1][:5]:
            st.markdown(f"<div class='glass-sm'><span style='font-size:11px;color:var(--tx2);line-height:1.4'>{h}</span></div>", unsafe_allow_html=True)

# ── リクエスト画面 ─────────────────────────────────────────────────────────────
if st.session_state.mode=="request":
    st.markdown(f"<h1>{t['request_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:5px;margin-bottom:20px'>{t['request_sub']}</p>", unsafe_allow_html=True)

    # 重要度（フォーム外 = 即時反映）
    st.markdown(f"<div style='font-size:13px;font-weight:500;color:var(--tx2);margin-bottom:6px'>{t['priority_label']}</div>", unsafe_allow_html=True)
    pc1,pc2,pc3,pc4 = st.columns(4)
    for col,pk in zip([pc1,pc2,pc3,pc4],PRIO_KEYS):
        with col:
            selected = st.session_state.priority==pk
            color = pc[pk]
            bg_style = f"background:{color}!important;color:{'#fff' if pk in ('urgent','high') else ('#1d1d1f' if not D else '#1d1d1f')}!important;border-color:{color}!important;" if selected else ""
            lbl = t[f"prio_{pk}"]
            if st.button(lbl, key=f"p_{pk}", use_container_width=True,
                         type="primary" if selected else "secondary"):
                st.session_state.priority=pk; st.rerun()

    with st.form("rf"):
        instruction = st.text_area(t["instruction_label"], placeholder=t["instruction_ph"], height=150)
        eng_comment = st.text_area(t["comment_label"], placeholder=t["comment_ph"], height=72)
        submitted = st.form_submit_button(t["submit"], use_container_width=True, type="primary")

    if submitted and instruction.strip():
        st.session_state.deployed=False; st.session_state.result=None
        bph=st.empty(); mph=st.empty()
        steps=[t["step1"],t["step2"],t["step3"],t["step4"],t["step5"]]
        bar=bph.progress(0)
        for i,msg in enumerate(steps):
            mph.markdown(f"<div class='glass-sm' style='margin-top:8px'><span style='font-size:13px;color:var(--tx2)'>{msg}...</span></div>", unsafe_allow_html=True)
            bar.progress(int((i+1)/len(steps)*95)); time.sleep(0.3)
        full = instruction + (f"\n\n[{t['eng_cmt']}]\n{eng_comment}" if eng_comment.strip() else "")
        result = run_pipeline(full)
        result._priority = st.session_state.priority
        result._eng_comment = eng_comment
        st.session_state.result=result
        lbl = instruction[:28]+"…" if len(instruction)>28 else instruction
        st.session_state.history.append(f"{datetime.now().strftime('%H:%M')}  {lbl}")
        bph.empty(); mph.empty()
        if result.success:
            st.markdown(f"<div class='glass ag' style='margin-top:12px'><span style='font-size:14px;font-weight:600;color:var(--grn)'>{t['submit_ok']}</span><br><span style='font-size:13px;color:var(--tx2);margin-top:4px;display:block'>{t['submit_ok_sub']}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='glass aa' style='margin-top:12px'><span style='font-size:14px;font-weight:600;color:var(--amb)'>{t['submit_warn']}</span><br><span style='font-size:13px;color:var(--tx2);margin-top:4px;display:block'>{t['submit_warn_sub']}</span></div>", unsafe_allow_html=True)
    elif submitted:
        st.warning(t["submit_empty"])

    if st.session_state.deployed:
        st.markdown(f"<div class='glass ag' style='margin-top:12px'><span style='font-size:14px;font-weight:600;color:var(--grn)'>{t['deployed_ok']}</span><br><span style='font-size:12px;color:var(--tx3);margin-top:4px;display:block'>{t['deployed_at']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>", unsafe_allow_html=True)

# ── エンジニア画面 ─────────────────────────────────────────────────────────────
elif st.session_state.mode=="engineer":
    if not st.session_state.engineer_auth:
        st.markdown(f"<div class='glass' style='margin-top:40px;text-align:center;padding:36px'><span style='font-size:15px;color:var(--tx2)'>{t['eng_need_pw']}</span></div>", unsafe_allow_html=True); st.stop()
    result=st.session_state.result
    if result is None:
        st.markdown(f"<div class='glass' style='margin-top:40px;text-align:center;padding:36px'><span style='font-size:15px;color:var(--tx2)'>{t['eng_no_req']}</span></div>", unsafe_allow_html=True); st.stop()

    st.markdown(f"<h1>{t['eng_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:5px;margin-bottom:20px'>{t['eng_sub']}</p>", unsafe_allow_html=True)

    c1,c2,c3=st.columns(3)
    with c1:
        dot="dg" if result.success else "dr"; lbl=t["test_ok"] if result.success else t["test_fail"]
        st.markdown(f"<div class='mc'><div class='ml'>{t['sandbox']}</div><div style='margin-top:9px'><span class='dot {dot}'></span><span style='font-size:13px;font-weight:500;color:var(--txt)'>{lbl}</span></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='mc'><div class='ml'>{t['debug']}</div><div class='mv'>{result.iterations}</div><div class='mu'>{t['times']}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='mc'><div class='ml'>{t['lines']}</div><div class='mv'>{result.changed_lines}</div><div class='mu'>{t['lines_u']}</div></div>", unsafe_allow_html=True)

    prio=getattr(result,'_priority','mid')
    pc_color=pc.get(prio,"#8e8e93")
    st.markdown(f"<div style='margin:6px 0 14px'><span class='badge' style='background:{pc_color}22;color:{pc_color};border:1px solid {pc_color}55'>{t['prio_badge']}: {t[f'prio_{prio}']}</span></div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['user_req']}</p>", unsafe_allow_html=True)
    ec=getattr(result,'_eng_comment','')
    instr=result.instruction.split(f"\n\n[{t['eng_cmt']}]")[0] if ec else result.instruction
    st.markdown(f"<div class='glass al'><span style='font-size:14px;line-height:1.65;color:var(--txt)'>{_esc(instr)}</span></div>", unsafe_allow_html=True)
    if ec:
        st.markdown(f"<div class='glass-sm aa'><span style='font-size:11px;color:var(--tx3)'>{t['eng_cmt']}</span><br><span style='font-size:14px;color:var(--tx2)'>{_esc(ec)}</span></div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['ai_report']}</p>", unsafe_allow_html=True)
    st.markdown(f"<div class='glass aa'>{result.report}</div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['code_diff']}</p>", unsafe_allow_html=True)
    t1,t2,t3=st.tabs([t["tab_diff"],t["tab_before"],t["tab_after"]])
    with t1: st.markdown(f"<div class='glass' style='padding:12px 14px;overflow-x:auto'>{_diff_html(result.original_code,result.new_code)}</div>", unsafe_allow_html=True)
    with t2: st.code(result.original_code, language="html")
    with t3: st.code(result.new_code, language="html")

    with st.expander(t["log"]):
        if result.test_output: st.code(result.test_output, language="bash")
        else: st.markdown(f"<span style='font-size:13px;color:var(--tx3)'>{t['log_none']}</span>", unsafe_allow_html=True)
        if result.test_error: st.code(result.test_error, language="bash")

    st.markdown(f"<p class='sec'>{t['decision']}</p>", unsafe_allow_html=True)
    ok,ng=st.columns(2)
    with ok:
        st.markdown(f"<div class='glass' style='padding:16px 18px'><span style='font-size:14px;font-weight:600;color:var(--txt)'>{t['approve_title']}</span><br><span style='font-size:12px;color:var(--tx3);display:block;margin-top:3px;margin-bottom:11px'>{t['approve_sub']}</span>", unsafe_allow_html=True)
        if st.button(t["approve_btn"],use_container_width=True,type="primary",key="ap"):
            with st.spinner("..."): apply_code(result.new_code); time.sleep(0.8)
            st.session_state.deployed=True
            st.markdown(f"<div class='glass-sm ag' style='margin-top:8px'><span style='font-size:13px;color:var(--grn);font-weight:600'>{t['approve_done']}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with ng:
        st.markdown(f"<div class='glass' style='padding:16px 18px'><span style='font-size:14px;font-weight:600;color:var(--txt)'>{t['reject_title']}</span><br><span style='font-size:12px;color:var(--tx3);display:block;margin-top:3px;margin-bottom:11px'>{t['reject_sub']}</span>", unsafe_allow_html=True)
        fb=st.text_area(t["reject_ph"],height=84,label_visibility="collapsed",key="fb")
        if st.button(t["regen_btn"],use_container_width=True,key="rg"):
            if fb.strip():
                with st.spinner("..."):
                    nr=run_pipeline(f"{result.instruction}\n\n[修正]\n{fb}",result.original_code)
                st.session_state.result=nr; st.rerun()
            else: st.warning(t["regen_warn"])
        st.markdown("</div>", unsafe_allow_html=True)

# ── 設定画面 ───────────────────────────────────────────────────────────────────
elif st.session_state.mode=="settings":
    st.markdown(f"<h1>{t['settings_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:5px;margin-bottom:20px'>{t['settings_sub']}</p>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['sys_info']}</p>", unsafe_allow_html=True)
    sv=SYSTEMS[st.session_state.selected_system]
    rows=[
        (t["sys_url"],   f'<a href="{sv["url"]}" target="_blank" style="color:var(--txt);text-decoration:underline;text-underline-offset:2px">{sv["url"]}</a>'),
        (t["sys_source"],f'<code style="font-size:12px;color:var(--tx2);background:var(--bg2);padding:2px 7px;border-radius:5px">{sv["source"]}</code>'),
        (t["sys_path"],  f'<code style="font-size:12px;color:var(--tx2);background:var(--bg2);padding:2px 7px;border-radius:5px">{sv["path"]}</code>'),
    ]
    rows_html="".join(
        f"<div style='display:flex;align-items:center;padding:10px 0;border-bottom:1px solid var(--brd);gap:14px'>"
        f"<span style='font-size:10px;font-weight:600;color:var(--tx3);text-transform:uppercase;letter-spacing:.4px;min-width:80px'>{lbl}</span>"
        f"<span style='font-size:13px;color:var(--tx2)'>{val}</span></div>"
        for lbl,val in rows
    )
    st.markdown(f"<div class='glass' style='padding:0 18px'>{rows_html}</div>", unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['theme_sec']}</p>", unsafe_allow_html=True)
    tc1,tc2=st.columns(2)
    with tc1:
        if st.button(t["theme_light"],key="sl",use_container_width=True,type="primary" if not D else "secondary"):
            st.session_state.theme="light"; st.query_params["theme"]="light"; st.rerun()
    with tc2:
        if st.button(t["theme_dark"],key="sd",use_container_width=True,type="primary" if D else "secondary"):
            st.session_state.theme="dark"; st.query_params["theme"]="dark"; st.rerun()

    st.markdown(f"<p class='sec'>{t['lang_sec']}</p>", unsafe_allow_html=True)
    lc1,lc2=st.columns(2)
    with lc1:
        if st.button("日本語",key="sja",use_container_width=True,type="primary" if lg=="ja" else "secondary"):
            st.session_state.lang="ja"; st.query_params["lang"]="ja"; st.rerun()
    with lc2:
        if st.button("English",key="sen",use_container_width=True,type="primary" if lg=="en" else "secondary"):
            st.session_state.lang="en"; st.query_params["lang"]="en"; st.rerun()

    st.markdown(f"<p class='sec'>{t['notif_sec']}</p>", unsafe_allow_html=True)
    st.markdown("<div class='glass' style='padding:16px 18px'>", unsafe_allow_html=True)
    notif=st.checkbox(t["notif_auto"],value=st.session_state.notif_auto)
    st.session_state.notif_auto=notif
    st.markdown(f"<div style='margin-top:14px;margin-bottom:6px'><span style='font-size:13px;font-weight:500;color:var(--tx2)'>{t['hist_limit']}</span></div>", unsafe_allow_html=True)
    lim=st.slider("",5,50,st.session_state.history_limit,5,label_visibility="collapsed")
    st.session_state.history_limit=lim
    st.markdown("</div>", unsafe_allow_html=True)
