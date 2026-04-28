import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompt"

# ── API ───────────────────────────────────────────────────────────────────────
ARK_API_KEY  = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3"

# ── Models ────────────────────────────────────────────────────────────────────
ANALYSIS_MODEL    = "seed-2-0-pro-260328"
STORYBOARD_MODEL  = "seed-2-0-pro-260328"
SEEDREAM_MODEL    = "seedream-5-0-260128"
SEEDANCE_V2_MODEL = "dreamina-seedance-2-0-260128"

# ── Video generation defaults ─────────────────────────────────────────────────
VIDEO_RATIO           = "9:16"
VIDEO_DURATION        = 15
VIDEO_GENERATE_AUDIO  = True
VIDEO_WATERMARK       = False

# ── Token pricing (USD) ───────────────────────────────────────────────────────
COST_PER_1K_INPUT        = 0.0005
COST_PER_1K_OUTPUT       = 0.003
COST_PER_IMAGE           = 0.04
COST_PER_1K_VIDEO_TOKENS = 0.007
