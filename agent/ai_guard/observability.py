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


def increment(metric: str, value: int = 1) -> None:
    METRICS[metric] += value


def snapshot() -> dict[str, int]:
    return dict(METRICS)


def log_event(
    config,
    *,
    action: str,
    reason: str,
    model: str | None = None,
    findings: Iterable[str] | None = None,
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
    print(json.dumps(event, separators=(",", ":")))
