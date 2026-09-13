#!/usr/bin/env sh
set -eu

RELEASE_NAME="${RELEASE_NAME:-ai-guard}"
NAMESPACE="${NAMESPACE:-ai-guard-system}"
CHART="${CHART:-./charts/ai-guard}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-ghcr.io/thawwaiyanhein/ai-guard}"
IMAGE_TAG="${IMAGE_TAG:-0.1.0}"
CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.20.3}"
CERT_MANAGER_NAMESPACE="${CERT_MANAGER_NAMESPACE:-cert-manager}"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: $1 is required" >&2
    exit 1
  fi
}

need kubectl
need helm

echo "Installing AI-Guard prerequisites..."

if kubectl get crd certificates.cert-manager.io >/dev/null 2>&1 &&
   kubectl get deployment cert-manager -n "$CERT_MANAGER_NAMESPACE" >/dev/null 2>&1; then
  echo "cert-manager is already installed."
else
  echo "Installing cert-manager $CERT_MANAGER_VERSION..."
  helm upgrade --install \
    cert-manager oci://quay.io/jetstack/charts/cert-manager \
    --version "$CERT_MANAGER_VERSION" \
    --namespace "$CERT_MANAGER_NAMESPACE" \
    --create-namespace \
    --set crds.enabled=true \
    --wait
fi

echo "Installing AI-Guard..."
helm upgrade --install "$RELEASE_NAME" "$CHART" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --set image.repository="$IMAGE_REPOSITORY" \
  --set image.tag="$IMAGE_TAG" \
  --wait

kubectl rollout status "deployment/$RELEASE_NAME" -n "$NAMESPACE"

cat <<EOF
AI-Guard is installed.

Enable an app by adding this Pod template annotation:

  ai-guard.io/enabled: "true"

Example:

  spec:
    template:
      metadata:
        annotations:
          ai-guard.io/enabled: "true"
EOF
