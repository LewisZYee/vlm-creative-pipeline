"""
QA & Monitoring — Step 4
Feeds the Seedance-generated video back into Seed 2.0 Pro VLM to evaluate:
  1. Instruction following — did the video match the production prompt?
  2. Compliance — does the generated output contain any violations?
"""
import json
import re

import config

QA_SYSTEM_PROMPT = """You are a QA engineer reviewing AI-generated video ads.

You will receive:
1. The original production prompt used to generate the video
2. The generated video itself

Evaluate the video on two dimensions:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A. INSTRUCTION FOLLOWING (score 1–10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check whether the video accurately followed the production prompt. Look for deviations in:
- Character appearance (does it match the character reference brief?)
- Environment / location (correct setting, colours, lighting?)
- Dialogue / voiceover (correct words, pacing, tone?)
- On-screen text / subtitles (correct wording and timing?)
- Product appearance (correct if product was specified?)
- Camera movement and shot types
- Music and audio mood
- Overall timing and structure

For each deviation: note what was expected vs what actually appeared.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B. COMPLIANCE (score 1–10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check the generated video for any compliance violations:
- Financial guarantee or unrealistic return claims
- Hard-sell or aggressive pressure language
- Missing or unclear disclaimers where required
- Misleading visual claims
- Platform policy violations (prohibited gestures, imagery, or claims)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT — JSON only, no markdown fences, no explanation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "instruction_following_score": <1–10>,
  "compliance_score": <1–10>,
  "overall_pass": <true|false>,
  "instruction_issues": [
    {
      "element": "<what aspect — e.g. Environment, Dialogue, Character>",
      "expected": "<what the prompt specified>",
      "actual": "<what the video shows>"
    }
  ],
  "compliance_issues": [
    {
      "severity": "HIGH | MEDIUM | LOW",
      "description": "<one sentence — what the violation is>",
      "timestamp": "<approximate timestamp, e.g. 0:03–0:07>"
    }
  ],
  "summary": "<2–3 sentence overall assessment>"
}

overall_pass = true only if instruction_following_score >= 7 AND compliance_score >= 8 AND no HIGH compliance issues.
"""


def qa_generated_video(video_url: str, original_prompt: str, api_key: str = "") -> dict:
    """
    QA a Seedance-generated video against its original production prompt.

    Args:
        video_url:       HTTPS URL of the generated video (from Seedance).
        original_prompt: The full video prompt that was sent to Seedance.
        api_key:         BytePlus Ark API key (falls back to config if empty).

    Returns:
        {
            "qa": dict,    # structured QA result
            "raw": str,
            "usage": dict,
        }
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=api_key or config.ARK_API_KEY)

    response = client.chat.completions.create(
        model=config.ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "## Original Production Prompt\n\n" + original_prompt,
                    },
                    {
                        "type": "video_url",
                        "video_url": {"url": video_url, "fps": 1},
                    },
                    {
                        "type": "text",
                        "text": "Please evaluate the generated video against the production prompt above.",
                    },
                ],
            },
        ],
        thinking={"type": "enabled"},
    )

    dump = response.model_dump(exclude_none=True)
    raw = ""
    for ch in dump.get("choices", []):
        raw += (ch.get("message") or {}).get("content") or ""

    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean.strip())

    try:
        qa_data = json.loads(clean)
    except Exception:
        qa_data = {
            "instruction_following_score": 0,
            "compliance_score": 0,
            "overall_pass": False,
            "instruction_issues": [],
            "compliance_issues": [],
            "summary": "Failed to parse QA response.",
        }

    usage = dump.get("usage", {})
    return {
        "qa": qa_data,
        "raw": raw,
        "usage": {
            "prompt_tokens":     usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens":  usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
            "total_tokens":      usage.get("total_tokens", 0),
        },
        "usage_raw": usage,
    }
