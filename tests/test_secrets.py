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


def test_detects_additional_provider_tokens():
    text = (
        "ghp_abcdefghijklmnopqrstuvwxyz1234567890 "
        "xoxb-123456789012-123456789012-abcdefghijklmnopqrstuvwx "
        "AIzaSyA12345678901234567890123456789012345"
    )

    findings = detect_secrets(text)
    kinds = {finding.kind for finding in findings}

    assert "secret.github_token" in kinds
    assert "secret.slack_token" in kinds
    assert "secret.google_api_key" in kinds


def test_detects_high_entropy_unknown_secret():
    findings = detect_secrets("token q9W8e7R6t5Y4u3I2o1P0a9S8d7F6g5H4j3K2l1Z")
    assert any(finding.kind == "secret.high_entropy" for finding in findings)


def test_detects_more_common_provider_tokens():
    text = " ".join(
        [
            "sk_live_abcdefghijklmnopqrstuvwxyz123456",
            "AC0123456789abcdef0123456789abcdef",
            "twilio_auth_token=0123456789abcdef0123456789abcdef",
            "SG.abcdefghijklmnop.qrstuvwxyzABCDEFGHIJKLMN",
            "hf_abcdefghijklmnopqrstuvwxyz123456",
            "mfa.abcdefghijklmnopqrstuvwxyz123456",
            "secret_abcdefghijklmnopqrstuvwxyz123456",
            "DD_API_KEY=0123456789abcdef0123456789abcdef",
            "DD_APP_KEY=0123456789abcdef0123456789abcdef01234567",
            "atlasv1." + "A" * 60,
        ]
    )

    findings = detect_secrets(text)
    kinds = {finding.kind for finding in findings}

    assert "secret.stripe_key" in kinds
    assert "secret.twilio_sid" in kinds
    assert "secret.twilio_auth_token" in kinds
    assert "secret.sendgrid_api_key" in kinds
    assert "secret.huggingface_token" in kinds
    assert "secret.discord_bot_token" in kinds
    assert "secret.notion_token" in kinds
    assert "secret.datadog_api_key" in kinds
    assert "secret.datadog_app_key" in kinds
    assert "secret.terraform_cloud_token" in kinds
