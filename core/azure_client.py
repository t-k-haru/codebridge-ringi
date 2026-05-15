# -*- coding: utf-8 -*-
"""
Azure OpenAI (o4-mini) との通信。HTML修正に特化したプロンプト設計。
"""
import os
import re
from openai import AzureOpenAI

def _get_client() -> AzureOpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    if "/api/projects/" in endpoint:
        endpoint = endpoint.split("/api/projects/")[0] + "/"
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2025-01-01-preview",
        azure_endpoint=endpoint,
    )

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o4-mini")


def generate_code(instruction: str, existing_code: str) -> str:
    client = _get_client()
    system_prompt = (
        "You are an expert frontend engineer. "
        "Modify the given HTML demo page according to the user's instruction. "
        "RULES: "
        "1) Only change what is explicitly requested. "
        "2) Keep ALL existing content, structure, CSS, JS, and data intact. "
        "3) Return the ENTIRE HTML file — do not simplify or omit any part. "
        "4) Wrap output in ```html ... ``` block. "
        "5) Preserve Japanese text and existing styles."
    )
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                "[Existing HTML — return ALL of this with ONLY the requested change]\n"
                "```html\n" + existing_code + "\n```\n\n"
                "[Change instruction]\n" + instruction + "\n\n"
                "IMPORTANT: Return the COMPLETE HTML. Do not compress or omit any section."
            )},
        ],
        max_completion_tokens=32000,
    )
    return response.choices[0].message.content


def fix_code(code: str, error: str, instruction: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": (
            "Fix this HTML validation error while keeping the original instruction satisfied.\n"
            "[Original instruction]: " + instruction + "\n"
            "[Error]: " + error + "\n"
            "[HTML (first 4000 chars)]: " + code[:4000] + "...\n\n"
            "Return the fixed complete HTML wrapped in ```html ... ```"
        )}],
        max_completion_tokens=32000,
    )
    return response.choices[0].message.content


def generate_report(instruction: str, original: str, new_code: str,
                    test_output: str, test_error: str, iterations: int) -> str:
    client = _get_client()
    status = "成功" if not test_error else "要確認"
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": (
            "Create a concise HTML report in Japanese for an engineer reviewing this HTML change.\n"
            "Instruction: " + instruction + "\n"
            "Validation: " + status + " (" + str(iterations) + " attempts)\n"
            "Output: " + (test_output or 'none') + "\n"
            "Error: " + (test_error or 'none') + "\n\n"
            "Include: summary (1-2 sentences), bullet list of changes, any risks. No code blocks."
        )}],
        max_completion_tokens=2000,
    )
    return response.choices[0].message.content


def extract_code_block(text: str) -> str:
    match = re.search(r"```html\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(<!DOCTYPE|<html)(.*?)```", text, re.DOTALL)
    if match:
        return (match.group(1) + match.group(2)).strip()
    if "<!DOCTYPE" in text or "<html" in text:
        return text.strip()
    return text.strip()
