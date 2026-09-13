import re

from .policy import Finding


PATTERNS = [
    ("secret.openai_api_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("secret.aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("secret.jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("secret.bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.IGNORECASE)),
    (
        "secret.private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
]


REPLACEMENTS = {
    "secret.openai_api_key": "[REDACTED_OPENAI_KEY]",
    "secret.aws_access_key": "[REDACTED_AWS_KEY]",
    "secret.jwt": "[REDACTED_JWT]",
    "secret.bearer_token": "[REDACTED_BEARER_TOKEN]",
    "secret.private_key": "[REDACTED_PRIVATE_KEY]",
}


def detect_secrets(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            findings.append(Finding(kind, match.group(0), match.start(), match.end()))
    return findings


def redact_secrets(text: str) -> tuple[str, list[Finding], int]:
    findings = detect_secrets(text)
    for finding in sorted(findings, key=lambda item: item.start, reverse=True):
        text = text[: finding.start] + REPLACEMENTS[finding.kind] + text[finding.end :]
    return text, findings, len(findings)
