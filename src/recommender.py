from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
import csv

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file into a list of typed dictionaries."""
    songs: List[Dict] = []

    with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            songs.append(
                {
                    "id": int(row["id"]),
                    "title": row["title"],
                    "artist": row["artist"],
                    "genre": row["genre"],
                    "mood": row["mood"],
                    "energy": float(row["energy"]),
                    "tempo_bpm": float(row["tempo_bpm"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                }
            )

    return songs


def score_song(user_prefs: Dict[str, Any], song: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Score one song against user preferences and return score plus reasons."""
    score = 0.0
    reasons: List[str] = []

    favorite_genre = user_prefs.get("favorite_genre", user_prefs.get("genre"))
    favorite_mood = user_prefs.get("favorite_mood", user_prefs.get("mood"))
    genre_points = float(user_prefs.get("genre_points", 2.0))
    mood_points = float(user_prefs.get("mood_points", 1.0))

    if favorite_genre and song.get("genre") == favorite_genre:
        score += genre_points
        reasons.append(f"genre match (+{genre_points:.1f})")

    if favorite_mood and song.get("mood") == favorite_mood:
        score += mood_points
        reasons.append(f"mood match (+{mood_points:.1f})")

    numeric_features = [
        ("energy", ["target_energy", "energy"], 1.0),
        ("tempo_bpm", ["target_tempo_bpm", "tempo_bpm", "tempo"], 120.0),
        ("valence", ["target_valence", "valence"], 1.0),
        ("danceability", ["target_danceability", "danceability"], 1.0),
        ("acousticness", ["target_acousticness", "acousticness"], 1.0),
    ]

    for feature_name, possible_target_keys, feature_scale in numeric_features:
        target_value = None
        for key in possible_target_keys:
            if key in user_prefs:
                target_value = user_prefs[key]
                break

        if target_value is None or feature_name not in song:
            continue

        weight = float(user_prefs.get(f"weight_{feature_name}", 1.0))
        distance = abs(float(song[feature_name]) - float(target_value))
        closeness = max(0.0, 1.0 - (distance / feature_scale))
        contribution = weight * closeness

        score += contribution
        reasons.append(
            f"{feature_name} closeness {closeness:.2f} x weight {weight:.2f} (+{contribution:.2f})"
        )

    if not reasons:
        reasons.append("no strong feature matches; score based on available defaults")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Rank songs by score and return the top-k with explanations."""
    if k <= 0:
        return []

    scored_songs = [
        (
            song,
            score,
            "; ".join(reasons),
        )
        for song in songs
        for score, reasons in [score_song(user_prefs, song)]
    ]

    ranked_songs = sorted(scored_songs, key=lambda item: item[1], reverse=True)
    return ranked_songs[:k]
