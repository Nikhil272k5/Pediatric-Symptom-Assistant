import streamlit as st
import httpx
import json
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Mumzworld Symptom Triage",
    page_icon="🌸",
    layout="centered"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main { background: #fdf6f0; }

.stTextArea textarea {
    border-radius: 12px;
    border: 1px solid #e8d5c4;
    font-size: 15px;
    background: #fff;
}

.stButton > button {
    border-radius: 10px;
    background: linear-gradient(135deg, #e8735a, #c9507a);
    color: white;
    font-weight: 600;
    font-size: 16px;
    padding: 12px 28px;
    border: none;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.88; }

.triage-badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 15px;
    letter-spacing: 0.04em;
    margin-bottom: 8px;
}
.badge-HOME_CARE  { background:#d1fae5; color:#065f46; }
.badge-MONITOR    { background:#fef3c7; color:#92400e; }
.badge-SEE_DOCTOR { background:#fee2e2; color:#991b1b; }
.badge-EMERGENCY  { background:#fca5a5; color:#7f1d1d; animation: pulse 1.5s infinite; }

@keyframes pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(220,38,38,.4); }
    50%      { box-shadow: 0 0 0 8px rgba(220,38,38,0); }
}

.advice-card {
    background: white;
    border-radius: 14px;
    padding: 20px;
    border: 1px solid #f0e0d6;
    box-shadow: 0 2px 8px rgba(0,0,0,.04);
    height: 100%;
}
.advice-card h4 { margin-top: 0; font-size: 15px; color: #6b7280; }
.advice-card p  { font-size: 15px; line-height: 1.6; color: #1f2937; }

.arabic-text { direction: rtl; text-align: right; font-size: 15px; line-height: 1.8; }

.disclaimer {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 12px;
    border-top: 1px solid #f3f4f6;
    padding-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("## 🌸 Mumzworld Pediatric Symptom Assistant")
st.markdown(
    "Describe your child's symptoms in **English** or **Arabic**. "
    "We'll help you understand what to do next."
)
st.markdown("---")

# ── Input ────────────────────────────────────────────────────────────────────
user_input = st.text_area(
    "Describe your child's symptoms:",
    placeholder=(
        "My 8-month-old has had a fever of 39°C for two days and is refusing to eat...\n\n"
        "أو: طفلتي عمرها سنة، عندها سخونة من أمس وترفض الرضاعة..."
    ),
    height=160,
    key="symptom_input"
)

col_btn, col_hint = st.columns([1, 3])
with col_btn:
    submitted = st.button("Check symptoms ›", type="primary", use_container_width=True)
with col_hint:
    st.caption("Results appear in both English and Arabic. This tool is for guidance only.")

# ── Processing & Results ─────────────────────────────────────────────────────
if submitted:
    if not user_input.strip():
        st.warning("Please describe your child's symptoms before submitting.")
        st.stop()

    with st.spinner("Analysing symptoms across three AI agents…"):
        try:
            response = httpx.post(
                f"{API_BASE_URL}/triage",
                json={"input": user_input},
                timeout=90.0
            )
            result = response.json()
        except Exception as e:
            st.error(f"Could not reach the API server. Is `python app.py` running?\n\n`{e}`")
            st.stop()

    st.markdown("---")

    # ── Error responses ──────────────────────────────────────────────────────
    error_type = result.get("error")

    if error_type == "out_of_scope":
        st.info(
            f"🔍 This doesn't look like a child symptom description.\n\n"
            f"**{result.get('suggestion_en', '')}**\n\n"
            f"*{result.get('suggestion_ar', '')}*"
        )
        st.stop()

    if error_type == "empty_input":
        st.warning(result.get("message_en", "Please describe symptoms."))
        st.stop()

    if error_type == "schema_validation_failed":
        st.error(f"⚠️ Validation error: {result.get('detail', 'Unknown error')}")
        with st.expander("Raw model output"):
            st.code(result.get("raw_output", ""), language="json")
        st.stop()

    # ── Valid triage response ────────────────────────────────────────────────
    triage_level = result.get("triage_level", "UNKNOWN")
    confidence   = result.get("confidence", 0.0)
    deferral     = result.get("deferral_required", False)
    lang         = result.get("input_language", "en")
    sources      = result.get("sources_cited", [])
    extraction   = result.get("extraction", {})

    # Triage badge
    badge_class = f"badge-{triage_level}" if triage_level in ["HOME_CARE","MONITOR","SEE_DOCTOR","EMERGENCY"] else ""
    st.markdown(
        f'<span class="triage-badge {badge_class}">{triage_level.replace("_", " ")}</span>',
        unsafe_allow_html=True
    )
    st.progress(confidence, text=f"Model confidence: {confidence:.0%}")

    # Language tag
    lang_labels = {"en": "🇬🇧 English input", "ar": "🇸🇦 Arabic input", "mixed": "🌐 Mixed language input"}
    st.caption(lang_labels.get(lang, ""))

    # Deferral banner
    if deferral:
        st.error("⚠️ **A healthcare professional should evaluate your child.** Do not delay.")

    # Uncertainty note
    uncertainty = extraction.get("uncertainty_note")
    if uncertainty:
        st.warning(f"ℹ️ **Note:** {uncertainty}")

    # Advice cards
    st.markdown("### Guidance")
    col_en, col_ar = st.columns(2)

    with col_en:
        st.markdown(
            f'<div class="advice-card">'
            f'<h4>🇬🇧 English</h4>'
            f'<p>{result.get("advice_en", "N/A")}</p>'
            f'<div class="disclaimer">{result.get("disclaimer_en", "")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with col_ar:
        st.markdown(
            f'<div class="advice-card">'
            f'<h4>🇸🇦 العربية</h4>'
            f'<p class="arabic-text">{result.get("advice_ar", "N/A")}</p>'
            f'<div class="disclaimer arabic-text">{result.get("disclaimer_ar", "")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Meta info
    st.markdown("---")
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        symptoms = extraction.get("symptoms_identified", [])
        if symptoms:
            st.markdown("**Symptoms identified:**")
            for s in symptoms:
                st.markdown(f"- {s}")
        age = extraction.get("child_age_mentioned")
        dur = extraction.get("duration_mentioned")
        if age: st.markdown(f"**Age mentioned:** {age}")
        if dur: st.markdown(f"**Duration mentioned:** {dur}")

    with meta_col2:
        if sources:
            st.markdown("**KB rules cited:**")
            for s in sources:
                st.markdown(f"- `{s}`")

    with st.expander("🔍 Full JSON response"):
        st.json(result)
