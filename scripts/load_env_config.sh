#!/usr/bin/env bash
# Load port/environments/<env>/config.env into the current shell.
# Usage: source scripts/load_env_config.sh dev
set -euo pipefail

ENV_NAME="${1:-dev}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${REPO_ROOT}/port/environments/${ENV_NAME}/config.env"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Config file not found: ${CONFIG_FILE}" >&2
  return 1 2>/dev/null || exit 1
fi

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" || "$line" == \#* ]] && continue
  [[ "$line" != *"="* ]] && continue
  key="${line%%=*}"
  value="${line#*=}"
  key="$(echo "$key" | xargs)"
  # Do not override variables already set in the environment (GitHub vars win).
  if [[ -z "${!key:-}" ]]; then
    export "${key}=${value}"
  fi
done < "${CONFIG_FILE}"

echo "Loaded config from ${CONFIG_FILE}"
