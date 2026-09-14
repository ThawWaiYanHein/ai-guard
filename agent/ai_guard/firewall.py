import copy
from dataclasses import dataclass
from typing import Any

from .config import Config
from .observability import increment, increment_finding, log_event
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
    redaction_report: list[dict[str, Any]] | None = None


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


def _scan_text(text: str, config: Config, policy: Policy) -> tuple[str, list[Finding], int]:
    text, pii_findings, pii_count = redact_pii(text, config)
    text, secret_findings, secret_count = redact_secrets(text, config)
    injection_findings = detect_prompt_injection(
        text,
        high_action=policy.overrides.get("prompt_injection.high", Action.OBSERVE)
        if policy.overrides
        else Action.OBSERVE,
    )
    return text, pii_findings + secret_findings + injection_findings, pii_count + secret_count


def _redact_text(text: str, config: Config, policy: Policy) -> tuple[str, list[Finding], int]:
    return _scan_text(text, config, policy)


def _record_findings(findings: list[Finding]) -> None:
    for finding in findings:
        increment_finding(finding.kind)


def inspect_payload(
    api: str,
    payload: dict[str, Any],
    config: Config | None = None,
    policy: Policy | None = None,
) -> GuardResult:
    config = config or Config.from_env()
    policy = policy or default_policy(config)
    increment("requests_inspected")

    sanitized = copy.deepcopy(payload)
    sanitized, findings, redactions = _walk_strings(
        sanitized, lambda text: _redact_text(text, config, policy)
    )
    increment("redactions_performed", redactions)
    _record_findings(findings)

    report = [finding.report(policy.action_for(finding)) for finding in findings]
    blocked = any(item["action"] == Action.BLOCK.value for item in report)
    model = payload.get("model")
    if blocked and config.mode == "enforce":
        increment("blocked_requests")
        log_event(
            config,
            action="blocked",
            reason="policy blocked request",
            model=model,
            findings=[finding.kind for finding in findings],
            reports=report,
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
        reports=report,
    )
    return GuardResult(sanitized, action, findings, redactions, report)
