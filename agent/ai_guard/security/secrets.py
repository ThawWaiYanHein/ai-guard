import math
import re

from ..config import Config
from .policy import Finding


PATTERNS = [
    ("secret.openai_api_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("secret.aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("secret.github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b")),
    ("secret.github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("secret.slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("secret.google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("secret.azure_storage_key", re.compile(r"\bAccountKey=[A-Za-z0-9+/=]{40,}\b")),
    ("secret.azure_sas_token", re.compile(r"\bsig=[A-Za-z0-9%+/=]{32,}\b")),
    ("secret.stripe_key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b")),
    ("secret.twilio_sid", re.compile(r"\bAC[0-9a-fA-F]{32}\b")),
    ("secret.twilio_auth_token", re.compile(r"\b(?:twilio[_-]auth[_-]token|TWILIO_AUTH_TOKEN)[:= ]+[0-9a-fA-F]{32}\b")),
    ("secret.sendgrid_api_key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b")),
    ("secret.huggingface_token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("secret.discord_bot_token", re.compile(r"\b(?:mfa\.[A-Za-z0-9_-]{20,}|[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27,})\b")),
    ("secret.notion_token", re.compile(r"\bsecret_[A-Za-z0-9]{32,}\b")),
    ("secret.datadog_api_key", re.compile(r"\b(?:datadog[_-]api[_-]key|DD_API_KEY)[:= ]+[0-9a-fA-F]{32}\b")),
    ("secret.datadog_app_key", re.compile(r"\b(?:datadog[_-]app[_-]key|DD_APP_KEY)[:= ]+[0-9a-fA-F]{40}\b")),
    ("secret.terraform_cloud_token", re.compile(r"\batlasv1\.[A-Za-z0-9_-]{60,}\b")),
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

ENTROPY_CANDIDATE = re.compile(r"\b[A-Za-z0-9_+/=-]{32,}\b")

REPLACEMENTS = {
    "secret.openai_api_key": "[REDACTED_OPENAI_KEY]",
    "secret.aws_access_key": "[REDACTED_AWS_KEY]",
    "secret.github_token": "[REDACTED_GITHUB_TOKEN]",
    "secret.github_fine_grained_token": "[REDACTED_GITHUB_TOKEN]",
    "secret.slack_token": "[REDACTED_SLACK_TOKEN]",
    "secret.google_api_key": "[REDACTED_GOOGLE_API_KEY]",
    "secret.azure_storage_key": "AccountKey=[REDACTED_AZURE_KEY]",
    "secret.azure_sas_token": "sig=[REDACTED_AZURE_SAS]",
    "secret.stripe_key": "[REDACTED_STRIPE_KEY]",
    "secret.twilio_sid": "[REDACTED_TWILIO_SID]",
    "secret.twilio_auth_token": "[REDACTED_TWILIO_AUTH_TOKEN]",
    "secret.sendgrid_api_key": "[REDACTED_SENDGRID_API_KEY]",
    "secret.huggingface_token": "[REDACTED_HUGGINGFACE_TOKEN]",
    "secret.discord_bot_token": "[REDACTED_DISCORD_TOKEN]",
    "secret.notion_token": "[REDACTED_NOTION_TOKEN]",
    "secret.datadog_api_key": "[REDACTED_DATADOG_API_KEY]",
    "secret.datadog_app_key": "[REDACTED_DATADOG_APP_KEY]",
    "secret.terraform_cloud_token": "[REDACTED_TERRAFORM_CLOUD_TOKEN]",
    "secret.jwt": "[REDACTED_JWT]",
    "secret.bearer_token": "[REDACTED_BEARER_TOKEN]",
    "secret.private_key": "[REDACTED_PRIVATE_KEY]",
    "secret.high_entropy": "[REDACTED_HIGH_ENTROPY_SECRET]",
}


def _allowed(value: str, config: Config) -> bool:
    if value in config.allowlist:
        return True
    for pattern in config.ignore_patterns:
        try:
            if re.search(pattern, value):
                return True
        except re.error:
            if pattern and pattern in value:
                return True
    return False


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {ch: value.count(ch) for ch in set(value)}
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _looks_like_secret(value: str) -> bool:
    if len(value) < 32:
        return False
    if value.isdigit():
        return False
    if len(set(value)) < 12:
        return False
    return _entropy(value) >= 4.2


def detect_secrets(text: str, config: Config | None = None) -> list[Finding]:
    config = config or Config.from_env()
    findings: list[Finding] = []
    occupied: list[tuple[int, int]] = []

    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if _allowed(value, config):
                continue
            findings.append(Finding(kind, value, match.start(), match.end(), severity="high"))
            occupied.append((match.start(), match.end()))

    if config.entropy_secrets_enabled:
        for match in ENTROPY_CANDIDATE.finditer(text):
            if any(match.start() >= start and match.end() <= end for start, end in occupied):
                continue
            value = match.group(0)
            if _allowed(value, config) or not _looks_like_secret(value):
                continue
            findings.append(Finding("secret.high_entropy", value, match.start(), match.end(), severity="medium"))

    return findings


def redact_secrets(text: str, config: Config | None = None) -> tuple[str, list[Finding], int]:
    findings = detect_secrets(text, config)
    for finding in sorted(findings, key=lambda item: item.start, reverse=True):
        text = text[: finding.start] + REPLACEMENTS[finding.kind] + text[finding.end :]
    return text, findings, len(findings)
