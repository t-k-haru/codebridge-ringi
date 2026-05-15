# -*- coding: utf-8 -*-
import streamlit as st
import os, time, difflib
from datetime import datetime
from dotenv import load_dotenv
from core.orchestrator import run_pipeline
from core.sandbox import read_target_code, apply_code

load_dotenv()

T = {
    "ja": {
        "app_name": "CodeBridge",
        "mode_request": "リクエスト", "mode_engineer": "エンジニア", "mode_settings": "設定",
        "system_label": "対象システム",
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
        "step1": "指示を解析中", "step2": "コードを生成中",
        "step3": "サンドボックスで検証中", "step4": "結果を確認中", "step5": "レポートを作成中",
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
        "log": "実行ログ", "log_none": "出力なし", "decision": "判断",
        "approve_title": "承認してデプロイ",
        "approve_sub": "バックアップ後に本番環境へ反映します",
        "approve_btn": "承認", "approve_done": "デプロイが完了しました",
        "reject_title": "差し戻して再生成",
        "reject_sub": "修正コメントを添えてAIに再依頼します",
        "reject_ph": "例：ボタンの色を青ではなく緑に",
        "regen_btn": "再生成", "regen_warn": "修正コメントを入力してください",
        "settings_title": "設定", "settings_sub": "CodeBridgeの動作をカスタマイズします。",
        "sys_info": "システム情報", "sys_url": "デモURL",
        "sys_source": "ソースファイル", "sys_path": "ファイルパス",
        "theme_sec": "外観", "lang_sec": "言語",
        "notif_sec": "オプション", "notif_auto": "承認後にデプロイ通知を表示",
        "hist_limit": "履歴の保持件数", "history_label": "最近のリクエスト",
    },
    "en": {
        "app_name": "CodeBridge",
        "mode_request": "Request", "mode_engineer": "Engineer", "mode_settings": "Settings",
        "system_label": "Target System",
        "theme_light": "Light", "theme_dark": "Dark", "lang_toggle": "JA",
        "request_title": "Request Changes",
        "request_sub": "Describe what you want to change. AI will convert it to code.",
        "instruction_label": "Instructions",
        "instruction_ph": "e.g.:\n· Change the header background color\n· Make KPI numbers larger\n· Add row hover highlight",
        "priority_label": "Priority",
        "prio_low": "Low", "prio_mid": "Mid", "prio_high": "High", "prio_urgent": "Urgent",
        "comment_label": "Comment to Engineer (optional)",
        "comment_ph": "Add any supplementary notes here",
        "submit": "Send to AI",
        "submit_ok": "Code generated",
        "submit_ok_sub": "An engineer is reviewing. Changes will be applied after approval.",
        "submit_warn": "Engineer review required",
        "submit_warn_sub": "AI attempted the task but some issues remain.",
        "submit_empty": "Please enter instructions",
        "deployed_ok": "Successfully deployed", "deployed_at": "Deployed at",
        "step1": "Analyzing", "step2": "Generating code",
        "step3": "Validating", "step4": "Verifying", "step5": "Creating report",
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
        "log": "Execution Log", "log_none": "No output", "decision": "Decision",
        "approve_title": "Approve & Deploy",
        "approve_sub": "A backup will be taken before deploying",
        "approve_btn": "Approve", "approve_done": "Deploy complete",
        "reject_title": "Reject & Regenerate",
        "reject_sub": "Send correction comments to AI",
        "reject_ph": "e.g.: Make the button green instead of blue",
        "regen_btn": "Regenerate", "regen_warn": "Please enter correction comments",
        "settings_title": "Settings", "settings_sub": "Customize CodeBridge.",
        "sys_info": "System Information", "sys_url": "Demo URL",
        "sys_source": "Source File", "sys_path": "File Path",
        "theme_sec": "Appearance", "lang_sec": "Language",
        "notif_sec": "Options", "notif_auto": "Show deploy notification after approval",
        "hist_limit": "History limit", "history_label": "Recent Requests",
    }
}

# アクティブなシステムのみ（飲食・介護医療は非表示）
SYSTEMS = {
    "shift_generic": {
        "name_ja": "シフト管理（汎用）", "name_en": "Shift Mgmt (Generic)",
        "url": "https://shift.nobushi.jp/demo-generic/",
        "source": "target_app/demo_local.html",
        "path": "/target_app/demo_local.html", "active": True,
    },
}

PRIO_KEYS = ["low","mid","high","urgent"]
PRIO_C = {"low":"#34c759","mid":"#555","high":"#ff9500","urgent":"#ff3b30"}
PRIO_C_D = {"low":"#34c759","mid":"#aaa","high":"#ff9f0a","urgent":"#ff453a"}

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
    return "\n".join(out) or "<span class='dc'>変更なし</span>"

st.set_page_config(page_title="CodeBridge", layout="wide", initial_sidebar_state="expanded")

qp = st.query_params
defaults = {
    "mode":"request","theme":qp.get("theme","light"),"lang":qp.get("lang","ja"),
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
pc = PRIO_C_D if D else PRIO_C

# ── CSS（テーマ別にキャッシュして再計算コストを下げる）───────────────────────
@st.cache_data(show_spinner=False)
def _css(dark: bool) -> str:
    BG  = "#1c1c1e" if dark else "#f2f2f7"
    BG2 = "#2c2c2e" if dark else "#e5e5ea"
    SFC = "rgba(44,44,46,0.94)" if dark else "rgba(255,255,255,0.94)"
    SFC2= "rgba(58,58,60,0.97)" if dark else "rgba(245,245,247,0.98)"
    GLB = "rgba(255,255,255,0.10)" if dark else "rgba(255,255,255,0.92)"
    BRD = "rgba(255,255,255,0.11)" if dark else "rgba(0,0,0,0.09)"
    TXT = "#f5f5f7" if dark else "#1d1d1f"
    TX2 = "#aeaeb2" if dark else "#3d3d3f"
    TX3 = "#636366" if dark else "#8e8e93"
    INB = "rgba(62,62,64,0.98)" if dark else "#ffffff"
    INR = "rgba(255,255,255,0.22)" if dark else "rgba(0,0,0,0.20)"
    SHD = "0 2px 16px rgba(0,0,0,0.45)" if dark else "0 2px 10px rgba(0,0,0,0.07)"
    # Primary button: white text on black (light) / black text on white (dark)
    PBGC= "#1d1d1f" if not dark else "#f5f5f7"
    PTXT= "#ffffff" if not dark else "#1d1d1f"
    return f"""
:root{{--bg:{BG};--bg2:{BG2};--sfc:{SFC};--sfc2:{SFC2};
  --glb:{GLB};--brd:{BRD};--txt:{TXT};--tx2:{TX2};--tx3:{TX3};
  --inb:{INB};--inr:{INR};--shd:{SHD};--pbg:{PBGC};--ptxt:{PTXT};
  --grn:#34c759;--amb:#ff9500;--red:#ff3b30;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,[data-testid="stAppViewContainer"]{{background:var(--bg)!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',sans-serif;
  color:var(--txt);-webkit-font-smoothing:antialiased;}}
[data-testid="stSidebar"]{{background:var(--sfc)!important;
  backdrop-filter:saturate(180%) blur(24px)!important;
  border-right:1px solid var(--brd)!important;}}
[data-testid="stSidebar"]>div:first-child{{padding:20px 14px 18px}}
.main .block-container{{padding:22px 28px 48px;max-width:1040px}}
h1{{font-size:22px;font-weight:600;letter-spacing:-.3px;color:var(--txt)}}
p,.stMarkdown p{{font-size:14px;line-height:1.6;color:var(--tx2)}}
/* glass cards */
.glass{{background:var(--sfc);backdrop-filter:saturate(180%) blur(20px);
  border:1px solid var(--glb);border-radius:14px;
  box-shadow:var(--shd);padding:16px 18px;margin-bottom:10px;}}
.glass-sm{{background:var(--sfc);backdrop-filter:blur(14px);
  border:1px solid var(--glb);border-radius:10px;
  box-shadow:0 1px 5px rgba(0,0,0,{0.22 if dark else 0.04});
  padding:9px 12px;margin-bottom:6px;}}
.al{{border-left:3px solid var(--txt)}}
.ag{{border-left:3px solid var(--grn)}}
.aa{{border-left:3px solid var(--amb)}}
.ar{{border-left:3px solid var(--red)}}
/* metric */
.mc{{background:var(--sfc);backdrop-filter:blur(14px);border:1px solid var(--glb);
  border-radius:12px;box-shadow:var(--shd);padding:13px 14px;text-align:center;}}
.ml{{font-size:9.5px;font-weight:600;color:var(--tx3);letter-spacing:.4px;text-transform:uppercase}}
.mv{{font-size:26px;font-weight:300;letter-spacing:-1px;color:var(--txt);line-height:1.1;margin:3px 0 2px}}
.mu{{font-size:11px;color:var(--tx3)}}
.sec{{font-size:9.5px;font-weight:600;letter-spacing:.6px;text-transform:uppercase;
  color:var(--tx3);margin:18px 0 7px;padding-bottom:5px;border-bottom:1px solid var(--brd)}}
.dot{{width:6px;height:6px;border-radius:50%;display:inline-block;margin-right:4px}}
.dg{{background:var(--grn)}}.dr{{background:var(--red)}}
.badge{{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600}}
/* ALL buttons */
button,
.stButton>button,
[data-testid="stFormSubmitButton"]>button,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"]{{
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  font-size:13px!important;font-weight:500!important;border-radius:9px!important;
  padding:8px 14px!important;transition:opacity .12s ease,transform .12s ease!important;
  white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;
  min-height:40px!important;line-height:1!important;
}}
/* primary */
.stButton>button[kind="primary"],
[data-testid="stFormSubmitButton"]>button,
[data-testid="stBaseButton-primary"]{{
  background:var(--pbg)!important;border:none!important;
  color:var(--ptxt)!important;
  box-shadow:0 2px 6px rgba(0,0,0,{0.35 if dark else 0.20})!important;
}}
.stButton>button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"]>button:hover{{opacity:.82!important;transform:translateY(-1px)!important}}
/* secondary */
.stButton>button:not([kind="primary"]),
[data-testid="stBaseButton-secondary"]{{
  background:var(--sfc2)!important;border:1px solid var(--brd)!important;
  color:var(--txt)!important;
}}
.stButton>button:not([kind="primary"]):hover{{background:var(--sfc)!important;transform:translateY(-1px)!important}}
/* inputs */
.stTextArea textarea,.stTextInput input{{
  background:var(--inb)!important;border:1.5px solid var(--inr)!important;
  border-radius:10px!important;font-size:13.5px!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  color:var(--txt)!important;
  box-shadow:0 1px 4px rgba(0,0,0,{0.28 if dark else 0.06})!important;
  padding:9px 11px!important;
}}
.stTextArea textarea::placeholder,.stTextInput input::placeholder{{color:var(--tx3)!important;opacity:1!important}}
.stTextArea textarea:focus,.stTextInput input:focus{{
  border-color:rgba({('255,255,255,0.5' if dark else '0,0,0,0.45')})!important;
  box-shadow:0 0 0 2px rgba({('255,255,255,0.08' if dark else '0,0,0,0.06')})!important;outline:none!important;
}}
label,[data-testid="stWidgetLabel"]{{color:var(--tx2)!important;font-size:12.5px!important;font-weight:500!important}}
/* progress */
.stProgress>div>div>div{{background:var(--pbg)!important;border-radius:3px!important}}
.stProgress>div>div{{background:var(--brd)!important;border-radius:3px!important}}
/* tabs */
.stTabs [data-baseweb="tab-list"]{{background:var(--bg2)!important;border-radius:9px!important;padding:3px!important;gap:2px!important;border:none!important}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;border-radius:7px!important;font-size:12.5px!important;font-weight:500!important;color:var(--tx3)!important;padding:5px 11px!important;border:none!important;white-space:nowrap!important}}
.stTabs [aria-selected="true"]{{background:var(--sfc)!important;color:var(--txt)!important;box-shadow:0 1px 4px rgba(0,0,0,{0.28 if dark else 0.07})!important}}
/* alerts */
.stAlert{{border-radius:11px!important;font-size:13.5px!important;border:none!important}}
/* diff */
.da{{background:rgba(52,199,89,.11);color:{'#4cd964' if dark else '#1a7a35'};padding:1px 8px;border-left:2px solid var(--grn);display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dd{{background:rgba(255,59,48,.09);color:{'#ff453a' if dark else '#c0392b'};padding:1px 8px;border-left:2px solid var(--red);display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dc{{color:var(--tx3);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dh{{color:var(--tx2);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:11px;font-weight:600}}
/* system item */
.si{{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:9px;margin-bottom:3px}}
.si.on{{background:rgba({('255,255,255,0.10' if dark else '0,0,0,0.06')})}}
.sdot{{width:6px;height:6px;border-radius:50%;flex-shrink:0;background:var(--grn)}}
.sname{{font-size:12px;font-weight:500;color:var(--txt)}}
/* misc */
[data-testid="stHorizontalBlock"]{{gap:7px}}
footer{{display:none}}#MainMenu{{visibility:hidden}}[data-testid="stDecoration"]{{display:none}}
hr{{border:none;border-top:1px solid var(--brd);margin:11px 0}}
.stCheckbox>label{{color:var(--tx2)!important;font-size:13.5px!important}}
::-webkit-scrollbar{{width:4px;height:4px}}
::-webkit-scrollbar-thumb{{background:var(--brd);border-radius:2px}}
@media(max-width:768px){{
  .main .block-container{{padding:14px 10px 28px!important}}
  [data-testid="stSidebar"]>div:first-child{{padding:14px 10px!important}}
  h1{{font-size:18px!important}}
  .mv{{font-size:22px!important}}
  .glass{{padding:12px 12px!important}}
}}
"""

st.markdown(f"<style>{_css(D)}</style>", unsafe_allow_html=True)

# ── サイドバー ─────────────────────────────────────────────────────────────────
with st.sidebar:
    r1,r2 = st.columns([3,1])
    with r1:
        st.markdown(f"<div style='font-size:16px;font-weight:700;letter-spacing:-.4px;color:var(--txt);padding-top:2px'>{t['app_name']}</div>", unsafe_allow_html=True)
    with r2:
        if st.button("◑" if D else "◐", key="thm"):
            nth = "light" if D else "dark"
            st.session_state.theme=nth; st.query_params["theme"]=nth; st.rerun()
    lc,_=st.columns([1,2])
    with lc:
        if st.button(t["lang_toggle"],key="lng"):
            nl="en" if lg=="ja" else "ja"
            st.session_state.lang=nl; st.query_params["lang"]=nl; st.rerun()

    st.markdown("<hr>",unsafe_allow_html=True)

    # モードボタン（改行しないようにkey短く＆フォント小さめ）
    mc1,mc2,mc3=st.columns(3)
    for col,(k,lbl) in zip([mc1,mc2,mc3],[("request",t["mode_request"]),("engineer",t["mode_engineer"]),("settings",t["mode_settings"])]):
        with col:
            if st.button(lbl,key=f"m{k[:2]}",use_container_width=True,type="primary" if st.session_state.mode==k else "secondary"):
                st.session_state.mode=k; st.rerun()

    st.markdown("<hr>",unsafe_allow_html=True)

    # システム選択（アクティブなもののみ表示）
    st.markdown(f"<div class='sec' style='margin-top:2px'>{t['system_label']}</div>",unsafe_allow_html=True)
    for sk,sv in SYSTEMS.items():
        nm=sv["name_ja"] if lg=="ja" else sv["name_en"]
        is_sel=(st.session_state.selected_system==sk)
        st.markdown(f"<div class='si on'><div class='sdot'></div><span class='sname'>{nm}</span></div>",unsafe_allow_html=True)
        if st.button(nm,key=f"sy{sk[:4]}",use_container_width=True,type="primary" if is_sel else "secondary"):
            st.session_state.selected_system=sk; st.rerun()

    if st.session_state.mode=="engineer" and not st.session_state.engineer_auth:
        st.markdown("<hr>",unsafe_allow_html=True)
        pw=st.text_input(t["eng_pass"],type="password",placeholder=t["eng_pass_ph"])
        if pw==os.getenv("ENGINEER_PASSWORD","engineer123"):
            st.session_state.engineer_auth=True; st.rerun()
        elif pw:
            st.markdown(f"<div class='glass-sm ar' style='margin-top:5px'><span style='font-size:12.5px;color:var(--red)'>{t['eng_wrong']}</span></div>",unsafe_allow_html=True)

    if st.session_state.history:
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown(f"<div class='sec' style='margin-top:2px'>{t['history_label']}</div>",unsafe_allow_html=True)
        for h in st.session_state.history[-st.session_state.history_limit:][::-1][:5]:
            st.markdown(f"<div class='glass-sm'><span style='font-size:11px;color:var(--tx2);line-height:1.4'>{h}</span></div>",unsafe_allow_html=True)

# ── リクエスト画面 ─────────────────────────────────────────────────────────────
if st.session_state.mode=="request":
    st.markdown(f"<h1>{t['request_title']}</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:4px;margin-bottom:18px'>{t['request_sub']}</p>",unsafe_allow_html=True)

    # 重要度（フォーム外）
    st.markdown(f"<div style='font-size:12.5px;font-weight:500;color:var(--tx2);margin-bottom:5px'>{t['priority_label']}</div>",unsafe_allow_html=True)
    pp1,pp2,pp3,pp4=st.columns(4)
    for col,pk in zip([pp1,pp2,pp3,pp4],PRIO_KEYS):
        with col:
            sel=(st.session_state.priority==pk)
            lbl=t[f"prio_{pk}"]
            if st.button(lbl,key=f"pr{pk}",use_container_width=True,type="primary" if sel else "secondary"):
                st.session_state.priority=pk; st.rerun()

    with st.form("rf",clear_on_submit=False):
        instruction=st.text_area(t["instruction_label"],placeholder=t["instruction_ph"],height=140)
        eng_comment=st.text_area(t["comment_label"],placeholder=t["comment_ph"],height=68)
        submitted=st.form_submit_button(t["submit"],use_container_width=True,type="primary")

    if submitted and instruction.strip():
        st.session_state.deployed=False; st.session_state.result=None
        bph=st.empty(); mph=st.empty()
        steps=[t["step1"],t["step2"],t["step3"],t["step4"],t["step5"]]
        bar=bph.progress(0)
        for i,msg in enumerate(steps):
            mph.markdown(f"<div class='glass-sm' style='margin-top:7px'><span style='font-size:13px;color:var(--tx2)'>{msg}...</span></div>",unsafe_allow_html=True)
            bar.progress(int((i+1)/len(steps)*95)); time.sleep(0.25)
        full=instruction+(f"\n\n[{t['eng_cmt']}]\n{eng_comment}" if eng_comment.strip() else "")
        result=run_pipeline(full)
        result._priority=st.session_state.priority
        result._eng_comment=eng_comment
        st.session_state.result=result
        lbl2=instruction[:28]+"…" if len(instruction)>28 else instruction
        st.session_state.history.append(f"{datetime.now().strftime('%H:%M')}  {lbl2}")
        bph.empty(); mph.empty()
        if result.success:
            st.markdown(f"<div class='glass ag' style='margin-top:10px'><span style='font-size:13.5px;font-weight:600;color:var(--grn)'>{t['submit_ok']}</span><br><span style='font-size:12.5px;color:var(--tx2);margin-top:3px;display:block'>{t['submit_ok_sub']}</span></div>",unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='glass aa' style='margin-top:10px'><span style='font-size:13.5px;font-weight:600;color:var(--amb)'>{t['submit_warn']}</span><br><span style='font-size:12.5px;color:var(--tx2);margin-top:3px;display:block'>{t['submit_warn_sub']}</span></div>",unsafe_allow_html=True)
    elif submitted:
        st.warning(t["submit_empty"])
    if st.session_state.deployed:
        st.markdown(f"<div class='glass ag' style='margin-top:10px'><span style='font-size:13.5px;font-weight:600;color:var(--grn)'>{t['deployed_ok']}</span><br><span style='font-size:11.5px;color:var(--tx3);margin-top:3px;display:block'>{t['deployed_at']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>",unsafe_allow_html=True)

# ── エンジニア画面 ─────────────────────────────────────────────────────────────
elif st.session_state.mode=="engineer":
    if not st.session_state.engineer_auth:
        st.markdown(f"<div class='glass' style='margin-top:36px;text-align:center;padding:32px'><span style='font-size:14px;color:var(--tx2)'>{t['eng_need_pw']}</span></div>",unsafe_allow_html=True); st.stop()
    result=st.session_state.result
    if result is None:
        st.markdown(f"<div class='glass' style='margin-top:36px;text-align:center;padding:32px'><span style='font-size:14px;color:var(--tx2)'>{t['eng_no_req']}</span></div>",unsafe_allow_html=True); st.stop()

    st.markdown(f"<h1>{t['eng_title']}</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:4px;margin-bottom:18px'>{t['eng_sub']}</p>",unsafe_allow_html=True)

    c1,c2,c3=st.columns(3)
    with c1:
        dot="dg" if result.success else "dr"; lbl3=t["test_ok"] if result.success else t["test_fail"]
        st.markdown(f"<div class='mc'><div class='ml'>{t['sandbox']}</div><div style='margin-top:8px'><span class='dot {dot}'></span><span style='font-size:13px;font-weight:500;color:var(--txt)'>{lbl3}</span></div></div>",unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='mc'><div class='ml'>{t['debug']}</div><div class='mv'>{result.iterations}</div><div class='mu'>{t['times']}</div></div>",unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='mc'><div class='ml'>{t['lines']}</div><div class='mv'>{result.changed_lines}</div><div class='mu'>{t['lines_u']}</div></div>",unsafe_allow_html=True)

    prio=getattr(result,'_priority','mid')
    pc_col=pc.get(prio,"#8e8e93")
    st.markdown(f"<div style='margin:5px 0 12px'><span class='badge' style='background:{pc_col}22;color:{pc_col};border:1px solid {pc_col}44'>{t['prio_badge']}: {t[f'prio_{prio}']}</span></div>",unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['user_req']}</p>",unsafe_allow_html=True)
    ec=getattr(result,'_eng_comment','')
    instr=result.instruction.split(f"\n\n[{t['eng_cmt']}]")[0] if ec else result.instruction
    st.markdown(f"<div class='glass al'><span style='font-size:13.5px;line-height:1.65;color:var(--txt)'>{_esc(instr)}</span></div>",unsafe_allow_html=True)
    if ec:
        st.markdown(f"<div class='glass-sm aa'><span style='font-size:10.5px;color:var(--tx3)'>{t['eng_cmt']}</span><br><span style='font-size:13.5px;color:var(--tx2)'>{_esc(ec)}</span></div>",unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['ai_report']}</p>",unsafe_allow_html=True)
    st.markdown(f"<div class='glass aa'>{result.report}</div>",unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['code_diff']}</p>",unsafe_allow_html=True)
    t1,t2,t3=st.tabs([t["tab_diff"],t["tab_before"],t["tab_after"]])
    with t1: st.markdown(f"<div class='glass' style='padding:11px 13px;overflow-x:auto'>{_diff_html(result.original_code,result.new_code)}</div>",unsafe_allow_html=True)
    with t2: st.code(result.original_code,language="html")
    with t3: st.code(result.new_code,language="html")

    with st.expander(t["log"]):
        if result.test_output: st.code(result.test_output,language="bash")
        else: st.markdown(f"<span style='font-size:12.5px;color:var(--tx3)'>{t['log_none']}</span>",unsafe_allow_html=True)
        if result.test_error: st.code(result.test_error,language="bash")

    st.markdown(f"<p class='sec'>{t['decision']}</p>",unsafe_allow_html=True)
    ok,ng=st.columns(2)
    with ok:
        st.markdown(f"<div class='glass' style='padding:14px 16px'><span style='font-size:13.5px;font-weight:600;color:var(--txt)'>{t['approve_title']}</span><br><span style='font-size:11.5px;color:var(--tx3);display:block;margin-top:3px;margin-bottom:10px'>{t['approve_sub']}</span>",unsafe_allow_html=True)
        if st.button(t["approve_btn"],use_container_width=True,type="primary",key="ap"):
            with st.spinner("..."): apply_code(result.new_code); time.sleep(0.7)
            st.session_state.deployed=True
            st.markdown(f"<div class='glass-sm ag' style='margin-top:7px'><span style='font-size:12.5px;color:var(--grn);font-weight:600'>{t['approve_done']}</span></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
    with ng:
        st.markdown(f"<div class='glass' style='padding:14px 16px'><span style='font-size:13.5px;font-weight:600;color:var(--txt)'>{t['reject_title']}</span><br><span style='font-size:11.5px;color:var(--tx3);display:block;margin-top:3px;margin-bottom:10px'>{t['reject_sub']}</span>",unsafe_allow_html=True)
        fb=st.text_area(t["reject_ph"],height=80,label_visibility="collapsed",key="fb")
        if st.button(t["regen_btn"],use_container_width=True,key="rg"):
            if fb.strip():
                with st.spinner("..."):
                    nr=run_pipeline(f"{result.instruction}\n\n[修正]\n{fb}",result.original_code)
                st.session_state.result=nr; st.rerun()
            else: st.warning(t["regen_warn"])
        st.markdown("</div>",unsafe_allow_html=True)

# ── 設定画面 ───────────────────────────────────────────────────────────────────
elif st.session_state.mode=="settings":
    st.markdown(f"<h1>{t['settings_title']}</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:4px;margin-bottom:18px'>{t['settings_sub']}</p>",unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['sys_info']}</p>",unsafe_allow_html=True)
    sv=SYSTEMS[st.session_state.selected_system]
    rows=[
        (t["sys_url"],f'<a href="{sv["url"]}" target="_blank" style="color:var(--txt);text-decoration:underline;text-underline-offset:2px">{sv["url"]}</a>'),
        (t["sys_source"],f'<code style="font-size:11.5px;color:var(--tx2);background:var(--bg2);padding:2px 6px;border-radius:4px">{sv["source"]}</code>'),
        (t["sys_path"],f'<code style="font-size:11.5px;color:var(--tx2);background:var(--bg2);padding:2px 6px;border-radius:4px">{sv["path"]}</code>'),
    ]
    rh="".join(
        f"<div style='display:flex;align-items:center;padding:9px 0;border-bottom:1px solid var(--brd);gap:12px'>"
        f"<span style='font-size:9.5px;font-weight:600;color:var(--tx3);text-transform:uppercase;letter-spacing:.4px;min-width:76px'>{lb}</span>"
        f"<span style='font-size:12.5px;color:var(--tx2)'>{vl}</span></div>"
        for lb,vl in rows
    )
    st.markdown(f"<div class='glass' style='padding:0 16px'>{rh}</div>",unsafe_allow_html=True)

    st.markdown(f"<p class='sec'>{t['theme_sec']}</p>",unsafe_allow_html=True)
    tc1,tc2=st.columns(2)
    with tc1:
        if st.button(t["theme_light"],key="sl",use_container_width=True,type="primary" if not D else "secondary"):
            st.session_state.theme="light"; st.query_params["theme"]="light"; st.rerun()
    with tc2:
        if st.button(t["theme_dark"],key="sd",use_container_width=True,type="primary" if D else "secondary"):
            st.session_state.theme="dark"; st.query_params["theme"]="dark"; st.rerun()

    st.markdown(f"<p class='sec'>{t['lang_sec']}</p>",unsafe_allow_html=True)
    lc1,lc2=st.columns(2)
    with lc1:
        if st.button("日本語",key="sja",use_container_width=True,type="primary" if lg=="ja" else "secondary"):
            st.session_state.lang="ja"; st.query_params["lang"]="ja"; st.rerun()
    with lc2:
        if st.button("English",key="sen",use_container_width=True,type="primary" if lg=="en" else "secondary"):
            st.session_state.lang="en"; st.query_params["lang"]="en"; st.rerun()

    st.markdown(f"<p class='sec'>{t['notif_sec']}</p>",unsafe_allow_html=True)
    st.markdown("<div class='glass' style='padding:14px 16px'>",unsafe_allow_html=True)
    notif=st.checkbox(t["notif_auto"],value=st.session_state.notif_auto)
    st.session_state.notif_auto=notif
    st.markdown(f"<div style='margin-top:12px;margin-bottom:5px'><span style='font-size:12.5px;font-weight:500;color:var(--tx2)'>{t['hist_limit']}</span></div>",unsafe_allow_html=True)
    lim=st.slider("",5,50,st.session_state.history_limit,5,label_visibility="collapsed")
    st.session_state.history_limit=lim
    st.markdown("</div>",unsafe_allow_html=True)
