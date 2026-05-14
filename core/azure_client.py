"""
Azure OpenAI (o4-mini) との通信を担当するモジュール。
"""
import os
import re
from openai import AzureOpenAI

def _get_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o4-mini")


def generate_code(instruction: str, existing_code: str) -> str:
    """既存コードと指示を受け取り、修正後のコード全体を返す。"""
    client = _get_client()

    system_prompt = """あなたは優秀なソフトウェアエンジニアです。
既存のコードに対して、ユーザーの指示に従って必要最小限の変更を加えてください。

【厳守ルール】
1. 変更は指示された箇所のみに限定する
2. 既存の動作を壊さない
3. コード全体を返す（変更箇所だけでなくファイル全体）
4. 必ず ```python ... ``` のコードブロックで囲む
5. コードブロック以外の説明文は最小限にする"""

    user_prompt = f"""【既存コード】
```python
{existing_code}
```

【変更指示】
{instruction}

上記の指示に従って修正したコード全体を返してください。"""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=4000,
    )
    return response.choices[0].message.content


def fix_code(code: str, error: str, instruction: str) -> str:
    """実行エラーを受け取り、修正したコードを返す。"""
    client = _get_client()

    user_prompt = f"""コードを実行したところ以下のエラーが発生しました。
元の指示を満たしつつ、エラーを修正してください。

【元の指示】
{instruction}

【エラーメッセージ】
{error}

【現在のコード】
```python
{code}
```

修正したコード全体を ```python ... ``` ブロックで返してください。"""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": user_prompt}],
        max_completion_tokens=4000,
    )
    return response.choices[0].message.content


def generate_report(instruction: str, original: str, new_code: str,
                    test_output: str, test_error: str, iterations: int) -> str:
    """エンジニア向けの変更レポートを生成する。"""
    client = _get_client()

    status = "✅ 成功" if not test_error else "⚠️ エラーあり（要確認）"

    user_prompt = f"""以下のコード変更について、エンジニア向けの簡潔なレポートをHTML形式で作成してください。

【ユーザー指示】: {instruction}
【テスト結果】: {status}
【デバッグ試行回数】: {iterations}回
【テスト出力】: {test_output or "なし"}
【エラー】: {test_error or "なし"}

以下の形式でHTMLを返してください（Streamlit st.markdownで表示します）：
- 変更サマリー（1〜2文）
- 主な変更点（箇条書き）
- 注意点・リスク（あれば）
- 推奨アクション

装飾は最小限に。コードブロックは不要。"""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": user_prompt}],
        max_completion_tokens=1000,
    )
    return response.choices[0].message.content


def extract_code_block(text: str) -> str:
    """レスポンステキストからPythonコードブロックを抽出する。"""
    # ```python ... ``` パターン
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # ``` ... ``` パターン（言語指定なし）
    match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # コードブロックがない場合はそのまま返す
    return text.strip()
