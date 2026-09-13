import pytest

from ai_guard.config import Config
from ai_guard.firewall import AIGuardBlockedError, inspect_payload
from ai_guard.security.policy import Action, Policy


def test_policy_can_block_secret_findings():
    with pytest.raises(AIGuardBlockedError):
        inspect_payload(
            "responses",
            {"model": "gpt-4.1-mini", "input": "token sk-proj-abcdefghijklmnopqrstuvwxyz"},
            Config(mode="enforce", cache_enabled=False),
            Policy(secrets=Action.BLOCK),
        )
