import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _on_off_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on", "enabled", "enable"}


@dataclass(frozen=True)
class Config:
    enabled: bool = True
    mode: str = "enforce"
    cache_enabled: bool = False
    cache_ttl: int = 600
    policy_name: str = "default"
    namespace: str = "unknown"
    application: str = "unknown"
    pii_enabled: bool = True
    pii_types: tuple[str, ...] = ("all",)
    pii_phone_countries: tuple[str, ...] = ("US", "MM", "INTL")
    allowlist: tuple[str, ...] = ()
    ignore_patterns: tuple[str, ...] = ()
    presidio_enabled: bool = False
    entropy_secrets_enabled: bool = True
    prompt_injection_action: str = "OBSERVE"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            enabled=_bool_env("AI_GUARD_ENABLED", True),
            mode=os.getenv("AI_GUARD_MODE", "enforce").lower(),
            cache_enabled=_bool_env("AI_GUARD_CACHE", False),
            cache_ttl=int(os.getenv("AI_GUARD_CACHE_TTL", "600")),
            policy_name=os.getenv("AI_GUARD_POLICY", "default"),
            namespace=os.getenv("POD_NAMESPACE", os.getenv("KUBERNETES_NAMESPACE", "unknown")),
            application=os.getenv("APP_NAME", os.getenv("HOSTNAME", "unknown")),
            pii_enabled=_on_off_env("AI_GUARD_PII", True),
            pii_types=_csv_env("AI_GUARD_PII_TYPES", ("all",)),
            pii_phone_countries=_csv_env("AI_GUARD_PHONE_COUNTRIES", ("US", "MM", "INTL")),
            allowlist=_csv_env("AI_GUARD_ALLOWLIST"),
            ignore_patterns=_csv_env("AI_GUARD_IGNORE_PATTERNS"),
            presidio_enabled=_bool_env("AI_GUARD_PRESIDIO", False),
            entropy_secrets_enabled=_bool_env("AI_GUARD_ENTROPY_SECRETS", True),
            prompt_injection_action=os.getenv("AI_GUARD_PROMPT_INJECTION_ACTION", "OBSERVE").upper(),
        )
