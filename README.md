# 🎵 VibeMatch 2.0 — Gemini-Powered Music Recommender

VibeMatch 2.0 extends a rule-based music recommender with a Gemini-powered conversational AI layer. You describe your mood in plain English and the system figures out the rest.

<img src="https://github.com/jon-tous/ai110-demo/blob/main/assets/vibematch2.png">

---

## About the Original Project (VibeMatch 1.0)

The base project is a **content-based music recommendation simulation** built as a module 3 class project. Its goal was to demonstrate how recommendation algorithms work by:

- Representing songs as feature vectors (genre, mood, energy, tempo, valence, danceability, acousticness)
- Representing user preferences as a numeric "taste profile"
- Scoring every song against that profile using a transparent weighted formula
- Returning the top-K matches with scoring breakdowns

The system worked entirely through deterministic rules — no AI, no language understanding. Users had to specify exact numbers (`energy=0.88`, `tempo=128`), which is not how real people think about music.

---

## New AI Feature: Multi-Step Gemini Agent

VibeMatch 2.0 adds a **5-step AI pipeline** that wraps the existing recommender without replacing it:

```
User's natural language query
    │
    ▼
[Step 1] Gemini extracts a structured UserProfile (JSON mode)
    │
    ▼
[Step 2] Input guardrails clamp out-of-range values + warn on conflicts
    │
    ▼
[Step 3] Original recommend_songs() runs unchanged
    │
    ▼
[Step 4] Gemini self-critique: do the results match the user's intent?
         └─ If not: adjust profile and retry (max 2 attempts)
    │
    ▼
[Step 5] Gemini writes a friendly curator-style explanation
    │
    ▼
Streamlit UI displays picks + score breakdowns
```

The rule-based engine ([src/recommender.py](src/recommender.py)) is untouched. Gemini acts as an intelligent front-end and quality-checker.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                 │
│   Text input ──► pipeline ──► results + explanations         │
└──────────────┬───────────────────────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │  gemini_agent.py    │  ◄── google-generativeai (Gemini 1.5 Flash)
    │  ─────────────────  │
    │  1. extract_profile │  NL → structured JSON UserProfile
    │  2. self_critique   │  do recommendations match intent?
    │  3. gen_explanation │  friendly curator note
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   guardrails.py     │
    │  ─────────────────  │
    │  validate_profile   │  clamp values, warn on conflicts
    │  check_diversity    │  flag all-same-genre results
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   recommender.py    │  ◄── Original VibeMatch 1.0 engine
    │  ─────────────────  │
    │  load_songs()       │  CSV → list[dict]
    │  score_song()       │  weighted feature matching
    │  recommend_songs()  │  sort → top-K
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  data/songs.csv     │  18 songs, 10 features each
    └─────────────────────┘
```

---

## Setup Instructions

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd ai110-demo
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Mac/Linux
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key

Create a `.env` file in the project root (it's already gitignored):

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey).

### 5. Run the Streamlit app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Sample Inputs and Outputs

### Example 1 — "something calm to study to"

**Extracted profile:**
```json
{
  "favorite_genre": "lofi",
  "favorite_mood": "focused",
  "target_energy": 0.35,
  "target_tempo_bpm": 80,
  "target_valence": 0.55,
  "target_danceability": 0.5,
  "target_acousticness": 0.75
}
```

**Top picks:** Midnight Coding, Library Rain, Focus Flow, Spacewalk Thoughts, Coffee Shop Stories

**Curator note:** *"These picks settle into a mellow, unhurried groove that keeps your brain in the zone without pulling your attention away. The lofi and ambient textures give you just enough sonic backdrop to feel present without being distracted."*

---

### Example 2 — "upbeat pop for a summer party"

**Extracted profile:**
```json
{
  "favorite_genre": "pop",
  "favorite_mood": "happy",
  "target_energy": 0.85,
  "target_tempo_bpm": 125,
  "target_valence": 0.85,
  "target_danceability": 0.88,
  "target_acousticness": 0.12
}
```

**Top picks:** Sunrise City, Gym Hero, Tidal Hearts, Sunset Bazaar, Rooftop Lights

**Curator note:** *"These tracks bring the kind of feel-good, high-energy brightness that makes a party come alive — bright production, danceable grooves, and melodies that stick."*

---

### Example 3 — "dark moody late night synthwave"

**Extracted profile:**
```json
{
  "favorite_genre": "synthwave",
  "favorite_mood": "moody",
  "target_energy": 0.72,
  "target_tempo_bpm": 112,
  "target_valence": 0.42,
  "target_danceability": 0.7,
  "target_acousticness": 0.15
}
```

**Top picks:** Night Drive Loop, Polar Lights Pulse, Neon Alley Cipher, Tidal Hearts, Velvet Afterglow

---

## Running Tests

### Existing unit tests (no API key needed)

```bash
pytest
```

Tests verify that recommendations are ranked by score and explanations are non-empty.

### Guardrail evaluation script

```bash
python eval/eval_guardrails.py
```

This tests:
- **Section 1 (no API key):** 6 guardrail unit tests covering valid input, out-of-range clamping, unknown genre/mood, contradiction detection, and diversity checking
- **Section 2 (requires API key):** 3 full pipeline tests with self-critique validation

Sample Section 1 output:
```
============================================================
SECTION 1: Input Validation Guardrails (no API key needed)
============================================================

Test 1b: Out-of-range values → clamped with warnings
  [✓] PASS: Energy clamped to 1.0
  [✓] PASS: Tempo clamped to 200
  [✓] PASS: Valence clamped to 0.0
  [✓] PASS: Warnings generated for out-of-range values
  Warnings issued:
    - 'target_energy' value 1.80 is outside the valid range [0.0, 1.0] — clamped to fit.
    - 'target_tempo_bpm' value 240.00 is outside the valid range [60.0, 200.0] — clamped to fit.
    - 'target_valence' value -0.30 is outside the valid range [0.0, 1.0] — clamped to fit.
```

### Original CLI runner

```bash
python -m src.main
```

---

## Reliability & Guardrail Component

### Input guardrails (`src/guardrails.py`)

`validate_profile()` applies four checks before the recommender runs:

| Check | What it does |
|---|---|
| Numeric range clamping | Clamps energy/valence/danceability/acousticness to [0, 1]; tempo to [60, 200] |
| Unknown genre warning | Warns if genre isn't in the 15-song catalog genres |
| Unknown mood warning | Warns if mood isn't in the 14 known moods |
| Contradiction detection | Warns if energy > 0.8 AND acousticness > 0.8 (physically rare combination) |

### Output guardrail (`check_diversity`)

`check_diversity()` inspects the final recommendations and returns `False` if all picks share the same genre. The app surfaces a note to the user when this happens.

### Self-critique loop (`src/gemini_agent.py`)

`self_critique()` asks Gemini to evaluate whether the recommendations actually match the user's stated intent. If `matches_intent=False`, the app applies the suggested adjustments and re-runs the recommender (up to 2 retries). This catches cases where Gemini's extracted profile was slightly off.

---

## Reflection on AI Collaboration

### How AI was used during development

Claude was used for the full development cycle: exploring the existing codebase, planning the architecture, writing all new code, and debugging import path issues. The planning conversation helped clarify how to keep the original `recommender.py` untouched while building the Gemini layer on top.

Gemini itself is the runtime AI in the final product — it handles profile extraction (structured JSON mode), self-critique, and explanation generation.

### One helpful AI suggestion

The most useful suggestion was using `response_mime_type="application/json"` in the Gemini generation config rather than asking the model to return JSON in the prompt and then parsing it manually. This eliminated a whole class of parsing errors where Gemini would sometimes wrap the JSON in markdown code fences.

### One flawed AI suggestion

An early design from AI suggested using `google.generativeai`'s `response_schema` parameter to enforce a strict JSON schema. In practice, this caused errors with the version of the SDK installed — the schema validation feature behaves differently across SDK versions. The simpler `response_mime_type="application/json"` approach was more reliable.

### Limitations

- **Tiny catalog (18 songs):** Gemini might extract a perfect profile but the catalog has no matching songs. A real system needs 10,000+ tracks.
- **Tempo scaling:** The original `score_song()` uses a 120-point scale for tempo vs. 1.0 for other features, making tempo underweighted. This is a known bug inherited from v1.
- **Gemini latency:** Each recommendation takes 2–4 API calls. The UI is noticeably slower than a local-only system.
- **Self-critique accuracy:** Gemini's critique is a language model judgment, not a ground-truth evaluation. It can be wrong.

### Future improvements

- Expand the song catalog to 500+ tracks with richer metadata
- Add user session history so preferences refine over time
- Replace the fixed-weight scoring with a learned ranking model
- Cache Gemini profile extractions for identical queries
- Add a feedback loop: "Was this recommendation good?" trains future weights

---

## Reflection and Ethics: Thinking Critically About This AI

### Limitations and biases in the system

The most significant bias lives in the original scoring algorithm inherited from v1: an exact genre match awards +2 points, a fixed bonus that often drowns out numeric similarity. A jazz song with a nearly identical energy and tempo to what someone asked for will lose to a pop song that only loosely matches the numbers, just because the genre label matches. This encodes a hidden assumption that genre boundaries are meaningful and rigid, which isn't how most listeners actually experience music.

A second bias is in the catalog itself. The 18-song dataset was constructed manually and skews toward Western popular genres — pop, rock, lofi, synthwave. Classical gets one song, as does metal, hip-hop, and afrobeat. A user whose taste centers on any of those genres will get worse recommendations than a pop listener, simply because there are fewer options to match against. The system will confidently recommend a song from a different genre and call it a "good match," with no signal to the user that the catalog just didn't have what they needed.

Gemini introduces a third layer of bias: its interpretation of natural language is shaped by what the training data associated with certain words and genres. Describing music as "aggressive" or "hard" probably maps reliably to metal or rock, because that association is common in English-language text. More culturally specific descriptions — referencing regional music scenes or non-English terminology — may be poorly parsed or mapped to the closest Western equivalent.

### Could this system be misused, and how would you prevent it?

A music recommender is low-stakes, but the architecture generalizes to higher-risk contexts. The main misuse surface here is the Gemini profile extraction step: because the system trusts Gemini's JSON output and passes it directly to the recommender, a carefully crafted input could try to inject values that manipulate the scoring in unintended ways (e.g., extremely high genre weights, or edge-case numeric values designed to surface specific songs). The input guardrails in `guardrails.py` address this by clamping all numeric fields to valid ranges before they reach the recommender — garbage in gets corrected before it can do damage.

At a broader level, a production version of this system would need to be careful about reinforcing filter bubbles. If users only ever get recommendations close to what they already like, the system never exposes them to new genres or artists. Real platforms address this with deliberate diversity injection; this project's `check_diversity()` function is a minimal version of that idea.

### What surprised me while testing the system's reliability?

Two things stood out. First, the self-critique loop failed more than expected on the "EXTREMELY INTENSE FAST METAL" query — Gemini correctly identified that only one truly metal song existed in the catalog and flagged the results as a poor match. The surprise wasn't that it caught the problem; it was that there was nothing the retry could do about it, because the catalog simply doesn't have enough metal songs. The guardrail exposed a real data limitation rather than a logic error, which wasn't the failure mode I anticipated.

Second, the input guardrail for contradictory combinations (high energy + high acousticness) turned out to be more useful than expected. During testing, Gemini occasionally extracted this combination for queries like "intense folk music" or "energetic acoustic guitar." The warning didn't block the query, but surfacing it to the user sets honest expectations — the system is telling you it's doing its best with a catalog that doesn't have many songs fitting that description. That transparency felt like the right design choice.

---

## Project Files

```
ai110-demo/
├── app.py                    # Streamlit UI (VibeMatch 2.0 entry point)
├── requirements.txt          # Dependencies
├── .env                      # GEMINI_API_KEY goes here (gitignored)
├── data/
│   └── songs.csv             # 18-song catalog
├── src/
│   ├── recommender.py        # Original rule-based engine (unchanged)
│   ├── gemini_agent.py       # Gemini pipeline (NEW)
│   ├── guardrails.py         # Input/output validation (NEW)
│   └── main.py               # Original CLI runner
├── eval/
│   └── eval_guardrails.py    # Evaluation script (NEW)
├── tests/
│   └── test_recommender.py   # Original unit tests
└── model_card.md             # Original model card
```
