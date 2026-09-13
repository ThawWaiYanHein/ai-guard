import copy
from dataclasses import dataclass
from typing import Any

from .config import Config
from .observability import increment, log_event
from .security.injection import detect_prompt_injection
from .security.pii import redact_pii
from .security.policy import Action, Finding, Policy, default_policy
from .security.secrets import redact_secrets


class AIGuardBlockedError(RuntimeError):
    pass


@dataclass
class GuardResult:
    payload: dict[str, Any]
    action: str
    findings: list[Finding]
    redactions: int = 0


def _walk_strings(value: Any, fn) -> tuple[Any, list[Finding], int]:
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, list):
        total_findings: list[Finding] = []
        redactions = 0
        output = []
        for item in value:
            new_item, findings, count = _walk_strings(item, fn)
            output.append(new_item)
            total_findings.extend(findings)
            redactions += count
        return output, total_findings, redactions
    if isinstance(value, dict):
        total_findings = []
        redactions = 0
        output = {}
        for key, item in value.items():
            new_item, findings, count = _walk_strings(item, fn)
            output[key] = new_item
            total_findings.extend(findings)
            redactions += count
        return output, total_findings, redactions
    return value, [], 0


def _redact_text(text: str) -> tuple[str, list[Finding], int]:
    text, pii_findings, pii_count = redact_pii(text)
    text, secret_findings, secret_count = redact_secrets(text)
    injection_findings = detect_prompt_injection(text)
    return text, pii_findings + secret_findings + injection_findings, pii_count + secret_count


def inspect_payload(
    api: str,
    payload: dict[str, Any],
    config: Config | None = None,
    policy: Policy | None = None,
) -> GuardResult:
    config = config or Config.from_env()
    policy = policy or default_policy()
    increment("requests_inspected")

    sanitized = copy.deepcopy(payload)
    sanitized, findings, redactions = _walk_strings(sanitized, _redact_text)
    increment("redactions_performed", redactions)

    blocked = any(policy.action_for(finding) == Action.BLOCK for finding in findings)
    model = payload.get("model")
    if blocked and config.mode == "enforce":
        increment("blocked_requests")
        log_event(
            config,
            action="blocked",
            reason="policy blocked request",
            model=model,
            findings=[finding.kind for finding in findings],
        )
        raise AIGuardBlockedError("AI-Guard blocked request by policy")

    action = "redacted" if redactions else "allowed"
    if findings and not redactions:
        action = "observed"
    log_event(
        config,
        action=action,
        reason=f"{api} request inspected",
        model=model,
        findings=[finding.kind for finding in findings],
    )
    return GuardResult(sanitized, action, findings, redactions)
