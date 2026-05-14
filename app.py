import streamlit as st
import os
import time
import difflib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from core.orchestrator import run_pipeline, TaskResult
from core.sandbox import read_target_code, apply_code

load_dotenv()


# ─────────────────────────────────────────────
# ユーティリティ関数（先頭で定義）
# ─────────────────────────────────────────────
def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_diff_html(original: str, new: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(),
        new.splitlines(),
        lineterm="",
        n=3,
    )
    lines = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            lines.append(f"<span class='diff-ctx'>{_esc(line)}</span>")
        elif line.startswith("+"):
            lines.append(f"<span class='diff-add'>{_esc(line)}</span>")
        elif line.startswith("-"):
            lines.append(f"<span class='diff-del'>{_esc(line)}</span>")
        else:
            lines.append(f"<span class='diff-ctx'>{_esc(line)}</span>")
    return "\n".join(lines) if lines else "<span class='diff-ctx'>変更なし</span>"

# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CodeBridge AI",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ベース */
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #1a1d27; border-right: 1px solid #2d3148; }
h1, h2, h3 { color: #e8eaf6; }
p, label, .stMarkdown { color: #b0b8d1; }

/* カード */
.card {
    background: #1e2235;
    border: 1px solid #2d3148;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.card-green  { border-left: 4px solid #00e676; }
.card-blue   { border-left: 4px solid #448aff; }
.card-yellow { border-left: 4px solid #ffd740; }
.card-red    { border-left: 4px solid #ff5252; }

/* ステータスバッジ */
.badge {
    display:inline-block; padding:3px 10px;
    border-radius:20px; font-size:12px; font-weight:600;
}
.badge-ok  { background:#00e67622; color:#00e676; border:1px solid #00e67655; }
.badge-err { background:#ff525222; color:#ff5252; border:1px solid #ff525255; }
.badge-run { background:#448aff22; color:#448aff; border:1px solid #448aff55; }

/* ボタン */
.stButton button {
    border-radius: 8px; font-weight: 600;
    transition: all 0.2s;
}
.stButton button:hover { transform: translateY(-1px); }

/* diff */
.diff-add { background:#00e67615; color:#00e676; padding:2px 8px;
            border-left:3px solid #00e676; display:block; }
.diff-del { background:#ff525215; color:#ff5252; padding:2px 8px;
            border-left:3px solid #ff5252; display:block; }
.diff-ctx { background:#1e223500; color:#8892a4; padding:2px 8px; display:block; }

div[data-testid="stHorizontalBlock"] { gap: 16px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# セッション初期化
# ─────────────────────────────────────────────
for k, v in {
    "mode": "user",
    "result": None,
    "deployed": False,
    "engineer_auth": False,
    "history": [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# サイドバー
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌉 CodeBridge AI")
    st.markdown("<small style='color:#6b7494'>AIがコードを、あなたが承認する</small>",
                unsafe_allow_html=True)
    st.divider()

    mode = st.radio("モード選択", ["🙋 ユーザー画面", "🔧 エンジニア画面"],
                    index=0 if st.session_state.mode == "user" else 1)
    st.session_state.mode = "user" if "ユーザー" in mode else "engineer"

    if st.session_state.mode == "engineer" and not st.session_state.engineer_auth:
        pw = st.text_input("エンジニアパスワード", type="password")
        if pw == os.getenv("ENGINEER_PASSWORD", "engineer123"):
            st.session_state.engineer_auth = True
            st.rerun()
        elif pw:
            st.error("パスワードが違います")

    st.divider()
    if st.session_state.history:
        st.markdown("#### 📋 最近のタスク")
        for h in st.session_state.history[-3:][::-1]:
            st.markdown(f"<small style='color:#6b7494'>• {h}</small>",
                        unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ユーザー画面
# ─────────────────────────────────────────────
if st.session_state.mode == "user":
    st.markdown("# 🙋 システム変更リクエスト")
    st.markdown(
        "<div class='card card-blue'>"
        "<b>非エンジニアの方へ：</b> 変えたいことを日本語で入力するだけでOKです。"
        "AIがコードに翻訳し、エンジニアが確認した後に反映されます。"
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("user_form"):
        instruction = st.text_area(
            "何を変えたいですか？",
            placeholder=(
                "例：\n"
                "・トップページに「現在キャンペーン中」というバナーを追加したい\n"
                "・お問い合わせボタンの色を青から赤に変えてほしい\n"
                "・商品一覧ページに価格でソートする機能をつけたい"
            ),
            height=150,
        )
        submitted = st.form_submit_button("🚀 AIに依頼する", use_container_width=True)

    if submitted and instruction.strip():
        st.session_state.deployed = False
        st.session_state.result = None

        progress_ph = st.empty()
        steps = [
            ("🤖 AIが指示を解析中...", 0.3),
            ("✍️ コードを生成中...", 0.5),
            ("🧪 サンドボックスで動作テスト中...", 0.7),
            ("🔍 AIが結果を検証中...", 0.85),
            ("📝 エンジニア向けレポートを作成中...", 0.95),
        ]
        bar = progress_ph.progress(0)
        status_ph = st.empty()

        for msg, pct in steps:
            status_ph.info(msg)
            bar.progress(pct)
            time.sleep(0.4)

        result: TaskResult = run_pipeline(instruction)
        st.session_state.result = result
        st.session_state.history.append(
            f"{datetime.now().strftime('%H:%M')} — {instruction[:30]}..."
        )

        progress_ph.empty()
        status_ph.empty()

        if result.success:
            st.success(
                "✅ AIがコードを生成しました！エンジニアが確認中です。"
                "承認されると自動的に反映されます。"
            )
        else:
            st.warning(
                "⚠️ AIは対応を試みましたが、エンジニアの確認が必要です。"
                "エンジニア画面を確認してください。"
            )

    elif submitted:
        st.warning("指示を入力してください")

    if st.session_state.deployed:
        st.markdown(
            "<div class='card card-green'>"
            "🎉 <b>本番環境への反映が完了しました！</b><br>"
            f"<small>承認時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>"
            "</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# エンジニア画面
# ─────────────────────────────────────────────
elif st.session_state.mode == "engineer":
    if not st.session_state.engineer_auth:
        st.warning("サイドバーからエンジニアパスワードを入力してください")
        st.stop()

    st.markdown("# 🔧 エンジニアレビュー画面")

    result: TaskResult = st.session_state.result

    if result is None:
        st.info("まだAIからの提案がありません。ユーザー画面からリクエストを送ってください。")
        st.stop()

    # ── ステータス概要 ──────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        badge = "badge-ok" if result.success else "badge-err"
        label = "テスト成功" if result.success else "テスト失敗"
        st.markdown(
            f"<div class='card'><small>サンドボックス</small><br>"
            f"<span class='badge {badge}'>{label}</span></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='card'><small>デバッグ試行回数</small><br>"
            f"<b style='font-size:24px;color:#e8eaf6'>{result.iterations}</b> 回</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div class='card'><small>変更行数</small><br>"
            f"<b style='font-size:24px;color:#e8eaf6'>{result.changed_lines}</b> 行</div>",
            unsafe_allow_html=True,
        )

    # ── 元の指示 ────────────────────────────────
    st.markdown("### 📩 ユーザーからの指示")
    st.markdown(
        f"<div class='card card-blue'>{result.instruction}</div>",
        unsafe_allow_html=True,
    )

    # ── AIレポート ──────────────────────────────
    st.markdown("### 🤖 AIレポート")
    st.markdown(
        f"<div class='card card-yellow'>{result.report}</div>",
        unsafe_allow_html=True,
    )

    # ── コード差分 ──────────────────────────────
    st.markdown("### 📝 コード変更差分（Before / After）")
    tab1, tab2, tab3 = st.tabs(["🔀 差分ビュー", "📄 変更前", "✨ 変更後"])

    with tab1:
        diff_html = _build_diff_html(result.original_code, result.new_code)
        st.markdown(
            f"<div class='card' style='font-family:monospace;font-size:13px;"
            f"overflow-x:auto'>{diff_html}</div>",
            unsafe_allow_html=True,
        )
    with tab2:
        st.code(result.original_code, language="python")
    with tab3:
        st.code(result.new_code, language="python")

    # ── テスト結果 ──────────────────────────────
    with st.expander("🧪 サンドボックス実行ログ", expanded=False):
        if result.test_output:
            st.code(result.test_output, language="bash")
        else:
            st.info("出力なし")
        if result.test_error:
            st.code(result.test_error, language="bash")

    # ── 承認 / 拒否 ─────────────────────────────
    st.markdown("---")
    st.markdown("### 🚦 最終判断")

    col_ok, col_ng = st.columns(2)

    with col_ok:
        if st.button("✅ 承認してデプロイ", use_container_width=True, type="primary"):
            with st.spinner("バックアップ取得 → 本番環境に反映中..."):
                apply_code(result.new_code)
                time.sleep(1.5)
            st.session_state.deployed = True
            st.success("🚀 デプロイ完了！本番環境に反映されました。")
            st.balloons()

    with col_ng:
        with st.expander("❌ 拒否して再指示"):
            feedback = st.text_area("AIへの追加指示・修正コメント")
            if st.button("🔄 再生成する", use_container_width=True):
                if feedback.strip():
                    new_instruction = f"{result.instruction}\n\n【エンジニアからの修正指示】{feedback}"
                    with st.spinner("AIが再生成中..."):
                        new_result = run_pipeline(new_instruction, result.original_code)
                    st.session_state.result = new_result
                    st.rerun()
                else:
                    st.warning("修正コメントを入力してください")



