from dataclasses import dataclass
from enum import Enum


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


@dataclass(frozen=True)
class Policy:
    pii: Action = Action.REDACT
    secrets: Action = Action.REDACT
    prompt_injection: Action = Action.OBSERVE

    def action_for(self, finding: Finding) -> Action:
        if finding.kind.startswith("pii."):
            return self.pii
        if finding.kind.startswith("secret."):
            return self.secrets
        if finding.kind.startswith("prompt_injection"):
            return self.prompt_injection
        return Action.ALLOW


def default_policy() -> Policy:
    return Policy()
