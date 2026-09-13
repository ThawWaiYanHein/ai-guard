from ai_guard.security.secrets import detect_secrets, redact_secrets


def test_detects_and_redacts_common_secrets():
    text = (
        "OpenAI sk-proj-abcdefghijklmnopqrstuvwxyz "
        "AWS AKIAABCDEFGHIJKLMNOP "
        "Bearer abcdefghijklmnopqrstuvwxyz123456"
    )

    redacted, findings, count = redact_secrets(text)

    kinds = {finding.kind for finding in findings}
    assert "secret.openai_api_key" in kinds
    assert "secret.aws_access_key" in kinds
    assert "secret.bearer_token" in kinds
    assert count == 3
    assert "sk-proj" not in redacted


def test_detects_jwt():
    findings = detect_secrets(
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signaturevalue"
    )
    assert any(finding.kind == "secret.jwt" for finding in findings)
