"""Shared helpers for Ark calls and model response handling."""
import json
import re
from pathlib import Path
from typing import Any

import config


def ark_client(api_key: str = ""):
    """Create an Ark client using a supplied session key or the env fallback."""
    from byteplussdkarkruntime import Ark

    return Ark(base_url=config.ARK_BASE_URL, api_key=api_key or config.ARK_API_KEY)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def message_content(response: Any) -> tuple[str, dict]:
    """Return concatenated assistant content and the raw usage dict."""
    dump = response.model_dump(exclude_none=True)
    content = ""
    for choice in dump.get("choices", []):
        content += (choice.get("message") or {}).get("content") or ""
    return content, dump.get("usage", {})


def usage_summary(usage: dict, reasoning: bool = True) -> dict:
    return {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "reasoning_tokens": (
            usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            if reasoning
            else 0
        ),
        "total_tokens": usage.get("total_tokens", 0),
    }


def parse_json_response(text: str) -> dict:
    """Parse a JSON object returned with or without markdown fences."""
    clean = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean.strip())
    return json.loads(clean)
