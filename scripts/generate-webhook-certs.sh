#!/usr/bin/env sh
set -eu

NAMESPACE="${NAMESPACE:-ai-guard-system}"
SERVICE="${SERVICE:-ai-guard-webhook}"
SECRET="${SECRET:-ai-guard-webhook-tls}"
MANIFEST="${MANIFEST:-k8s/ai-guard-operator.yaml}"
OUT="${OUT:-k8s/ai-guard-operator.rendered.yaml}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cat > "$TMP_DIR/ca.cnf" <<EOF
[req]
distinguished_name=req
x509_extensions=v3_ca
prompt=no
[req_distinguished_name]
CN=AI Guard Webhook CA
[v3_ca]
basicConstraints=critical,CA:TRUE
keyUsage=critical,keyCertSign,cRLSign
EOF

cat > "$TMP_DIR/server.cnf" <<EOF
[req]
distinguished_name=req
req_extensions=v3_req
prompt=no
[req_distinguished_name]
CN=${SERVICE}.${NAMESPACE}.svc
[v3_req]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names
[alt_names]
DNS.1=${SERVICE}
DNS.2=${SERVICE}.${NAMESPACE}
DNS.3=${SERVICE}.${NAMESPACE}.svc
DNS.4=${SERVICE}.${NAMESPACE}.svc.cluster.local
EOF

openssl genrsa -out "$TMP_DIR/ca.key" 2048
openssl req -x509 -new -nodes -key "$TMP_DIR/ca.key" -days 3650 -out "$TMP_DIR/ca.crt" -config "$TMP_DIR/ca.cnf"
openssl genrsa -out "$TMP_DIR/tls.key" 2048
openssl req -new -key "$TMP_DIR/tls.key" -out "$TMP_DIR/tls.csr" -config "$TMP_DIR/server.cnf"
openssl x509 -req -in "$TMP_DIR/tls.csr" -CA "$TMP_DIR/ca.crt" -CAkey "$TMP_DIR/ca.key" -CAcreateserial -out "$TMP_DIR/tls.crt" -days 365 -extensions v3_req -extfile "$TMP_DIR/server.cnf"

CA_BUNDLE="$(base64 < "$TMP_DIR/ca.crt" | tr -d '\n')"
TLS_CRT="$(base64 < "$TMP_DIR/tls.crt" | tr -d '\n')"
TLS_KEY="$(base64 < "$TMP_DIR/tls.key" | tr -d '\n')"
sed \
  -e "s|\${CA_BUNDLE}|${CA_BUNDLE}|g" \
  -e "s|\${TLS_CRT}|${TLS_CRT}|g" \
  -e "s|\${TLS_KEY}|${TLS_KEY}|g" \
  "$MANIFEST" > "$OUT"
echo "Rendered $OUT with CA bundle and TLS secret data for $NAMESPACE/$SECRET"
