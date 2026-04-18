"""
Step 4 — Video Generation (Seedance 2.0)
Builds per-scene prompts from the storyboard, submits async tasks to
dreamina-seedance-2-0-260128, and polls until completion.

Input per task:
  - text prompt  : videoGenPrompt header + new storyboard scene
  - reference_video : original "bad" video (base64 data URL) for character/style continuity
"""
import base64
import os
import re
from pathlib import Path
from typing import Optional

import config


# ── Video generation prompt ────────────────────────────────────────────────────
def _read_video_gen_prompt() -> str:
    path = config.PROMPTS_DIR / "videoGenPrompt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _encode_video(video_path: str) -> str:
    with open(video_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ── Scene prompt builder ──────────────────────────────────────────────────────
def build_scene_prompts(sections: dict) -> list[dict]:
    """
    Build individual Seedance 2.0 generation prompts from storyboard sections 4.1–4.4.

    Returns list of scene dicts:
    [
        {
            "label":     str,
            "prompt":    str,   # full text sent to Seedance
            "status":    "pending",
            "task_id":   None,
            "video_url": None,
            "error":     None,
        },
        ...
    ]
    """
    char   = sections.get("character", "")
    style  = sections.get("style", "")
    simplified = sections.get("simplified", "")

    rows = _parse_table_rows(simplified)
    n = len(rows)

    # Split into 3 scene groups: hook / main / cta
    splits = [
        rows[: max(1, n // 3)],
        rows[max(1, n // 3) : max(2, 2 * n // 3)],
        rows[max(2, 2 * n // 3) :],
    ]
    labels = ["Hook & Intro (0–5s)", "Product Demo (5–15s)", "CTA & Close (15–20s)"]

    try:
        base_prompt = _read_video_gen_prompt()
    except FileNotFoundError:
        base_prompt = "Generate an improved marketing video ad following this storyboard:\n\n--- NEW STORYBOARD ---\n"

    scenes = []
    for label, scene_rows in zip(labels, splits):
        if not scene_rows:
            continue
        scene_desc = "\n".join(
            f"[{r['second']}] {r['scene']} | Dialogue: {r['dialogue']}"
            for r in scene_rows
        )
        prompt = _build_prompt(base_prompt, label, scene_desc, char, style)
        scenes.append({
            "label":     label,
            "prompt":    prompt,
            "status":    "pending",
            "task_id":   None,
            "video_url": None,
            "error":     None,
        })

    # Fallback: one scene from the full storyboard
    if not scenes:
        fallback_desc = simplified[:1500] or sections.get("regeneration", "")
        prompt = _build_prompt(base_prompt, "Full Ad", fallback_desc, char, style)
        scenes.append({
            "label":     "Full Ad (0–20s)",
            "prompt":    prompt,
            "status":    "pending",
            "task_id":   None,
            "video_url": None,
            "error":     None,
        })

    return scenes


def _parse_table_rows(table_text: str) -> list[dict]:
    rows = []
    for line in table_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() not in ("second", ""):
            rows.append({
                "second":   cells[0] if len(cells) > 0 else "",
                "scene":    cells[1] if len(cells) > 1 else "",
                "dialogue": cells[2] if len(cells) > 2 else "",
                "notes":    cells[3] if len(cells) > 3 else "",
            })
    return rows


def _build_prompt(base: str, label: str, scene_desc: str, character: str, style: str) -> str:
    """
    Combine the videoGenPrompt header with scene-specific content.
    Seedance 2.0 works best with prompts under ~500 words.
    """
    parts = [
        base.strip(),
        f"\n## Scene: {label}\n",
        scene_desc,
    ]
    if character:
        parts.append(f"\n## Character Reference\n{character[:400]}")
    if style:
        parts.append(f"\n## Visual Style\n{style[:400]}")

    prompt = "\n".join(parts)
    if len(prompt) > 3000:
        prompt = prompt[:3000] + "\n[truncated]"
    return prompt



# ── Real implementation ────────────────────────────────────────────────────────
def submit_video_tasks(
    scenes: list[dict],
    reference_video_path: Optional[str] = None,
) -> list[dict]:
    """
    Submit all scene tasks to Seedance 2.0.

    Args:
        scenes:               List returned by build_scene_prompts().
        reference_video_path: Path to the original "bad" video.
                              Encoded as base64 and sent as reference_video so
                              Seedance preserves character/style continuity.

    Returns:
        Same list with task_id and status updated to "submitted".
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=config.ARK_API_KEY)

    is_v2 = "seedance-2" in config.VIDEO_MODEL or "dreamina" in config.VIDEO_MODEL

    # Encode reference video once, reuse for every scene task
    ref_video_b64 = None
    if reference_video_path:
        try:
            ref_video_b64 = _encode_video(reference_video_path)
        except Exception as e:
            print(f"[generator] Warning: could not encode reference video: {e}")

    for scene in scenes:
        content = [{"type": "text", "text": scene["prompt"]}]

        if ref_video_b64:
            if is_v2:
                # Seedance 2.0 requires reference_video as a public HTTPS URL — base64 not supported.
                # Character/style continuity is handled entirely via the text prompt
                # (storyboard sections 4.2 Character, 4.3 Scene, 4.4 Style).
                pass
            else:
                # Seedance 1.5 — first frame as first_frame reference
                # Extract first frame from the base64 video via ffmpeg
                import subprocess, tempfile, base64 as b64lib
                tmp_in  = tempfile.mktemp(suffix=".mp4")
                tmp_out = tempfile.mktemp(suffix=".jpg")
                try:
                    with open(tmp_in, "wb") as fv:
                        fv.write(b64lib.b64decode(ref_video_b64))
                    res = subprocess.run(
                        ["ffmpeg", "-y", "-i", tmp_in, "-vframes", "1", "-q:v", "2", tmp_out],
                        capture_output=True, timeout=15,
                    )
                    if res.returncode == 0:
                        with open(tmp_out, "rb") as fi:
                            frame_b64 = b64lib.b64encode(fi.read()).decode()
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"},
                            "role": "first_frame",
                        })
                except Exception as e:
                    print(f"[generator] Warning: first-frame extraction failed: {e}")
                finally:
                    for p in (tmp_in, tmp_out):
                        try: os.remove(p)
                        except: pass

        try:
            if is_v2:
                task = client.content_generation.tasks.create(
                    model=config.VIDEO_MODEL,
                    content=content,
                    ratio=config.VIDEO_RATIO,
                    duration=config.VIDEO_DURATION,
                    generate_audio=config.VIDEO_GENERATE_AUDIO,
                    watermark=config.VIDEO_WATERMARK,
                )
            else:
                task = client.content_generation.tasks.create(
                    model=config.VIDEO_MODEL,
                    content=content,
                    resolution=config.VIDEO_RESOLUTION,
                    duration=config.VIDEO_DURATION,
                    generate_audio=config.VIDEO_GENERATE_AUDIO,
                )
            scene["task_id"] = task.id
            scene["status"]  = "submitted"
        except Exception as e:
            scene["status"] = "failed"
            scene["error"]  = str(e)

    return scenes


def poll_video_tasks(scenes: list[dict]) -> list[dict]:
    """
    Poll all in-flight tasks once and update their status.
    Call repeatedly (with sleep between) until all_done() returns True.
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=config.ARK_API_KEY)

    for scene in scenes:
        if scene["status"] in ("succeeded", "failed") or not scene.get("task_id"):
            continue
        try:
            result = client.content_generation.tasks.get(task_id=scene["task_id"])
            scene["status"] = result.status      # "running" | "succeeded" | "failed"
            if result.status == "succeeded":
                # SDK uses result.content.video_url (not result.output.video_url)
                scene["video_url"] = result.content.video_url
            elif result.status == "failed":
                scene["error"] = str(getattr(result, "error", "unknown"))
        except Exception as e:
            scene["error"] = str(e)

    return scenes


def all_done(scenes: list[dict]) -> bool:
    return all(s["status"] in ("succeeded", "failed") for s in scenes)


# ── Step 5 — Seedream image generation ────────────────────────────────────────

def generate_image(prompt: str) -> dict:
    """
    Generate an image with Seedream 5.0 Lite via the synchronous images.generate API.

    Args:
        prompt: Text prompt for the image.

    Returns:
        {
            "image_url": str | None,
            "status":    "succeeded" | "failed",
            "error":     str | None,
        }
    """
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=config.ARK_API_KEY)

    try:
        response = client.images.generate(
            model=config.SEEDREAM_MODEL,
            prompt=prompt,
        )
        image_url = response.data[0].url

        # Extract usage if the API returns it
        usage_raw = {}
        try:
            dump = response.model_dump(exclude_none=True)
            usage_raw = dump.get("usage", {})
        except Exception:
            pass

        return {
            "image_url": image_url,
            "status":    "succeeded",
            "error":     None,
            "usage_raw": usage_raw,
        }
    except Exception as e:
        return {"image_url": None, "status": "failed", "error": str(e), "usage_raw": {}}


# ── Step 5 — Seedance 2.0 per-shot video generation ──────────────────────────

def generate_shot_video(
    prompt: str,
    char_image_url: Optional[str] = None,
    product_image_url: Optional[str] = None,
    poll_interval: int = 5,
    duration: Optional[int] = None,
) -> dict:
    """
    Submit a Seedance 2.0 video generation task with optional reference images
    (character and product) and poll until complete.

    Args:
        prompt:            AI video prompt for this shot.
        char_image_url:    URL of the Seedream-generated character reference image.
        product_image_url: URL of the Seedream-generated product reference image.
        poll_interval:     Seconds between status polls.
        duration:          Video duration in seconds. Defaults to config.VIDEO_DURATION.

    Returns:
        {
            "video_url": str | None,
            "task_id":   str,
            "status":    "succeeded" | "failed",
            "error":     str | None,
        }
    """
    import time
    from byteplussdkarkruntime import Ark

    client = Ark(base_url=config.ARK_BASE_URL, api_key=config.ARK_API_KEY)

    content = [{"type": "text", "text": prompt}]

    # Attach reference images.
    # char_image_url   — HTTPS URL from Seedream (Seedance requires HTTPS for video, but
    #                    accepts base64 data URIs for reference images).
    # product_image_url — HTTPS URL or base64 data URI from user's uploaded product photo.
    # role="reference_image" is required by the API for all image content items.
    if char_image_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": char_image_url},
            "role": "reference_image",
        })
    if product_image_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": product_image_url},
            "role": "reference_image",
        })

    task = client.content_generation.tasks.create(
        model=config.SEEDANCE_V2_MODEL,
        content=content,
        ratio=config.VIDEO_RATIO,
        duration=duration if duration is not None else config.VIDEO_DURATION,
        generate_audio=config.VIDEO_GENERATE_AUDIO,
        watermark=config.VIDEO_WATERMARK,
    )
    task_id = task.id

    while True:
        result = client.content_generation.tasks.get(task_id=task_id)
        if result.status == "succeeded":
            video_url = result.content.video_url

            # Extract usage from the completed task response
            usage_raw = {}
            video_tokens = 0
            try:
                dump = result.model_dump(exclude_none=True)
                usage_raw = dump.get("usage", {})
                video_tokens = usage_raw.get("completion_tokens", 0) or usage_raw.get("total_tokens", 0)
            except Exception:
                pass

            return {
                "video_url":    video_url,
                "task_id":      task_id,
                "status":       "succeeded",
                "error":        None,
                "usage_raw":    usage_raw,
                "video_tokens": video_tokens,
            }
        elif result.status == "failed":
            err = str(getattr(result, "error", "unknown error"))
            return {"video_url": None, "task_id": task_id, "status": "failed",
                    "error": err, "usage_raw": {}, "video_tokens": 0}
        time.sleep(poll_interval)
