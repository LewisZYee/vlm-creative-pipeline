"""
Step 2 — Content Critique
Parses scores/status directly from the analyzer markdown (so they are always
consistent), then calls the LLM only to extract structured issues and
recommendations.
"""
import re

import config
from pipeline.common import ark_client, message_content, parse_json_response, usage_summary

# ── Parse scores directly from analyzer output ────────────────────────────────
def _parse_scores(text: str) -> dict:
    """
    Read the Scoring Dashboard table from analyzer output.
    Handles formats like: | Compliance | 5/10 | or | **Overall Score** | **6.95 /10** |
    Returns a dict with keys: compliance, traffic, brand, safety, overall.
    """
    scores = {}
    # Match any scoring table row — captures the metric name and numeric score.
    # Score cell formats: "5/10", "4.5/10", "6.95 /10", or bare "4.5"
    pattern = (
        r"\|\s*\*{0,2}([^|*\n]{3,50}?)\*{0,2}\s*"
        r"\|\s*\*{0,2}([\d.]+)\s*/?\s*(?:10)?\*{0,2}\s*\|"
    )
    for m in re.finditer(pattern, text, re.IGNORECASE):
        label = m.group(1).strip().lower()
        try:
            score = float(m.group(2))
        except ValueError:
            continue
        if "overall" in label:
            scores["overall"] = score
        elif "compliance" in label:
            scores["compliance"] = score
        elif "distribution" in label or "traffic" in label:
            scores["traffic"] = score
        elif "brand" in label:
            scores["brand"] = score
        elif "safety" in label:
            scores["safety"] = score
        elif "hook" in label:
            scores["hook_depth"] = score
        elif "conversion" in label:
            scores["conversion_potential"] = score
    return scores


def _parse_compliance(text: str) -> tuple[str, str]:
    """Extract compliance status and risk level from analyzer output."""
    status_m = re.search(r"Status:\s*\*{0,2}(PASS|AT RISK|FAIL)\*{0,2}", text, re.IGNORECASE)
    risk_m   = re.search(r"Risk level:\s*\*{0,2}(Low|Medium|High)\*{0,2}", text, re.IGNORECASE)
    status = status_m.group(1).upper()      if status_m else "UNKNOWN"
    risk   = risk_m.group(1).capitalize()   if risk_m   else "Unknown"
    return status, risk


def _parse_viral(text: str) -> tuple[int, str]:
    """Extract viral potential score and explanation from analyzer output."""
    # Score may appear as "8/10", "8", "**8/10**"
    score_m = re.search(
        r"Viral Potential Score[^:\n]*[:\n]\s*\*{0,2}(\d+)\s*/?\s*(?:10)?\*{0,2}",
        text, re.IGNORECASE,
    )
    score = int(score_m.group(1)) if score_m else 0

    # Explanation follows on the next non-empty line(s) after the score
    if score_m:
        snippet = text[score_m.end():score_m.end() + 600].strip()
        for line in snippet.splitlines():
            line = line.strip().lstrip("*#").strip()
            if line and len(line) > 15:
                return score, line
    return score, ""


# ── LLM prompt — only issues + recommendations ───────────────────────────────
ISSUES_SYSTEM_PROMPT = """You are a compliance and performance expert reviewing a short-form video ad analysis.

Given the full analysis report below, extract and return a JSON object with this exact schema:
{
  "issues": [
    {
      "id": <int>,
      "timestamp": "<e.g. 0:03–0:07>",
      "original_content": "<key flagged phrase only, max 8 words>",
      "issue": "<one sentence, max 15 words — what the problem is>",
      "severity": "HIGH | MEDIUM | LOW",
      "policy_type": "<2–4 word label, e.g. Financial Guarantee, Hard-sell Tone, FOMO>",
      "suggested_fix": "<one sentence, verb-first, max 15 words>"
    }
  ],
  "top_recommendations": [
    "<verb-first, max 12 words>",
    "<verb-first, max 12 words>",
    "<verb-first, max 12 words>"
  ],
  "what_works_well": [
    "<one sentence, max 10 words>",
    "<one sentence, max 10 words>"
  ]
}

Rules:
- Extract issues ONLY from what is explicitly flagged in the report. Do not invent new ones.
- Severity HIGH = prohibited policy violation; MEDIUM = restricted/quality issue; LOW = minor optimization.
- Be concise: every field is a single short phrase or sentence — no multi-sentence values.
- Return ONLY the JSON object. No markdown fences, no explanation.
"""

# ── Main ──────────────────────────────────────────────────────────────────────
def generate_critique(analysis_text: str, api_key: str = "") -> dict:
    """
    Generate a structured critique from the Step 1 analysis output.

    Scores, compliance status, and risk level are parsed directly from the
    analyzer markdown so they are always consistent with what the VLM reported.
    The LLM is used only to extract structured issues and recommendations.

    Returns:
        {
            "critique": dict,
            "usage": dict,
        }
    """
    # ── Parse scores/status directly from analyzer text ───────────────────────
    scores = _parse_scores(analysis_text)
    status, risk = _parse_compliance(analysis_text)
    viral_score, viral_explanation = _parse_viral(analysis_text)

    # ── LLM call for issues + recommendations only ────────────────────────────
    client = ark_client(api_key)
    response = client.chat.completions.create(
        model=config.ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": ISSUES_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Here is the full video analysis report. "
                    "Extract the issues and recommendations:\n\n"
                    + analysis_text
                ),
            },
        ],
        thinking={"type": "disabled"},
    )

    raw, usage = message_content(response)
    llm_data = parse_json_response(raw)

    critique = {
        "compliance_status": status,
        "risk_level": risk,
        "scores": scores,
        "issues": llm_data.get("issues", []),
        "viral_potential_score": viral_score,
        "viral_potential_explanation": viral_explanation,
        "top_recommendations": llm_data.get("top_recommendations", []),
        "what_works_well": llm_data.get("what_works_well", []),
    }

    return {
        "critique": critique,
        "usage": usage_summary(usage, reasoning=False),
        "usage_raw": usage,
    }
