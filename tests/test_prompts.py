from screenscribe.prompts import apply_analysis_prompt_override


def test_apply_analysis_prompt_override_keeps_base_prompt_when_blank() -> None:
    base_prompt = "Analyze this screenshot and respond in JSON."

    assert apply_analysis_prompt_override(base_prompt, "") == base_prompt
    assert apply_analysis_prompt_override(base_prompt, "   ") == base_prompt


def test_apply_analysis_prompt_override_appends_operator_instructions() -> None:
    base_prompt = "Analyze this screenshot and respond in JSON."
    override = "Focus on auth resilience and cross-device completion."

    result = apply_analysis_prompt_override(base_prompt, override)

    assert base_prompt in result
    assert override in result
    assert "Preserve every required field" in result
