# -*- coding: utf-8 -*-
import os, re
from openai import AzureOpenAI

_last_usage = {"input": 0, "output": 0}

def get_last_token_usage():
    return _last_usage["input"], _last_usage["output"]

def _get_client():
    ep = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    if "/api/projects/" in ep:
        ep = ep.split("/api/projects/")[0] + "/"
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2025-01-01-preview",
        azure_endpoint=ep,
    )

DEPLOY = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o4-mini")

def _call(messages, max_tokens=32000):
    client = _get_client()
    resp = client.chat.completions.create(
        model=DEPLOY, messages=messages, max_completion_tokens=max_tokens,
    )
    u = resp.usage
    if u:
        _last_usage["input"]  = u.prompt_tokens
        _last_usage["output"] = u.completion_tokens
    return resp.choices[0].message.content

SYS = (
    "You are an expert frontend engineer. "
    "Modify the given HTML demo page per the user instruction. "
    "Rules: 1) Only change what is asked. "
    "2) Keep ALL existing content/CSS/JS/data intact. "
    "3) Return the ENTIRE HTML file — do not omit any part. "
    "4) Wrap output in ```html ... ```. "
    "5) Preserve Japanese text and existing styles."
)

def generate_code(instruction, existing_code):
    return _call([
        {"role": "system", "content": SYS},
        {"role": "user", "content": (
            "[Existing HTML — return ALL of this with ONLY the requested change]\n"
            "```html\n" + existing_code + "\n```\n\n"
            "[Change instruction]\n" + instruction + "\n\n"
            "IMPORTANT: Return the COMPLETE HTML. Do not compress or omit any section."
        )},
    ])

def fix_code(code, error, instruction):
    return _call([{"role": "user", "content": (
        "Fix this HTML validation error while keeping the original instruction.\n"
        "[Instruction]: " + instruction + "\n"
        "[Error]: " + error + "\n"
        "[HTML excerpt]: " + code[:4000] + "...\n\n"
        "Return fixed complete HTML in ```html ... ```"
    )}])

def generate_report(instruction, original, new_code, test_output, test_error, iterations):
    status = "成功" if not test_error else "要確認"
    return _call([{"role": "user", "content": (
        "Create a concise HTML report in Japanese for an engineer reviewing this HTML change.\n"
        "Instruction: " + instruction + "\n"
        "Validation: " + status + " (" + str(iterations) + " attempts)\n"
        "Output: " + (test_output or 'none') + "\n"
        "Error: " + (test_error or 'none') + "\n\n"
        "Include: summary (1-2 sentences), bullet list of changes, any risks. No code blocks."
    )}, ], max_tokens=2000)

def extract_code_block(text):
    m = re.search(r"```html\s*(.*?)```", text, re.DOTALL)
    if m: return m.group(1).strip()
    m = re.search(r"```\s*(<!DOCTYPE|<html)(.*?)```", text, re.DOTALL)
    if m: return (m.group(1)+m.group(2)).strip()
    if "<!DOCTYPE" in text or "<html" in text: return text.strip()
    return text.strip()
