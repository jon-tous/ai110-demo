"""
VibeMatch 2.0 — Gemini-powered conversational music recommender.

Run with:
    streamlit run app.py
"""

import os
import sys
import pathlib

# Allow imports from src/ without installing the package
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
from recommender import load_songs, recommend_songs
from gemini_agent import extract_user_profile, self_critique, generate_explanation
from guardrails import validate_profile, check_diversity

# ── Constants ────────────────────────────────────────────────────────────────

SONGS_CSV = ROOT / "data" / "songs.csv"
MAX_RETRIES = 2

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="VibeMatch 2.0",
    page_icon="🎵",
    layout="centered",
)

st.title("🎵 VibeMatch 2.0")
st.caption("Describe your music mood in plain English — Gemini translates it, the recommender finds your songs.")

# ── Load songs once ──────────────────────────────────────────────────────────

@st.cache_data
def load_catalog():
    return load_songs(str(SONGS_CSV))

songs = load_catalog()

# ── Input ─────────────────────────────────────────────────────────────────────

with st.form("query_form"):
    user_query = st.text_input(
        "What are you in the mood for?",
        placeholder="e.g. something upbeat for my morning run",
    )
    top_k = st.slider("Number of recommendations", min_value=3, max_value=10, value=5)
    submitted = st.form_submit_button("Find my vibe →")

# ── Pipeline ──────────────────────────────────────────────────────────────────

if submitted and user_query.strip():
    with st.spinner("Asking Gemini to understand your vibe..."):
        try:
            # Step 1: Extract profile from natural language
            raw_profile = extract_user_profile(user_query)
        except Exception as e:
            st.error(f"Could not reach Gemini: {e}")
            st.stop()

    # Step 2: Validate + clamp profile values
    profile, warnings = validate_profile(raw_profile)

    if warnings:
        with st.expander("⚠️ Guardrail warnings", expanded=True):
            for w in warnings:
                st.warning(w)

    with st.expander("🔍 Extracted profile", expanded=False):
        st.json(profile)

    # Step 3: Run the rule-based recommender
    recommendations = recommend_songs(profile, songs, k=top_k)

    # Step 4: Self-critique + optional retry
    with st.spinner("Checking quality..."):
        for attempt in range(MAX_RETRIES):
            try:
                critique = self_critique(user_query, recommendations)
            except Exception:
                critique = {"matches_intent": True, "reason": "", "suggested_adjustments": {}}
                break

            if critique["matches_intent"]:
                break

            # Adjust profile and retry
            adjustments = critique.get("suggested_adjustments", {})
            if adjustments and attempt < MAX_RETRIES - 1:
                profile.update(adjustments)
                profile, _ = validate_profile(profile)
                recommendations = recommend_songs(profile, songs, k=top_k)
            else:
                break

    if not critique["matches_intent"] and critique.get("reason"):
        st.info(f"Note from quality check: {critique['reason']}")

    # Check diversity
    if not check_diversity(recommendations):
        st.caption("_All recommendations are the same genre — try broadening your query for more variety._")

    # Step 5: Gemini explanation
    with st.spinner("Writing your curator note..."):
        try:
            explanation = generate_explanation(user_query, recommendations)
        except Exception:
            explanation = None

    # ── Display results ───────────────────────────────────────────────────────

    st.markdown("---")
    st.subheader("Your Picks")

    if explanation:
        st.markdown(f"> {explanation}")

    for i, (song, score, breakdown) in enumerate(recommendations, start=1):
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{i}. {song['title']}** — {song['artist']}")
                st.caption(f"{song['genre'].title()} · {song['mood'].title()} · {song['tempo_bpm']} BPM")
            with col2:
                st.metric("Score", f"{score:.2f}")
            with st.expander("Score breakdown"):
                for reason in breakdown.split(";"):
                    r = reason.strip()
                    if r:
                        st.write(f"• {r}")
            st.divider()

elif submitted:
    st.warning("Please enter a music mood description first.")
