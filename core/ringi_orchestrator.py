# -*- coding: utf-8 -*-
"""
稟議分析AIパイプライン。Azure OpenAI (o4-mini) を使って申請内容を分析し
RingiDraft を返す。
"""
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from core.azure_client import _call, get_last_token_usage
from core.auth import estimate_cost

EXTENSION_TYPES = {
    "code_deploy": "コード変更の自動反映",
    # 将来追加予定:
    # "amazon_purchase": "Amazon自動購入",
    # "slack_invite":    "Slackへの自動招待",
}

APPROVAL_TYPE_LABELS = {
    "confirm":   "確認型",
    "notify":    "通知型",
    "judge":     "判断型",
    "consensus": "合議型",
}


@dataclass
class RingiDraft:
    approval_type: str
    draft_title: str
    draft_body: str
    suggested_approver_id: int
    suggested_approver_name: str
    suggested_approver_reason: str
    extension_type: Optional[str]
    risk_level: str
    key_points: list = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


_SYSTEM = """あなたは日本企業の稟議書作成AIアシスタントです。
申請内容を分析し、以下のJSON形式のみで回答してください。前置きや説明は一切不要です。JSONのみ出力してください。

{
  "approval_type": "confirm|notify|judge|consensus",
  "draft_title": "稟議書タイトル（30文字以内）",
  "draft_body": "## 申請背景\\n内容\\n\\n## 変更内容\\n内容\\n\\n## 想定影響・リスク\\n内容\\n\\n## 承認のお願い\\n内容",
  "suggested_approver_id": <整数>,
  "suggested_approver_name": "名前",
  "suggested_approver_reason": "推薦理由（50文字以内）",
  "extension_type": "code_deploy" または null,
  "risk_level": "low|medium|high",
  "key_points": ["ポイント1", "ポイント2"]
}

承認タイプ判定基準:
- confirm（確認型）: 前例あり・リスク低・規定内
- notify（通知型）: 情報共有のみ・決定不要
- judge（判断型）: 例外・高リスク・新規判断が必要
- consensus（合議型）: 組織横断・重要投資・複数部門関与

extension_type:
- 「コード」「システム」「画面」「変更」「実装」「修正」「機能」「バグ」「追加」「削除」を含む → "code_deploy"
- それ以外 → null

承認者選定: 提供されたapproverリストから最適な1名を選んでください。"""


def analyze_request(raw_input: str, requester_name: str, available_approvers: list) -> RingiDraft:
    approvers_desc = "\n".join(
        f"- id={a['id']}, name={a['name']}, role={a['role']}"
        for a in available_approvers
    )
    user_msg = f"申請者: {requester_name}\n\n申請内容:\n{raw_input}\n\n利用可能な承認者:\n{approvers_desc}\n\nJSONのみで回答してください。"

    raw = _call(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user_msg}],
        max_tokens=4000,
    )
    tok_in, tok_out = get_last_token_usage()
    cost = estimate_cost(tok_in, tok_out)

    data = _extract_json(raw)

    fallback_approver = available_approvers[0] if available_approvers else {"id": 0, "name": ""}
    return RingiDraft(
        approval_type=data.get("approval_type", "judge"),
        draft_title=data.get("draft_title", "申請"),
        draft_body=data.get("draft_body", raw_input),
        suggested_approver_id=int(data.get("suggested_approver_id", fallback_approver["id"])),
        suggested_approver_name=data.get("suggested_approver_name", fallback_approver["name"]),
        suggested_approver_reason=data.get("suggested_approver_reason", ""),
        extension_type=data.get("extension_type"),
        risk_level=data.get("risk_level", "medium"),
        key_points=data.get("key_points", []),
        input_tokens=tok_in,
        output_tokens=tok_out,
        cost_usd=cost,
    )


def _extract_json(text: str) -> dict:
    m = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}
