# Contributing

AI-Guard is focused on Kubernetes-native, zero-code LLM security auto-instrumentation. Contributions should preserve that core promise: install once in the cluster, then application teams opt in with an annotation.

## Development

```sh
python -m pip install pytest flask
python -m pytest
```

Build the image:

```sh
docker build -t ai-guard:0.1.0 .
```

Run a local Kind demo:

```sh
./scripts/kind-demo.sh
```

On Windows:

```powershell
.\scripts\kind-demo.ps1
```

## Pull Requests

- Keep changes scoped and add tests for mutation, detection, cache, or policy behavior.
- Do not log raw secrets, PII, prompts, or completions in new code.
- Keep application integration zero-code where possible.
- Prefer Kubernetes-native primitives over custom control-plane services.

## Good First Issues

- Add provider adapters for Anthropic, Bedrock, or LiteLLM.
- Add ConfigMap-backed policy loading.
- Add Prometheus ServiceMonitor support.
- Improve detector precision with labeled regression cases.
