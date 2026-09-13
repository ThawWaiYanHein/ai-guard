# Security Policy

AI-Guard is an early MVP. Treat it as experimental until your own review, threat model, and tests say otherwise.

## Reporting Vulnerabilities

Please report security issues privately through your repository's GitHub Security Advisory flow. If that is not configured yet, create a private contact method before announcing the project broadly.

Do not open public issues for vulnerabilities that expose secrets, bypass policies, or weaken webhook admission behavior.

## Current Security Posture

- The webhook runs over HTTPS and uses Kubernetes AdmissionReview v1.
- The default agent policy redacts PII and secrets before OpenAI SDK requests are sent.
- Prompt injection is observe-only by default.
- The memory cache is intended for development, not production multi-replica deployments.
- Regex detectors are useful guardrails, not complete DLP.

## Production Hardening Checklist

- Use pinned image digests.
- Use cert-manager or an equivalent certificate rotation strategy.
- Scope admission to trusted namespaces.
- Add ConfigMap or CRD policy management with validation.
- Send audit logs to a tamper-resistant sink.
- Disable or replace memory cache for sensitive production workloads.
