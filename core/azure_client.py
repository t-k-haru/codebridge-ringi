"""
Azure OpenAI (o4-mini) との通信。
HTML修正に特化したプロンプト設計。
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
    """既存HTMLと指示を受け取り、修正後のHTML全体を返す。"""
    client = _get_client()

    system_prompt = """あなたは優秀なフロントエンドエンジニアです。
シフト管理システムのHTMLデモページに対して、ユーザーの指示に従って必要最小限の変更を加えてください。

【厳守ルール】
1. 変更は指示された箇所のみに限定する
2. 既存のデザイン・機能・データを壊さない
3. HTML全体を返す（変更箇所だけでなくファイル全体）
4. 必ず ```html ... ``` のコードブロックで囲む
5. 日本語UIを維持する
6. インラインCSSやJavaScriptの既存スタイルを尊重する"""

    user_prompt = f"""【既存HTML】
```html
{existing_code}
```

【変更指示】
{instruction}

上記の指示に従って修正したHTML全体を返してください。"""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_completion_tokens=8000,
    )
    return response.choices[0].message.content


def fix_code(code: str, error: str, instruction: str) -> str:
    """バリデーションエラーを受け取り、修正したHTMLを返す。"""
    client = _get_client()
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": f"""HTMLにエラーがあります。修正してください。
【元の指示】{instruction}
【エラー】{error}
【現在のHTML（先頭500文字）】{code[:500]}...
修正したHTML全体を ```html ... ``` で返してください。"""}],
        max_completion_tokens=8000,
    )
    return response.choices[0].message.content


def generate_report(instruction: str, original: str, new_code: str,
                    test_output: str, test_error: str, iterations: int) -> str:
    """エンジニア向けの変更レポートを生成する。"""
    client = _get_client()
    status = "成功" if not test_error else "要確認"
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": f"""以下のHTML変更について、エンジニア向けの簡潔なレポートをHTML形式で作成してください。
【ユーザー指示】: {instruction}
【バリデーション結果】: {status}（{iterations}回試行）
【出力】: {test_output or "なし"}
【エラー】: {test_error or "なし"}

以下を含むHTMLレポートを返してください（コードブロック不要）：
- 変更サマリー（1〜2文）
- 主な変更点（箇条書き）
- 注意点（あれば）"""}],
        max_completion_tokens=1000,
    )
    return response.choices[0].message.content


def extract_code_block(text: str) -> str:
    """レスポンスからhtmlコードブロックを抽出する。"""
    match = re.search(r"```html\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(<!DOCTYPE|<html)(.*?)```", text, re.DOTALL)
    if match:
        return (match.group(1) + match.group(2)).strip()
    # コードブロックなしでそのままHTMLが返ってきた場合
    if "<!DOCTYPE" in text or "<html" in text:
        return text.strip()
    return text.strip()
