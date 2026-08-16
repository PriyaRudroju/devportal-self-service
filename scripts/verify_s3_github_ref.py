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
S3_REQUEST_WORKFLOW_ID = "provision_s3_request"
S3_REQUEST_WORKFLOW_FILE = "provision-s3-request.json"
EXPECTED_REF = "{{ .event.diff.before.properties.gitRef }}"
EXPECTED_WORKFLOW_REF = "{{ .outputs.trigger.git_ref }}"
EXPECTED_PORT_RUN_ID = "{{ .event.diff.before.properties.portRunId }}"
FORBIDDEN_REF = "{{ .event.diff.after.properties.gitRef }}"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_port_config import (  # noqa: E402
    build_variables,
    prepare_action_payload,
    prepare_workflow_payload,
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


def load_repo_request_workflow(repo_root: Path) -> dict:
    config_path = repo_root / "port" / "environments" / "config.env"
    variables = build_variables(config_path)
    workflow_path = repo_root / "port" / "environments" / "workflows" / S3_REQUEST_WORKFLOW_FILE
    raw = workflow_path.read_text(encoding="utf-8")
    rendered = substitute(raw, variables)
    payload = json.loads(rendered)
    return prepare_workflow_payload(payload, variables)


def find_dispatch_github_node(workflow: dict) -> dict | None:
    for node in workflow.get("nodes") or []:
        if isinstance(node, dict) and node.get("identifier") == "dispatch_github":
            return node
    return None


def extract_workflow_dispatch_props(workflow: dict) -> tuple[str | None, dict, str]:
    """Return (ref, workflow inputs, url) for the request workflow dispatch node.

    Legacy Port orgs reject GitHub INTEGRATION_ACTION nodes inside workflows, so the
    node dispatches through the GitHub REST API with a WEBHOOK instead.
    """
    node = find_dispatch_github_node(workflow)
    if not node:
        return None, {}, ""
    config = node.get("config") or {}
    url = config.get("url") or ""

    body = config.get("body") if isinstance(config.get("body"), dict) else {}
    if body:
        inputs = body.get("inputs") if isinstance(body.get("inputs"), dict) else {}
        return body.get("ref"), inputs, url

    props = config.get("integrationActionExecutionProperties") or {}
    inputs = props.get("workflowInputs") or {}
    return props.get("ref"), inputs if isinstance(inputs, dict) else {}, url


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


def verify_request_workflow_dispatch(
    ref: str | None,
    inputs: dict,
    url: str,
    *,
    label: str,
) -> list[str]:
    errors: list[str] = []
    if not ref:
        errors.append(f"{label}: missing dispatch ref on dispatch_github")
        return errors
    if "ref" in inputs:
        errors.append(f"{label}: ref must not be one of the GitHub workflow inputs")
    normalized = normalize_template(ref)
    if "outputs.trigger.git_ref" not in normalized:
        errors.append(
            f"{label}: dispatch_github ref is {ref!r}, expected {EXPECTED_WORKFLOW_REF}"
        )
    port_run_id = inputs.get("port_run_id")
    if not isinstance(port_run_id, str) or not port_run_id.strip():
        errors.append(f"{label}: missing port_run_id in dispatch_github inputs")
    if url and "/actions/workflows/provision-s3-bucket.yml/dispatches" not in url:
        errors.append(
            f"{label}: dispatch_github url is {url!r}, expected the provision-s3-bucket.yml dispatches endpoint"
        )
    if "{{" in url and ".outputs." in url:
        errors.append(
            f"{label}: dispatch_github url contains a runtime template; Port rejects templated webhook URLs at apply time"
        )
    return errors


def fetch_live_automation(api_url: str, token: str) -> dict:
    status, body = api_get(f"{api_url.rstrip('/')}/v1/actions/{S3_AUTOMATION_ID}", token)
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"Failed to fetch live automation: {status} {body}")
    return body.get("action") or body


def fetch_live_request_workflow(api_url: str, token: str) -> dict:
    status, body = api_get(f"{api_url.rstrip('/')}/v1/workflows/{S3_REQUEST_WORKFLOW_ID}", token)
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"Failed to fetch live request workflow: {status} {body}")
    return body.get("workflow") or body


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify S3 GitHub dispatch branch ref")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--check-live", action="store_true", help="Fetch automation and workflow from Port API")
    parser.add_argument("--api-url", default=os.environ.get("PORT_API_URL", "https://api.port.io"))
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    repo_automation = load_repo_automation(repo_root)
    repo_ref = extract_dispatch_ref(repo_automation)
    repo_inputs = extract_workflow_inputs(repo_automation)
    repo_workflow = load_repo_request_workflow(repo_root)
    repo_wf_ref, repo_wf_inputs, repo_wf_url = extract_workflow_dispatch_props(repo_workflow)

    print("=== S3 GitHub ref verification ===")
    print(f"Repo automation ref: {repo_ref!r}")
    print(f"Repo automation port_run_id: {repo_inputs.get('port_run_id')!r}")
    print(f"Repo request workflow dispatch_github ref: {repo_wf_ref!r}")

    errors = verify_ref(repo_ref, label="repo automation")
    errors.extend(verify_port_run_id(repo_inputs, label="repo automation"))
    errors.extend(
        verify_request_workflow_dispatch(
            repo_wf_ref, repo_wf_inputs, repo_wf_url, label="repo request workflow"
        )
    )
    if not errors:
        print("OK   repo automation and request workflow dispatch refs are correct")

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
        errors.extend(verify_ref(live_ref, label="live Port automation"))
        errors.extend(verify_port_run_id(live_inputs, label="live Port automation"))

        live_workflow = fetch_live_request_workflow(args.api_url, token)
        live_wf_ref, live_wf_inputs, live_wf_url = extract_workflow_dispatch_props(live_workflow)
        print(f"Live request workflow dispatch_github ref: {live_wf_ref!r}")
        errors.extend(
            verify_request_workflow_dispatch(
                live_wf_ref, live_wf_inputs, live_wf_url, label="live Port request workflow"
            )
        )
        if not errors:
            print("OK   live Port automation and request workflow match expected ref templates")
        elif live_ref != repo_ref or live_wf_ref != repo_wf_ref:
            print(
                "HINT: re-apply Port config: python scripts/apply_port_config.py --env dev "
                "--resources automations,workflows",
                file=sys.stderr,
            )

    if errors:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
        return 1

    print(
        "PASS S3 request workflow Trigger GitHub node dispatches provision-s3-bucket.yml "
        "using trigger.git_ref"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
