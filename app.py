# -*- coding: utf-8 -*-
import streamlit as st
import os, time, difflib, io
from datetime import datetime
from dotenv import load_dotenv
from core.orchestrator import run_pipeline
from core.sandbox import read_target_code, apply_code
import core.auth as auth

load_dotenv()

# ── ページ設定（最初に一度だけ）────────────────────────────────────────────────
st.set_page_config(page_title="CodeBridge", layout="wide", initial_sidebar_state="collapsed")

# ── セッション初期化 ────────────────────────────────────────────────────────────
qp = st.query_params
_def = {
    "logged_in": False, "user": None,
    "theme": qp.get("theme", "dark"),
    "lang":  qp.get("lang",  "en"),
    "mode": "request",
    "sidebar_open": False,
    "result": None, "deployed": False,
    "history": [], "priority": "mid",
    "history_limit": 10,
    "settings_tab": "appearance",
}
for k, v in _def.items():
    if k not in st.session_state:
        st.session_state[k] = v

D  = st.session_state.theme == "dark"
lg = st.session_state.lang

# ── i18n ────────────────────────────────────────────────────────────────────────
def _t(ja, en): return ja if lg == "ja" else en

ROLES = {"requester": _t("リクエスター","Requester"),
         "engineer":  _t("エンジニア","Engineer"),
         "admin":     _t("管理者","Admin")}
PRIO_KEYS = ["low","mid","high","urgent"]
SYSTEM_URL = "https://nobushi-shift.webdav-lolipop.jp/demo_codebrige.html"
SYSTEM_NAME = _t("シフト管理","Shift Management")

# ── CSS（テーマ固定でキャッシュ）──────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _css(dark: bool) -> str:
    if dark:
        BG="#111113"; BG2="#1c1c1e"; SFC="rgba(28,28,30,0.97)"; SFC2="rgba(38,38,40,0.98)"
        GLB="rgba(255,255,255,0.10)"; BRD="rgba(255,255,255,0.12)"
        TXT="#f5f5f7"; TX2="#d1d1d6"; TX3="#8e8e93"
        INB="rgba(44,44,46,0.98)"; INR="rgba(255,255,255,0.20)"
        SHD="0 4px 24px rgba(0,0,0,0.55)"
        PBGC="#f5f5f7"; PTXT="#111113"
        SBGC="rgba(44,44,46,0.9)"; STXT="#d1d1d6"; SBRD="rgba(255,255,255,0.14)"
    else:
        BG="#f2f2f7"; BG2="#e5e5ea"; SFC="rgba(255,255,255,0.96)"; SFC2="rgba(242,242,247,0.98)"
        GLB="rgba(255,255,255,0.85)"; BRD="rgba(0,0,0,0.09)"
        TXT="#111113"; TX2="#3a3a3c"; TX3="#6d6d72"
        INB="#ffffff"; INR="rgba(0,0,0,0.22)"
        SHD="0 2px 12px rgba(0,0,0,0.09)"
        PBGC="#111113"; PTXT="#ffffff"
        SBGC="rgba(242,242,247,0.95)"; STXT="#3a3a3c"; SBRD="rgba(0,0,0,0.10)"
    return f"""
:root{{
  --bg:{BG};--bg2:{BG2};--sfc:{SFC};--sfc2:{SFC2};
  --glb:{GLB};--brd:{BRD};--txt:{TXT};--tx2:{TX2};--tx3:{TX3};
  --inb:{INB};--inr:{INR};--shd:{SHD};
  --pbg:{PBGC};--ptxt:{PTXT};
  --sbg:{SBGC};--stxt:{STXT};--sbrd:{SBRD};
  --grn:#34c759;--amb:#ff9500;--red:#ff3b30;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,[data-testid="stAppViewContainer"]{{
  background:var(--bg)!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',sans-serif;
  color:var(--txt);-webkit-font-smoothing:antialiased;
}}
/* ── サイドバー ── */
[data-testid="stSidebar"]{{
  background:var(--sbg)!important;
  backdrop-filter:saturate(200%) blur(24px)!important;
  border-right:1px solid var(--sbrd)!important;
}}
[data-testid="stSidebar"]>div:first-child{{padding:18px 14px 16px}}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div{{color:var(--stxt)!important}}
/* ── メインコンテンツ ── */
.main .block-container{{padding:20px 24px 48px;max-width:1020px}}
h1{{font-size:21px;font-weight:600;letter-spacing:-.3px;color:var(--txt)!important}}
h2{{font-size:16px;font-weight:600;color:var(--txt)!important}}
p,.stMarkdown p{{font-size:14px;line-height:1.6;color:var(--tx2)!important}}
/* ── ガラスカード ── */
.g{{background:var(--sfc);backdrop-filter:blur(20px);
  border:1px solid var(--glb);border-radius:13px;
  box-shadow:var(--shd);padding:15px 17px;margin-bottom:10px}}
.gs{{background:var(--sfc2);border:1px solid var(--brd);border-radius:10px;
  padding:9px 12px;margin-bottom:6px}}
.al{{border-left:3px solid var(--txt)}}
.ag{{border-left:3px solid var(--grn)}}
.aa{{border-left:3px solid var(--amb)}}
.ar{{border-left:3px solid var(--red)}}
/* ── メトリクス ── */
.mc{{background:var(--sfc);border:1px solid var(--glb);border-radius:12px;
  box-shadow:var(--shd);padding:13px 14px;text-align:center}}
.ml{{font-size:9.5px;font-weight:700;color:var(--tx3);letter-spacing:.5px;text-transform:uppercase}}
.mv{{font-size:26px;font-weight:300;letter-spacing:-1px;color:var(--txt);line-height:1.1;margin:4px 0 2px}}
.mu{{font-size:11px;color:var(--tx3)}}
/* ── セクションヘッダー ── */
.sec{{font-size:9.5px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;
  color:var(--tx3);margin:16px 0 7px;padding-bottom:5px;border-bottom:1px solid var(--brd)}}
/* ── ドット・バッジ ── */
.dot{{width:6px;height:6px;border-radius:50%;display:inline-block;margin-right:4px}}
.dg{{background:var(--grn)}}.dr{{background:var(--red)}}
.badge{{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600}}
/* ── ボタン ── */
.stButton>button,
[data-testid="stFormSubmitButton"]>button{{
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  font-size:13px!important;font-weight:500!important;border-radius:9px!important;
  padding:8px 14px!important;transition:opacity .12s,transform .12s!important;
  white-space:nowrap!important;min-height:40px!important;line-height:1.2!important;
}}
.stButton>button[kind="primary"],
[data-testid="stFormSubmitButton"]>button{{
  background:var(--pbg)!important;border:none!important;color:var(--ptxt)!important;
  box-shadow:0 2px 8px rgba(0,0,0,0.25)!important;
}}
.stButton>button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"]>button:hover{{opacity:.80!important;transform:translateY(-1px)!important}}
.stButton>button:not([kind="primary"]){{
  background:var(--sfc2)!important;border:1px solid var(--brd)!important;color:var(--txt)!important;
}}
.stButton>button:not([kind="primary"]):hover{{opacity:.80!important;transform:translateY(-1px)!important}}
/* ── 入力 ── */
.stTextArea textarea,.stTextInput input{{
  background:var(--inb)!important;border:1.5px solid var(--inr)!important;
  border-radius:10px!important;font-size:13.5px!important;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;
  color:var(--txt)!important;padding:9px 11px!important;
}}
.stTextArea textarea::placeholder,.stTextInput input::placeholder{{color:var(--tx3)!important;opacity:1!important}}
.stTextArea textarea:focus,.stTextInput input:focus{{
  border-color:rgba({'255,255,255,0.45' if dark else '0,0,0,0.40'})!important;
  box-shadow:0 0 0 2px rgba({'255,255,255,0.07' if dark else '0,0,0,0.06'})!important;
  outline:none!important;
}}
label,[data-testid="stWidgetLabel"]{{color:var(--tx2)!important;font-size:12.5px!important;font-weight:500!important}}
/* ── プログレス ── */
.stProgress>div>div>div{{background:var(--pbg)!important;border-radius:3px!important}}
.stProgress>div>div{{background:var(--brd)!important;border-radius:3px!important}}
/* ── タブ ── */
.stTabs [data-baseweb="tab-list"]{{background:var(--bg2)!important;border-radius:9px!important;padding:3px!important;gap:2px!important;border:none!important}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;border-radius:7px!important;font-size:12.5px!important;font-weight:500!important;color:var(--tx3)!important;padding:5px 11px!important;border:none!important;white-space:nowrap!important}}
.stTabs [aria-selected="true"]{{background:var(--sfc)!important;color:var(--txt)!important;box-shadow:0 1px 4px rgba(0,0,0,0.20)!important}}
/* ── アラート ── */
.stAlert{{border-radius:11px!important;font-size:13px!important;border:none!important}}
/* ── Diff ── */
.da{{background:rgba(52,199,89,.12);color:{'#5be075' if dark else '#1a6b30'};padding:1px 8px;border-left:2px solid var(--grn);display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dd{{background:rgba(255,59,48,.10);color:{'#ff6961' if dark else '#a01010'};padding:1px 8px;border-left:2px solid var(--red);display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dc{{color:var(--tx3);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:12px}}
.dh{{color:var(--tx2);padding:1px 8px;display:block;font-family:'SF Mono',monospace;font-size:11px;font-weight:600}}
/* ── misc ── */
[data-testid="stHorizontalBlock"]{{gap:7px}}
footer{{display:none}}#MainMenu{{visibility:hidden}}[data-testid="stDecoration"]{{display:none}}
hr{{border:none;border-top:1px solid var(--brd);margin:10px 0}}
.stCheckbox>label{{color:var(--tx2)!important;font-size:13px!important}}
.stRadio>div label{{color:var(--tx2)!important}}
.stSelectbox>div>div{{background:var(--inb)!important;border:1.5px solid var(--inr)!important;border-radius:10px!important;color:var(--txt)!important}}
::-webkit-scrollbar{{width:4px;height:4px}}
::-webkit-scrollbar-thumb{{background:var(--brd);border-radius:2px}}
/* ── モバイル対応 ── */
@media(max-width:768px){{
  .main .block-container{{padding:12px 10px 28px!important}}
  h1{{font-size:18px!important}}
  .mv{{font-size:22px!important}}
  .g{{padding:12px 12px!important}}
}}
/* ── ハンバーガー非表示のデフォルト制御 ── */
[data-testid="collapsedControl"]{{display:flex!important}}
"""

st.markdown(f"<style>{_css(D)}</style>", unsafe_allow_html=True)

# ── JS: スマホでサイドバーを閉じた状態をデフォルトに ─────────────────────────
st.markdown("""<script>
(function(){
  function closeSidebarOnMobile(){
    if(window.innerWidth<=768){
      var btn=document.querySelector('[data-testid="collapsedControl"]');
      var sidebar=document.querySelector('[data-testid="stSidebar"]');
      if(sidebar && sidebar.getAttribute('aria-expanded')==='true' && btn){
        // 初回ロード時のみ閉じる
        if(!window._cbInit){ window._cbInit=true; btn.click(); }
      }
    }
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',closeSidebarOnMobile);
  } else { closeSidebarOnMobile(); }
})();
</script>""", unsafe_allow_html=True)

def _esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _diff(a,b):
    out=[]
    for ln in difflib.unified_diff(a.splitlines(),b.splitlines(),lineterm="",n=3):
        if ln.startswith(("+++","---","@@")): out.append(f"<span class='dh'>{_esc(ln)}</span>")
        elif ln.startswith("+"): out.append(f"<span class='da'>{_esc(ln)}</span>")
        elif ln.startswith("-"): out.append(f"<span class='dd'>{_esc(ln)}</span>")
        else: out.append(f"<span class='dc'>{_esc(ln)}</span>")
    return "\n".join(out) or "<span class='dc'>No changes</span>"

def _card(content, cls="g", extra=""):
    st.markdown(f"<div class='{cls}' style='{extra}'>{content}</div>", unsafe_allow_html=True)

def _sec(label):
    st.markdown(f"<div class='sec'>{label}</div>", unsafe_allow_html=True)

# ── ログイン画面 ────────────────────────────────────────────────────────────────
def show_login():
    st.markdown("<div style='max-width:360px;margin:60px auto'>", unsafe_allow_html=True)
    _card(
        f"<div style='font-size:22px;font-weight:700;letter-spacing:-.4px;color:var(--txt);margin-bottom:4px'>CodeBridge</div>"
        f"<div style='font-size:13px;color:var(--tx3);margin-bottom:20px'>"
        + _t("ログインしてください","Please sign in") + "</div>",
        extra="max-width:360px;margin:0 auto"
    )
    email = st.text_input(_t("メールアドレス","Email"), key="li_email", placeholder="you@example.com")
    pw    = st.text_input(_t("パスワード","Password"), type="password", key="li_pw")
    if st.button(_t("ログイン","Sign in"), use_container_width=True, type="primary", key="li_btn"):
        user = auth.login(email, pw)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            # 権限によって初期画面を決める
            st.session_state.mode = "request" if user["role"]=="requester" else "request"
            st.rerun()
        else:
            st.error(_t("メールアドレスまたはパスワードが違います","Invalid email or password"))
    st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    show_login()
    st.stop()

user = st.session_state.user
role = user["role"]  # requester / engineer / admin
PRIO_C = {"low":"#34c759","mid": "#f5f5f7" if D else "#111113",
           "high":"#ff9500","urgent":"#ff3b30"}

# ── サイドバー ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # ユーザー情報
    st.markdown(
        f"<div style='font-size:15px;font-weight:700;letter-spacing:-.3px;color:var(--stxt)'>{user['name']}</div>"
        f"<div style='font-size:11.5px;color:var(--tx3);margin-bottom:12px'>{user['email']} · {ROLES.get(role,role)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    # ナビゲーション
    nav_items = [("request", _t("リクエスト","Request"))]
    if role in ("engineer","admin"):
        nav_items.append(("engineer", _t("エンジニア","Engineer")))
    if role == "admin":
        nav_items.append(("admin", _t("管理","Admin")))
    nav_items.append(("settings", _t("設定","Settings")))

    for k,lbl in nav_items:
        tp = "primary" if st.session_state.mode==k else "secondary"
        if st.button(lbl, key=f"nav_{k}", use_container_width=True, type=tp):
            st.session_state.mode=k; st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # システム
    st.markdown(f"<div class='sec'>{_t('対象システム','System')}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;padding:7px 0'>"
        f"<div style='width:7px;height:7px;border-radius:50%;background:var(--grn);flex-shrink:0'></div>"
        f"<span style='font-size:13px;color:var(--stxt)'>{SYSTEM_NAME}</span></div>",
        unsafe_allow_html=True,
    )

    if st.session_state.history:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<div class='sec'>{_t('最近のリクエスト','Recent')}</div>", unsafe_allow_html=True)
        for h in st.session_state.history[-5:][::-1]:
            st.markdown(f"<div class='gs'><span style='font-size:11px;color:var(--tx2)'>{h}</span></div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button(_t("ログアウト","Sign out"), key="logout"):
        for k in ["logged_in","user","result","deployed","history"]:
            st.session_state[k] = False if k=="logged_in" else (None if k in ("user","result") else [])
        st.rerun()

# ── 右上：設定ギアボタン ─────────────────────────────────────────────────────
c_title, c_gear = st.columns([10,1])
with c_title:
    mode_titles = {
        "request":  _t("変更をリクエスト","Request Changes"),
        "engineer": _t("エンジニアレビュー","Engineer Review"),
        "admin":    _t("管理","Admin"),
        "settings": _t("設定","Settings"),
    }
    st.markdown(f"<h1>{mode_titles.get(st.session_state.mode,'CodeBridge')}</h1>", unsafe_allow_html=True)
with c_gear:
    if st.button("⚙", key="gear_btn", help=_t("設定","Settings")):
        st.session_state.mode = "settings"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# リクエスト画面
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "request":

    # 重要度（フォーム外で即時反映）
    st.markdown(f"<div style='font-size:12.5px;font-weight:600;color:var(--tx2);margin-bottom:6px'>"
                + _t("重要度","Priority") + "</div>", unsafe_allow_html=True)
    pp=st.columns(4)
    prio_labels = {
        "low":_t("低","Low"),"mid":_t("中","Med"),
        "high":_t("高","High"),"urgent":_t("緊急","Urgent")
    }
    for col,pk in zip(pp,PRIO_KEYS):
        with col:
            sel=(st.session_state.priority==pk)
            if st.button(prio_labels[pk],key=f"pr{pk}",use_container_width=True,type="primary" if sel else "secondary"):
                st.session_state.priority=pk; st.rerun()

    with st.form("rf",clear_on_submit=False):
        instruction = st.text_area(
            _t("指示内容","Instructions"),
            placeholder=_t(
                "例：\n・シフト表のヘッダー色を変えたい\n・KPIの数字フォントを大きくしたい",
                "e.g.:\n· Change the header background color\n· Make KPI numbers larger"
            ),
            height=140,
        )
        eng_comment = st.text_area(
            _t("エンジニアへのコメント（任意）","Comment to Engineer (optional)"),
            placeholder=_t("補足情報があれば","Add any notes here"),
            height=68,
        )
        submitted = st.form_submit_button(
            _t("AIに送信","Send to AI"), use_container_width=True, type="primary"
        )

    if submitted and instruction.strip():
        st.session_state.deployed=False; st.session_state.result=None
        bph=st.empty(); mph=st.empty()
        steps=[_t("解析中","Analyzing"),_t("生成中","Generating"),
               _t("検証中","Validating"),_t("確認中","Verifying"),_t("レポート作成中","Reporting")]
        bar=bph.progress(0)
        for i,msg in enumerate(steps):
            mph.markdown(f"<div class='gs' style='margin-top:7px'><span style='font-size:13px;color:var(--tx2)'>{msg}...</span></div>",unsafe_allow_html=True)
            bar.progress(int((i+1)/len(steps)*95)); time.sleep(0.2)
        full=instruction+(f"\n\n[Comment]\n{eng_comment}" if eng_comment.strip() else "")
        result=run_pipeline(full)
        result._priority=st.session_state.priority; result._eng_comment=eng_comment
        st.session_state.result=result
        lbl2=instruction[:28]+"…" if len(instruction)>28 else instruction
        st.session_state.history.append(f"{datetime.now().strftime('%H:%M')}  {lbl2}")
        # ログ記録
        auth.log_action(user["id"],user["name"],
                        "request",instruction[:200],result.cost_usd)
        auth.log_cost(user["id"],instruction,result.input_tokens,result.output_tokens,result.cost_usd)
        bph.empty(); mph.empty()
        if result.success:
            st.markdown(f"<div class='g ag'><span style='font-size:13.5px;font-weight:600;color:var(--grn)'>{_t('コードを生成しました','Code generated')}</span><br><span style='font-size:12.5px;color:var(--tx2);margin-top:3px;display:block'>{_t('エンジニアが確認中です','An engineer is reviewing')}</span></div>",unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='g aa'><span style='font-size:13.5px;font-weight:600;color:var(--amb)'>{_t('エンジニアの確認が必要です','Engineer review required')}</span></div>",unsafe_allow_html=True)
    elif submitted:
        st.warning(_t("指示内容を入力してください","Please enter instructions"))

    if st.session_state.deployed:
        st.markdown(f"<div class='g ag'><span style='font-size:13.5px;font-weight:600;color:var(--grn)'>{_t('本番環境への反映が完了しました','Successfully deployed')}</span></div>",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# エンジニア画面
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.mode == "engineer" and role in ("engineer","admin"):
    result=st.session_state.result
    if result is None:
        st.markdown(f"<div class='g' style='text-align:center;padding:32px'><span style='font-size:14px;color:var(--tx2)'>{_t('リクエスト画面から指示を送ると、ここに表示されます','Send a request to see review content here')}</span></div>",unsafe_allow_html=True); st.stop()

    c1,c2,c3=st.columns(3)
    with c1:
        dot="dg" if result.success else "dr"; lbl3=_t("テスト成功","Test Passed") if result.success else _t("テスト失敗","Test Failed")
        st.markdown(f"<div class='mc'><div class='ml'>{_t('サンドボックス','Sandbox')}</div><div style='margin-top:8px'><span class='dot {dot}'></span><span style='font-size:13px;font-weight:600;color:var(--txt)'>{lbl3}</span></div></div>",unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='mc'><div class='ml'>{_t('デバッグ試行','Debug')}</div><div class='mv'>{result.iterations}</div><div class='mu'>{_t('回','times')}</div></div>",unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='mc'><div class='ml'>{_t('変更行数','Lines')}</div><div class='mv'>{result.changed_lines}</div><div class='mu'>{_t('行','lines')}</div></div>",unsafe_allow_html=True)

    prio=getattr(result,'_priority','mid')
    pc_col=PRIO_C.get(prio,"#8e8e93")
    st.markdown(f"<div style='margin:5px 0 12px'><span class='badge' style='background:{pc_col}22;color:{pc_col};border:1px solid {pc_col}44'>{_t('重要度','Priority')}: {prio_labels[prio]}</span></div>",unsafe_allow_html=True)

    _sec(_t("ユーザーからの指示","User Instructions"))
    ec=getattr(result,'_eng_comment','')
    instr=result.instruction.split("\n\n[Comment]")[0] if ec else result.instruction
    st.markdown(f"<div class='g al'><span style='font-size:13.5px;line-height:1.65;color:var(--txt)'>{_esc(instr)}</span></div>",unsafe_allow_html=True)
    if ec:
        st.markdown(f"<div class='gs aa'><span style='font-size:10.5px;color:var(--tx3)'>{_t('コメント','Comment')}</span><br><span style='font-size:13.5px;color:var(--tx2)'>{_esc(ec)}</span></div>",unsafe_allow_html=True)

    _sec(_t("AIレポート","AI Report"))
    st.markdown(f"<div class='g aa'>{result.report}</div>",unsafe_allow_html=True)

    _sec(_t("コード変更内容","Code Changes"))
    t1,t2,t3=st.tabs([_t("差分","Diff"),_t("変更前","Before"),_t("変更後","After")])
    with t1: st.markdown(f"<div class='g' style='padding:11px 13px;overflow-x:auto'>{_diff(result.original_code,result.new_code)}</div>",unsafe_allow_html=True)
    with t2: st.code(result.original_code,language="html")
    with t3: st.code(result.new_code,language="html")

    with st.expander(_t("実行ログ","Execution Log")):
        if result.test_output: st.code(result.test_output,language="bash")
        if result.test_error:  st.code(result.test_error,language="bash")
        if not result.test_output and not result.test_error:
            st.markdown(f"<span style='font-size:12.5px;color:var(--tx3)'>{_t('出力なし','No output')}</span>",unsafe_allow_html=True)

    _sec(_t("判断","Decision"))
    ok,ng=st.columns(2)
    with ok:
        st.markdown(f"<div class='g' style='padding:14px 16px'><span style='font-size:13.5px;font-weight:600;color:var(--txt)'>{_t('承認してデプロイ','Approve & Deploy')}</span><br><span style='font-size:11.5px;color:var(--tx3);display:block;margin-top:3px;margin-bottom:10px'>{_t('バックアップ後に本番へ反映','Backup taken before deploy')}</span>",unsafe_allow_html=True)
        if st.button(_t("承認","Approve"),use_container_width=True,type="primary",key="ap"):
            with st.spinner("..."): apply_code(result.new_code); time.sleep(0.6)
            st.session_state.deployed=True
            auth.log_action(user["id"],user["name"],"approve",result.instruction[:100])
            st.markdown(f"<div class='gs ag'><span style='font-size:12.5px;color:var(--grn);font-weight:600'>{_t('デプロイ完了','Deploy complete')}</span></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
    with ng:
        st.markdown(f"<div class='g' style='padding:14px 16px'><span style='font-size:13.5px;font-weight:600;color:var(--txt)'>{_t('差し戻して再生成','Reject & Regenerate')}</span><br><span style='font-size:11.5px;color:var(--tx3);display:block;margin-top:3px;margin-bottom:10px'>{_t('修正コメントを添えてAIに再依頼','Send correction to AI')}</span>",unsafe_allow_html=True)
        fb=st.text_area(_t("修正コメント","Correction"),height=80,label_visibility="collapsed",key="fb")
        if st.button(_t("再生成","Regenerate"),use_container_width=True,key="rg"):
            if fb.strip():
                with st.spinner("..."):
                    nr=run_pipeline(f"{result.instruction}\n\n[Correction]\n{fb}",result.original_code)
                auth.log_action(user["id"],user["name"],"reject_regen",fb[:100])
                st.session_state.result=nr; st.rerun()
            else: st.warning(_t("修正コメントを入力してください","Please enter correction comments"))
        st.markdown("</div>",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 管理画面
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.mode == "admin" and role == "admin":
    atabs = st.tabs([
        _t("ユーザー管理","Users"),
        _t("アクティビティログ","Activity Log"),
        _t("コスト","Cost"),
    ])

    # ── ユーザー管理 ──
    with atabs[0]:
        _sec(_t("ユーザー一覧","User List"))
        users = auth.list_users()
        for u in users:
            c1,c2,c3,c4=st.columns([3,2,2,2])
            with c1: st.markdown(f"<span style='font-size:13px;color:var(--txt)'>{u['name']}</span><br><span style='font-size:11px;color:var(--tx3)'>{u['email']}</span>",unsafe_allow_html=True)
            with c2:
                new_role=st.selectbox("",["requester","engineer","admin"],
                    index=["requester","engineer","admin"].index(u["role"]),
                    key=f"ur{u['id']}",label_visibility="collapsed")
                if new_role!=u["role"]:
                    auth.update_user_role(u["id"],new_role)
                    auth.log_action(user["id"],user["name"],"role_change",f"{u['email']} → {new_role}")
                    st.rerun()
            with c3:
                if st.button(_t("PW リセット","Reset PW"),key=f"rp{u['id']}",use_container_width=True):
                    tmp=auth.reset_password(u["id"])
                    auth.log_action(user["id"],user["name"],"reset_pw",u["email"])
                    st.success(f"{_t('仮パスワード','Temp PW')}: `{tmp}`")
            with c4:
                if u["id"] != user["id"]:
                    label = _t("無効化","Disable") if u["active"] else _t("有効化","Enable")
                    if st.button(label,key=f"ta{u['id']}",use_container_width=True):
                        auth.toggle_user_active(u["id"], not u["active"])
                        auth.log_action(user["id"],user["name"],"toggle_user",u["email"])
                        st.rerun()

        _sec(_t("新規ユーザー追加","Add User"))
        nc1,nc2=st.columns(2)
        with nc1:
            nu_name  = st.text_input(_t("名前","Name"),key="nu_name")
            nu_email = st.text_input(_t("メール","Email"),key="nu_email")
        with nc2:
            nu_pw   = st.text_input(_t("初期パスワード","Initial PW"),key="nu_pw",type="password")
            nu_role = st.selectbox(_t("権限","Role"),["requester","engineer","admin"],key="nu_role")
        if st.button(_t("追加","Add"),key="nu_add",type="primary"):
            ok2,msg=auth.create_user(nu_name,nu_email,nu_pw,nu_role)
            if ok2:
                auth.log_action(user["id"],user["name"],"create_user",nu_email)
                st.success(_t("追加しました","User added")); st.rerun()
            else: st.error(msg)

    # ── アクティビティログ ──
    with atabs[1]:
        logs = auth.get_activity_log(500)
        _sec(_t("最新500件","Latest 500 records"))
        for row in logs[:50]:
            st.markdown(
                f"<div class='gs' style='margin-bottom:4px'>"
                f"<span style='font-size:10.5px;color:var(--tx3)'>{row['ts']}</span> "
                f"<span style='font-size:12.5px;color:var(--txt);font-weight:600'>{row['user_name']}</span> "
                f"<span style='font-size:12px;color:var(--tx2)'>{row['action']}</span> "
                f"<span style='font-size:11.5px;color:var(--tx3)'>{(row['detail'] or '')[:60]}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        csv_data=auth.log_to_csv()
        st.download_button(
            _t("CSV ダウンロード","Download CSV"),
            data=csv_data, file_name="activity_log.csv",
            mime="text/csv", type="primary",
        )

    # ── コスト ──
    with atabs[2]:
        monthly=auth.get_monthly_cost()
        _sec(_t(f"今月の合計（{datetime.utcnow().strftime('%Y年%m月')}）",
                f"This Month ({datetime.utcnow().strftime('%B %Y')})"))
        co1,co2,co3=st.columns(3)
        with co1: st.markdown(f"<div class='mc'><div class='ml'>Total Cost</div><div class='mv'>${(monthly['total'] or 0):.4f}</div><div class='mu'>USD</div></div>",unsafe_allow_html=True)
        with co2: st.markdown(f"<div class='mc'><div class='ml'>Input Tokens</div><div class='mv'>{int(monthly['inp'] or 0):,}</div></div>",unsafe_allow_html=True)
        with co3: st.markdown(f"<div class='mc'><div class='ml'>Output Tokens</div><div class='mv'>{int(monthly['out'] or 0):,}</div></div>",unsafe_allow_html=True)
        _sec(_t("リクエスト別コスト","Per Request Cost"))
        for row in auth.get_cost_history(30):
            st.markdown(
                f"<div class='gs'>"
                f"<span style='font-size:10.5px;color:var(--tx3)'>{row['ts']}</span> "
                f"<span style='font-size:12px;color:var(--tx2)'>{(row['request_text'] or '')[:50]}</span> "
                f"<span style='font-size:12px;color:var(--txt);float:right'>${row['cost_usd']:.5f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# 設定画面
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.mode == "settings":
    # 外観
    _sec(_t("外観","Appearance"))
    tc1,tc2=st.columns(2)
    with tc1:
        if st.button(_t("ライト","Light"),key="sl",use_container_width=True,type="primary" if not D else "secondary"):
            st.session_state.theme="light"; st.query_params["theme"]="light"; st.rerun()
    with tc2:
        if st.button(_t("ダーク","Dark"),key="sd",use_container_width=True,type="primary" if D else "secondary"):
            st.session_state.theme="dark"; st.query_params["theme"]="dark"; st.rerun()

    _sec(_t("言語","Language"))
    lc1,lc2=st.columns(2)
    with lc1:
        if st.button("日本語",key="sja",use_container_width=True,type="primary" if lg=="ja" else "secondary"):
            st.session_state.lang="ja"; st.query_params["lang"]="ja"; st.rerun()
    with lc2:
        if st.button("English",key="sen",use_container_width=True,type="primary" if lg=="en" else "secondary"):
            st.session_state.lang="en"; st.query_params["lang"]="en"; st.rerun()

    _sec(_t("パスワード変更","Change Password"))
    st.markdown("<div class='g' style='padding:14px 16px'>",unsafe_allow_html=True)
    old_pw = st.text_input(_t("現在のパスワード","Current Password"),type="password",key="cpw")
    new_pw = st.text_input(_t("新しいパスワード","New Password"),type="password",key="npw")
    new_pw2= st.text_input(_t("新しいパスワード（確認）","Confirm New Password"),type="password",key="npw2")
    if st.button(_t("変更","Change"),key="cpw_btn",type="primary"):
        logged=auth.login(user["email"],old_pw)
        if not logged: st.error(_t("現在のパスワードが違います","Current password is incorrect"))
        elif new_pw!=new_pw2: st.error(_t("新しいパスワードが一致しません","Passwords do not match"))
        elif len(new_pw)<8: st.error(_t("8文字以上必要です","Minimum 8 characters"))
        else:
            auth.change_password(user["id"],new_pw)
            auth.log_action(user["id"],user["name"],"change_password","")
            st.success(_t("パスワードを変更しました","Password changed"))
    st.markdown("</div>",unsafe_allow_html=True)

    if role in ("engineer","admin"):
        _sec(_t("システム情報","System Info"))
        rows=[
            (_t("デモURL","Demo URL"),
             f'<a href="{SYSTEM_URL}" target="_blank" style="color:var(--txt);text-decoration:underline">{SYSTEM_URL}</a>'),
            (_t("ソース","Source"),
             '<code style="font-size:11.5px;color:var(--tx2);background:var(--bg2);padding:2px 6px;border-radius:4px">target_app/demo_local.html</code>'),
        ]
        rh="".join(f"<div style='display:flex;align-items:center;padding:9px 0;border-bottom:1px solid var(--brd);gap:12px'><span style='font-size:9.5px;font-weight:700;color:var(--tx3);text-transform:uppercase;min-width:70px'>{lb}</span><span style='font-size:13px'>{vl}</span></div>" for lb,vl in rows)
        st.markdown(f"<div class='g' style='padding:0 16px'>{rh}</div>",unsafe_allow_html=True)

        if role=="admin":
            _sec(_t("コスト（今月）","Cost This Month"))
            monthly=auth.get_monthly_cost()
            st.markdown(f"<div class='g'><span style='font-size:18px;font-weight:300;color:var(--txt)'>${(monthly['total'] or 0):.4f}</span> <span style='font-size:13px;color:var(--tx3)'>USD</span></div>",unsafe_allow_html=True)
