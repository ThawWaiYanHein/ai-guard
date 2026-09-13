from ai_guard.cache import cache_key, can_cache


def test_cache_key_includes_generation_parameters():
    left = cache_key(
        "responses",
        {"model": "gpt-4.1-mini", "input": "hello", "temperature": 0, "max_output_tokens": 64},
    )
    right = cache_key(
        "responses",
        {"model": "gpt-4.1-mini", "input": "hello", "temperature": 1, "max_output_tokens": 64},
    )

    assert left != right


def test_cache_skips_streaming_tools_and_conversation_state():
    assert not can_cache({"stream": True})
    assert not can_cache({"tools": [{"type": "function"}]})
    assert not can_cache({"previous_response_id": "resp_123"})
    assert can_cache({"model": "gpt-4.1-mini", "input": "hello"})
