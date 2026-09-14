import re

from .policy import Action, Finding


RULES = [
    (
        "prompt_injection.high",
        "high",
        re.compile(r"\breveal (?:the )?(?:system|developer) prompt\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.high",
        "high",
        re.compile(r"\bprint (?:the )?(?:system|developer) instructions\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.high",
        "high",
        re.compile(r"\bexfiltrate\b.*\b(?:secret|token|key|credential)s?\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.high",
        "high",
        re.compile(r"\b(?:dump|show|leak).{0,40}\b(?:environment variables|api keys|secrets)\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.medium",
        "medium",
        re.compile(r"\bignore (?:all )?(?:previous|prior|above) instructions\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.medium",
        "medium",
        re.compile(r"\bdisregard (?:all )?(?:previous|prior|above) instructions\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.medium",
        "medium",
        re.compile(r"\byou are now (?:in )?(?:developer|god|admin|root) mode\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.medium",
        "medium",
        re.compile(r"\bdo not follow (?:the )?(?:system|developer) instructions\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.low",
        "low",
        re.compile(r"\bjailbreak\b|\bDAN mode\b|\broleplay as unrestricted\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.tool.high",
        "high",
        re.compile(r"\bcall (?:any|all) tools?\b.*\bwithout (?:asking|confirmation|approval)\b", re.IGNORECASE),
    ),
    (
        "prompt_injection.output_leak.high",
        "high",
        re.compile(r"\binclude (?:the )?(?:hidden|system|developer) prompt in (?:the )?answer\b", re.IGNORECASE),
    ),
]


def detect_prompt_injection(
    text: str,
    *,
    high_action: Action = Action.OBSERVE,
) -> list[Finding]:
    findings: list[Finding] = []
    for kind, severity, pattern in RULES:
        for match in pattern.finditer(text):
            action = high_action if severity == "high" else Action.OBSERVE
            findings.append(
                Finding(kind, match.group(0), match.start(), match.end(), severity=severity, action=action)
            )
    return findings
