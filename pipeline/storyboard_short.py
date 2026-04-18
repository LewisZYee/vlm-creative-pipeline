"""
Storyboard Generation (Short) — 15-second version
Takes the full analysis text and generates a revised, compliance-clean 15-second
storyboard. Fixes all issues, preserves what works, compressed to exactly 15 seconds.
"""
import re

import config


STORYBOARD_SHORT_PROMPT = """You are a professional video director, storyboard artist, performance advertising creative strategist, and AI video generation prompt engineer. You specialise in short-form social ads for TikTok, Instagram Reels, and YouTube Shorts.

You will receive one input: a detailed analysis of an existing video ad, including all identified compliance violations, quality issues, optimization suggestions, and the original second-by-second storyboard.

Your task is to generate a **new, improved 15-second storyboard** that:
- Is ALWAYS exactly 15 seconds long — compress or cut accordingly, never exceed 15s
- Fixes every compliance issue flagged in the analysis
- Preserves the strongest hook, core message, and CTA from the original
- Maximises hook strength (first 3 seconds are critical), 5s completion rate, and cold start qualification
- Is ready for AI video generation (Seedance / Seedream)

---

## Brand Tone of Voice Guidelines

**Do:**
- Sound like a confident, knowledgeable friend genuinely excited about what the product does
- Use direct, conversational language — short sentences, active voice, concrete specifics
- Let hype come from real outcomes ("I made my first trade in 60 seconds") not empty superlatives
- Use "you" language — speak to the viewer's goal, not the product's features

**Don't:**
- Use corporate or scripted language
- Over-promise or use financial guarantee language (compliance risk + trust killer)
- Sound like a TV commercial
- Use dead phrases: "easy money", "passive income", "financial freedom", "life-changing"

---

## 15-Second Compression Rules

- Total runtime is EXACTLY 15 seconds. Every second counts.
- Structure must follow: Hook (0–3s) → Problem/Demo (4–10s) → CTA (11–15s)
- If the original is longer than 15s: cut the weakest middle section, keep the hook and CTA
- If the original is shorter than 15s: expand the demo/proof section with the strongest existing content
- Every second must serve a clear purpose — cut anything that does not move the viewer closer to the CTA

## Dialogue Word Budget — HARD LIMIT

- Maximum 50 spoken words total across the entire 15-second video
- Count every spoken word before finalising the storyboard. If the total exceeds 50, cut the weakest dialogue lines until it does not.
- Speech rate is 3–4 words per second — a single 1-second row can carry at most 3–4 words of dialogue
- Each dialogue line must be one natural breath. A line that takes more than one breath to say must be split or cut.
- At least 2 seconds must have no dialogue at all — use these for visual beats, product close-ups, or reaction shots
- Between every two consecutive dialogue sentences, allow a 0.3-second micro-pause for natural breath — account for this when filling each row

---

## Instructions

1. Read all issues in the analysis carefully before writing.
2. Write a new 15-second storyboard from scratch, informed by the original.
3. Fix every flagged compliance or quality issue.
4. Apply Brand Tone of Voice to every dialogue and voiceover line.
5. Mark each second as [CHANGED: reason] or [KEPT] in Optimization Notes.
6. Fill the Music column for every row — specify ONE background music track that runs the full 15 seconds. Pick a specific genre and BPM (e.g. "upbeat lo-fi hip-hop, 100 BPM"). Note how it behaves: enters at mid-energy at 0s, ducks under dialogue, swells on silent visual beats, lifts at the CTA. Do not write "upbeat music" — be specific.

---

## Output Structure

# 1. Video Overview (Revised)

- Total duration: **15 seconds**
- Video type
- Platform fit
- Aspect ratio
- Core theme
- Main characters
- Main scenes
- Hook quality (strong / medium / weak) with reason
- 5s completion rate prediction with reason
- Cold Start qualification likelihood with reason
- CTA present (yes/no)
- Issues resolved (list all)

# 2. New Second-by-Second Storyboard Table (15 rows)

| Time Range | Visual Content | Characters | Emotion | Action | Shot Type | On-Screen Text | Dialogue | Music | Transition | Key Information | Optimization Notes |
|------------|----------------|------------|---------|--------|-----------|----------------|----------|-------|------------|-----------------|-------------------|

Rules:
- Exactly 15 rows (one per second, 1s–15s)
- Mark every row [CHANGED: reason] or [KEPT]
- For rewritten dialogue: add tone register, e.g. [TONE: punchy/confident]

# 3. Change Summary

## Issues Fixed
## Seconds Modified
## What Was Preserved
## Tone & Dialogue Changes

# 4. Final Generation Output

## 4.1 Simplified Storyboard
| Second | Scene Description | Dialogue | Tone Note | Notes |
|--------|-------------------|----------|-----------|-------|
(15 rows, one per second — 1s through 15s)


---

## Output Requirements
- Output language: English
- Total video duration: exactly 15 seconds
- Label every row [CHANGED: reason] or [KEPT]
- Apply Brand Tone of Voice to every rewritten dialogue line
"""


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
        "simplified": extract_section(storyboard_text, "## 4.1 Simplified Storyboard"),
    }


def generate_storyboard_short(analysis_text: str) -> dict:
    """
    Generate a revised 15-second storyboard from the Step 1 analysis output.

    Args:
        analysis_text: Full markdown text returned by analyze_video().

    Returns:
        {
            "content":  str,   # full storyboard markdown
            "sections": dict,  # parsed sections 4.1–4.5
            "usage":    dict,
        }
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=config.ARK_API_KEY)

    combined = (
        STORYBOARD_SHORT_PROMPT
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
