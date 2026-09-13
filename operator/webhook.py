import base64
import json
import os
from pathlib import Path
from typing import Any

try:
    from flask import Flask, Response, jsonify, request
except ModuleNotFoundError:
    Flask = None
    Response = None
    jsonify = None
    request = None


ANNOTATION_ENABLED = "ai-guard.io/enabled"
AI_GUARD_IMAGE = os.getenv("AI_GUARD_IMAGE", "ai-guard:0.1.0")
AGENT_VOLUME_NAME = "ai-guard-volume"
INIT_CONTAINER_NAME = "ai-guard-init"
AGENT_MOUNT_PATH = "/opt/ai-guard"
INIT_MOUNT_PATH = "/shared"
WEBHOOK_METRICS = {
    "admission_reviews_total": 0,
    "pods_injected_total": 0,
    "patches_generated_total": 0,
}

class _LocalApp:
    def get(self, *_args, **_kwargs):
        return lambda fn: fn

    def post(self, *_args, **_kwargs):
        return lambda fn: fn

    def run(self, *_args, **_kwargs):
        raise RuntimeError("Flask is required to run the AI-Guard webhook server")


app = Flask(__name__) if Flask is not None else _LocalApp()


def _has_named(items: list[dict[str, Any]], name: str) -> bool:
    return any(item.get("name") == name for item in items)


def _agent_volume() -> dict[str, Any]:
    return {"name": AGENT_VOLUME_NAME, "emptyDir": {}}


def _init_container(image: str) -> dict[str, Any]:
    return {
        "name": INIT_CONTAINER_NAME,
        "image": image,
        "imagePullPolicy": "IfNotPresent",
        "command": [
            "sh",
            "-c",
            "mkdir -p /shared && cp -r /ai-guard/agent/. /shared/",
        ],
        "volumeMounts": [
            {
                "name": AGENT_VOLUME_NAME,
                "mountPath": INIT_MOUNT_PATH,
            }
        ],
        "securityContext": {
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
            "runAsUser": 0,
            "capabilities": {"drop": ["ALL"]},
        },
    }


def _agent_mount() -> dict[str, Any]:
    return {
        "name": AGENT_VOLUME_NAME,
        "mountPath": AGENT_MOUNT_PATH,
        "readOnly": True,
    }


def _env(name: str, value: str) -> dict[str, str]:
    return {"name": name, "value": value}


def _container_patch_path(container_index: int, field: str) -> str:
    return f"/spec/containers/{container_index}/{field}"


def _ensure_volume(pod: dict[str, Any], patches: list[dict[str, Any]]) -> None:
    spec = pod.setdefault("spec", {})
    volumes = spec.get("volumes")
    if volumes is None:
        patches.append({"op": "add", "path": "/spec/volumes", "value": [_agent_volume()]})
        return
    if not _has_named(volumes, AGENT_VOLUME_NAME):
        patches.append({"op": "add", "path": "/spec/volumes/-", "value": _agent_volume()})


def _ensure_init_container(
    pod: dict[str, Any], patches: list[dict[str, Any]], image: str
) -> None:
    spec = pod.setdefault("spec", {})
    init_containers = spec.get("initContainers")
    container = _init_container(image)
    if init_containers is None:
        patches.append(
            {"op": "add", "path": "/spec/initContainers", "value": [container]}
        )
        return
    if not _has_named(init_containers, INIT_CONTAINER_NAME):
        patches.append({"op": "add", "path": "/spec/initContainers/-", "value": container})


def _ensure_env(
    container: dict[str, Any],
    container_index: int,
    patches: list[dict[str, Any]],
) -> None:
    env = container.get("env")
    desired = [_env("AI_GUARD_ENABLED", "true")]

    if env is None:
        desired.append(_env("PYTHONPATH", AGENT_MOUNT_PATH))
        patches.append(
            {
                "op": "add",
                "path": _container_patch_path(container_index, "env"),
                "value": desired,
            }
        )
        return

    names = {item.get("name"): index for index, item in enumerate(env)}
    if "AI_GUARD_ENABLED" not in names:
        patches.append(
            {
                "op": "add",
                "path": f"{_container_patch_path(container_index, 'env')}/-",
                "value": _env("AI_GUARD_ENABLED", "true"),
            }
        )

    pythonpath_index = names.get("PYTHONPATH")
    if pythonpath_index is None:
        patches.append(
            {
                "op": "add",
                "path": f"{_container_patch_path(container_index, 'env')}/-",
                "value": _env("PYTHONPATH", AGENT_MOUNT_PATH),
            }
        )
        return

    pythonpath = env[pythonpath_index]
    existing_value = pythonpath.get("value")
    if existing_value is not None and AGENT_MOUNT_PATH not in existing_value.split(":"):
        patches.append(
            {
                "op": "replace",
                "path": (
                    f"{_container_patch_path(container_index, 'env')}/"
                    f"{pythonpath_index}/value"
                ),
                "value": f"{AGENT_MOUNT_PATH}:{existing_value}",
            }
        )


def _ensure_mount(
    container: dict[str, Any],
    container_index: int,
    patches: list[dict[str, Any]],
) -> None:
    mounts = container.get("volumeMounts")
    mount = _agent_mount()
    if mounts is None:
        patches.append(
            {
                "op": "add",
                "path": _container_patch_path(container_index, "volumeMounts"),
                "value": [mount],
            }
        )
        return

    if not any(
        item.get("name") == AGENT_VOLUME_NAME
        or item.get("mountPath") == AGENT_MOUNT_PATH
        for item in mounts
    ):
        patches.append(
            {
                "op": "add",
                "path": f"{_container_patch_path(container_index, 'volumeMounts')}/-",
                "value": mount,
            }
        )


def build_patches(pod: dict[str, Any], image: str = AI_GUARD_IMAGE) -> list[dict[str, Any]]:
    patches: list[dict[str, Any]] = []
    _ensure_volume(pod, patches)
    _ensure_init_container(pod, patches, image)

    for index, container in enumerate(pod.get("spec", {}).get("containers", [])):
        _ensure_mount(container, index, patches)
        _ensure_env(container, index, patches)

    return patches


def should_inject(pod: dict[str, Any]) -> bool:
    annotations = pod.get("metadata", {}).get("annotations", {}) or {}
    return annotations.get(ANNOTATION_ENABLED, "").lower() == "true"


def metrics_text() -> str:
    lines = [
        "# HELP ai_guard_admission_reviews_total AdmissionReview requests processed.",
        "# TYPE ai_guard_admission_reviews_total counter",
        f"ai_guard_admission_reviews_total {WEBHOOK_METRICS['admission_reviews_total']}",
        "# HELP ai_guard_pods_injected_total Pods selected for AI-Guard injection.",
        "# TYPE ai_guard_pods_injected_total counter",
        f"ai_guard_pods_injected_total {WEBHOOK_METRICS['pods_injected_total']}",
        "# HELP ai_guard_patches_generated_total JSONPatch operations generated.",
        "# TYPE ai_guard_patches_generated_total counter",
        f"ai_guard_patches_generated_total {WEBHOOK_METRICS['patches_generated_total']}",
    ]
    return "\n".join(lines) + "\n"


def admission_response(
    uid: str, allowed: bool = True, patches: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    response: dict[str, Any] = {"uid": uid, "allowed": allowed}
    if patches:
        response["patchType"] = "JSONPatch"
        response["patch"] = base64.b64encode(
            json.dumps(patches, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")
    return {"apiVersion": "admission.k8s.io/v1", "kind": "AdmissionReview", "response": response}


@app.get("/healthz")
def healthz():
    body = {"status": "ok"}
    return jsonify(body) if jsonify is not None else body


@app.get("/metrics")
def metrics():
    body = metrics_text()
    if Response is None:
        return body
    return Response(body, mimetype="text/plain; version=0.0.4")


@app.post("/mutate")
@app.post("/")
def mutate():
    if request is None or jsonify is None:
        raise RuntimeError("Flask is required to handle admission requests")
    WEBHOOK_METRICS["admission_reviews_total"] += 1
    admission = request.get_json(force=True, silent=False)
    request_obj = admission.get("request", {})
    uid = request_obj.get("uid", "")
    pod = request_obj.get("object", {})

    patches = build_patches(pod) if should_inject(pod) else []
    if patches:
        WEBHOOK_METRICS["pods_injected_total"] += 1
        WEBHOOK_METRICS["patches_generated_total"] += len(patches)
    return jsonify(admission_response(uid=uid, patches=patches))


def _ssl_context():
    cert_file = Path(os.getenv("TLS_CERT_FILE", "/tls/tls.crt"))
    key_file = Path(os.getenv("TLS_KEY_FILE", "/tls/tls.key"))
    if cert_file.exists() and key_file.exists():
        return str(cert_file), str(key_file)
    if os.getenv("AI_GUARD_ALLOW_INSECURE_HTTP", "").lower() == "true":
        return None
    raise RuntimeError(
        f"TLS certificate files not found at {cert_file} and {key_file}. "
        "Set AI_GUARD_ALLOW_INSECURE_HTTP=true only for local development."
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8443")), ssl_context=_ssl_context())
