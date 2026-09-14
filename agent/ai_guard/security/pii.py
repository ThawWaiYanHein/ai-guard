import re

from ..config import Config
from .policy import Finding


EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IP_ADDRESS = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
CREDIT_CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SSN = re.compile(r"\b(?!000|666|9\d\d)\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b")
PASSPORT = re.compile(r"\b(?:passport|passport no\.?|passport number)[:# ]+([A-Z0-9]{6,9})\b", re.IGNORECASE)
ADDRESS = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.' -]{2,60}\s+"
    r"(?:street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|lane|ln\.?|drive|dr\.?)\b",
    re.IGNORECASE,
)
NAME = re.compile(r"\b(?:my name is|name is|name:) +([A-Z][a-z]+(?: [A-Z][a-z]+){1,3})\b")

PHONE_PATTERNS = {
    "US": re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(?[2-9]\d{2}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\w)"),
    "MM": re.compile(r"(?<!\w)(?:\+?95[-.\s]?)?(?:9|09)[0-9][-.\s]?\d{3}[-.\s]?\d{4,5}(?!\w)"),
    "INTL": re.compile(r"(?<!\w)\+\d{1,3}[-.\s]?(?:\d[-.\s]?){7,14}\d(?!\w)"),
}

REPLACEMENTS = {
    "pii.email": "[REDACTED_EMAIL]",
    "pii.phone": "[REDACTED_PHONE]",
    "pii.ip_address": "[REDACTED_IP]",
    "pii.credit_card": "[REDACTED_CREDIT_CARD]",
    "pii.ssn": "[REDACTED_SSN]",
    "pii.passport": "[REDACTED_PASSPORT]",
    "pii.address": "[REDACTED_ADDRESS]",
    "pii.name": "[REDACTED_NAME]",
}


def _enabled(kind: str, config: Config) -> bool:
    requested = {item.lower() for item in config.pii_types}
    return "all" in requested or kind.removeprefix("pii.").lower() in requested


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


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _valid_phone(value: str, country: str) -> bool:
    digits = _digits(value)
    if country == "US":
        return len(digits) in {10, 11} and not _luhn(value)
    if country == "MM":
        return 8 <= len(digits) <= 13 and not _luhn(value)
    return 9 <= len(digits) <= 16 and not _luhn(value)


def _append_regex(
    findings: list[Finding],
    text: str,
    kind: str,
    pattern: re.Pattern,
    config: Config,
    *,
    group: int = 0,
    severity: str = "medium",
) -> None:
    if not _enabled(kind, config):
        return
    for match in pattern.finditer(text):
        value = match.group(group)
        start = match.start(group)
        end = match.end(group)
        if _allowed(value, config):
            continue
        if kind == "pii.credit_card" and not _luhn(value):
            continue
        findings.append(Finding(kind, value, start, end, severity=severity))


def _presidio_findings(text: str, config: Config) -> list[Finding]:
    if not config.presidio_enabled:
        return []
    try:
        from presidio_analyzer import AnalyzerEngine
    except Exception:
        return []

    analyzer = AnalyzerEngine()
    findings = []
    for result in analyzer.analyze(text=text, language="en"):
        value = text[result.start : result.end]
        kind = f"pii.presidio.{result.entity_type.lower()}"
        if _allowed(value, config):
            continue
        findings.append(Finding(kind, value, result.start, result.end, severity="medium"))
    return findings


def detect_pii(text: str, config: Config | None = None) -> list[Finding]:
    config = config or Config.from_env()
    findings: list[Finding] = []

    _append_regex(findings, text, "pii.email", EMAIL, config)
    _append_regex(findings, text, "pii.ip_address", IP_ADDRESS, config)
    _append_regex(findings, text, "pii.credit_card", CREDIT_CARD, config, severity="high")
    _append_regex(findings, text, "pii.ssn", SSN, config, severity="high")
    _append_regex(findings, text, "pii.passport", PASSPORT, config, group=1, severity="high")
    _append_regex(findings, text, "pii.address", ADDRESS, config)
    _append_regex(findings, text, "pii.name", NAME, config, group=1)

    if _enabled("pii.phone", config):
        countries = {country.upper() for country in config.pii_phone_countries}
        for country, pattern in PHONE_PATTERNS.items():
            if country not in countries:
                continue
            for match in pattern.finditer(text):
                value = match.group(0)
                if _allowed(value, config) or not _valid_phone(value, country):
                    continue
                findings.append(Finding("pii.phone", value, match.start(), match.end()))

    findings.extend(_presidio_findings(text, config))
    return _dedupe(findings)


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen = set()
    output = []
    for finding in sorted(findings, key=lambda item: (item.start, -(item.end - item.start))):
        key = (finding.kind, finding.start, finding.end)
        if key in seen:
            continue
        seen.add(key)
        output.append(finding)
    return output


def redact_pii(text: str, config: Config | None = None) -> tuple[str, list[Finding], int]:
    findings = detect_pii(text, config)
    for finding in sorted(findings, key=lambda item: item.start, reverse=True):
        replacement = REPLACEMENTS.get(finding.kind, "[REDACTED_PII]")
        text = text[: finding.start] + replacement + text[finding.end :]
    return text, findings, len(findings)
