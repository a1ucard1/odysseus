from src.clean_agent_preview import preview_response_token_budget


def test_qwen_budget_uses_reasoning_default_without_session_override():
    model = 'tinyrick/Qwen3.6-35B-A3B-uncensored-heretic-vision-llmfan46:Q4_K_M'
    assert preview_response_token_budget(model, 0) == 32768
    assert preview_response_token_budget(model, None) == 32768
    assert preview_response_token_budget(model, 1024) == 1024
    assert preview_response_token_budget(model, 32768) == 32768
    assert preview_response_token_budget(model, 65536) == 32768
    assert preview_response_token_budget('other-model', 0) == 768
