#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for devportal-self-service.
#
# The application code is Python standard-library only (Port config tooling in
# scripts/, the Teams-approval Lambda in lambda/), so there are no Python
# packages to install. This script installs the Terraform toolchain used by the
# terraform/ IaC and pre-warms module providers so `terraform validate` works
# without network on later runs. Safe to run repeatedly.
set -euo pipefail

TERRAFORM_VERSION="1.9.8"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Python =="
python3 --version

echo "== Terraform =="
if command -v terraform >/dev/null 2>&1 && terraform version | grep -q "v${TERRAFORM_VERSION}"; then
  echo "terraform v${TERRAFORM_VERSION} already installed"
else
  tmp="$(mktemp -d)"
  url="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
  echo "Downloading ${url}"
  curl -fsSL -o "${tmp}/terraform.zip" "${url}"
  (cd "${tmp}" && unzip -o -q terraform.zip)
  sudo install -m 0755 "${tmp}/terraform" /usr/local/bin/terraform
  rm -rf "${tmp}"
fi
terraform version

echo "== Pre-warm Terraform module providers (best-effort) =="
for module in "${REPO_ROOT}"/terraform/modules/*/; do
  [ -d "${module}" ] || continue
  echo "-- init ${module}"
  if ! (cd "${module}" && terraform init -backend=false -input=false -no-color >/dev/null); then
    echo "WARN: provider init failed for ${module} (continuing)"
  fi
done

echo "Install complete."
