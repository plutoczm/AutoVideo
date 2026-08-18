import json
import os
from typing import Any

import requests
from google import genai
from google.genai import types


def _extract_text_from_ark_response(payload: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in payload.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(str(content["text"]))
    if texts:
        return "\n".join(texts)
    if payload.get("output_text"):
        return str(payload["output_text"])
    raise RuntimeError("Doubao Responses API returned no output_text")


def _gemini_json(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for LLM_PROVIDER=gemini")
    model = os.getenv("GEMINI_LLM_MODEL", "gemini-3.6-flash")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response")
    return response.text


def _doubao_json(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("ARK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ARK_API_KEY is required for LLM_PROVIDER=doubao")
    base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
    model = os.getenv("DOUBAO_LLM_MODEL", "doubao-seed-2-1-turbo-260628")
    prompt = (
        system_prompt
        + "\n\nReturn only one valid JSON object and no Markdown.\n\n"
        + user_prompt
    )
    response = requests.post(
        f"{base_url}/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "input": prompt,
            "thinking": {"type": "disabled"},
        },
        timeout=180,
    )
    response.raise_for_status()
    return _extract_text_from_ark_response(response.json())


def _deepseek_json(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for LLM_PROVIDER=deepseek")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_json(system_prompt: str, user_prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    if provider == "gemini":
        return _gemini_json(system_prompt, user_prompt)
    if provider == "doubao":
        return _doubao_json(system_prompt, user_prompt)
    if provider == "deepseek":
        return _deepseek_json(system_prompt, user_prompt)
    raise RuntimeError("LLM_PROVIDER must be gemini, doubao or deepseek")
