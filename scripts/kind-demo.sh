#!/usr/bin/env sh
set -eu

CLUSTER="${CLUSTER:-ai-guard-demo}"
IMAGE="${IMAGE:-ai-guard:0.1.0}"

if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER"
fi

docker build -t "$IMAGE" .
kind load docker-image "$IMAGE" --name "$CLUSTER"

helm install \
  cert-manager oci://quay.io/jetstack/charts/cert-manager \
  --version v1.20.3 \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true \
  --wait

helm upgrade --install ai-guard ./charts/ai-guard \
  --namespace ai-guard-system \
  --create-namespace \
  --set image.repository=ai-guard \
  --set image.tag=0.1.0

kubectl rollout status deployment/ai-guard -n ai-guard-system
kubectl apply -f k8s/example-app.yaml
kubectl rollout status deployment/ai-guard-example-app

echo "AI-Guard demo is running. Inspect the injected pod with:"
echo "kubectl get pod -l app=ai-guard-example-app -o yaml"
