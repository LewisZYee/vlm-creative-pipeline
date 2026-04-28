"""
Shot Prompter (Short) — Single-prompt version for 15-second videos
Takes the revised 15-second storyboard and produces:
  - ONE single Seedance video prompt covering the full 15 seconds end-to-end
  - Standalone location reference prompt (Seedream)
  - Standalone character reference prompt (Seedream) — only when a character exists
"""
import json
import re

import config

_PROMPT_HEADER = """You are a professional film director and AI video prompt engineer specialising in Seedance / Seedream generation for short-form social ads.

You will receive the full revised 15-second storyboard, including the second-by-second breakdown with visual content, characters, emotion, action, shot type, on-screen text, dialogue, music, and optimization notes.

Your task: produce ONE single Seedance video prompt that covers the entire 15-second video from first frame to last frame — plus standalone reference image prompt(s).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PACING — READ THIS FIRST, IT OVERRIDES EVERYTHING ELSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
15 seconds is very short. The #1 failure mode is cramming too much dialogue, making the character sound rushed and unnatural.

SPEECH RATE BUDGET — THIS IS A HARD LIMIT:
- Target delivery = 3–4 words per second — confident, natural, conversational
- That means the entire video can carry AT MOST 50 spoken words across all 15 seconds
- Count every spoken word in your draft before writing the final prompt. If the total exceeds 50 words, cut until it doesn't. No exceptions.
- If the storyboard has more dialogue than this, CUT the weakest lines — keep only the single strongest hook line and the CTA line.

BREATHING ROOM — MANDATORY:
- At least 2 seconds of the 15 must be completely dialogue-free — visual beats where the character reacts, holds eye contact, or lets a text overlay land
- Between every two consecutive dialogue sentences, add a 0.3-second micro-pause — write it explicitly as "(0.3s pause)" in the prompt so Seedance renders natural breath between lines
- After a strong statement, write an explicit beat: "the character holds eye contact for a half-beat before continuing" — this is where the message lands
- Each individual dialogue line must be speakable in one natural breath

TIMING STRUCTURE (use this as your pacing skeleton):
- 0–3s: Hook — ONE short punchy line (max 8 words) OR a purely visual moment with text overlay. No more.
- 4–10s: Demo/Problem — at most 2–3 short lines (max 12 words each), each followed by a brief visual beat
- 11–15s: CTA — one clear line (max 8 words) or text overlay only, then a 2-second hold on the final frame

SELF-CHECK BEFORE WRITING THE FINAL PROMPT:
Count the total spoken words in your draft. If the count exceeds 50, go back and cut. Write the word count in a comment to yourself, then write the final prompt.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MUSIC — REQUIRED IN EVERY PROMPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Music is not optional — every video prompt must include a full music brief. Use the storyboard's music column as your starting point, then make it concrete and specific.

MUSIC STRUCTURE FOR 15 SECONDS:
- 0–3s (Hook): music enters at mid energy — present and attention-grabbing but not overpowering, giving the hook line room to land
- 4–10s (Demo): music sits slightly lower in the mix, ducking under dialogue so speech is always clear; rises slightly on silent visual beats to maintain momentum
- 11–15s (CTA): music lifts back up in energy for the final 4 seconds, then fades cleanly on the freeze frame or hard cut

MUSIC STYLE GUIDELINES:
- Genre: pick ONE specific genre that matches the ad's energy (e.g. "upbeat lo-fi hip-hop", "driving electronic with a clean synth lead", "warm acoustic pop", "modern trap with muted 808s") — never just say "upbeat music"
- BPM: specify a BPM range (e.g. 95–105 BPM for a confident, purposeful feel; 115–125 BPM for high energy; 80–90 BPM for a warmer, trust-building tone)
- Tone: the music must reinforce the emotional arc — curious and light at the hook, building confidence through the demo, punchy and decisive at the CTA
- Mix: always specify that dialogue sections should have music ducked to -12 dB or "sitting clearly beneath the voiceover"; rise to full mix during text-only or silent moments

Write the music brief as a continuous description woven into the video prompt, not as a separate list. Include: genre, BPM, how it enters, how it behaves under dialogue, how it builds to the CTA, and how it exits.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE SINGLE VIDEO PROMPT — CRITICAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a SINGLE flowing paragraph of 400–550 words that describes the entire 15-second video as one continuous experience. It is the ONLY thing the Seedance operator will read.
"""

_PROMPT_WITH_CHARACTER = """
The prompt must:
- Open with: "Use the provided character reference image for the character's exact appearance, clothing, and style throughout the entire video. Use the provided product reference image for the product featured in this video — replicate its exact shape, colour, packaging, and branding in every shot where it appears."
- Cover the full 15 seconds without leaving any gap
- Include EVERY piece of on-screen text with approximate second of appearance
- Include ALL dialogue lines quoted exactly with approximate timing AND a beat of silence after each
- Describe the complete emotional arc from hook through demo to CTA
- The CTA must be explicit: what text appears, what the character says or does, and a 2-second hold on the final frame

MANDATORY ELEMENTS — all woven into the single paragraph:

0. REFERENCE IMAGE DECLARATIONS — open the prompt with these two sentences verbatim:
   "Use the provided character reference image for the character's exact appearance, clothing, and style throughout the entire video. Use the provided product reference image for the product featured in this video — replicate its exact shape, colour, packaging, and branding in every shot where it appears."
1. OPENING FRAME — the very first image the viewer sees, including character position, expression, and environment
2. CHARACTER — always refer to them as "the character"; do not describe appearance (reference image provided)
3. PRODUCT — refer to the product by its category name (e.g. "the serum bottle"). In every scene where the product is shown, write: "the product matches the provided product reference image exactly". Do NOT invent a product description.
4. FULL ACTION SEQUENCE — character movements, gestures, expressions, and transitions across all 15 seconds in temporal order
5. ALL DIALOGUE — every spoken line quoted exactly, with approximate second of delivery and an explicit pause noted after each line
6. ALL ON-SCREEN TEXT — every text overlay, graphic, or caption, with exact wording and approximate second of appearance
7. ENVIRONMENT — describe the set once clearly; note any scene changes if they occur
8. CAMERA PROGRESSION — how the camera moves or changes across the 15 seconds
9. LIGHTING — key light quality and any changes
10. AUDIO & MUSIC — specific genre, BPM range, how music enters, ducks under dialogue, builds to CTA, and exits; any SFX
11. CLOSING FRAME — the exact final image, what text is visible, character's final state, a 2-second hold, then how the video ends

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCE PROMPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each is a standalone paragraph of 75–100 words maximum.

character:
  Tight casting brief. Front-facing portrait, for video generation reference.
  Cover the essentials only: gender, approximate age, ethnicity, skin tone, hair style, build.
  One sentence on clothing (key garment, colour, fit). One sentence on overall vibe/energy.
  Do NOT list every accessory or fabric detail.

location:
  Tight environment brief. Cover the essentials only: interior or exterior, room type, dominant wall/floor materials, key furniture pieces (2–3 max), primary light source, time of day implied, and overall colour mood.
  Do NOT enumerate every prop or background element.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — JSON only, no markdown fences, no explanation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "video_prompt": "<single flowing paragraph 400–550 words covering the entire 15-second video>",
  "reference_prompts": {
    "character": "<standalone paragraph 75–100 words>",
    "location":  "<standalone paragraph 75–100 words>"
  }
}
"""

_PROMPT_NO_CHARACTER = """
The prompt must:
- Open with: "Use the provided product reference image for the product featured in this video — replicate its exact shape, colour, packaging, and branding in every shot where it appears."
- Cover the full 15 seconds without leaving any gap
- Include EVERY piece of on-screen text with approximate second of appearance
- Include ALL voiceover/narration lines quoted exactly with approximate timing
- The CTA must be explicit: what text appears and a 2-second hold on the final frame

MANDATORY ELEMENTS — all woven into the single paragraph:

0. REFERENCE IMAGE DECLARATION — open the prompt with this sentence verbatim:
   "Use the provided product reference image for the product featured in this video — replicate its exact shape, colour, packaging, and branding in every shot where it appears."
1. OPENING FRAME — the very first image the viewer sees, including environment and composition
2. PRODUCT — refer to the product by its category name. In every scene where the product is shown, write: "the product matches the provided product reference image exactly". Do NOT invent a product description.
3. FULL VISUAL SEQUENCE — compositions, movements, and transitions across all 15 seconds in temporal order
4. ALL VOICEOVER/NARRATION — every spoken line quoted exactly, with approximate second of delivery
5. ALL ON-SCREEN TEXT — every text overlay, graphic, or caption, with exact wording and approximate second of appearance
6. ENVIRONMENT — describe the setting clearly; note any scene changes
7. CAMERA PROGRESSION — how the camera moves or changes across the 15 seconds
8. LIGHTING — key light quality and any changes
9. AUDIO & MUSIC — specific genre, BPM range, how music enters, builds, and exits; any SFX
10. CLOSING FRAME — the exact final image, what text is visible, a 2-second hold, then how the video ends

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCE PROMPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

location:
  Tight environment brief (75–100 words). Cover: interior or exterior, room/location type, dominant surfaces, key props (max 3), primary light source, time of day, colour mood.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — JSON only, no markdown fences, no explanation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "video_prompt": "<single flowing paragraph 400–550 words covering the entire 15-second video>",
  "reference_prompts": {
    "location": "<standalone paragraph 75–100 words>"
  }
}
"""


def _build_system_prompt(has_character: bool) -> str:
    return _PROMPT_HEADER + (_PROMPT_WITH_CHARACTER if has_character else _PROMPT_NO_CHARACTER)


def generate_shot_prompts_short(
    storyboard_content: str,
    sections: dict,
    api_key: str = "",
    has_character: bool = True,
) -> dict:
    """
    Generate a single Seedance video prompt for the full 15-second video,
    plus standalone reference prompts.

    Args:
        storyboard_content: Full 15-second storyboard markdown from storyboard_short.
        sections:           Parsed sections dict (simplified, character, scene, style).
        api_key:            BytePlus Ark API key (falls back to config if empty).
        has_character:      False if the video has no human character — omits character
                            reference instruction and character brief from output.
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=api_key or config.ARK_API_KEY)

    character_description = sections.get("character_description", "")
    character             = sections.get("character", "")
    scene                 = sections.get("scene", "")
    style                 = sections.get("style", "")

    user_content = (
        "## Full Revised 15-Second Storyboard\n"
        "(Use the detailed second-by-second table as the primary source "
        "for visual content, dialogue, on-screen text, and timing.)\n\n"
        + storyboard_content
        + "\n\n---\n\n"
        "## Distilled Reference Sections\n"
        "(Use these to build rich standalone reference prompts.)\n\n"
    )

    if has_character and character_description:
        user_content += (
            "### Character Visual Description (extracted from original video)\n"
            "(Prioritise this for appearance details — it reflects the actual actor.)\n\n"
            + character_description
            + "\n\n"
        )

    if has_character and character:
        user_content += "### Character Reference\n\n" + character + "\n\n"

    user_content += (
        "### Scene & Environment Reference\n\n" + scene
        + "\n\n### Style & Camera Reference\n\n" + style
    )

    response = client.chat.completions.create(
        model=config.STORYBOARD_MODEL,
        messages=[
            {"role": "system", "content": _build_system_prompt(has_character)},
            {"role": "user",   "content": user_content},
        ],
        thinking={"type": "enabled"},
    )

    dump = response.model_dump(exclude_none=True)
    raw  = ""
    for ch in dump.get("choices", []):
        raw += (ch.get("message") or {}).get("content") or ""

    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean.strip())
    data  = json.loads(clean)

    usage = dump.get("usage", {})
    return {
        "video_prompt": data.get("video_prompt", ""),
        "reference":    data.get("reference_prompts", {}),
        "raw":          raw,
        "usage": {
            "prompt_tokens":     usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens":  usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
            "total_tokens":      usage.get("total_tokens", 0),
        },
        "usage_raw": usage,
    }
