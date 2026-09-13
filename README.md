# AI-Guard

Kubernetes-native zero-code LLM security auto-instrumentation.

AI-Guard is for platform teams that want OpenTelemetry-style auto-instrumentation for LLM security. Install AI-Guard once in a Kubernetes cluster, then application teams opt in with one annotation:

```yaml
spec:
  template:
    metadata:
      annotations:
        ai-guard.io/enabled: "true"
```

No application code changes. No app image rebuild. No sidecar.

## Why This Exists

Most LLM guardrail libraries require developers to edit application code. AI-Guard takes a different path: it uses a Kubernetes mutating admission webhook to inject a Python agent into annotated Pods, then `sitecustomize.py` patches OpenAI SDK calls at runtime.

This project is not trying to beat every guardrail framework at detection quality. The goal is to make LLM security easy to roll out across Kubernetes workloads.

## What It Does

- Injects an init container, shared volume, volume mount, and environment variables into annotated Pods.
- Loads a Python agent automatically with `sitecustomize.py`.
- Intercepts OpenAI Python SDK calls:
  - `client.chat.completions.create()`
  - `await client.chat.completions.create()`
  - `client.responses.create()`
  - `await client.responses.create()`
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
AI-Guard patches OpenAI SDK create() methods
  |
  v
PII -> secrets -> prompt-injection observe -> redaction -> exact cache -> OpenAI
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
kubectl get pod -l app=ai-guard-example-app -o yaml
```

Look for:

- `ai-guard-init`
- `ai-guard-volume`
- `/opt/ai-guard`
- `AI_GUARD_ENABLED=true`
- `PYTHONPATH=/opt/ai-guard`

## One-Command Install

For a published release, users should install with one command:

```sh
curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_ORG/ai-guard/main/scripts/install.sh | sh
```

On Windows PowerShell:

```powershell
iwr -useb https://raw.githubusercontent.com/YOUR_GITHUB_ORG/ai-guard/main/scripts/install.ps1 | iex
```

The installer checks for cert-manager, installs it if needed, installs AI-Guard with Helm, and waits for rollout.

Until you publish a container image, local users can run:

```sh
IMAGE_REPOSITORY=ai-guard IMAGE_TAG=0.1.0 ./scripts/install.sh
```

After publishing an image, users can pin it:

```sh
curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_ORG/ai-guard/main/scripts/install.sh | \
  IMAGE_REPOSITORY=ghcr.io/YOUR_GITHUB_ORG/ai-guard IMAGE_TAG=0.1.0 sh
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
| `AI_GUARD_CACHE` | `true` | Enables development memory cache. |
| `AI_GUARD_CACHE_TTL` | `600` | Cache TTL in seconds. |
| `AI_GUARD_POLICY` | `default` | Reserved for future policy profile loading. |

## Default Policy

- PII: redact email, phone, credit card, and IP address.
- Secrets: redact OpenAI API keys, AWS keys, JWTs, bearer tokens, and private keys.
- Prompt injection: observe only.

The default policy is intentionally conservative for an MVP: redact obvious sensitive data, log what happened, and avoid pretending regex detection is complete DLP.

## Cache Behavior

AI-Guard uses a SHA-256 exact cache key over response-shaping request fields such as model, messages/input, instructions, temperature, token limits, tools, response format, reasoning, `top_p`, seed, and stop sequences.

AI-Guard does not cache:

- streaming requests
- tool calls
- conversation state
- `previous_response_id`

The current memory cache is for development only.

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
- Redis cache backend or cache-off production profile
- output scanning
- Anthropic, Bedrock, LiteLLM, and LangChain adapters
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
