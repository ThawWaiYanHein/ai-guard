import json
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable


METRICS = Counter(
    {
        "requests_inspected": 0,
        "redactions_performed": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "blocked_requests": 0,
    }
)

FINDING_METRICS = Counter()


def increment(metric: str, value: int = 1) -> None:
    METRICS[metric] += value


def increment_finding(kind: str, value: int = 1) -> None:
    FINDING_METRICS[kind] += value


def snapshot() -> dict[str, int]:
    output = dict(METRICS)
    for kind, value in FINDING_METRICS.items():
        output[f"finding.{kind}"] = value
    return output


def log_event(
    config,
    *,
    action: str,
    reason: str,
    model: str | None = None,
    findings: Iterable[str] | None = None,
    reports: Iterable[dict] | None = None,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "namespace": config.namespace,
        "application": config.application,
        "model": model,
        "action": action,
        "reason": reason,
    }
    if findings:
        event["findings"] = list(findings)
    if reports:
        event["reports"] = list(reports)
    print(json.dumps(event, separators=(",", ":")))
