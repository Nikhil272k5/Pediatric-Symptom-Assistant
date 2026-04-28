from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional
from enum import Enum


class TriageLevel(str, Enum):
    HOME_CARE  = "HOME_CARE"
    MONITOR    = "MONITOR"
    SEE_DOCTOR = "SEE_DOCTOR"
    EMERGENCY  = "EMERGENCY"


class SymptomExtraction(BaseModel):
    symptoms_identified: list[str] = Field(
        description="Exact symptom strings extracted from parent input. Never invented."
    )
    child_age_mentioned: Optional[str] = Field(
        default=None,
        description="Age as stated by parent. e.g. '6 months', '2 years'. Null if not stated."
    )
    duration_mentioned: Optional[str] = Field(
        default=None,
        description="Duration as stated. e.g. '2 days', 'since yesterday'. Null if not stated."
    )
    red_flag_signals: list[str] = Field(
        default_factory=list,
        description="KB rule IDs matched. Empty list if none. e.g. ['RF001', 'RF006']"
    )
    uncertainty_note: Optional[str] = Field(
        default=None,
        description="If input is vague, ambiguous, or incomplete, explain what is unclear."
    )
    out_of_scope: bool = Field(
        default=False,
        description="True if input is not about a child's health symptoms."
    )
    out_of_scope_reason: Optional[str] = Field(
        default=None,
        description="If out_of_scope is True, one-sentence explanation."
    )


class TriageResponse(BaseModel):
    input_language: Literal["en", "ar", "mixed"]
    triage_level: Optional[TriageLevel] = Field(
        description="Null only if out_of_scope is True."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in triage level. Must be < 0.6 if age or duration unknown."
    )
    extraction: SymptomExtraction
    advice_en: Optional[str] = Field(
        default=None,
        description="Native English advice. Null if out_of_scope. Max 120 words. No drug names."
    )
    advice_ar: Optional[str] = Field(
        default=None,
        description="Native Arabic advice. NOT a translation of EN. Null if out_of_scope."
    )
    deferral_required: bool = Field(
        description="True if any red_flag_signals present. Structurally enforced."
    )
    disclaimer_en: str = Field(
        default="This information is for general guidance only and does not constitute medical advice. Always consult a qualified healthcare professional for your child's health concerns."
    )
    disclaimer_ar: str = Field(
        default="هذه المعلومات للتوجيه العام فقط ولا تُعدّ نصيحة طبية. يُرجى دائمًا استشارة طبيب مختص لأي مخاوف تتعلق بصحة طفلك."
    )
    sources_cited: list[str] = Field(
        default_factory=list,
        description="KB rule IDs cited in this response."
    )

    @model_validator(mode="after")
    def confidence_reflects_uncertainty(self):
        extraction = self.extraction
        if extraction:
            age_unknown = extraction.child_age_mentioned is None
            duration_unknown = extraction.duration_mentioned is None
            if (age_unknown or duration_unknown) and self.confidence > 0.65:
                raise ValueError(
                    "Confidence cannot exceed 0.65 when child age or duration is unknown. "
                    f"Got {self.confidence}. Populate uncertainty_note explaining what is missing."
                )
        return self

    @model_validator(mode="after")
    def enforce_deferral_when_red_flags_present(self):
        if self.extraction.red_flag_signals and not self.deferral_required:
            raise ValueError(
                f"deferral_required must be True when red_flag_signals is non-empty. "
                f"Red flags found: {self.extraction.red_flag_signals}"
            )
        if self.extraction.red_flag_signals:
            if self.triage_level not in [TriageLevel.SEE_DOCTOR, TriageLevel.EMERGENCY]:
                raise ValueError(
                    "When red_flag_signals is non-empty, triage_level must be "
                    "SEE_DOCTOR or EMERGENCY."
                )
        return self

    @model_validator(mode="after")
    def out_of_scope_implies_null_triage(self):
        if self.extraction.out_of_scope:
            if self.triage_level is not None:
                raise ValueError("triage_level must be None when out_of_scope is True.")
            if self.advice_en is not None or self.advice_ar is not None:
                raise ValueError("advice fields must be None when out_of_scope is True.")
        return self


class ValidationError(BaseModel):
    error: Literal["schema_validation_failed"] = "schema_validation_failed"
    detail: str
    raw_output: str


class OutOfScopeResponse(BaseModel):
    error: Literal["out_of_scope"] = "out_of_scope"
    reason: str
    suggestion_en: str = "Mumzworld's customer support team is happy to help with product questions."
    suggestion_ar: str = "فريق خدمة عملاء مامز وورلد سعيد بمساعدتك في أسئلة المنتجات."


class EmptyInputError(BaseModel):
    error: Literal["empty_input"] = "empty_input"
    message_en: str = "Please describe your child's symptoms so we can help."
    message_ar: str = "يُرجى وصف أعراض طفلك حتى نتمكن من المساعدة."
