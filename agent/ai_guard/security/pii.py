import re

from .policy import Finding


PATTERNS = [
    ("pii.email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("pii.phone", re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\w)")),
    ("pii.ip_address", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    ("pii.credit_card", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
]


REPLACEMENTS = {
    "pii.email": "[REDACTED_EMAIL]",
    "pii.phone": "[REDACTED_PHONE]",
    "pii.ip_address": "[REDACTED_IP]",
    "pii.credit_card": "[REDACTED_CREDIT_CARD]",
}


def _luhn(candidate: str) -> bool:
    digits = [int(ch) for ch in candidate if ch.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def detect_pii(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            if kind == "pii.credit_card" and not _luhn(match.group(0)):
                continue
            findings.append(Finding(kind, match.group(0), match.start(), match.end()))
    return findings


def redact_pii(text: str) -> tuple[str, list[Finding], int]:
    findings = detect_pii(text)
    for finding in sorted(findings, key=lambda item: item.start, reverse=True):
        text = text[: finding.start] + REPLACEMENTS[finding.kind] + text[finding.end :]
    return text, findings, len(findings)
