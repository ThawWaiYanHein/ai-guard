from ai_guard.config import Config


def test_cache_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AI_GUARD_CACHE", raising=False)

    assert Config.from_env().cache_enabled is False


def test_cache_can_be_enabled_by_env(monkeypatch):
    monkeypatch.setenv("AI_GUARD_CACHE", "true")

    assert Config.from_env().cache_enabled is True


def test_pii_can_be_disabled_by_env(monkeypatch):
    monkeypatch.setenv("AI_GUARD_PII", "off")

    assert Config.from_env().pii_enabled is False
