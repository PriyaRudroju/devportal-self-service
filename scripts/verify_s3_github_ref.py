#!/usr/bin/env python3
"""Verify S3 GitHub dispatch uses diff.before.properties.gitRef (repo and live Port)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

S3_AUTOMATION_ID = "trigger_github_on_s3_ready"
S3_AUTOMATION_FILE = "trigger-github-on-s3-ready.json"
EXPECTED_REF = "{{ .event.diff.before.properties.gitRef }}"
EXPECTED_PORT_RUN_ID = "{{ .event.diff.before.properties.portRunId }}"
FORBIDDEN_REF = "{{ .event.diff.after.properties.gitRef }}"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_port_config import (  # noqa: E402
    build_variables,
    prepare_action_payload,
    substitute,
)


def get_port_token(api_url: str) -> str:
    client_id = os.environ.get("PORT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("PORT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("PORT_CLIENT_ID and PORT_CLIENT_SECRET are required for live checks")
    payload = json.dumps({"clientId": client_id, "clientSecret": client_secret}).encode("utf-8")
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/v1/auth/access_token",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    token = data.get("accessToken")
    if not token:
        raise RuntimeError("Port token response missing accessToken")
    return token


def api_get(url: str, token: str) -> tuple[int, dict | list | str]:
    request = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def normalize_template(value: str) -> str:
    """Collapse whitespace so Port API formatting differences still match."""
    return re.sub(r"\s+", "", value.strip())


def find_gitref_template(obj: object) -> str | None:
    """Find any template string referencing gitRef anywhere in Port action JSON."""
    if isinstance(obj, str) and "gitRef" in obj:
        return obj
    if isinstance(obj, dict):
        for value in obj.values():
            found = find_gitref_template(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_gitref_template(item)
            if found:
                return found
    return None


def extract_dispatch_ref(automation: dict) -> str | None:
    invocation = automation.get("invocationMethod") or {}
    props = invocation.get("integrationActionExecutionProperties") or {}
    ref = props.get("ref")
    if isinstance(ref, str) and ref.strip():
        return ref

    # Port API responses may hoist or nest dispatch fields differently.
    direct_ref = invocation.get("ref")
    if isinstance(direct_ref, str) and direct_ref.strip():
        return direct_ref

    workflow_inputs = props.get("workflowInputs") or invocation.get("workflowInputs") or {}
    nested_ref = workflow_inputs.get("ref")
    if isinstance(nested_ref, str) and nested_ref.strip():
        return nested_ref

    return find_gitref_template(automation)


def ref_uses_diff_before(ref: str) -> bool:
    normalized = normalize_template(ref)
    return "diff.before.properties.gitRef" in normalized


def ref_uses_diff_after(ref: str) -> bool:
    normalized = normalize_template(ref)
    return "diff.after.properties.gitRef" in normalized


def load_repo_automation(repo_root: Path) -> dict:
    config_path = repo_root / "port" / "environments" / "config.env"
    variables = build_variables(config_path)
    automation_path = repo_root / "port" / "environments" / "automations" / S3_AUTOMATION_FILE
    raw = automation_path.read_text(encoding="utf-8")
    rendered = substitute(raw, variables)
    payload = json.loads(rendered)
    return prepare_action_payload(payload, variables)


def extract_workflow_inputs(automation: dict) -> dict:
    invocation = automation.get("invocationMethod") or {}
    props = invocation.get("integrationActionExecutionProperties") or {}
    inputs = props.get("workflowInputs") or {}
    return inputs if isinstance(inputs, dict) else {}


def verify_port_run_id(inputs: dict, *, label: str) -> list[str]:
    errors: list[str] = []
    port_run_id = inputs.get("port_run_id")
    if not isinstance(port_run_id, str) or not port_run_id.strip():
        errors.append(f"{label}: missing port_run_id in workflowInputs")
        return errors
    normalized = normalize_template(port_run_id)
    if "diff.before.properties.portRunId" not in normalized and "context.entityIdentifier" not in normalized:
        errors.append(
            f"{label}: port_run_id is {port_run_id!r}, expected diff.before.properties.portRunId "
            "or context.entityIdentifier"
        )
    return errors


def verify_ref(ref: str | None, *, label: str) -> list[str]:
    errors: list[str] = []
    if not ref:
        errors.append(f"{label}: missing top-level ref in integrationActionExecutionProperties")
        return errors
    if ref_uses_diff_after(ref):
        errors.append(
            f"{label}: ref still uses diff.after.properties.gitRef — "
            "GitHub defaults to main when gitRef is omitted from diff.after on status-only updates"
        )
    elif not ref_uses_diff_before(ref):
        errors.append(
            f"{label}: ref is {ref!r}, expected a template containing diff.before.properties.gitRef"
        )
    return errors


def fetch_live_automation(api_url: str, token: str) -> dict:
    status, body = api_get(f"{api_url.rstrip('/')}/v1/actions/{S3_AUTOMATION_ID}", token)
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"Failed to fetch live automation: {status} {body}")
    return body.get("action") or body


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify S3 automation GitHub dispatch branch ref")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--check-live", action="store_true", help="Fetch automation from Port API")
    parser.add_argument("--api-url", default=os.environ.get("PORT_API_URL", "https://api.port.io"))
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    repo_automation = load_repo_automation(repo_root)
    repo_ref = extract_dispatch_ref(repo_automation)
    repo_inputs = extract_workflow_inputs(repo_automation)

    print("=== S3 GitHub ref verification ===")
    print(f"Repo automation ref: {repo_ref!r}")
    print(f"Repo automation port_run_id: {repo_inputs.get('port_run_id')!r}")

    errors = verify_ref(repo_ref, label="repo")
    errors.extend(verify_port_run_id(repo_inputs, label="repo"))
    if not errors:
        print("OK   repo automation ref template is correct")

    if args.check_live:
        token = get_port_token(args.api_url)
        live_automation = fetch_live_automation(args.api_url, token)
        live_ref = extract_dispatch_ref(live_automation)
        live_inputs = extract_workflow_inputs(live_automation)
        print(f"Live automation ref: {live_ref!r}")
        print(f"Live automation port_run_id: {live_inputs.get('port_run_id')!r}")
        if live_ref is None:
            invocation = live_automation.get("invocationMethod") or {}
            print(
                "DEBUG live invocationMethod:",
                json.dumps(invocation, indent=2),
                file=sys.stderr,
            )
        errors.extend(verify_ref(live_ref, label="live Port"))
        errors.extend(verify_port_run_id(live_inputs, label="live Port"))
        if not errors:
            print("OK   live Port automation matches expected ref template")
        elif live_ref != repo_ref:
            print(
                "HINT: re-apply Port config: python scripts/apply_port_config.py --env dev --resources automations",
                file=sys.stderr,
            )

    if errors:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
        return 1

    print("PASS S3 automation will dispatch provision-s3-bucket.yml using diff.before.properties.gitRef")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
