"""
Shot Prompter (Short) — Individual shots version
Takes the revised 15-second storyboard and produces:
  - 2–3 individual Seedance shot prompts (~10s each), following the prompt_to_learn format
  - Each shot prompt includes: character reference instruction, product reference instruction,
    character description, environment description, and a timestamped scene breakdown
  - Standalone character reference prompt (for Seedream generation)
"""
import config
from pipeline.common import ark_client, message_content, parse_json_response, usage_summary


DIRECTOR_SYSTEM_PROMPT_SHORT = """You are a world-class short-form video ecommerce director and Seedance AI video prompt engineer specialising in TikTok / Reels / Shorts product ads.

You will receive a revised 15-second storyboard for a compliance-clean product ad, including the second-by-second breakdown with visual content, dialogue, on-screen text, and shot notes.

Your task: break the storyboard into individual shots (~10 seconds each) and write a production-ready Seedance prompt for each shot.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEFORE YOU WRITE A SINGLE SHOT — READ THIS FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
These clips will be edited together into one seamless video. The #1 failure mode is shots that feel like disconnected, independent clips. Before writing any prompt, map the full narrative arc across all shots:

- What is the character's position, posture, and emotional state at the END of each shot? Write this down for yourself first.
- The character's position/motion at the END of shot N must be the logical starting point of shot N+1.
- The dialogue is ONE continuous conversation — it does not restart between shots. A sentence that begins in shot N can end in shot N+1.
- Music is ONE continuous track — do not describe it as starting fresh in each shot. Describe it once fully in Shot 1, then in later shots only note changes (e.g. "music builds", "beat lifts", "music fades").

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHOT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- For a video up to 20s: produce 2 shots (~10s each)
- For a video 20–40s: produce 3–4 shots (~10s each)
- Each shot is one continuous ~10-second clip. Never split a shot mid-dialogue-sentence.
- Label shots by function: Hook, Demo, CTA, etc.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROMPT FORMAT — MANDATORY FOR EVERY SHOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each shot prompt must be a single markdown string following this EXACT structure:

## Shot {N}: {Label} ({time_range})

[Character: use the provided character reference image for the character's exact appearance, clothing, and style throughout this entire shot.]
[Product: use the provided product reference image — replicate its exact shape, colour, packaging, and branding with 100% accuracy. Only show the product when the scene breakdown explicitly calls for it. If a segment does not mention the product, it must NOT appear in frame.]

**Environment:** {Room type, dominant surfaces, key props (max 3), light source, time of day, colour mood. Be concrete and cinematic. Keep consistent with other shots unless the scene explicitly changes.}

**Continuity:** {For Shot 1 write: "Opening shot." For Shot N>1 write: "Continues from Shot {N-1}: the character was [exact position/action/emotion at end of previous shot]. This shot opens with [exact entry state]. Exits into Shot {N+1}: [describe how this shot ends to set up the next — character position, emotion, action]." For the final shot write: "Final shot — exits with [closing frame description]."}

**Scene Breakdown:**
- {start}s – {end}s: [{Camera type and movement}] + [{Exact character action and body language — cinematic specifics, not abstract summaries}] + [Voiceover (en-US, {emotional tone}): "{exact words spoken}"] + [Subtitle: "{ALL CAPS SHORT PHRASE, MAX 6 WORDS}"]
- {start}s – {end}s: [{Camera type and movement}] + [{Exact character action}] + [Voiceover (en-US, {emotional tone}): "{exact words}"] + [Subtitle: "{ALL CAPS SUBTITLE}"]
...repeat for each timestamped segment within the shot...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Every timestamped segment must include ALL FOUR elements: camera, action, voiceover, subtitle. No exceptions.
2. Voiceover MUST specify language (en-US) and emotional tone in parentheses, e.g. (en-US, excited/surprised tone) or (en-US, warm/confiding tone) or (en-US, urgent/direct tone).
3. Actions must be cinematic and specific. NOT "shows the product" — WRITE "holds the product up to camera center with both hands, tilting it 15 degrees toward the lens, making direct eye contact with the viewer."
4. Product visibility rule: if a segment does not explicitly show the product, write [No product visible in this segment] inside the camera bracket, e.g. "[Medium shot, handheld — no product visible]".
5. Subtitles are ALL CAPS, punchy phrases, max 6 words per subtitle.
6. Voiceover dialogue must be copied EXACTLY from the storyboard — do not paraphrase or shorten.
7. Timestamps within a shot must be continuous from the shot's start time to its end time with no gaps.
8. The character must NOT reset to a neutral standing position between shots — this is the #1 cause of disconnected feel. The entry state of every shot must follow naturally from the exit state of the previous one.
9. Keep the character on the same side of the frame across consecutive shots unless a deliberate scene change is described in the storyboard.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCE PROMPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
character: Tight casting brief. Front-facing portrait, for video generation reference.
  Cover the essentials only: gender, approximate age, ethnicity, skin tone, hair style, build.
  One sentence on clothing (key garment, colour, fit). One sentence on overall vibe/energy.
  Do NOT list every accessory or fabric detail.

location: Standalone environment brief for Seedream (75–100 words). Cover: interior/exterior, room type, dominant wall/floor surfaces, key furniture/props (max 3), primary light source, time of day, colour mood.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT — valid JSON only, no markdown fences, no explanation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "shots": [
    {
      "shot_id": 1,
      "label": "Hook",
      "time_range": "0s–7s",
      "duration_sec": 7,
      "prompt": "<full shot prompt string in the exact format above>"
    }
  ],
  "reference": {
    "character": "<standalone paragraph 75–100 words>",
    "location":  "<standalone paragraph 75–100 words>"
  }
}
"""


def generate_shot_prompts_short(storyboard_content: str, sections: dict, api_key: str = "") -> dict:
    """
    Generate individual Seedance shot prompts (~10s each) from the revised storyboard.
    Each prompt follows the prompt_to_learn format:
      - Character reference instruction
      - Product reference instruction
      - Character description + Environment description
      - Timestamped scene breakdown with camera / action / voiceover / subtitle

    Args:
        storyboard_content: Full 15-second storyboard markdown from storyboard_short.
        sections:           Parsed sections dict (simplified, character, scene, style).

    Returns:
        {
            "shots":     list[dict],   # each has shot_id, label, time_range, duration_sec, prompt
            "reference": dict,         # {"character": str, "location": str}
            "raw":       str,
            "usage":     dict,
        }
    """
    client = ark_client(api_key)

    character_description = sections.get("character_description", "")
    character             = sections.get("character", "")
    scene                 = sections.get("scene", "")
    style                 = sections.get("style", "")

    user_content = (
        "## Full Revised 15-Second Storyboard\n"
        "(Use the detailed second-by-second table as the primary source "
        "for dialogue, on-screen text, actions, and timing.)\n\n"
        + storyboard_content
        + "\n\n---\n\n"
        "## Reference Sections\n"
        "(Use these to write the Character Description, Environment Description, "
        "and standalone reference prompts in each shot.)\n\n"
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
        + "\n\n### Scene & Environment\n\n" + scene
        + "\n\n### Style & Camera\n\n"      + style
    )

    response = client.chat.completions.create(
        model=config.STORYBOARD_MODEL,
        messages=[
            {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT_SHORT},
            {"role": "user",   "content": user_content},
        ],
        thinking={"type": "enabled"},
    )

    raw, usage = message_content(response)
    data = parse_json_response(raw)
    return {
        "shots":     data.get("shots", []),
        "reference": data.get("reference", {}),
        "raw":       raw,
        "usage": usage_summary(usage),
        "usage_raw": usage,
    }
