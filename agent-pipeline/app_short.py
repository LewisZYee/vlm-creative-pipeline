"""
Creative Production Pipeline — Conversational Agent UI (Short-form)
Run: streamlit run agent-pipeline/app_short.py

Author: Lewis Zhao, BytePlus EUI Solution Architect
"""
import sys
import tempfile
from pathlib import Path

import streamlit as st

# ── Imports from root pipeline ─────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

import config
from pipeline.analyzer import analyze_video
from pipeline.critic import generate_critique
from pipeline.storyboard_short import generate_storyboard_short
from pipeline.shotprompter_short import generate_shot_prompts_short
from pipeline.generator import generate_image, generate_shot_video
from pipeline.qa_monitor import qa_generated_video

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Creative Pipeline",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Wide layout — fills the viewport */
.block-container { max-width: 1100px; padding-top: 1.5rem; padding-bottom: 3rem; }

/* Tighten gap between messages */
[data-testid="stChatMessage"] { margin-bottom: 2px; }

/* Send-style buttons — no text wrap, consistent sizing, flush to right edge */
[data-testid="stButton"] button {
    white-space: nowrap;
    min-width: 140px;
    margin-right: -0.5rem;
}

/* Consistent 1rem for all chat response text */
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li,
[data-testid="stChatMessageContent"] ol,
[data-testid="stChatMessageContent"] ul { font-size: 1rem !important; }

/* ── Smaller metrics ─────────────────────────────────── */
[data-testid="stMetricLabel"] p  { font-size: 0.78rem !important; }
[data-testid="stMetricValue"]    { font-size: 1.08rem !important; }
[data-testid="stMetric"]         { padding: 6px 2px !important; }

/* ── Section micro-label ─────────────────────────────── */
.section-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748b;
    margin: 14px 0 4px 0;
}

/* ── Compliance badge ────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.76rem;
    font-weight: 700;
    margin-right: 6px;
    vertical-align: middle;
}
.badge-pass { background: #16a34a22; color: #4ade80; border: 1px solid #4ade8040; }
.badge-risk { background: #d9770622; color: #fbbf24; border: 1px solid #fbbf2440; }
.badge-fail { background: #dc262622; color: #f87171; border: 1px solid #f8717140; }

/* ── Issue card ──────────────────────────────────────── */
.issue-card {
    border-left: 3px solid #334155;
    padding: 7px 12px;
    margin: 5px 0;
    border-radius: 0 7px 7px 0;
    background: rgba(148, 163, 184, 0.12);
    font-size: 0.85rem;
    line-height: 1.55;
}
.issue-high { border-color: #f87171; }
.issue-med  { border-color: #fbbf24; }
.issue-low  { border-color: #4ade80; }
.issue-meta { font-weight: 600; }
.issue-ts   { color: #475569; font-size: 0.74rem; font-weight: 400; margin-left: 5px; }
.issue-orig { color: #94a3b8; font-style: italic; font-size: 0.82rem; margin: 2px 0; }
.issue-fix  { color: #7dd3fc; font-size: 0.82rem; }

/* ── File pill (shown after file selected) ───────────── */
.file-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.82rem;
    color: #cbd5e1;
}

/* ── Token note ──────────────────────────────────────── */
.token-note {
    color: #475569;
    font-size: 0.72rem;
    margin-top: 12px;
    padding-top: 8px;
    border-top: 1px solid #1e293b;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
_DEFAULTS = {
    "current_step": 0,      # 0=input  1=analysis done  3=storyboard done  4=generation
    "video_path": None,
    "video_name": None,
    "performance": "bad",
    "analysis_result": None,
    "critique_result": None,
    "storyboard_result": None,
    "shot_result": None,
    "character_description": "",
    "gen_images": {},
    "gen_videos": {},
    "qa_result": None,
    "_stage_path": None,    # file staged for analysis (before clicking Analyze)
    "_stage_name": None,
    "_stage_perf": "bad",
    "api_usage": {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
        "video_tokens": 0,
        "images_generated": 0,
        "videos_generated": 0,
    },
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── API Key Gate ───────────────────────────────────────────────────────────────
if "ark_api_key" not in st.session_state:
    st.session_state.ark_api_key = ""

if not st.session_state.ark_api_key:
    st.markdown("## Enter your BytePlus API Key")
    st.markdown(
        "Your key is used only for this browser session and is never stored or logged. "
        "Each participant uses their own key and pays their own usage costs."
    )
    with st.form("api_key_form"):
        key_input = st.text_input(
            "API Key",
            type="password",
            placeholder="Paste your BytePlus Ark API key here…",
        )
        if st.form_submit_button("Start →", type="primary"):
            if key_input.strip():
                st.session_state.ark_api_key = key_input.strip()
                st.rerun()
            else:
                st.error("Please enter a valid API key.")
    st.stop()

_API_KEY = st.session_state.ark_api_key


# ── Helpers ────────────────────────────────────────────────────────────────────
def _add_usage(usage: dict, video_tokens: int = 0):
    u = st.session_state.api_usage
    u["prompt_tokens"]     += usage.get("prompt_tokens", 0)
    u["completion_tokens"] += usage.get("completion_tokens", 0)
    u["total_tokens"]      += usage.get("total_tokens", 0)
    u["calls"]             += 1
    u["video_tokens"]      += video_tokens


def _save_upload(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def _cost() -> float:
    u = st.session_state.api_usage
    return (
        u["prompt_tokens"]     / 1000 * config.COST_PER_1K_INPUT
        + u["completion_tokens"] / 1000 * config.COST_PER_1K_OUTPUT
        + u["video_tokens"]      / 1000 * config.COST_PER_1K_VIDEO_TOKENS
        + u["images_generated"]  * config.COST_PER_IMAGE
    )


_SEV_ICON  = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
_SEV_CLASS = {"HIGH": "issue-high", "MEDIUM": "issue-med", "LOW": "issue-low"}


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 Creative Pipeline")
    st.caption("BytePlus Seed 2.0 Pro · Seedream · Seedance")
    st.divider()

    cs = st.session_state.current_step
    st.markdown(f"{'✅' if cs > 1  else ('⏳' if cs == 1 else '○')} **Step 1** — Analysis & Compliance")
    st.markdown(f"{'✅' if cs > 3  else ('⏳' if cs == 3 else '○')} **Step 2** — Storyboard")
    st.markdown(f"{'✅' if cs > 4  else ('⏳' if cs == 4 else '○')} **Step 3** — Image & Video")

    _qa = st.session_state.get("qa_result")
    if _qa:
        _pass = _qa["qa"].get("overall_pass", False)
        _icon = "✅" if _pass else "❌"
        _label = "PASS" if _pass else "FAIL"
        st.markdown(f"{_icon} **Add On** — QA & Monitoring · **{_label}**")
    else:
        st.markdown("○ **Add On** — QA & Monitoring")

    st.divider()
    u = st.session_state.api_usage
    col1, col2 = st.columns(2)
    col1.metric(
        "Images",
        u["images_generated"],
        help=f"Each image ~${config.COST_PER_IMAGE}/call. Image API returns no tokens — image cost is tracked separately and not included in the token count.",
    )
    col2.metric("Videos", u["videos_generated"])
    total_all_tokens = u["total_tokens"] + u["video_tokens"]
    st.metric(
        "Tokens Used",
        f"{total_all_tokens:,}",
        help="Seed 2.0 Pro (text + video analysis) + Seedance 2.0 (video generation). Image generation is not token-billed and is excluded.",
    )
    cost = _cost()
    st.metric("Est. Cost (USD)", f"${cost:.4f}")

    st.divider()
    if st.button("↺ Start Over", use_container_width=True):
        for k, v in _DEFAULTS.items():
            st.session_state[k] = v if not isinstance(v, dict) else dict(v)
        st.rerun()

    st.divider()
    st.caption("Lewis Zhao - BytePlus EUI")


# ══════════════════════════════════════════════════════════════════════════════
# [AGENT] Greeting — always shown, collapses once past step 0
# ══════════════════════════════════════════════════════════════════════════════
with st.chat_message("assistant", avatar="🎬"):

    if st.session_state.current_step == 0:
        st.markdown("**Hi! I'm your creative production assistant.**")
        st.markdown(
            "Upload a marketing video and I'll analyze it for compliance issues, "
            "score it across 6 dimensions, then generate an improved 15-second version."
        )

        st.markdown("")
        perf_choice = st.radio(
            "How did this video perform?",
            [
                "Underperforming — analyze what went wrong",
                "Top-performing — understand what works",
            ],
            index=0,
        )
        performance = "bad" if "Underperforming" in perf_choice else "good"
        st.session_state._stage_perf = performance

        uploaded = st.file_uploader(
            "Drop a .mp4 / .mov file",
            type=["mp4", "mov", "avi"],
            label_visibility="collapsed",
        )
        if uploaded:
            if st.session_state._stage_name != uploaded.name:
                st.session_state._stage_path = _save_upload(uploaded)
                st.session_state._stage_name = uploaded.name
            st.markdown(
                f'<div class="file-pill">📹 {uploaded.name}</div>',
                unsafe_allow_html=True,
            )

    else:
        # Compact — just the intro line
        st.markdown(
            "**Hi! I'm your creative production assistant.** "
            "Upload a video to analyze compliance, score performance, and generate an improved version."
        )


# ── Analyze button — in user bubble so it's naturally right-aligned ────────────
if st.session_state.current_step == 0 and st.session_state._stage_name:
    with st.chat_message("user"):
        st.markdown(f"📹 **{st.session_state._stage_name}**")
        if st.button("Analyze →", type="primary", key="analyze_btn"):
            st.session_state.video_path  = st.session_state._stage_path
            st.session_state.video_name  = st.session_state._stage_name
            st.session_state.performance = st.session_state._stage_perf
            st.session_state.current_step = 1
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# [USER] Video submission message — shown once step >= 1
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step >= 1:
    perf_label = "underperforming" if st.session_state.performance == "bad" else "top-performing"
    with st.chat_message("user"):
        st.markdown(
            f"📹 **{st.session_state.video_name}**  \n"
            f"_{perf_label} · please analyze for compliance and performance_"
        )


# ══════════════════════════════════════════════════════════════════════════════
# [AGENT] Analysis — run then display
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step >= 1:

    # Run if not done yet
    if st.session_state.analysis_result is None:
        with st.chat_message("assistant", avatar="🎬"):
            with st.status("Analyzing your video…", expanded=True) as status:
                st.write("📹 Sending to Seed 2.0 Pro VLM…")
                a_result = analyze_video(
                    st.session_state.video_path,
                    performance=st.session_state.performance,
                    api_key=_API_KEY,
                )
                _add_usage(a_result["usage"])
                st.session_state.analysis_result = a_result
                st.session_state.character_description = a_result.get("character_description", "")

                st.write("🔍 Extracting compliance issues and scores…")
                cr = generate_critique(a_result["content"], api_key=_API_KEY)
                _add_usage(cr["usage"])
                st.session_state.critique_result = cr

                status.update(label="Analysis complete ✓", state="complete")
        st.rerun()

    # Display results
    if st.session_state.analysis_result and st.session_state.critique_result:
        result = st.session_state.analysis_result
        cr     = st.session_state.critique_result
        crit   = cr["critique"]

        status_val = crit.get("compliance_status", "—")
        risk       = crit.get("risk_level", "—")
        viral      = crit.get("viral_potential_score", "—")
        scores     = crit.get("scores", {})
        issues     = crit.get("issues", [])
        recs       = crit.get("top_recommendations", [])
        positives  = crit.get("what_works_well", [])
        n_high     = sum(1 for i in issues if i.get("severity") == "HIGH")
        vp_expl    = crit.get("viral_potential_explanation", "")

        with st.chat_message("assistant", avatar="🎬"):

            # Lead sentence
            if n_high:
                st.markdown(
                    f"I found **{len(issues)} issue{'s' if len(issues) != 1 else ''}** "
                    f"({n_high} critical). Here's the full picture:"
                )
            elif issues:
                st.markdown(
                    f"Analysis complete — **{len(issues)} minor issue{'s' if len(issues) != 1 else ''}** found, "
                    f"no critical violations."
                )
            else:
                st.markdown("Analysis complete — no compliance issues. Your video looks clean.")

            # Compliance status bar
            badge_cls  = {"PASS": "badge-pass", "AT RISK": "badge-risk", "FAIL": "badge-fail"}.get(status_val, "badge-risk")
            badge_icon = {"PASS": "✅", "AT RISK": "⚠️", "FAIL": "🚫"}.get(status_val, "⚪")
            st.markdown(
                f'<span class="badge {badge_cls}">{badge_icon} {status_val}</span>'
                f'Risk: <strong>{risk}</strong> &nbsp;·&nbsp; '
                f'Viral: <strong>{viral}/10</strong> &nbsp;·&nbsp; '
                f'Overall: <strong>{scores.get("overall", "—")}/10</strong>',
                unsafe_allow_html=True,
            )
            if vp_expl:
                st.caption(f"💡 {vp_expl}")

            # Scores — 6-column grid (small font via CSS)
            st.markdown('<div class="section-label">Score Breakdown</div>', unsafe_allow_html=True)
            cols = st.columns(6)
            for col, (name, key) in zip(cols, [
                ("Compliance",   "compliance"),
                ("Distribution", "traffic"),
                ("Brand",        "brand"),
                ("Safety",       "safety"),
                ("Hook",         "hook_depth"),
                ("Conversion",   "conversion_potential"),
            ]):
                val = scores.get(key, "—")
                col.metric(name, f"{val}/10" if val != "—" else "—")

            # Flagged issues
            if issues:
                st.markdown(
                    f'<div class="section-label">Flagged Issues ({len(issues)})</div>',
                    unsafe_allow_html=True,
                )
                for issue in issues:
                    sev   = issue.get("severity", "LOW")
                    st.markdown(
                        f'<div class="issue-card {_SEV_CLASS.get(sev, "issue-low")}">'
                        f'<div class="issue-meta">'
                        f'{_SEV_ICON.get(sev, "⚪")} {issue.get("policy_type", "")}'
                        f'<span class="issue-ts">· {issue.get("timestamp", "")}</span>'
                        f'</div>'
                        f'<div class="issue-orig">"{issue.get("original_content", "")}"</div>'
                        f'<div class="issue-fix">→ {issue.get("suggested_fix", "")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Recommendations
            if recs:
                st.markdown('<div class="section-label">Recommendations</div>', unsafe_allow_html=True)
                for i, rec in enumerate(recs, 1):
                    st.markdown(f"{i}. {rec}")

            # What's working (collapsed)
            if positives:
                with st.expander(f"✅ What's Working Well ({len(positives)})"):
                    for p in positives:
                        st.markdown(f"• {p}")

            # Download full analysis report
            video_stem = Path(st.session_state.video_name or "video").stem
            st.download_button(
                label="⬇️ Download Full Analysis Report (.md)",
                data=result["content"],
                file_name=f"analysis_{video_stem}.md",
                mime="text/markdown",
            )

            # Token note
            a_tok = result["usage"]["total_tokens"]
            r_tok = cr["usage"]["total_tokens"]
            st.markdown(
                f'<div class="token-note">Step 1 total tokens: {a_tok + r_tok:,} '
                f'(analysis {a_tok:,} + risk summary {r_tok:,})</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# [AGENT] Storyboard offer + [USER] CTA on right
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step >= 1 and st.session_state.critique_result:

    n_issues = len(st.session_state.critique_result["critique"].get("issues", []))

    if st.session_state.storyboard_result is None:
        # Agent asks
        with st.chat_message("assistant", avatar="🎬"):
            st.markdown(
                f"I can generate an improved **15-second storyboard** that "
                f"{'fixes all ' + str(n_issues) + ' issues and ' if n_issues else ''}"
                f"optimises the Hook → Demo → CTA flow. Ready?"
            )
        with st.chat_message("user"):
            if st.button("Generate Storyboard →", type="primary", key="to_storyboard"):
                st.session_state.current_step = 3
                st.rerun()

    else:
        # Persistent user confirmation message
        with st.chat_message("user"):
            st.markdown("Generate Storyboard →")


# ══════════════════════════════════════════════════════════════════════════════
# [AGENT] Storyboard generation + results
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step >= 3:

    if st.session_state.storyboard_result is None:
        with st.chat_message("assistant", avatar="🎬"):
            with st.status("Generating improved storyboard…", expanded=True) as status:
                st.write("✍️ Restructuring 15-second Hook → Demo → CTA flow…")
                sb_result = generate_storyboard_short(st.session_state.analysis_result["content"], api_key=_API_KEY)
                _add_usage(sb_result["usage"])
                st.session_state.storyboard_result = sb_result
                status.update(label="Storyboard ready ✓", state="complete")
        st.rerun()

    if st.session_state.storyboard_result:
        sr       = st.session_state.storyboard_result
        sections = sr.get("sections", {})

        with st.chat_message("assistant", avatar="🎬"):
            st.markdown(
                "Here's the improved storyboard — compliance issues fixed, "
                "flow tightened to 15 seconds."
            )

            overview = sections.get("overview", "")
            if overview:
                st.markdown(overview)

            # Download full storyboard as .md — no inline preview
            video_stem = Path(st.session_state.video_name or "video").stem
            st.download_button(
                label="⬇️ Download Full Storyboard (.md)",
                data=sr.get("content", ""),
                file_name=f"storyboard_{video_stem}.md",
                mime="text/markdown",
            )

            if st.session_state.character_description:
                with st.expander("Character Description"):
                    st.markdown(st.session_state.character_description)

            simplified = sections.get("simplified", "")
            if simplified:
                st.markdown('<div class="section-label">Simplified Storyboard</div>', unsafe_allow_html=True)
                st.markdown(simplified)

            s2_tok = sr["usage"]["total_tokens"]
            st.markdown(
                f'<div class="token-note">Step 2 total tokens: {s2_tok:,}</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# [AGENT] Shot prompt offer + [USER] CTA on right
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step >= 3 and st.session_state.storyboard_result:

    if st.session_state.shot_result is None:
        with st.chat_message("assistant", avatar="🎬"):
            st.markdown(
                "Next: I'll build the **Seedance video prompt** and reference image prompts "
                "for character and location. Then we generate the final ad."
            )
        with st.chat_message("user"):
            if st.button("Generate Shot Prompts →", type="primary", key="to_shots"):
                st.session_state.current_step = 4
                st.rerun()
    else:
        with st.chat_message("user"):
            st.markdown("Generate Shot Prompts →")


# ══════════════════════════════════════════════════════════════════════════════
# [AGENT] Shot prompts + image / video generation
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step >= 4:

    # Run if not done yet
    if st.session_state.shot_result is None:
        with st.chat_message("assistant", avatar="🎬"):
            with st.status("Building video prompt…", expanded=True) as status:
                st.write("🎯 Translating storyboard into Seedance-ready prompt…")
                sr   = st.session_state.storyboard_result
                secs          = {**sr["sections"], "character_description": st.session_state.character_description}
                has_character = bool(st.session_state.character_description)
                sh_result = generate_shot_prompts_short(sr["content"], secs, api_key=_API_KEY, has_character=has_character)
                _add_usage(sh_result["usage"])
                st.session_state.shot_result = sh_result
                status.update(label="Prompts ready ✓", state="complete")
        st.rerun()

    if st.session_state.shot_result:
        shot_result = st.session_state.shot_result
        reference   = shot_result.get("reference", {})

        with st.chat_message("assistant", avatar="🎬"):
            st.markdown(
                "Prompts are ready. Generate reference images first, "
                "then create the final 15-second video."
            )

            s3_tok = shot_result["usage"]["total_tokens"]
            st.markdown(
                f'<div class="token-note">Step 3 total tokens: {s3_tok:,}</div>',
                unsafe_allow_html=True,
            )

            # Reference images
            st.markdown("**Reference Images — Seedream 5.0 Lite**")

            tab_char, tab_product = st.tabs(["👤 Character", "📦 Add Product Info"])

            # ── Character tab ─────────────────────────────────────────────────
            with tab_char:
                _has_char = bool(st.session_state.character_description)
                if not _has_char and not reference.get("character", ""):
                    st.info("No character detected in this video — character reference is not needed.")
                else:
                    _ref_key = "ref_prompt_character"
                    if _ref_key not in st.session_state:
                        st.session_state[_ref_key] = reference.get("character", "")

                    st.text_area("Prompt (editable)", height=120, key=_ref_key)
                    char_prompt = st.session_state[_ref_key]
                    char_gen    = st.session_state.gen_images.get("character", {})
                    char_done   = char_gen.get("status") == "succeeded"

                    if st.button(
                        f"{'Regen' if char_done else 'Generate'} Character Image",
                        key="gen_img_character",
                        type="secondary" if char_done else "primary",
                        disabled=not char_prompt,
                    ):
                        with st.spinner("Generating character image with Seedream 5.0 Lite…"):
                            res = generate_image(char_prompt, api_key=_API_KEY)
                        st.session_state.gen_images["character"] = res
                        if res.get("status") == "succeeded":
                            st.session_state.api_usage["images_generated"] += 1
                        st.rerun()

                    if char_done and char_gen.get("image_url"):
                        st.image(char_gen["image_url"], caption="Character reference · $0.04")
                    elif char_gen.get("status") == "failed":
                        st.error(f"Failed: {char_gen.get('error', 'unknown')}")

            # ── Product Info tab ──────────────────────────────────────────────
            with tab_product:
                st.markdown("Upload 1–3 product photos (different angles). Seedance will replicate the exact appearance.")
                import base64 as _b64
                uploads = st.file_uploader(
                    "Upload product photos",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key="product_image_upload",
                    label_visibility="collapsed",
                )
                if uploads:
                    uploads = uploads[:3]
                    uris = []
                    for f in uploads:
                        ext  = Path(f.name).suffix.lower().lstrip(".")
                        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                        uris.append(f"data:{mime};base64,{_b64.b64encode(f.read()).decode()}")
                    st.session_state.gen_images["product"] = {"status": "succeeded", "image_urls": uris}
                    cols = st.columns(len(uploads))
                    for col, f, uri in zip(cols, uploads, uris):
                        col.image(uri, caption=f.name, width=160)

            # ── Single 15-second video generation ────────────────────────────
            st.markdown("---")
            st.markdown("**Full 15-Second Video — Seedance 2.0**")

            char_img     = st.session_state.gen_images.get("character", {}).get("image_url")
            product_imgs = st.session_state.gen_images.get("product",   {}).get("image_urls", [])
            has_ref      = bool(char_img or product_imgs)

            if has_ref:
                ready_labels = " + ".join(filter(None, [
                    "character" if char_img else "",
                    f"{len(product_imgs)} product photo{'s' if len(product_imgs) > 1 else ''}" if product_imgs else "",
                ]))
                st.success(f"Reference images ready: {ready_labels}")
            else:
                st.info("No reference images — video will be generated from prompt only.")

            _vid_key = "shot_prompt_main"
            if _vid_key not in st.session_state:
                st.session_state[_vid_key] = shot_result.get("video_prompt", "")

            st.text_area(
                "Video Prompt — full 15 seconds (editable)",
                height=280,
                key=_vid_key,
            )
            prompt     = st.session_state[_vid_key]
            vid_result = st.session_state.gen_videos.get("main", {})
            is_done    = vid_result.get("status") == "succeeded"

            if st.button(
                f"{'Regen' if is_done else 'Generate'} with Reference →",
                key="vid_ref",
                type="secondary" if is_done else "primary",
                disabled=not prompt,
            ):
                with st.spinner("Generating 15-second video… (1–2 min)"):
                    res = generate_shot_video(prompt, char_img, product_imgs, api_key=_API_KEY)
                st.session_state.gen_videos["main"] = res
                _add_usage({}, video_tokens=res.get("video_tokens", 0))
                st.session_state.api_usage["videos_generated"] += 1
                st.rerun()

            if is_done and vid_result.get("video_url"):
                st.success("Video generated!")
                st.video(vid_result["video_url"])
                st.caption(f"Seedance 2.0 · {vid_result.get('video_tokens', 0):,} video tokens")

                # ── ADD ON: QA & Monitoring ───────────────────────────────────
                st.markdown("---")
                st.markdown("**ADD ON — QA & Monitoring**")
                st.markdown(
                    "Feed the generated video back to Seed 2.0 Pro to check "
                    "instruction following and compliance."
                )

                qa_done = st.session_state.qa_result is not None
                if st.button(
                    f"{'Re-run' if qa_done else 'Run'} QA Check →",
                    key="run_qa",
                    type="secondary" if qa_done else "primary",
                ):
                    with st.spinner("Running QA analysis… (30–60 sec)"):
                        qa_res = qa_generated_video(
                            vid_result["video_url"],
                            st.session_state.get(_vid_key, ""),
                            api_key=_API_KEY,
                        )
                    _add_usage(qa_res["usage"])
                    st.session_state.qa_result = qa_res
                    st.rerun()

                if st.session_state.qa_result:
                    qa  = st.session_state.qa_result["qa"]
                    _if = qa.get("instruction_following_score", 0)
                    _co = qa.get("compliance_score", 0)
                    _ok = qa.get("overall_pass", False)

                    pass_badge = (
                        '<span class="badge badge-pass">✅ PASS</span>'
                        if _ok else
                        '<span class="badge badge-fail">🚫 FAIL</span>'
                    )
                    st.markdown(pass_badge, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    c1.metric("Instruction Following", f"{_if}/10")
                    c2.metric("Compliance", f"{_co}/10")

                    summary = qa.get("summary", "")
                    if summary:
                        st.caption(summary)

                    inst_issues = qa.get("instruction_issues", [])
                    if inst_issues:
                        st.markdown('<div class="section-label">Instruction Deviations</div>', unsafe_allow_html=True)
                        for issue in inst_issues:
                            st.markdown(
                                f'<div class="issue-card issue-med">'
                                f'<div class="issue-meta">{issue.get("element", "")}</div>'
                                f'<div class="issue-orig">Expected: {issue.get("expected", "")}</div>'
                                f'<div class="issue-fix">Actual: {issue.get("actual", "")}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    comp_issues = qa.get("compliance_issues", [])
                    if comp_issues:
                        st.markdown('<div class="section-label">Compliance Issues</div>', unsafe_allow_html=True)
                        for issue in comp_issues:
                            sev = issue.get("severity", "LOW")
                            st.markdown(
                                f'<div class="issue-card {_SEV_CLASS.get(sev, "issue-low")}">'
                                f'<div class="issue-meta">'
                                f'{_SEV_ICON.get(sev, "⚪")} {issue.get("description", "")}'
                                f'<span class="issue-ts">· {issue.get("timestamp", "")}</span>'
                                f'</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    qa_tok = st.session_state.qa_result["usage"]["total_tokens"]
                    st.markdown(
                        f'<div class="token-note">QA tokens: {qa_tok:,}</div>',
                        unsafe_allow_html=True,
                    )

            elif vid_result.get("status") == "failed":
                st.error(f"Generation failed: {vid_result.get('error', 'unknown')}")
