from ai_guard.config import Config
from ai_guard.security.pii import detect_pii, redact_pii


def test_detects_new_pii_types():
    text = (
        "my name is Jane Smith, SSN 123-45-6789, "
        "passport A1234567, address 123 Main Street"
    )

    findings = detect_pii(text)
    kinds = {finding.kind for finding in findings}

    assert "pii.name" in kinds
    assert "pii.ssn" in kinds
    assert "pii.passport" in kinds
    assert "pii.address" in kinds


def test_pii_types_can_be_configured():
    redacted, findings, count = redact_pii(
        "email person@example.com and SSN 123-45-6789",
        Config(pii_types=("email",)),
    )

    assert count == 1
    assert "[REDACTED_EMAIL]" in redacted
    assert "123-45-6789" in redacted
    assert {finding.kind for finding in findings} == {"pii.email"}


def test_allowlist_skips_known_safe_value():
    redacted, findings, count = redact_pii(
        "email support@example.com",
        Config(allowlist=("support@example.com",)),
    )

    assert count == 0
    assert findings == []
    assert "support@example.com" in redacted


def test_phone_country_precision_skips_disabled_country():
    redacted, findings, count = redact_pii(
        "Call 415-555-1212",
        Config(pii_types=("phone",), pii_phone_countries=("MM",)),
    )

    assert count == 0
    assert findings == []
    assert "415-555-1212" in redacted


def test_pii_can_be_disabled():
    redacted, findings, count = redact_pii(
        "email person@example.com and SSN 123-45-6789",
        Config(pii_enabled=False),
    )

    assert count == 0
    assert findings == []
    assert "person@example.com" in redacted
    assert "123-45-6789" in redacted
