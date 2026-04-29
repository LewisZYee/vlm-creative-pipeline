"""
Step 1 — Video Analysis
Calls Seed 2.0 Pro VLM with the analysis prompt and returns the full compliance
review + storyboard breakdown.
"""
import base64
import re

import config
from pipeline.common import ark_client, message_content, read_text, usage_summary


def _fix_markdown(text: str) -> str:
    """
    Fix markdown rendering issues in model output before displaying in Streamlit.

    Problem: The model mirrors `---` dividers from the prompt. In CommonMark,
    `---` on the line immediately after a text line (with no blank line between)
    is a setext H2 heading — it hijacks that line's font size, overriding any
    `###` header the model intended. Section 3 is particularly affected because
    it ends with bullet points and the model places `---` right after.

    Fix: Replace bare `---` divider lines with empty lines (preserve the visual
    break without the setext-heading side effect).
    """
    # Replace lines that are purely `---` (optional surrounding whitespace) with blank lines.
    # Use a lookahead/lookbehind to avoid touching table separator rows (---|---|---).
    lines = text.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"-{3,}", stripped):
            # Pure horizontal rule — replace with blank line to prevent setext heading
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


# ── Real implementation ────────────────────────────────────────────────────────
def _encode_video(video_path: str) -> str:
    with open(video_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


_PERFORMANCE_CONTEXTS = {
    "bad": (
        "IMPORTANT CONTEXT: This video is a known UNDERPERFORMING ad. "
        "It has been flagged for high Cost per App Install, high Cost per Add Payment Info, "
        "low Average Watch Time, low Video View Rate, and low Conversion Rate. "
        "Your analysis must diagnose the specific creative reasons behind each of these failures. "
        "Do not give the benefit of the doubt — find the root causes."
    ),
    "good": (
        "IMPORTANT CONTEXT: This video is a known TOP-PERFORMING ad. "
        "It has demonstrated low Cost per App Install, low Cost per Add Payment Info, "
        "high Average Watch Time, high Video View Rate, and strong Conversion Rate. "
        "Your analysis should identify WHAT makes it work — which creative elements drive each metric — "
        "so these strengths can be replicated. Still flag any compliance issues honestly."
    ),
}


def _read_prompt(performance: str = "bad") -> str:
    path = config.PROMPTS_DIR / "analysisPrompt"
    template = read_text(path)
    context = _PERFORMANCE_CONTEXTS.get(performance, _PERFORMANCE_CONTEXTS["bad"])
    return template.replace("{PERFORMANCE_CONTEXT}", context)


def _parse_character_description(content: str) -> tuple:
    """
    Split the model response into (analysis_content, character_description).
    Splits on the '# PART 3: CHARACTER DESCRIPTION' header.
    """
    marker = "# PART 3: CHARACTER DESCRIPTION"
    idx = content.find(marker)
    if idx == -1:
        return content.strip(), ""
    analysis = content[:idx].strip()
    char_desc = content[idx + len(marker):].strip()
    return analysis, char_desc


def analyze_video(video_path: str, performance: str = "bad", api_key: str = "") -> dict:
    """
    Analyze a video file with Seed 2.0 Pro VLM.

    Args:
        video_path:   Absolute path to the video file.
        performance:  "bad" (underperforming, default) or "good" (top-performing).
                      Injects context into the prompt so the LLM calibrates its analysis angle.

    Returns:
        {
            "content": str,           # full markdown analysis
            "usage": {
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int,
            },
        }
    """
    client = ark_client(api_key)
    prompt = _read_prompt(performance)
    video_b64 = _encode_video(video_path)

    response = client.chat.completions.create(
        model=config.ANALYSIS_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": f"data:video/mp4;base64,{video_b64}",
                            "fps": 1,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        thinking={"type": "enabled"},
    )

    content, usage = message_content(response)

    analysis, char_desc = _parse_character_description(content)
    return {
        "content": _fix_markdown(analysis),
        "character_description": char_desc,
        "usage": usage_summary(usage),
        "usage_raw": usage,
    }
