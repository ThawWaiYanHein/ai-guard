import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    enabled: bool = True
    mode: str = "enforce"
    cache_enabled: bool = True
    cache_ttl: int = 600
    policy_name: str = "default"
    namespace: str = "unknown"
    application: str = "unknown"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            enabled=_bool_env("AI_GUARD_ENABLED", True),
            mode=os.getenv("AI_GUARD_MODE", "enforce").lower(),
            cache_enabled=_bool_env("AI_GUARD_CACHE", True),
            cache_ttl=int(os.getenv("AI_GUARD_CACHE_TTL", "600")),
            policy_name=os.getenv("AI_GUARD_POLICY", "default"),
            namespace=os.getenv("POD_NAMESPACE", os.getenv("KUBERNETES_NAMESPACE", "unknown")),
            application=os.getenv("APP_NAME", os.getenv("HOSTNAME", "unknown")),
        )
