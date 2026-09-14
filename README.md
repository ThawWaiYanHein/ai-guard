# AI-Guard

Kubernetes-native zero-code LLM security auto-instrumentation.

AI-Guard is for platform teams that want OpenTelemetry-style auto-instrumentation for LLM security. Install AI-Guard once in a Kubernetes cluster, then application teams opt in with one annotation:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-apps
  labels:
    ai-guard.io/injection: enabled
```

```yaml
spec:
  template:
    metadata:
      annotations:
        ai-guard.io/enabled: "true"
```

No application code changes. No app image rebuild. No sidecar. By default, AI-Guard only receives admission requests for namespaces labeled `ai-guard.io/injection=enabled`.

## Why This Exists

Most LLM guardrail libraries require developers to edit application code. AI-Guard takes a different path: it uses a Kubernetes mutating admission webhook to inject a Python agent into annotated Pods, then `sitecustomize.py` patches provider SDK calls at runtime.

This project is not trying to beat every guardrail framework at detection quality. The goal is to make LLM security easy to roll out across Kubernetes workloads.

## What It Does

- Injects an init container, shared volume, volume mount, and environment variables into annotated Pods.
- Loads a Python agent automatically with `sitecustomize.py`.
- Intercepts provider SDK calls:
  - `client.chat.completions.create()`
  - `await client.chat.completions.create()`
  - `client.responses.create()`
  - `await client.responses.create()`
  - `client.models.generate_content()` for Gemini-style SDK usage
  - `client.messages.create()` for Anthropic-style SDK usage
  - `litellm.completion()` and `litellm.acompletion()`
- Redacts common PII and secrets before requests leave the workload.
- Observes prompt-injection patterns.
- Supports an exact in-memory development cache.
- Emits JSON audit logs and Prometheus-style webhook metrics.

## Architecture

```text
Application Deployment
  |
  | ai-guard.io/enabled=true
  v
Kubernetes Mutating Admission Webhook
  |
  | AdmissionReview v1 + JSONPatch
  v
Pod with ai-guard-init + emptyDir + env + PYTHONPATH
  |
  v
Python startup imports /opt/ai-guard/sitecustomize.py
  |
  v
AI-Guard patches provider SDK methods
  |
  v
PII -> secrets -> prompt-injection observe -> redaction -> exact cache -> provider SDK
```

## Quickstart With Kind

Prerequisites:

- Docker
- Kind
- kubectl
- Helm

```sh
./scripts/kind-demo.sh
```

On Windows PowerShell:

```powershell
.\scripts\kind-demo.ps1
```

The demo builds the image, creates or reuses a Kind cluster, loads the image, installs AI-Guard with Helm, deploys the example app, and waits for rollout.

Verify injection:

```sh
kubectl label namespace default ai-guard.io/injection=enabled
kubectl get pod -l app=ai-guard-example-app -o yaml
```

Look for:

- `ai-guard-init`
- `ai-guard-volume`
- `/opt/ai-guard`
- `AI_GUARD_ENABLED=true`
- `PYTHONPATH=/opt/ai-guard`

## One-Command Install

Install with one command:

```sh
curl -fsSL https://raw.githubusercontent.com/ThawWaiYanHein/ai-guard/main/scripts/install.sh | sh
```

On Windows PowerShell:

```powershell
iwr -useb https://raw.githubusercontent.com/ThawWaiYanHein/ai-guard/main/scripts/install.ps1 | iex
```

The installer checks for cert-manager, installs it if needed, installs AI-Guard with Helm, and waits for rollout.

By default, the chart uses:

```text
ghcr.io/thawwaiyanhein/ai-guard:0.1.0
```

For local image development, override the image:

```sh
IMAGE_REPOSITORY=ai-guard IMAGE_TAG=0.1.0 ./scripts/install.sh
```

For local chart development:

```sh
./scripts/install.sh
```

On Windows:

```powershell
.\scripts\install.ps1
```

## Manual Install

Build the image:

```sh
docker build -t ai-guard:0.1.0 .
```

For Kind:

```sh
kind load docker-image ai-guard:0.1.0
```

For Minikube:

```sh
minikube image load ai-guard:0.1.0
```

Install cert-manager. AI-Guard uses cert-manager to create the webhook serving certificate and inject the webhook CA bundle, which is the same style of operational setup used by many Kubernetes webhook-based operators:

```sh
helm install \
  cert-manager oci://quay.io/jetstack/charts/cert-manager \
  --version v1.20.3 \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true
```

Install AI-Guard:

```sh
helm upgrade --install ai-guard ./charts/ai-guard \
  --namespace ai-guard-system \
  --create-namespace
```

Deploy the sample app:

```sh
kubectl label namespace default ai-guard.io/injection=enabled
kubectl apply -f k8s/example-app.yaml
```

## Raw Manifest Install

If you do not want Helm:

```sh
./scripts/generate-webhook-certs.sh
kubectl apply -f k8s/ai-guard-operator.rendered.yaml
```

On Windows:

```powershell
.\scripts\generate-webhook-certs.ps1
kubectl apply -f k8s\ai-guard-operator.rendered.yaml
```

## Manual TLS Fallback

If you do not want cert-manager, you can still generate Helm TLS values manually:

```sh
./scripts/generate-helm-tls-values.sh
helm upgrade --install ai-guard ./charts/ai-guard \
  --namespace ai-guard-system \
  --create-namespace \
  --set tls.certManager.enabled=false \
  -f charts/ai-guard/tls-values.generated.yaml
```

## Configuration

Application containers can override these variables:

| Variable | Default | Description |
| --- | --- | --- |
| `AI_GUARD_ENABLED` | `true` | Enables `sitecustomize.py` instrumentation. |
| `AI_GUARD_MODE` | `enforce` | Enforces blocking policies. |
| `AI_GUARD_CACHE` | `false` | Enables development memory cache when set to `true`. |
| `AI_GUARD_CACHE_TTL` | `600` | Cache TTL in seconds. |
| `AI_GUARD_POLICY` | `default` | Reserved for future policy profile loading. |
| `AI_GUARD_PII` | `on` | Enables PII detection/redaction. Set to `off` to skip PII handling. |
| `AI_GUARD_PII_TYPES` | `all` | Comma-separated PII types such as `email,phone,ssn`. |
| `AI_GUARD_PHONE_COUNTRIES` | `US,MM,INTL` | Phone detector country profiles. |
| `AI_GUARD_ALLOWLIST` | empty | Comma-separated exact values to skip. |
| `AI_GUARD_IGNORE_PATTERNS` | empty | Comma-separated regex/literal patterns to skip. |
| `AI_GUARD_ENTROPY_SECRETS` | `true` | Enables high-entropy unknown secret detection. |
| `AI_GUARD_PROMPT_INJECTION_ACTION` | `OBSERVE` | Action for high-confidence prompt injection: `OBSERVE` or `BLOCK`. |
| `AI_GUARD_PRESIDIO` | `false` | Enables optional Presidio analysis when Presidio is installed. |

Cluster-wide defaults can be set through Helm. For example, disable PII redaction for newly created instrumented Pods:

```sh
helm upgrade ai-guard ./charts/ai-guard \
  -n ai-guard-system \
  --reuse-values \
  --set agent.pii=off
```

Applications can still override the injected default by setting `AI_GUARD_PII` themselves.

Enable the optional development cache cluster-wide:

```sh
helm upgrade ai-guard ./charts/ai-guard \
  -n ai-guard-system \
  --reuse-values \
  --set agent.cache=true
```

Applications can still override the injected default by setting `AI_GUARD_CACHE` themselves.

## Default Policy

- PII: redact email, phone, credit card, IP address, SSN, passport number, address, and conservative name patterns.
- Secrets: redact OpenAI, AWS, GitHub, Slack, Google, Azure, Stripe, Twilio, SendGrid, Hugging Face, Discord, Notion, Datadog, Terraform Cloud, JWT, bearer token, private key, and high-entropy unknown secrets.
- Prompt injection: observe low/medium patterns and observe or block high-confidence patterns depending on `AI_GUARD_PROMPT_INJECTION_ACTION`.

The default policy is intentionally conservative for an MVP: redact obvious sensitive data, log what happened, and avoid pretending regex detection is complete DLP.

AI-Guard emits structured redaction reports with finding type, severity, action, location, and a short fingerprint. It does not log raw secret or PII values by default.

## Provider Support

AI-Guard currently patches these Python SDK paths on a best-effort basis:

| Provider | Supported calls |
| --- | --- |
| OpenAI | `client.responses.create()`, `client.chat.completions.create()` |
| Gemini | `client.models.generate_content()` |
| Anthropic | `client.messages.create()` |
| LiteLLM | `litellm.completion()`, `litellm.acompletion()` |

Sync and async resource classes are patched when the installed provider SDK exposes them. If an SDK changes internal resource class names, AI-Guard may need an adapter update.

## Cache Behavior

AI-Guard uses a SHA-256 exact cache key over response-shaping request fields such as model, messages/input, instructions, temperature, token limits, tools, response format, reasoning, `top_p`, seed, and stop sequences.

AI-Guard does not cache:

- streaming requests
- tool calls
- conversation state
- `previous_response_id`

The current memory cache is disabled by default and is for development only. Enable it explicitly with `AI_GUARD_CACHE=true`.

## Observability

Agent logs are JSON:

```json
{"timestamp":"2026-09-12T00:00:00+00:00","namespace":"default","application":"app","model":"gpt-4.1-mini","action":"redacted","reason":"responses request inspected"}
```

Webhook metrics are exposed at:

```text
GET /metrics
```

Current metrics:

- `ai_guard_admission_reviews_total`
- `ai_guard_pods_injected_total`
- `ai_guard_patches_generated_total`

## Testing

```sh
python -m pip install pytest flask
python -m pytest
```

The suite covers webhook JSONPatch generation, PII/secret redaction, policy blocking, metrics formatting, and cache behavior.

## Project Status

AI-Guard is an early open-source MVP. It is useful for demos, experimentation, and design feedback. Do not treat it as production DLP or a complete LLM security platform yet.

Production hardening roadmap:

- published container images and hosted Helm repository
- ConfigMap or CRD policy management
- pinned image digests
- Prometheus ServiceMonitor
- Redis cache backend with production-safe encryption/eviction controls
- Bedrock, LangChain, and LlamaIndex adapters
- optional output scanning with observe-first semantics
- e2e Kind tests in CI

## How This Differs From Guardrail Libraries

Projects like LLM Guard, NeMo Guardrails, and Guardrails AI are libraries/frameworks that developers integrate into application code. AI-Guard is a Kubernetes delivery mechanism for zero-code runtime protection.

The long-term opportunity is to integrate with strong guardrail engines while keeping the deployment model simple:

```text
Install once in Kubernetes.
Add one annotation.
Protect LLM calls automatically.
```

## License

MIT

