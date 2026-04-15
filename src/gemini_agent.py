"""
Gemini-powered agent for VibeMatch 2.0.

Implements a three-step AI pipeline that wraps the rule-based recommender:
  1. extract_user_profile  — parse natural language → structured UserProfile dict
  2. self_critique         — evaluate whether recommendations match user intent
  3. generate_explanation  — write a friendly explanation of the final picks
"""

import os
import json

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"

KNOWN_GENRES = [
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave",
    "hip hop", "indie pop", "folk", "reggaeton", "classical",
    "metal", "r&b", "afrobeat", "trance",
]

KNOWN_MOODS = [
    "happy", "chill", "intense", "relaxed", "focused", "moody",
    "nostalgic", "playful", "serene", "rebellious", "romantic",
    "euphoric", "dreamy", "gritty",
]


_client_instance: genai.Client | None = None


def _client() -> genai.Client:
    global _client_instance
    if _client_instance is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Add it to your .env file:\n"
                "  GEMINI_API_KEY=your_key_here"
            )
        _client_instance = genai.Client(api_key=api_key)
    return _client_instance


def extract_user_profile(user_query: str) -> dict:
    """
    Step 1: Parse a natural language music query into a structured profile dict.

    The returned dict uses the same key names expected by recommend_songs()
    in recommender.py (e.g. 'favorite_genre', 'target_energy', etc.).

    Args:
        user_query: Free-text music preference description.

    Returns:
        dict with keys: favorite_genre, favorite_mood, target_energy,
        target_tempo_bpm, target_valence, target_danceability, target_acousticness.
    """
    prompt = f"""You are a music preference parser. Extract a structured profile from the user's natural language music request.

Return a JSON object with EXACTLY these keys (no extras):
{{
  "favorite_genre": one of {KNOWN_GENRES} — pick the closest match, or null if unclear,
  "favorite_mood": one of {KNOWN_MOODS} — pick the closest match, or null if unclear,
  "target_energy": float 0.0-1.0 (0=very calm/quiet, 1=very high energy),
  "target_tempo_bpm": float 60-200 (beats per minute; fast=140+, medium=100, slow=75),
  "target_valence": float 0.0-1.0 (0=dark/sad, 1=bright/happy),
  "target_danceability": float 0.0-1.0 (0=not danceable, 1=very groovy),
  "target_acousticness": float 0.0-1.0 (0=electronic/produced, 1=acoustic/organic)
}}

Infer all seven values from the description. If a dimension is not mentioned, use a neutral default (0.5 for 0-1 fields, 100 for tempo).

User query: "{user_query}"
"""

    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    profile = json.loads(response.text)

    # Normalize None strings Gemini occasionally returns
    for key in ("favorite_genre", "favorite_mood"):
        if profile.get(key) in (None, "null", "None", ""):
            profile[key] = None

    return profile


def self_critique(user_query: str, recommendations: list) -> dict:
    """
    Step 4: Evaluate whether the top recommendations match the user's original intent.

    Args:
        user_query: The original natural language request.
        recommendations: List of (song_dict, score, explanation) tuples.

    Returns:
        dict with keys:
          - matches_intent (bool)
          - reason (str)
          - suggested_adjustments (dict of profile key → new value, or {})
    """
    rec_lines = "\n".join(
        f"  {i+1}. {r[0]['title']} by {r[0]['artist']} "
        f"(genre={r[0]['genre']}, mood={r[0]['mood']}, "
        f"energy={r[0]['energy']}, tempo={r[0]['tempo_bpm']}bpm)"
        for i, r in enumerate(recommendations)
    )

    prompt = f"""You are a music recommendation quality evaluator.

The user asked for: "{user_query}"

The system returned these top recommendations:
{rec_lines}

Does this list genuinely satisfy what the user asked for? Consider genre, mood, energy level, and overall vibe.

Return JSON with EXACTLY these keys:
{{
  "matches_intent": true or false,
  "reason": "1-2 sentences explaining why the list does or does not match",
  "suggested_adjustments": {{optional dict of profile key adjustments if matches_intent is false}}
}}

If matches_intent is true, set suggested_adjustments to an empty object {{}}.
"""

    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    result = json.loads(response.text)

    result.setdefault("matches_intent", True)
    result.setdefault("reason", "")
    result.setdefault("suggested_adjustments", {})

    return result


def generate_explanation(user_query: str, recommendations: list) -> str:
    """
    Step 5: Generate a friendly curator-style explanation for the recommendations.

    Args:
        user_query: The original natural language request.
        recommendations: List of (song_dict, score, explanation) tuples.

    Returns:
        A warm 2-3 sentence explanation string.
    """
    song_list = "\n".join(
        f"  - {r[0]['title']} by {r[0]['artist']} ({r[0]['genre']}, {r[0]['mood']})"
        for r in recommendations
    )

    prompt = f"""You are a friendly music curator. The listener asked for: "{user_query}"

You're recommending:
{song_list}

Write a warm, 2-3 sentence explanation of why these songs are a great fit. Be specific about the vibe, feel, and energy. Write in second person ("These picks..."). Do not use bullet points or lists.
"""

    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text.strip()
