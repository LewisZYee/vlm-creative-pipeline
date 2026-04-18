"""
Storyboard Generation (Long) — matches original video length
Takes the full analysis text and generates a revised, compliance-clean storyboard
at roughly the same duration as the original video — not compressed to 15s.
Uses the same storyboardPrompt as storyboard.py.
"""
import re

import config


def _read_storyboard_prompt() -> str:
    path = config.PROMPTS_DIR / "storyboardPrompt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_section(text: str, header: str) -> str:
    """Extract text under a markdown header until the next same-level header."""
    level   = len(header) - len(header.lstrip("#"))
    pattern = re.escape(header.strip())
    match   = re.search(rf"^{pattern}\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        match = re.search(rf"{pattern}", text, re.IGNORECASE)
    if not match:
        return ""
    start  = match.end()
    next_h = re.search(rf"^{'#' * level}(?!#)\s+\S", text[start:], re.MULTILINE)
    end    = start + next_h.start() if next_h else len(text)
    return text[start:end].strip()


def parse_sections(storyboard_text: str) -> dict:
    return {
        "simplified":   extract_section(storyboard_text, "## 4.1 Simplified Storyboard"),
        "character":    extract_section(storyboard_text, "## 4.2 Character Prompt"),
        "scene":        extract_section(storyboard_text, "## 4.3 Scene Prompt"),
        "style":        extract_section(storyboard_text, "## 4.4 Style and Camera Prompt"),
        "regeneration": extract_section(storyboard_text, "## 4.5 Regeneration Reference"),
    }


def generate_storyboard_short(analysis_text: str) -> dict:
    """
    Generate a revised storyboard from the Step 1 analysis output.
    Duration matches the original video — not compressed to 15 seconds.

    Args:
        analysis_text: Full markdown text returned by analyze_video().

    Returns:
        {
            "content":  str,   # full storyboard markdown
            "sections": dict,  # parsed sections
            "usage":    dict,
        }
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=config.ARK_API_KEY)

    storyboard_prompt = _read_storyboard_prompt()
    combined = (
        storyboard_prompt
        + "\n\n---\n\n## INPUT: Analysis Output\n\n"
        + analysis_text
    )

    response = client.chat.completions.create(
        model=config.STORYBOARD_MODEL,
        messages=[{"role": "user", "content": combined}],
        thinking={"type": "enabled"},
    )

    dump    = response.model_dump(exclude_none=True)
    content = ""
    for ch in dump.get("choices", []):
        content += (ch.get("message") or {}).get("content") or ""

    usage    = dump.get("usage", {})
    sections = parse_sections(content)

    return {
        "content":  content,
        "sections": sections,
        "usage": {
            "prompt_tokens":     usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens":  usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
            "total_tokens":      usage.get("total_tokens", 0),
        },
        "usage_raw": usage,
    }
