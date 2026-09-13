from ai_guard.config import Config
from ai_guard.firewall import inspect_payload


def test_firewall_redacts_nested_messages():
    result = inspect_payload(
        "chat.completions",
        {
            "model": "gpt-4.1-mini",
            "messages": [
                {
                    "role": "user",
                    "content": "email me at person@example.com and call 415-555-1212",
                }
            ],
        },
        Config(cache_enabled=False),
    )

    content = result.payload["messages"][0]["content"]
    assert "[REDACTED_EMAIL]" in content
    assert "[REDACTED_PHONE]" in content
    assert result.action == "redacted"
