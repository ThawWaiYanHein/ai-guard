param(
    [string]$ReleaseName = $env:RELEASE_NAME,
    [string]$Namespace = $env:NAMESPACE,
    [string]$Chart = $env:CHART,
    [string]$ChartVersion = $env:CHART_VERSION,
    [string]$ImageRepository = $env:IMAGE_REPOSITORY,
    [string]$ImageTag = $env:IMAGE_TAG,
    [string]$CertManagerVersion = $env:CERT_MANAGER_VERSION,
    [string]$CertManagerNamespace = $env:CERT_MANAGER_NAMESPACE
)

$ErrorActionPreference = "Stop"

if (-not $ReleaseName) { $ReleaseName = "ai-guard" }
if (-not $Namespace) { $Namespace = "ai-guard-system" }
if (-not $Chart) { $Chart = "oci://ghcr.io/thawwaiyanhein/charts/ai-guard" }
if (-not $ChartVersion) { $ChartVersion = "0.1.0" }
if (-not $ImageRepository) { $ImageRepository = "ghcr.io/thawwaiyanhein/ai-guard" }
if (-not $ImageTag) { $ImageTag = "0.1.0" }
if (-not $CertManagerVersion) { $CertManagerVersion = "v1.20.3" }
if (-not $CertManagerNamespace) { $CertManagerNamespace = "cert-manager" }

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required"
    }
}

Require-Command kubectl
Require-Command helm

Write-Host "Installing AI-Guard prerequisites..."

$hasCertManagerCrd = $false
$hasCertManagerDeployment = $false

try {
    kubectl get crd certificates.cert-manager.io | Out-Null
    $hasCertManagerCrd = $true
}
catch {
    $hasCertManagerCrd = $false
}

try {
    kubectl get deployment cert-manager -n $CertManagerNamespace | Out-Null
    $hasCertManagerDeployment = $true
}
catch {
    $hasCertManagerDeployment = $false
}

if ($hasCertManagerCrd -and $hasCertManagerDeployment) {
    Write-Host "cert-manager is already installed."
}
else {
    Write-Host "Installing cert-manager $CertManagerVersion..."
    helm upgrade --install `
        cert-manager oci://quay.io/jetstack/charts/cert-manager `
        --version $CertManagerVersion `
        --namespace $CertManagerNamespace `
        --create-namespace `
        --set crds.enabled=true `
        --wait
}

Write-Host "Installing AI-Guard..."
if ($Chart -like "oci://*") {
    helm upgrade --install $ReleaseName $Chart `
        --version $ChartVersion `
        --namespace $Namespace `
        --create-namespace `
        --set image.repository=$ImageRepository `
        --set image.tag=$ImageTag `
        --wait
}
else {
    helm upgrade --install $ReleaseName $Chart `
        --namespace $Namespace `
        --create-namespace `
        --set image.repository=$ImageRepository `
        --set image.tag=$ImageTag `
        --wait
}

kubectl rollout status "deployment/$ReleaseName" -n $Namespace

Write-Host "AI-Guard is installed."
Write-Host ""
Write-Host "Enable an app by adding this Pod template annotation:"
Write-Host ""
Write-Host '  ai-guard.io/enabled: "true"'
