from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_path(cache_dir: str, key: str) -> Path:
    d = Path(cache_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def chat_completions_min_tokens(
    *,
    system: str,
    user: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 220,
    timeout_s: int = 45,
    cache_dir: str = ".cache/llm",
) -> str:
    """
    Gọi API kiểu OpenAI-compatible (v1/chat/completions) với input tối giản.
    Có cache theo hash để tránh tốn token nhiều lần.

    Env vars (nếu không truyền trực tiếp):
    - LLM_API_KEY
    - LLM_BASE_URL (mặc định https://api.openai.com)
    - LLM_MODEL (mặc định gpt-4o-mini)
    """

    api_key = api_key or os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY env var")

    base_url = (base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com").rstrip("/")
    model = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    key = _sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    cp = _cache_path(cache_dir, key)
    if cp.exists():
        cached = json.loads(cp.read_text(encoding="utf-8"))
        return cached["text"]

    url = f"{base_url}/v1/chat/completions"
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=timeout_s,
    )
    r.raise_for_status()
    data: Dict[str, Any] = r.json()
    text = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    cp.write_text(json.dumps({"text": text}, ensure_ascii=False, indent=2), encoding="utf-8")
    return text

