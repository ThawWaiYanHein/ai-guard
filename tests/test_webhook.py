import base64
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEBHOOK_PATH = ROOT / "operator" / "webhook.py"


def load_webhook():
    spec = importlib.util.spec_from_file_location("ai_guard_webhook", WEBHOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_patches_handles_empty_pod_spec():
    webhook = load_webhook()
    pod = {
        "metadata": {"annotations": {"ai-guard.io/enabled": "true"}},
        "spec": {"containers": [{"name": "app", "image": "app:v1"}]},
    }

    patches = webhook.build_patches(pod, "ai-guard:test")
    paths = [patch["path"] for patch in patches]

    assert "/spec/initContainers" in paths
    assert "/spec/volumes" in paths
    assert "/spec/containers/0/env" in paths
    assert "/spec/containers/0/volumeMounts" in paths


def test_build_patches_appends_to_existing_collections_and_preserves_pythonpath():
    webhook = load_webhook()
    pod = {
        "metadata": {"annotations": {"ai-guard.io/enabled": "true"}},
        "spec": {
            "initContainers": [{"name": "existing-init", "image": "busybox"}],
            "volumes": [{"name": "data", "emptyDir": {}}],
            "containers": [
                {
                    "name": "app",
                    "image": "app:v1",
                    "env": [{"name": "PYTHONPATH", "value": "/app"}],
                    "volumeMounts": [{"name": "data", "mountPath": "/data"}],
                }
            ],
        },
    }

    patches = webhook.build_patches(pod, "ai-guard:test")
    assert {"op": "add", "path": "/spec/initContainers/-", "value": webhook._init_container("ai-guard:test")} in patches
    assert any(patch["path"] == "/spec/volumes/-" for patch in patches)
    assert any(patch["path"] == "/spec/containers/0/env/-" for patch in patches)
    assert any(
        patch["op"] == "replace"
        and patch["path"] == "/spec/containers/0/env/0/value"
        and patch["value"] == "/opt/ai-guard:/app"
        for patch in patches
    )
    assert any(patch["path"] == "/spec/containers/0/volumeMounts/-" for patch in patches)


def test_admission_response_encodes_json_patch():
    webhook = load_webhook()
    response = webhook.admission_response("uid-1", patches=[{"op": "add", "path": "/x", "value": 1}])

    decoded = json.loads(base64.b64decode(response["response"]["patch"]).decode("utf-8"))
    assert response["apiVersion"] == "admission.k8s.io/v1"
    assert response["response"]["patchType"] == "JSONPatch"
    assert decoded == [{"op": "add", "path": "/x", "value": 1}]


def test_metrics_text_is_prometheus_compatible():
    webhook = load_webhook()
    text = webhook.metrics_text()

    assert "ai_guard_admission_reviews_total" in text
    assert "ai_guard_pods_injected_total" in text
    assert "ai_guard_patches_generated_total" in text
