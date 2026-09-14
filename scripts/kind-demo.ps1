param(
    [string]$Cluster = "ai-guard-demo",
    [string]$Image = "ai-guard:0.1.0"
)

$ErrorActionPreference = "Stop"

$clusters = kind get clusters
if ($clusters -notcontains $Cluster) {
    kind create cluster --name $Cluster
}

docker build -t $Image .
kind load docker-image $Image --name $Cluster

helm install `
    cert-manager oci://quay.io/jetstack/charts/cert-manager `
    --version v1.20.3 `
    --namespace cert-manager `
    --create-namespace `
    --set crds.enabled=true `
    --wait

helm upgrade --install ai-guard .\charts\ai-guard `
    --namespace ai-guard-system `
    --create-namespace `
    --set image.repository=ai-guard `
    --set image.tag=0.1.0

kubectl rollout status deployment/ai-guard -n ai-guard-system
kubectl label namespace default ai-guard.io/injection=enabled --overwrite
kubectl apply -f .\k8s\example-app.yaml
kubectl rollout status deployment/ai-guard-example-app

Write-Host "AI-Guard demo is running. Inspect the injected pod with:"
Write-Host "kubectl get pod -l app=ai-guard-example-app -o yaml"
