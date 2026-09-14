from dataclasses import dataclass
from enum import Enum
import hashlib


class Action(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    OBSERVE = "OBSERVE"


@dataclass(frozen=True)
class Finding:
    kind: str
    value: str
    start: int
    end: int
    severity: str = "medium"
    action: Action | None = None

    def report(self, action: Action | None = None) -> dict[str, str | int]:
        effective_action = action or self.action or Action.OBSERVE
        return {
            "kind": self.kind,
            "severity": self.severity,
            "action": effective_action.value,
            "start": self.start,
            "end": self.end,
            "fingerprint": hashlib.sha256(self.value.encode("utf-8")).hexdigest()[:12],
        }


@dataclass(frozen=True)
class Policy:
    pii: Action = Action.REDACT
    secrets: Action = Action.REDACT
    prompt_injection: Action = Action.OBSERVE
    overrides: dict[str, Action] | None = None

    def action_for(self, finding: Finding) -> Action:
        if finding.action is not None:
            return finding.action
        if self.overrides and finding.kind in self.overrides:
            return self.overrides[finding.kind]
        if finding.kind.startswith("pii."):
            return self.pii
        if finding.kind.startswith("secret."):
            return self.secrets
        if finding.kind.startswith("prompt_injection"):
            return self.prompt_injection
        return Action.ALLOW


def _action(value: str | None, default: Action) -> Action:
    if not value:
        return default
    try:
        return Action(value.upper())
    except ValueError:
        return default


def default_policy(config=None) -> Policy:
    overrides: dict[str, Action] = {}
    if config is not None:
        overrides["prompt_injection.high"] = _action(config.prompt_injection_action, Action.OBSERVE)
    return Policy(overrides=overrides)
