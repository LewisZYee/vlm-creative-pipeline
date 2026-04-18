# Creative Production Pipeline

An AI-powered video ad analysis and creative generation system built on BytePlus Seed 2.0 Pro, Seedream, and Seedance.

**Author:** Lewis Zhao, BytePlus EUI Solution Architect

---

## What it does

Upload a marketing video (TikTok, Reels, YouTube Shorts). The pipeline will:

1. **Analyze** — Seed 2.0 Pro VLM reviews the video for compliance violations, scores it across 6 dimensions (compliance, traffic quality, brand safety, etc.), and produces a second-by-second storyboard breakdown
2. **Critique** — Extracts structured issues with severity levels (HIGH / MEDIUM / LOW) and targeted fix recommendations
3. **Storyboard** — Generates a revised, compliance-clean storyboard that preserves the strongest hook and CTA from the original
4. **Generate** — Produces reference images (Seedream) and per-scene videos (Seedance 2.0) from the new storyboard

Two UI variants are available:
- **Short-form** (`app_short.py`) — outputs a 15-second version
- **Long-form** (`app_long.py`) — outputs a longer-form version

---

## Project structure

```
vlm_creative_pipeline/
├── agent-pipeline/
│   ├── app_short.py          # Streamlit UI — 15-second short-form
│   └── app_long.py           # Streamlit UI — long-form
├── pipeline/
│   ├── analyzer.py           # Step 1: video analysis via Seed 2.0 Pro
│   ├── critic.py             # Step 2: score parsing + issue extraction
│   ├── storyboard_short.py   # Step 3: 15-second storyboard generation
│   ├── storyboard_long.py    # Step 3: long-form storyboard generation
│   ├── shotprompter_short.py # Step 3b: per-shot prompt builder (short)
│   ├── shotprompter_long.py  # Step 3b: per-shot prompt builder (long)
│   └── generator.py          # Step 4: Seedream image + Seedance video generation
├── prompt/
│   ├── analysisPrompt        # System prompt for video analysis
│   ├── storyboardPrompt      # System prompt for storyboard generation
│   └── videoGenPrompt        # Header prompt for Seedance video generation
├── config.py                 # API keys, model IDs, generation defaults
├── requirements.txt
└── .env                      # Your API credentials (not committed)
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd vlm_creative_pipeline
pip install -r requirements.txt
```

### 2. Configure API credentials

Copy the example below into a `.env` file at the project root:

```env
# BytePlus Ark API (Seed 2.0 Pro, Seedream, Seedance)
ARK_API_KEY=your_ark_api_key

# BytePlus IAM credentials (Asset Library)
BYTEPLUS_AK=your_access_key
BYTEPLUS_SK=your_secret_key
ASSET_GROUP_ID=group-xxxxxxxxxxxxxxxx
```

All keys are available from the [BytePlus console](https://console.byteplus.com).

### 3. Run

**Short-form (15-second output):**
```bash
streamlit run agent-pipeline/app_short.py
```

**Long-form output:**
```bash
streamlit run agent-pipeline/app_long.py
```

The app opens at `http://localhost:8501`.

---

## Usage

1. Select whether your video is **underperforming** or **top-performing**
2. Upload a `.mp4`, `.mov`, or `.avi` file
3. Click **Analyze →**
4. Step through the pipeline — each stage is interactive and shows full model output
5. Generate reference images and videos per scene in the final step

---

## Models used

| Model | Role |
|-------|------|
| `seed-2-0-pro-260328` | Video analysis & storyboard generation |
| `seedream-5-0-260128` | Character / scene reference image generation |
| `dreamina-seedance-2-0-260128` | Per-shot video generation |

---

## Requirements

- Python 3.10+
- BytePlus Ark API access with Seed 2.0 Pro, Seedream, and Seedance enabled
- BytePlus IAM credentials with Asset Library permissions
