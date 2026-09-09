#!/usr/bin/env bash
# Print identifier / title lines from BHGitOps/tfc_port_configuration.
# Usage: extract_identifiers.sh /path/to/tfc_port_configuration
set -euo pipefail

REPO="${1:-}"
if [[ -z "${REPO}" || ! -d "${REPO}" ]]; then
  echo "Usage: $0 /path/to/tfc_port_configuration" >&2
  exit 1
fi

FILES=(
  blueprints-terraform-cloud.tf
  blueprints-github.tf
  blueprints-jira.tf
  blueprints-aws.tf
  blueprint-self-service.tf
  ec2-action.tf
  s3-action.tf
  feedback.tf
  versions.tf
  providers.tf
)

echo "# Identifiers from ${REPO}"
echo
for rel in "${FILES[@]}"; do
  path="${REPO}/${rel}"
  echo "## ${rel}"
  if [[ ! -f "${path}" ]]; then
    echo "MISSING"
    echo
    continue
  fi
  grep -nE 'identifier|title|port_environment|PORT_BETA|string_props|conclusion|status|state' "${path}" \
    | head -n 80 || true
  echo
done

echo "## environments/*/ (port env mapping)"
for env in dev qa prod; do
  dir="${REPO}/environments/${env}"
  echo "### environments/${env}"
  if [[ ! -d "${dir}" ]]; then
    echo "MISSING"
    echo
    continue
  fi
  grep -nE 'port_environment|PORT_CLIENT|identifier|workspace' "${dir}"/*.tf 2>/dev/null | head -n 40 || true
  echo
done
