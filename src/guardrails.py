"""
Guardrails for VibeMatch 2.0.

Provides input validation for Gemini-extracted user profiles and
output diversity checking for recommendation results.
"""

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

NUMERIC_BOUNDS = {
    "target_energy":       (0.0, 1.0),
    "target_valence":      (0.0, 1.0),
    "target_danceability": (0.0, 1.0),
    "target_acousticness": (0.0, 1.0),
    "target_tempo_bpm":    (60.0, 200.0),
}


def validate_profile(profile: dict) -> tuple:
    """
    Validate and clamp a Gemini-extracted user profile.

    - Clamps all numeric fields to their valid ranges.
    - Warns if genre or mood is unrecognized.
    - Warns on physically contradictory combinations.

    Returns:
        (cleaned_profile, warnings) where warnings is a list of strings.
    """
    cleaned = dict(profile)
    warnings = []

    for key, (lo, hi) in NUMERIC_BOUNDS.items():
        raw = cleaned.get(key)
        if raw is None:
            continue
        val = float(raw)
        if val < lo or val > hi:
            warnings.append(
                f"'{key}' value {val:.2f} is outside the valid range "
                f"[{lo}, {hi}] — clamped to fit."
            )
            cleaned[key] = max(lo, min(hi, val))

    genre = cleaned.get("favorite_genre")
    if genre and genre not in KNOWN_GENRES:
        warnings.append(
            f"Genre '{genre}' is not in the catalog. "
            f"Results will be scored on numeric features only."
        )

    mood = cleaned.get("favorite_mood")
    if mood and mood not in KNOWN_MOODS:
        warnings.append(
            f"Mood '{mood}' is not in the catalog. "
            f"Results will be scored on numeric features only."
        )

    energy = float(cleaned.get("target_energy", 0.5))
    acousticness = float(cleaned.get("target_acousticness", 0.5))
    if energy > 0.8 and acousticness > 0.8:
        warnings.append(
            "High energy + high acousticness is a rare combination. "
            "The catalog has few songs that match both — results may feel off."
        )

    return cleaned, warnings


def check_diversity(recommendations: list) -> bool:
    """
    Check whether the top-k recommendations span more than one genre.

    Returns True if diverse (more than one genre present),
    False if all recommendations share the same genre.
    """
    if not recommendations:
        return True
    genres = {r[0]["genre"] for r in recommendations}
    return len(genres) > 1
