"""
Evaluation script for VibeMatch 2.0 guardrails and the full AI pipeline.

Tests three scenarios:
  1. Normal input   -- "something calm to study to"
  2. Extreme input  -- "EXTREMELY INTENSE FAST METAL" (out-of-range clamping)
  3. Happy input    -- "happy summer vibes" (self-critique validation)

Run from the project root:
    python eval/eval_guardrails.py

Requires GEMINI_API_KEY in .env for Section 2 pipeline tests.
"""

import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# noqa comments silence E402 (module-level import not at top) which is
# expected here because the sys.path insert must happen first.
from guardrails import validate_profile, check_diversity  # noqa: E402
from recommender import load_songs, recommend_songs  # noqa: E402

SONGS_CSV = ROOT / "data" / "songs.csv"
songs = load_songs(str(SONGS_CSV))


def _result(label: str, passed: bool, detail: str = "") -> None:
    icon = "✓" if passed else "✗"
    status = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {status}: {label}")
    if detail:
        print(f"        {detail}")


# ── Section 1: Guardrail unit tests (no API key needed) ───────────────────────

print("\n" + "=" * 60)
print("SECTION 1: Input Validation Guardrails (no API key needed)")
print("=" * 60)

# Test 1a: Valid values — no warnings expected
print("\nTest 1a: Valid profile → no warnings")
valid_profile = {
    "favorite_genre": "lofi",
    "favorite_mood": "chill",
    "target_energy": 0.4,
    "target_tempo_bpm": 80,
    "target_valence": 0.55,
    "target_danceability": 0.6,
    "target_acousticness": 0.75,
}
cleaned, warnings = validate_profile(valid_profile)
_result("No warnings on valid profile", len(warnings) == 0,
        f"Warnings: {warnings}")
_result("Values unchanged", cleaned["target_energy"] == 0.4)

# Test 1b: Out-of-range values — should be clamped with warnings
print("\nTest 1b: Out-of-range values → clamped with warnings")
extreme_profile = {
    "favorite_genre": "metal",
    "favorite_mood": "rebellious",
    "target_energy": 1.8,
    "target_tempo_bpm": 240,
    "target_valence": -0.3,
    "target_danceability": 0.5,
    "target_acousticness": 0.05,
}
cleaned, warnings = validate_profile(extreme_profile)
_result("Energy clamped to 1.0",
        cleaned["target_energy"] == 1.0,
        f"Got: {cleaned['target_energy']}")
_result("Tempo clamped to 200",
        cleaned["target_tempo_bpm"] == 200.0,
        f"Got: {cleaned['target_tempo_bpm']}")
_result("Valence clamped to 0.0",
        cleaned["target_valence"] == 0.0,
        f"Got: {cleaned['target_valence']}")
_result("Warnings generated for out-of-range values",
        len(warnings) >= 3,
        f"Got {len(warnings)} warning(s)")
print("  Warnings issued:")
for w in warnings:
    print(f"    - {w}")

# Test 1c: Unknown genre/mood — warning issued but profile not rejected
print("\nTest 1c: Unknown genre/mood → warning, not rejection")
unknown_profile = {
    "favorite_genre": "vaporwave",
    "favorite_mood": "existential",
    "target_energy": 0.5,
    "target_tempo_bpm": 90,
    "target_valence": 0.5,
    "target_danceability": 0.5,
    "target_acousticness": 0.5,
}
cleaned, warnings = validate_profile(unknown_profile)
_result("Profile not rejected (returned a dict)", isinstance(cleaned, dict))
_result("Warning issued for unknown genre",
        any("vaporwave" in w for w in warnings))
_result("Warning issued for unknown mood",
        any("existential" in w for w in warnings))
print("  Warnings issued:")
for w in warnings:
    print(f"    - {w}")

# Test 1d: Contradictory combination — energy + acousticness both high
print("\nTest 1d: High energy + high acoustic → contradiction warning")
contradictory = {
    "favorite_genre": "folk",
    "favorite_mood": "intense",
    "target_energy": 0.95,
    "target_tempo_bpm": 160,
    "target_valence": 0.4,
    "target_danceability": 0.6,
    "target_acousticness": 0.92,
}
_, warnings = validate_profile(contradictory)
_result(
    "Contradiction warning issued",
    any("acousticness" in w.lower() or "unusual" in w.lower()
        for w in warnings),
    f"Warnings: {warnings}",
)

# Test 1e: Diversity check
print("\nTest 1e: Diversity check on recommendations")

# With extreme genre weighting and k=3, all slots go to the 3 lofi songs
lofi_profile = {
    "favorite_genre": "lofi",
    "favorite_mood": "chill",
    "target_energy": 0.38,
    "target_tempo_bpm": 78,
    "target_valence": 0.6,
    "target_danceability": 0.58,
    "target_acousticness": 0.82,
    "genre_points": 8.0,
}
recs = recommend_songs(lofi_profile, songs, k=3)
genres = [r[0]["genre"] for r in recs]
print(f"  Genres returned (extreme weighting, k=3): {genres}")
_result(
    "Diversity check returns False when all picks share one genre",
    not check_diversity(recs),
    f"check_diversity returned: {check_diversity(recs)}",
)

# With low genre weighting, results span multiple genres
normal_profile = {
    "favorite_genre": "pop",
    "target_energy": 0.7,
    "target_tempo_bpm": 110,
    "target_valence": 0.65,
    "target_danceability": 0.7,
    "target_acousticness": 0.3,
    "genre_points": 1.0,
}
recs = recommend_songs(normal_profile, songs, k=5)
genres = [r[0]["genre"] for r in recs]
print(f"  Genres returned (low weighting, k=5): {genres}")
_result(
    "Diversity check returns True when genre weighting is low",
    check_diversity(recs),
    f"check_diversity returned: {check_diversity(recs)}",
)


# ── Section 2: Full pipeline tests (requires GEMINI_API_KEY) ─────────────────

print("\n" + "=" * 60)
print("SECTION 2: Full AI Pipeline Tests (requires GEMINI_API_KEY)")
print("=" * 60)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        from dotenv import load_dotenv  # noqa: E402
        load_dotenv(ROOT / ".env")
        api_key = os.getenv("GEMINI_API_KEY")
    except ImportError:
        pass

if not api_key:
    print("\n  Skipping pipeline tests — GEMINI_API_KEY not set.")
    print("  Add it to .env and re-run to test the full pipeline.")
else:
    from gemini_agent import (  # noqa: E402
        extract_user_profile,
        self_critique,
        generate_explanation,
    )

    TEST_CASES = [
        {
            "name": "Calm study music",
            "query": "something calm to study to",
            "check": ("target_energy", "le", 0.5),
        },
        {
            "name": "Intense metal",
            "query": "EXTREMELY INTENSE FAST METAL",
            "check": ("target_energy", "ge", 0.7),
        },
        {
            "name": "Happy summer vibes",
            "query": "happy summer vibes",
            "check": ("target_valence", "ge", 0.6),
        },
    ]

    for tc in TEST_CASES:
        print(f"\nTest: {tc['name']} — query: \"{tc['query']}\"")
        try:
            raw_profile = extract_user_profile(tc["query"])
            profile, w = validate_profile(raw_profile)
            recs = recommend_songs(profile, songs, k=5)
            critique = self_critique(tc["query"], recs)
            explanation = generate_explanation(tc["query"], recs)

            energy = profile.get("target_energy", "n/a")
            valence = profile.get("target_valence", "n/a")
            print(
                f"  Extracted: energy={energy}, valence={valence}, "
                f"genre={profile.get('favorite_genre')}, "
                f"mood={profile.get('favorite_mood')}"
            )
            if w:
                print(f"  Guardrail warnings: {w}")
            print(
                f"  Top pick: {recs[0][0]['title']} "
                f"by {recs[0][0]['artist']}"
            )
            print(
                f"  Self-critique: "
                f"matches_intent={critique['matches_intent']}"
            )
            reason = critique.get("reason", "")[:100]
            print(f"  Critique reason: {reason}")
            print(f"  Explanation: {explanation[:120]}...")

            key, op, threshold = tc["check"]
            val = float(profile.get(key, 0.0))
            if op == "le":
                passed = val <= threshold
                label = f"{key} ≤ {threshold} (got {val:.2f})"
            else:
                passed = val >= threshold
                label = f"{key} ≥ {threshold} (got {val:.2f})"
            _result(label, passed)

        except Exception as e:
            _result("Pipeline completed without exception", False, str(e))

print("\n" + "=" * 60)
print("Evaluation complete.")
print("=" * 60 + "\n")
