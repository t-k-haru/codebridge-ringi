"""
メインエージェントパイプライン。
指示 → コード生成 → サンドボックス実行 → 自己デバッグ → レポート生成
"""
from dataclasses import dataclass, field
from typing import Optional
from core.azure_client import (
    generate_code, fix_code, generate_report, extract_code_block
)
from core.sandbox import execute_code, read_target_code

MAX_DEBUG_ITERATIONS = 3


@dataclass
class TaskResult:
    instruction: str
    original_code: str
    new_code: str
    test_output: str
    test_error: str
    report: str
    iterations: int
    success: bool
    changed_lines: int = 0

    def __post_init__(self):
        if self.changed_lines == 0:
            self.changed_lines = _count_changed_lines(
                self.original_code, self.new_code
            )


def run_pipeline(instruction: str, base_code: Optional[str] = None) -> TaskResult:
    """
    メインパイプライン実行。
    base_code が None の場合は target_app/main.py を読む。
    """
    original_code = base_code if base_code else read_target_code()

    # ── Step 1: 初回コード生成 ──────────────────────────
    raw_response = generate_code(instruction, original_code)
    current_code = extract_code_block(raw_response)

    # ── Step 2: 自己デバッグループ ──────────────────────
    iterations = 0
    last_output = ""
    last_error = ""

    for i in range(MAX_DEBUG_ITERATIONS):
        iterations = i + 1
        output, error = execute_code(current_code)
        last_output = output
        last_error = error

        if not error:
            # テスト成功
            break

        if i < MAX_DEBUG_ITERATIONS - 1:
            # エラーを渡して再生成
            raw_fix = fix_code(current_code, error, instruction)
            current_code = extract_code_block(raw_fix)
        # 最終イテレーションでもエラーなら諦める

    success = not bool(last_error)

    # ── Step 3: レポート生成 ────────────────────────────
    report = generate_report(
        instruction=instruction,
        original=original_code,
        new_code=current_code,
        test_output=last_output,
        test_error=last_error,
        iterations=iterations,
    )

    return TaskResult(
        instruction=instruction,
        original_code=original_code,
        new_code=current_code,
        test_output=last_output,
        test_error=last_error,
        report=report,
        iterations=iterations,
        success=success,
    )


def _count_changed_lines(original: str, new: str) -> int:
    """変更・追加・削除された行数を数える。"""
    import difflib
    diff = list(difflib.unified_diff(
        original.splitlines(),
        new.splitlines(),
        lineterm="",
    ))
    return sum(1 for line in diff if line.startswith(("+", "-"))
               and not line.startswith(("+++", "---")))
