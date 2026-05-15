import streamlit as st
import os
import time
import difflib
from datetime import datetime
from dotenv import load_dotenv
from core.orchestrator import run_pipeline, TaskResult
from core.sandbox import read_target_code, apply_code

load_dotenv()

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
    return "\n".join(lines) if lines else "<span class='d-ctx'>変更なし</span>"

st.set_page_config(page_title="CodeBridge", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,[data-testid="stAppViewContainer"]{background:#f2f2f7!important;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',sans-serif;color:#1d1d1f;-webkit-font-smoothing:antialiased}
[data-testid="stSidebar"]{background:rgba(242,242,247,0.85)!important;backdrop-filter:saturate(180%) blur(20px)!important;border-right:1px solid rgba(0,0,0,0.08)!important}
[data-testid="stSidebar"]>div:first-child{padding:28px 20px}
.main .block-container{padding:32px 40px 48px;max-width:1100px}
h1{font-size:28px;font-weight:600;letter-spacing:-.4px;color:#1d1d1f}
p,.stMarkdown p{font-size:15px;line-height:1.6;color:#3d3d3f}
.cb-logo{font-size:17px;font-weight:700;letter-spacing:-.5px;color:#1d1d1f;margin-bottom:4px}
.cb-sub{font-size:12px;color:#8e8e93;font-weight:400;margin-bottom:24px;display:block}
.glass{background:rgba(255,255,255,0.75);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);border:1px solid rgba(255,255,255,0.9);border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.06),0 0 0 0.5px rgba(0,0,0,0.04);padding:20px 22px;margin-bottom:14px}
.glass-sm{background:rgba(255,255,255,0.75);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.9);border-radius:12px;box-shadow:0 1px 6px rgba(0,0,0,0.05);padding:12px 14px;margin-bottom:8px}
.accent-blue{border-left:3px solid #007aff}
.accent-green{border-left:3px solid #34c759}
.accent-amber{border-left:3px solid #ff9500}
.accent-red{border-left:3px solid #ff3b30}
.metric-card{background:rgba(255,255,255,0.75);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.9);border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,0.05);padding:16px 18px;text-align:center}
.metric-label{font-size:11px;font-weight:500;color:#8e8e93;letter-spacing:.3px;text-transform:uppercase}
.metric-value{font-size:32px;font-weight:300;letter-spacing:-1px;color:#1d1d1f;line-height:1.1;margin:4px 0 2px}
.metric-unit{font-size:13px;color:#8e8e93}
.section-header{font-size:11px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;color:#8e8e93;margin:24px 0 10px;padding-bottom:8px;border-bottom:1px solid rgba(0,0,0,0.06)}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block}
.dot-green{background:#34c759}
.dot-red{background:#ff3b30}
.stButton>button{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif!important;font-size:14px!important;font-weight:500!important;border-radius:10px!important;padding:10px 20px!important;transition:all .15s ease!important}
.stButton>button[kind="primary"]{background:#007aff!important;border:none!important;box-shadow:0 2px 8px rgba(0,122,255,.3)!important}
.stButton>button[kind="primary"]:hover{background:#0066d6!important;transform:translateY(-1px)!important}
.stButton>button:not([kind="primary"]){background:rgba(255,255,255,.9)!important;border:1px solid rgba(0,0,0,.12)!important;color:#1d1d1f!important}
.stTextArea textarea,.stTextInput input{background:rgba(255,255,255,.9)!important;border:1px solid rgba(0,0,0,.10)!important;border-radius:10px!important;font-size:14px!important;color:#1d1d1f!important;box-shadow:0 1px 4px rgba(0,0,0,.04)!important}
.stTextArea textarea:focus,.stTextInput input:focus{border-color:rgba(0,122,255,.5)!important;box-shadow:0 0 0 3px rgba(0,122,255,.12)!important}
.stProgress>div>div>div{background:#007aff!important;border-radius:4px!important}
.stProgress>div>div{background:rgba(0,0,0,.06)!important;border-radius:4px!important}
.stTabs [data-baseweb="tab-list"]{background:rgba(0,0,0,.04)!important;border-radius:10px!important;padding:3px!important;gap:2px!important;border:none!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:8px!important;font-size:13px!important;font-weight:500!important;color:#8e8e93!important;padding:6px 14px!important;border:none!important}
.stTabs [aria-selected="true"]{background:rgba(255,255,255,.9)!important;color:#1d1d1f!important;box-shadow:0 1px 4px rgba(0,0,0,.08)!important}
.stAlert{border-radius:12px!important;font-size:14px!important;border:none!important}
.d-add{background:rgba(52,199,89,.10);color:#1a7a35;padding:1px 8px;border-left:2px solid #34c759;display:block;font-family:monospace;font-size:12.5px}
.d-del{background:rgba(255,59,48,.10);color:#c0392b;padding:1px 8px;border-left:2px solid #ff3b30;display:block;font-family:monospace;font-size:12.5px}
.d-ctx{color:#8e8e93;padding:1px 8px;display:block;font-family:monospace;font-size:12.5px}
.d-hdr{color:#007aff;padding:1px 8px;display:block;font-family:monospace;font-size:12px;font-weight:500}
[data-testid="stHorizontalBlock"]{gap:12px}
footer{display:none}#MainMenu{visibility:hidden}[data-testid="stDecoration"]{display:none}
</style>""", unsafe_allow_html=True)

for k,v in {"mode":"user","result":None,"deployed":False,"engineer_auth":False,"history":[]}.items():
    if k not in st.session_state: st.session_state[k] = v

with st.sidebar:
    st.markdown("<div class='cb-logo'>CodeBridge</div><span class='cb-sub'>AIがコードを。あなたが承認する。</span>", unsafe_allow_html=True)
    mode = st.radio("画面", ["リクエスト","エンジニアレビュー"], index=0 if st.session_state.mode=="user" else 1)
    st.session_state.mode = "user" if mode=="リクエスト" else "engineer"
    if st.session_state.mode=="engineer" and not st.session_state.engineer_auth:
        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
        pw = st.text_input("パスワード", type="password", placeholder="エンジニア専用")
        if pw == os.getenv("ENGINEER_PASSWORD","engineer123"):
            st.session_state.engineer_auth = True; st.rerun()
        elif pw:
            st.markdown("<div class='glass-sm accent-red' style='margin-top:8px'><span style='font-size:13px;color:#c0392b'>パスワードが違います</span></div>", unsafe_allow_html=True)
    if st.session_state.history:
        st.markdown("<p class='section-header'>最近のリクエスト</p>", unsafe_allow_html=True)
        for h in st.session_state.history[-4:][::-1]:
            st.markdown(f"<div class='glass-sm'><span style='font-size:12px;color:#3d3d3f;line-height:1.4'>{h}</span></div>", unsafe_allow_html=True)

if st.session_state.mode == "user":
    st.markdown("<h1>変更をリクエスト</h1>", unsafe_allow_html=True)
    st.markdown("<p style='margin-top:6px;margin-bottom:28px;color:#6e6e73'>変えたいことを日本語で伝えるだけで、AIがコードに変換します。エンジニアが確認・承認した後に本番環境へ反映されます。</p>", unsafe_allow_html=True)
    with st.form("user_form"):
        instruction = st.text_area("指示内容", placeholder="例：\n・シフト表のヘッダー背景色を変えたい\n・KPIカードの数字を大きくしてほしい\n・テーブル行ホバー時にハイライトを追加したい", height=160)
        submitted = st.form_submit_button("AIに送信", use_container_width=True, type="primary")
    if submitted and instruction.strip():
        st.session_state.deployed = False; st.session_state.result = None
        bar_ph = st.empty(); msg_ph = st.empty()
        steps = [("指示を解析しています",0.20),("コードを生成しています",0.45),("サンドボックスで動作を検証しています",0.70),("AIが結果を確認しています",0.88),("エンジニア向けレポートを作成しています",0.96)]
        bar = bar_ph.progress(0)
        for msg,pct in steps:
            msg_ph.markdown(f"<div class='glass-sm' style='margin-top:12px'><span style='font-size:13px;color:#3d3d3f'>{msg}...</span></div>", unsafe_allow_html=True)
            bar.progress(pct); time.sleep(0.35)
        result = run_pipeline(instruction)
        st.session_state.result = result
        st.session_state.history.append(f"{datetime.now().strftime('%H:%M')}  {instruction[:28]}{'...' if len(instruction)>28 else ''}")
        bar_ph.empty(); msg_ph.empty()
        if result.success:
            st.markdown("<div class='glass accent-green' style='margin-top:16px'><span style='font-size:14px;font-weight:500;color:#1a7a35'>コードを生成しました</span><br><span style='font-size:13px;color:#6e6e73;margin-top:4px;display:block'>エンジニアが確認中です。承認後に本番環境へ反映されます。</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='glass accent-amber' style='margin-top:16px'><span style='font-size:14px;font-weight:500;color:#7a4a00'>エンジニアの確認が必要です</span><br><span style='font-size:13px;color:#6e6e73;margin-top:4px;display:block'>AIは対応を試みましたが、一部に課題があります。エンジニア画面を確認してください。</span></div>", unsafe_allow_html=True)
    elif submitted:
        st.warning("指示内容を入力してください")
    if st.session_state.deployed:
        st.markdown(f"<div class='glass accent-green' style='margin-top:16px'><span style='font-size:14px;font-weight:500;color:#1a7a35'>本番環境への反映が完了しました</span><br><span style='font-size:12px;color:#8e8e93;margin-top:4px;display:block'>反映日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>", unsafe_allow_html=True)

elif st.session_state.mode == "engineer":
    if not st.session_state.engineer_auth:
        st.markdown("<div class='glass' style='margin-top:40px;text-align:center;padding:40px'><span style='font-size:15px;color:#3d3d3f'>サイドバーからパスワードを入力してください</span></div>", unsafe_allow_html=True)
        st.stop()
    result = st.session_state.result
    if result is None:
        st.markdown("<div class='glass' style='margin-top:40px;text-align:center;padding:40px'><span style='font-size:15px;color:#3d3d3f'>リクエスト画面から指示を送ると、ここにレビュー内容が表示されます</span></div>", unsafe_allow_html=True)
        st.stop()
    st.markdown("<h1>エンジニアレビュー</h1>", unsafe_allow_html=True)
    st.markdown("<p style='margin-top:6px;margin-bottom:28px;color:#6e6e73'>AIが生成した変更内容を確認し、承認または差し戻しを行います。</p>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        dot="dot-green" if result.success else "dot-red"; label="テスト成功" if result.success else "テスト失敗"
        st.markdown(f"<div class='metric-card'><div class='metric-label'>サンドボックス</div><div style='margin-top:10px'><span class='dot {dot}'></span> <span style='font-size:14px;font-weight:500;color:#1d1d1f'>{label}</span></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>デバッグ試行</div><div class='metric-value'>{result.iterations}</div><div class='metric-unit'>回</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>変更行数</div><div class='metric-value'>{result.changed_lines}</div><div class='metric-unit'>行</div></div>", unsafe_allow_html=True)
    st.markdown("<p class='section-header' style='margin-top:28px'>ユーザーからの指示</p>", unsafe_allow_html=True)
    st.markdown(f"<div class='glass accent-blue'><span style='font-size:14px;line-height:1.6;color:#1d1d1f'>{_esc(result.instruction)}</span></div>", unsafe_allow_html=True)
    st.markdown("<p class='section-header'>AIレポート</p>", unsafe_allow_html=True)
    st.markdown(f"<div class='glass accent-amber'>{result.report}</div>", unsafe_allow_html=True)
    st.markdown("<p class='section-header'>コード変更内容</p>", unsafe_allow_html=True)
    tab1,tab2,tab3 = st.tabs(["差分","変更前","変更後"])
    with tab1:
        st.markdown(f"<div class='glass' style='padding:16px 18px;overflow-x:auto'>{_build_diff_html(result.original_code,result.new_code)}</div>", unsafe_allow_html=True)
    with tab2: st.code(result.original_code, language="python")
    with tab3: st.code(result.new_code, language="python")
    with st.expander("実行ログを確認"):
        if result.test_output: st.code(result.test_output, language="bash")
        else: st.markdown("<span style='font-size:13px;color:#8e8e93'>出力なし</span>", unsafe_allow_html=True)
        if result.test_error: st.code(result.test_error, language="bash")
    st.markdown("<p class='section-header' style='margin-top:28px'>判断</p>", unsafe_allow_html=True)
    col_ok,col_ng = st.columns(2)
    with col_ok:
        st.markdown("<div class='glass' style='padding:20px 22px'><span style='font-size:14px;font-weight:500;color:#1d1d1f'>承認してデプロイ</span><br><span style='font-size:12px;color:#8e8e93;display:block;margin-top:4px;margin-bottom:14px'>バックアップを取得した後、本番環境に反映します</span>", unsafe_allow_html=True)
        if st.button("承認", use_container_width=True, type="primary", key="approve"):
            with st.spinner("反映しています..."): apply_code(result.new_code); time.sleep(1.2)
            st.session_state.deployed = True
            st.markdown("<div class='glass-sm accent-green' style='margin-top:10px'><span style='font-size:13px;color:#1a7a35;font-weight:500'>デプロイが完了しました</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_ng:
        st.markdown("<div class='glass' style='padding:20px 22px'><span style='font-size:14px;font-weight:500;color:#1d1d1f'>差し戻して再生成</span><br><span style='font-size:12px;color:#8e8e93;display:block;margin-top:4px;margin-bottom:14px'>修正コメントを添えてAIに再依頼します</span>", unsafe_allow_html=True)
        feedback = st.text_area("修正コメント", placeholder="例：ボタンの色を青ではなく緑にしてください", height=90, label_visibility="collapsed")
        if st.button("再生成", use_container_width=True, key="regen"):
            if feedback.strip():
                with st.spinner("再生成しています..."):
                    new_result = run_pipeline(f"{result.instruction}\n\n【修正指示】{feedback}", result.original_code)
                st.session_state.result = new_result; st.rerun()
            else: st.warning("修正コメントを入力してください")
        st.markdown("</div>", unsafe_allow_html=True)
