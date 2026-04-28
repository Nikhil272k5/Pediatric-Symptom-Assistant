# Mumzworld Pediatric Symptom Triage

Bilingual (English + Arabic) pediatric symptom triage assistant for Mumzworld parents.  
A parent describes their child's symptoms in free text — in either language — and receives
a structured, validated, bilingual triage response.

---

## Setup (under 5 minutes)

```bash
cd mumzworld-triage
cp .env.example .env
# Edit .env: add your free OpenRouter API key from https://openrouter.ai
pip install -r requirements.txt

# Terminal 1 — Start the API
python app.py

# Terminal 2 — Start the UI
streamlit run ui.py

# Terminal 3 — Run evals (API must be running)
python evals/run_evals.py
```

---

## API Usage

```
POST http://localhost:8000/triage
Content-Type: application/json

{
  "input": "My 4-month-old has not eaten in 24 hours and is very limp",
  "locale": "auto"
}
```

Response: `TriageResponse` JSON (see `schema.py` for full structure).

---

## Architecture

Three-agent pipeline, each agent with a distinct output contract:

```
Parent input (EN / AR / mixed)
        │
        ▼
┌───────────────────┐
│  Extraction Agent │  → SymptomExtraction (Pydantic validated)
│  extraction.txt   │    symptoms, age, duration, red_flag_signals
└───────────────────┘
        │
        ▼
┌──────────────────────────┐
│  Classification Agent    │  → triage_level, confidence, reasoning
│  classification.txt      │    Hard rules: red flags → SEE_DOCTOR/EMERGENCY
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  Generation Agent        │  → advice_en, advice_ar
│  generation.txt          │    Arabic written independently (not translated)
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  Pydantic Validation     │  → TriageResponse (final contract)
│  schema.py               │    Rejects invalid confidence, missing deferral
└──────────────────────────┘
```

---

## Evals

Rubric (5 dimensions, 0–2 each, max 10 per case):

| Dimension          | Description |
|--------------------|-------------|
| `schema_valid`     | Response parses correctly or returns a structured error type |
| `triage_correct`   | Triage level matches expected (1 pt partial credit for conservative over-triage) |
| `deferral_enforced`| **BINARY** — red-flag cases MUST have `deferral_required: true` |
| `confidence_sane`  | Confidence ≤ 0.65 when age or duration is unknown |
| `no_hallucination` | `symptoms_identified` is a list (manual spot-check for invented content) |

14 test cases: 6 easy, 4 adversarial, 2 Arabic input, 2 edge cases (OOS + empty).

Critical threshold: `deferral_enforced` must be **2/2 for ALL red-flag cases**.  
Average score target: **≥ 8.0 / 10**

See `evals/results.md` for committed results after running the eval suite.

---

## Tradeoffs

**Problem selection**  
Pediatric triage was chosen because uncertainty handling is structurally mandatory.  
A model that hallucinates in a review synthesiser is annoying. One that hallucinates  
in a triage assistant is dangerous. The constraints become features.

**Architecture**  
Three-agent pipeline (extract → classify → generate) rather than one monolithic prompt.  
Each agent has a tighter output contract. Extraction failures surface at step 1, not buried  
inside a 500-word response. Tradeoff: three API calls per request, ~3× latency.  
For a prototype this is fine; for production, extraction + classification could merge.

**Model choice**  
`qwen/qwen-2.5-72b-instruct` via OpenRouter (free tier). Chosen for strong Arabic  
instruction-following and reliable JSON output. Llama-3.3-70B is the fallback on 5xx.

**Multilingual strategy**  
Arabic is generated independently from English, not translated. The generation prompt  
specifies *فصحى مبسطة* register and explicitly forbids translated idioms.

**Uncertainty handling — three layers**  
1. Pydantic confidence-floor validator (structural, cannot be bypassed in code)  
2. `uncertainty_note` field populated when input is vague  
3. `out_of_scope` flag for non-health queries

**What was cut**  
- Vector DB / semantic KB search: static JSONL + keyword matching sufficient for 15 rules  
- Fine-tuning: evals-first approach; fine-tune only once error patterns are clear  
- Auth / session state: stateless per-request prototype  
- Medication-name blocklist: currently prompt-enforced; add regex filter in production

**What to build next**  
1. Semantic KB search over WHO + AAP pediatric guidelines (EN + AR)  
2. Post-triage Mumzworld product recommendations (thermometer, ORS, nasal aspirator)  
3. Fine-tune a small classifier on labelled Mumzworld support ticket history  
4. Session memory for follow-up ("has the fever gone up since you last messaged?")  
5. Formal medical review of Arabic output by a native-speaking paediatrician

---

## Tooling

| Model | Role |
|-------|------|
| `qwen/qwen-2.5-72b-instruct` | All three pipeline agents (extract, classify, generate) |
| `meta-llama/llama-3.3-70b-instruct` | Automatic fallback on API 5xx |
| Claude Sonnet (Antigravity) | Scaffolding, schema design, prompt iteration |

**What worked**  
- Qwen2.5-72B produced clean JSON reliably with `response_format: json_object`  
- Three-prompt decomposition made iteration much cleaner than embedded strings  
- Pydantic model validators correctly enforce cross-field rules (deferral, confidence floor)

**What did not work (first iteration)**  
- Arabic outputs were clearly translated from English; fixed by rewriting the generation  
  prompt to specify "write fresh Arabic independently" with explicit register guidance  
- Model initially included medication dosage advice; fixed by explicit prohibition +  
  verification in evals  
- `response_format: json_object` not honoured on all OpenRouter models; added  
  `safe_parse_json()` to strip markdown fences as a fallback

All three system prompts committed verbatim in `prompts/` — no embedded prompt strings in code.
