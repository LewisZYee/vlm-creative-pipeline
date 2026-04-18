"""
Shot Prompter (Short) — Single-prompt version for 15-second videos
Takes the revised 15-second storyboard and produces:
  - ONE single Seedance video prompt covering the full 15 seconds end-to-end
  - Standalone character reference prompt (Seedream)
  - Standalone location reference prompt (Seedream)
"""
import json
import re

import config


DIRECTOR_SYSTEM_PROMPT_SHORT = """You are a professional film director and AI video prompt engineer specialising in Seedance / Seedream generation for short-form social ads.

You will receive the full revised 15-second storyboard, including the second-by-second breakdown with visual content, characters, emotion, action, shot type, on-screen text, dialogue, music, and optimization notes.

Your task: produce ONE single Seedance video prompt that covers the entire 15-second video from first frame to last frame — plus two standalone reference image prompts (character and location).

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

The prompt must:
- Open with: "Use the provided character reference image for the character's exact appearance, clothing, and style throughout the entire video. Use the provided product reference image for the product featured in this video — replicate its exact shape, colour, packaging, and branding in every shot where it appears."
- Cover the full 15 seconds without leaving any gap — viewer should be able to follow the complete story from this prompt alone
- Include EVERY piece of on-screen text, caption, title card, and lower-third in the exact wording from the storyboard and the approximate second they appear (e.g. "at 3 seconds, the text overlay reads…")
- Include ALL dialogue lines quoted exactly with approximate timing AND a beat of silence after each (e.g. "at 4 seconds the character says '…', then pauses, holding the camera's gaze for one beat")
- Describe the complete emotional arc: how the character's energy and expression evolve from the hook through the demo to the CTA
- NO sudden stops or unresolved narrative threads — the story must feel complete and satisfying at second 15
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
10. AUDIO & MUSIC — specific genre, BPM range, how music enters at 0s, ducks under dialogue, builds through the demo, lifts at the CTA, and exits; any SFX
11. CLOSING FRAME — the exact final image, what text is visible, character's final state, a 2-second hold, then how the video ends (fade / hard cut / freeze)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCE PROMPTS — 2 STANDALONE PARAGRAPHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each is a standalone paragraph of 75–100 words maximum. Keep them concise. Do NOT reference shot numbers or "as above".

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


def generate_shot_prompts_short(storyboard_content: str, sections: dict) -> dict:
    """
    Generate a single Seedance video prompt for the full 15-second video,
    plus standalone character and location reference prompts.

    Args:
        storyboard_content: Full 15-second storyboard markdown from storyboard_short.
        sections:           Parsed sections dict (simplified, character, scene, style).

    Returns:
        {
            "video_prompt": str,    # single prompt for the full 15s video
            "reference":    dict,   # {"character": str, "location": str}
            "raw":          str,
            "usage":        dict,
        }
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=config.ARK_API_KEY)

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

    if character_description:
        user_content += (
            "### Character Visual Description (extracted from original video)\n"
            "(Prioritise this for appearance details — it reflects the actual actor.)\n\n"
            + character_description
            + "\n\n"
        )

    user_content += (
        "### Character Reference\n\n"    + character
        + "\n\n### Scene & Environment Reference\n\n" + scene
        + "\n\n### Style & Camera Reference\n\n"      + style
    )

    response = client.chat.completions.create(
        model=config.STORYBOARD_MODEL,
        messages=[
            {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT_SHORT},
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
