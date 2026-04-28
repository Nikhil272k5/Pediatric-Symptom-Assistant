import re


def detect_language(text: str) -> str:
    """
    Detect if input is primarily English, Arabic, or mixed.
    Uses Unicode range for Arabic script: U+0600 to U+06FF.
    Falls back to 'mixed' when both are substantially present.
    """
    if not text:
        return "en"

    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    total = arabic_chars + latin_chars

    if total == 0:
        return "en"

    arabic_ratio = arabic_chars / total

    if arabic_ratio > 0.75:
        return "ar"
    elif arabic_ratio < 0.25:
        return "en"
    else:
        return "mixed"
