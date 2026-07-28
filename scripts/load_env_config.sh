#!/usr/bin/env bash
# Load port/environments/config.env into the current shell.
# Usage: source scripts/load_env_config.sh [dev|qa|prod]
# When an env name is passed, it must match PORT_ENV in config.env.
set -euo pipefail

ENV_NAME="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${REPO_ROOT}/port/environments/config.env"

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
  if [[ -z "${!key:-}" ]]; then
    export "${key}=${value}"
  fi
done < "${CONFIG_FILE}"

if [[ -n "${ENV_NAME}" && -n "${PORT_ENV:-}" && "${ENV_NAME}" != "${PORT_ENV}" ]]; then
  echo "FAIL: requested env '${ENV_NAME}' does not match PORT_ENV='${PORT_ENV}' in ${CONFIG_FILE}" >&2
  return 1 2>/dev/null || exit 1
fi

echo "Loaded config from ${CONFIG_FILE} (PORT_ENV=${PORT_ENV:-unknown})"
