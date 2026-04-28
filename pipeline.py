import httpx
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from schema import (
    TriageResponse, SymptomExtraction, TriageLevel,
    ValidationError, OutOfScopeResponse, EmptyInputError
)
from utils.language_detect import detect_language
from utils.kb_loader import load_kb, format_kb_for_prompt

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "qwen/qwen-2.5-72b-instruct")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "meta-llama/llama-3.3-70b-instruct")

PROMPTS_DIR = Path(__file__).parent / "prompts"
KB_PATH = Path(__file__).parent / "kb.jsonl"
KB = load_kb(str(KB_PATH))
KB_JSON = format_kb_for_prompt(KB)


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def call_model(system_prompt: str, user_message: str, model: str = PRIMARY_MODEL) -> str:
    """Call OpenRouter API with the given system prompt and user message."""
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sk-or-your-key-here":
        raise ValueError("OPENROUTER_API_KEY is not set. Please copy .env.example to .env and add your key.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://mumzworld.com",
        "X-Title": "Mumzworld Pediatric Triage"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"}
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        # Fallback to secondary model on 5xx errors
        if model == PRIMARY_MODEL and e.response.status_code >= 500:
            return call_model(system_prompt, user_message, model=FALLBACK_MODEL)
        raise


def safe_parse_json(raw: str) -> dict:
    """Parse JSON, stripping markdown fences if model added them despite instructions."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().strip("```").strip()
    return json.loads(raw)


def run_triage(user_input: str) -> dict:
    """
    Main pipeline. Three agents in sequence:
    1. Extraction agent  — pulls structured symptoms from free text
    2. Classification agent — assigns triage level and confidence
    3. Generation agent  — writes bilingual advice

    Then validates the assembled response against TriageResponse schema.
    Returns a dict that is always JSON-serialisable.
    """

    # Guard: empty input
    if not user_input or not user_input.strip():
        return EmptyInputError().model_dump()

    # Step 0: Detect input language
    input_language = detect_language(user_input)

    # ------------------------------------------------------------------ #
    # Step 1: Symptom extraction
    # ------------------------------------------------------------------ #
    extraction_prompt = load_prompt("extraction").replace(
        "{kb_json}", KB_JSON
    ).replace(
        "{user_input}", user_input
    )
    try:
        extraction_raw = call_model(
            system_prompt=extraction_prompt,
            user_message=user_input
        )
        extraction_data = safe_parse_json(extraction_raw)
        extraction = SymptomExtraction(**extraction_data)
    except Exception as e:
        raw = extraction_raw if 'extraction_raw' in dir() else str(e)
        return ValidationError(
            detail=f"Extraction agent returned invalid schema: {str(e)}",
            raw_output=raw
        ).model_dump()

    # Guard: out of scope
    if extraction.out_of_scope:
        return OutOfScopeResponse(
            reason=extraction.out_of_scope_reason or "Input not related to child health symptoms."
        ).model_dump()

    # ------------------------------------------------------------------ #
    # Step 2: Triage classification
    # ------------------------------------------------------------------ #
    classification_prompt = load_prompt("classification").replace(
        "{extraction_json}", extraction.model_dump_json(indent=2)
    )
    try:
        classification_raw = call_model(
            system_prompt=classification_prompt,
            user_message=f"Classify this extraction: {extraction.model_dump_json()}"
        )
        classification_data = safe_parse_json(classification_raw)
    except Exception as e:
        raw = classification_raw if 'classification_raw' in dir() else str(e)
        return ValidationError(
            detail=f"Classification agent returned invalid JSON: {str(e)}",
            raw_output=raw
        ).model_dump()

    # ------------------------------------------------------------------ #
    # Step 3: Bilingual output generation
    # ------------------------------------------------------------------ #
    generation_prompt = load_prompt("generation").replace(
        "{triage_json}", json.dumps(classification_data, indent=2)
    ).replace(
        "{extraction_json}", extraction.model_dump_json(indent=2)
    )
    try:
        generation_raw = call_model(
            system_prompt=generation_prompt,
            user_message="Generate bilingual advice for the above triage."
        )
        generation_data = safe_parse_json(generation_raw)
    except Exception as e:
        raw = generation_raw if 'generation_raw' in dir() else str(e)
        return ValidationError(
            detail=f"Generation agent returned invalid JSON: {str(e)}",
            raw_output=raw
        ).model_dump()

    # ------------------------------------------------------------------ #
    # Step 4: Assemble and validate final TriageResponse
    # ------------------------------------------------------------------ #
    triage_level_raw = classification_data.get("triage_level")
    triage_level = TriageLevel(triage_level_raw) if triage_level_raw else None
    deferral_required = bool(extraction.red_flag_signals)

    try:
        response = TriageResponse(
            input_language=input_language,
            triage_level=triage_level,
            confidence=float(classification_data.get("confidence", 0.5)),
            extraction=extraction,
            advice_en=generation_data.get("advice_en"),
            advice_ar=generation_data.get("advice_ar"),
            deferral_required=deferral_required,
            sources_cited=extraction.red_flag_signals
        )
        return response.model_dump()
    except Exception as e:
        return ValidationError(
            detail=f"Final schema validation failed: {str(e)}",
            raw_output=json.dumps({
                "classification": classification_data,
                "generation": generation_data
            })
        ).model_dump()
