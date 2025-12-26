"""Internationalized prompts for LLM and Vision analysis."""

from typing import Literal

PromptLanguage = Literal["pl", "en"]

# Semantic analysis prompts
SEMANTIC_ANALYSIS_PROMPTS: dict[str, str] = {
    "pl": """Jesteś ekspertem UX/UI i programistą analizującym feedback z nagrania screencast.

Przeanalizuj poniższy fragment transkrypcji. UWAGA: Użytkownik może zgłaszać problem, ALE TAKŻE może potwierdzać że coś działa poprawnie.

Fragment:
{text}

Kontekst (otaczające wypowiedzi):
{context}

Kategoria wykryta automatycznie: {category}

WAŻNE - Przykłady interpretacji:
- "To nie działa" → is_issue: true (zgłasza problem)
- "Te białe tła nie przeszkadzają" → is_issue: false (potwierdza że OK)
- "Powinno być przeźroczyste" → is_issue: true (zgłasza problem)
- "Działa ładnie" → is_issue: false (potwierdza że OK)
- "Jest brzydkie" → is_issue: true (zgłasza problem)
- "Teraz jest ok" → is_issue: false (potwierdza że OK)

Zwróć szczególną uwagę na NEGACJE ("nie przeszkadza", "nie ma problemu", "jest ok").

Odpowiedz w formacie JSON:
{{
    "is_issue": true/false,
    "sentiment": "problem|positive|neutral",
    "severity": "critical|high|medium|low|none",
    "summary": "Krótkie podsumowanie - CO użytkownik mówi (1-2 zdania)",
    "action_items": ["Lista konkretnych zadań do wykonania (pusta jeśli is_issue=false)"],
    "affected_components": ["Lista komponentów UI/funkcji których dotyczy"],
    "suggested_fix": "Sugerowane rozwiązanie techniczne (lub 'Brak - nie jest to problem' jeśli is_issue=false)"
}}

Odpowiadaj tylko JSON, bez dodatkowego tekstu.""",
    "en": """You are a UX/UI expert and developer analyzing feedback from a screencast recording.

Analyze the following transcript fragment. NOTE: The user may be reporting a problem, BUT ALSO may be confirming that something works correctly.

Fragment:
{text}

Context (surrounding speech):
{context}

Automatically detected category: {category}

IMPORTANT - Interpretation examples:
- "This doesn't work" → is_issue: true (reports problem)
- "The white backgrounds don't bother me" → is_issue: false (confirms OK)
- "Should be transparent" → is_issue: true (reports problem)
- "Works nicely" → is_issue: false (confirms OK)
- "It's ugly" → is_issue: true (reports problem)
- "Now it's fine" → is_issue: false (confirms OK)

Pay special attention to NEGATIONS ("doesn't bother", "no problem", "is ok").

Respond in JSON format:
{{
    "is_issue": true/false,
    "sentiment": "problem|positive|neutral",
    "severity": "critical|high|medium|low|none",
    "summary": "Brief summary - WHAT the user is saying (1-2 sentences)",
    "action_items": ["List of specific tasks to complete (empty if is_issue=false)"],
    "affected_components": ["List of affected UI components/features"],
    "suggested_fix": "Suggested technical solution (or 'None - not an issue' if is_issue=false)"
}}

Respond only with JSON, no additional text.""",
}

# Executive summary prompts
EXECUTIVE_SUMMARY_PROMPTS: dict[str, str] = {
    "pl": """Jesteś product managerem przygotowującym raport z przeglądu UX.

Na podstawie poniższych znalezisk, przygotuj krótkie podsumowanie wykonawcze (executive summary) dla zespołu developerskiego.

Znaleziska:
{findings}

Napisz podsumowanie w 3-5 zdaniach, skupiając się na:
1. Najważniejszych problemach do naprawienia
2. Ogólnym stanie UX aplikacji
3. Rekomendacji priorytetów

Odpowiadaj po polsku, zwięźle i konkretnie.""",
    "en": """You are a product manager preparing a UX review report.

Based on the following findings, prepare a brief executive summary for the development team.

Findings:
{findings}

Write a summary in 3-5 sentences, focusing on:
1. Most critical issues to fix
2. Overall state of the application UX
3. Priority recommendations

Be concise and specific.""",
}

# Vision analysis prompts
VISION_ANALYSIS_PROMPTS: dict[str, str] = {
    "pl": """Jesteś ekspertem UX/UI analizującym screenshot aplikacji desktopowej.

Kontekst z transkrypcji (co użytkownik mówił w tym momencie):
"{transcript_context}"

Przeanalizuj ten screenshot i odpowiedz w formacie JSON:
{{
    "ui_elements": ["Lista widocznych elementów UI (przyciski, formularze, itp.)"],
    "issues_detected": ["Lista problemów wizualnych/UX widocznych na screenshocie"],
    "accessibility_notes": ["Uwagi dotyczące dostępności"],
    "design_feedback": "Ogólna ocena designu i sugestie (1-2 zdania)",
    "technical_observations": "Obserwacje techniczne - błędy, artefakty, problemy z layoutem"
}}

Odpowiadaj tylko JSON, po polsku.""",
    "en": """You are a UX/UI expert analyzing a desktop application screenshot.

Context from transcript (what the user was saying at this moment):
"{transcript_context}"

Analyze this screenshot and respond in JSON format:
{{
    "ui_elements": ["List of visible UI elements (buttons, forms, etc.)"],
    "issues_detected": ["List of visual/UX issues visible in the screenshot"],
    "accessibility_notes": ["Accessibility observations"],
    "design_feedback": "Overall design assessment and suggestions (1-2 sentences)",
    "technical_observations": "Technical observations - errors, artifacts, layout issues"
}}

Respond only with JSON, in English.""",
}


def get_semantic_analysis_prompt(language: str = "pl") -> str:
    """Get semantic analysis prompt for the specified language."""
    lang = _normalize_language(language)
    return SEMANTIC_ANALYSIS_PROMPTS.get(lang, SEMANTIC_ANALYSIS_PROMPTS["en"])


def get_executive_summary_prompt(language: str = "pl") -> str:
    """Get executive summary prompt for the specified language."""
    lang = _normalize_language(language)
    return EXECUTIVE_SUMMARY_PROMPTS.get(lang, EXECUTIVE_SUMMARY_PROMPTS["en"])


def get_vision_analysis_prompt(language: str = "pl") -> str:
    """Get vision analysis prompt for the specified language."""
    lang = _normalize_language(language)
    return VISION_ANALYSIS_PROMPTS.get(lang, VISION_ANALYSIS_PROMPTS["en"])


def _normalize_language(language: str) -> str:
    """Normalize language code to supported values."""
    lang = language.lower().strip()

    # Map common language codes to supported ones
    pl_codes = {"pl", "pl-pl", "polish", "polski"}
    en_codes = {"en", "en-us", "en-gb", "english"}

    if lang in pl_codes:
        return "pl"
    if lang in en_codes:
        return "en"

    # Default to English for unsupported languages
    return "en"


def get_supported_languages() -> list[str]:
    """Get list of supported languages."""
    return ["pl", "en"]
