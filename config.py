import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompt"
OUTPUT_DIR = BASE_DIR / "output"
VIDEO_DIR = BASE_DIR / "video"

# ── API ───────────────────────────────────────────────────────────────────────
ARK_API_KEY    = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL   = "https://ark.ap-southeast.bytepluses.com/api/v3"
SPEECH_API_KEY = os.getenv("SPEECH_API_KEY", "")
TTS_API_KEY    = os.getenv("TTS_API_KEY", "")

# BytePlus IAM credentials — required for Asset Library (CreateAsset / GetAsset)
BYTEPLUS_AK      = os.getenv("BYTEPLUS_AK", "")
BYTEPLUS_SK      = os.getenv("BYTEPLUS_SK", "")
ASSET_GROUP_ID   = os.getenv("ASSET_GROUP_ID", "")   # e.g. "group-20260329160747-xxxxx"

ANALYSIS_MODEL = "seed-2-0-pro-260328"
STORYBOARD_MODEL = "seed-2-0-pro-260328"
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "dreamina-seedance-2-0-260128")
# Seedance 1.5 Pro: "seedance-1-5-pro-251215"  (working, uses resolution + first_frame)
# Seedance 2.0    : "dreamina-seedance-2-0-260128" (uses ratio + reference_video — needs account access)

# Step 5 generation models
SEEDREAM_MODEL   = "seedream-5-0-260128"          # image generation (character / scene references)
SEEDANCE_V2_MODEL = "dreamina-seedance-2-0-260128"  # video generation per shot

# ── Video generation defaults ─────────────────────────────────────────────────
VIDEO_RATIO = "9:16"            # Seedance 2.0: ratio param ("16:9"|"9:16"|"1:1")
VIDEO_RESOLUTION = "720p"       # Seedance 1.5: resolution param ("480p"|"720p"|"1080p")
VIDEO_DURATION = 15            # seconds (Seedance 1.5 max is 10)
VIDEO_GENERATE_AUDIO = True
VIDEO_WATERMARK = False
VIDEO_POLL_INTERVAL = 5        # seconds between status polls

# ── Token pricing — VERIFY against official BytePlus Ark pricing page ─────────
# These are placeholder estimates. Update with official rates before demo.
# Seed 2.0 Pro: input tokens (includes video frames) and output tokens (includes reasoning)
COST_PER_1K_INPUT  = 0.0005  # USD per 1K prompt tokens  — needs verification
COST_PER_1K_OUTPUT = 0.003   # USD per 1K completion tokens (reasoning + text) — needs verification
COST_PER_IMAGE = 0.04
# Seedance: billed per output token (frames). 173,700 tokens ≈ 8s 720p video.
# Actual rate from official pricing needed — this is a placeholder.
COST_PER_1K_VIDEO_TOKENS = 0.007  # USD per 1K video completion tokens — needs verification
