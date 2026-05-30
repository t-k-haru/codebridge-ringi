# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Optional
from core.azure_client import (
    generate_code, fix_code, generate_report, extract_code_block,
    get_last_token_usage,
)
from core.sandbox import execute_code, read_target_code

MAX_DEBUG = 10

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
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def __post_init__(self):
        if self.changed_lines == 0:
            import difflib
            diff = list(difflib.unified_diff(
                self.original_code.splitlines(),
                self.new_code.splitlines(), lineterm="",
            ))
            self.changed_lines = sum(
                1 for l in diff if l.startswith(("+","-")) and not l.startswith(("+++","---"))
            )

def run_pipeline(instruction: str, base_code: Optional[str] = None) -> TaskResult:
    original = base_code if base_code else read_target_code()
    raw = generate_code(instruction, original)
    current = extract_code_block(raw)
    tok_in, tok_out = get_last_token_usage()
    last_out = last_err = ""
    for i in range(MAX_DEBUG):
        out, err = execute_code(current)
        last_out, last_err = out, err
        if not err:
            break
        if i < MAX_DEBUG - 1:
            raw2 = fix_code(current, err, instruction)
            current = extract_code_block(raw2)
            ti2, to2 = get_last_token_usage()
            tok_in += ti2; tok_out += to2
    raw_rep = generate_report(instruction, original, current, last_out, last_err, i+1)
    ti3, to3 = get_last_token_usage()
    tok_in += ti3; tok_out += to3
    from core.auth import estimate_cost
    cost = estimate_cost(tok_in, tok_out)
    return TaskResult(
        instruction=instruction, original_code=original, new_code=current,
        test_output=last_out, test_error=last_err, report=raw_rep,
        iterations=i+1, success=not bool(last_err),
        input_tokens=tok_in, output_tokens=tok_out, cost_usd=cost,
    )
