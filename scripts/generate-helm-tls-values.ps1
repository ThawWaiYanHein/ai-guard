param(
    [string]$Namespace = "ai-guard-system",
    [string]$Service = "ai-guard-webhook",
    [string]$Out = "charts/ai-guard/tls-values.generated.yaml"
)

$ErrorActionPreference = "Stop"
$tmp = New-Item -ItemType Directory -Path ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "ai-guard-helm-certs-" + [guid]::NewGuid()))

try {
    $caCnf = @"
[req]
distinguished_name=req_distinguished_name
x509_extensions=v3_ca
prompt=no
[req_distinguished_name]
CN=AI Guard Webhook CA
[v3_ca]
basicConstraints=critical,CA:TRUE
keyUsage=critical,keyCertSign,cRLSign
"@
    $serverCnf = @"
[req]
distinguished_name=req_distinguished_name
req_extensions=v3_req
prompt=no
[req_distinguished_name]
CN=$Service.$Namespace.svc
[v3_req]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names
[alt_names]
DNS.1=$Service
DNS.2=$Service.$Namespace
DNS.3=$Service.$Namespace.svc
DNS.4=$Service.$Namespace.svc.cluster.local
"@

    $caCnfPath = Join-Path $tmp "ca.cnf"
    $serverCnfPath = Join-Path $tmp "server.cnf"
    Set-Content -LiteralPath $caCnfPath -Value $caCnf
    Set-Content -LiteralPath $serverCnfPath -Value $serverCnf

    openssl genrsa -out (Join-Path $tmp "ca.key") 2048
    openssl req -x509 -new -nodes -key (Join-Path $tmp "ca.key") -days 3650 -out (Join-Path $tmp "ca.crt") -config $caCnfPath
    openssl genrsa -out (Join-Path $tmp "tls.key") 2048
    openssl req -new -key (Join-Path $tmp "tls.key") -out (Join-Path $tmp "tls.csr") -config $serverCnfPath
    openssl x509 -req -in (Join-Path $tmp "tls.csr") -CA (Join-Path $tmp "ca.crt") -CAkey (Join-Path $tmp "ca.key") -CAcreateserial -out (Join-Path $tmp "tls.crt") -days 365 -extensions v3_req -extfile $serverCnfPath

    $outDir = Split-Path -Parent $Out
    if ($outDir) {
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    }

    $tlsCrt = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $tmp "tls.crt")))
    $tlsKey = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $tmp "tls.key")))
    $caBundle = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $tmp "ca.crt")))

    @"
tls:
  crt: "$tlsCrt"
  key: "$tlsKey"
  caBundle: "$caBundle"
"@ | Set-Content -LiteralPath $Out

    Write-Host "Rendered $Out for service $Service in namespace $Namespace"
}
finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force
}
