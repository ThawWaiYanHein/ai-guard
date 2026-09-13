import re

from .policy import Finding


PATTERNS = [
    re.compile(r"\bignore (?:all )?(?:previous|prior|above) instructions\b", re.IGNORECASE),
    re.compile(r"\breveal (?:the )?(?:system|developer) prompt\b", re.IGNORECASE),
    re.compile(r"\byou are now (?:in )?developer mode\b", re.IGNORECASE),
    re.compile(r"\bdisregard (?:all )?(?:previous|prior|above) instructions\b", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                Finding("prompt_injection.observed", match.group(0), match.start(), match.end())
            )
    return findings
