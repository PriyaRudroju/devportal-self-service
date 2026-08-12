#!/usr/bin/env python3
"""Apply Port blueprints, actions, automations, and workflows from Git to Port API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
REPLACE_LITERAL_PATTERN = re.compile(r"REPLACE_[A-Z0-9_]+")

ENV_OVERRIDE_KEYS = {
    "API_GATEWAY_URL",
    "GITHUB_INSTALLATION_ID",
    "LEGACY_GITHUB_INSTALLATION_ID",
    "GITHUB_ORG",
    "GITHUB_REPO",
    "AWS_REGION",
    "TFC_WORKSPACE",
    "GIT_REF_DEFAULT",
    "FEATURE_GIT_REFS",
}

ALL_RESOURCES = ("blueprints", "actions", "automations", "workflows")
GITHUB_MODES = ("legacy", "ocean")
# Ocean-only workflows skipped in legacy mode (Sunset app). Mixed workflows may include github-ocean nodes.
LEGACY_SKIP_WORKFLOW_FILES = frozenset({"provision-ec2-after-approval.json"})


def load_config(config_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not config_path.is_file():
        return values
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def build_git_ref_enum(variables: dict[str, str]) -> str:
    """Build JSON array for Port form git branch enum from config.env."""
    default_ref = (
        os.environ.get("GIT_REF_DEFAULT")
        or variables.get("GIT_REF_DEFAULT")
        or variables.get("GITHUB_WORKFLOW_REF")
        or "dev"
    ).strip()
    feature_refs_raw = os.environ.get("FEATURE_GIT_REFS", variables.get("FEATURE_GIT_REFS", ""))
    refs: list[str] = []
    if default_ref:
        refs.append(default_ref)
    for part in feature_refs_raw.split(","):
        ref = part.strip()
        if ref and ref not in refs:
            refs.append(ref)
    if not refs:
        refs.append("dev")
    return json.dumps(refs)


def build_variables(config_path: Path) -> dict[str, str]:
    """Load config.env first, then allow environment variable overrides."""
    variables = load_config(config_path)
    for key in ENV_OVERRIDE_KEYS:
        env_value = os.environ.get(key)
        if env_value:
            variables[key] = env_value
    variables["GIT_REF_ENUM"] = build_git_ref_enum(variables)
    if not variables.get("GIT_REF_DEFAULT"):
        variables["GIT_REF_DEFAULT"] = (
            os.environ.get("GIT_REF_DEFAULT")
            or variables.get("GITHUB_WORKFLOW_REF")
            or "dev"
        )
    return variables


def substitute(content: str, variables: dict[str, str]) -> str:
    result = content
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def find_unresolved_placeholders(content: str, *, require_installation_id: bool = True) -> list[str]:
    issues: list[str] = []
    for match in PLACEHOLDER_PATTERN.finditer(content):
        placeholder = match.group(1)
        if not require_installation_id and placeholder == "GITHUB_INSTALLATION_ID":
            continue
        issues.append(f"unreplaced placeholder: {{{{{placeholder}}}}}")
    for match in REPLACE_LITERAL_PATTERN.finditer(content):
        if not require_installation_id and "GITHUB" in match.group(0) and "INSTALLATION" in match.group(0):
            continue
        issues.append(f"unreplaced literal: {match.group(0)}")
    return issues


def resolve_github_mode(config: dict[str, str], cli_mode: str | None) -> str:
    if cli_mode:
        return cli_mode
    env_mode = os.environ.get("GITHUB_INTEGRATION_MODE", "").strip().lower()
    if env_mode in GITHUB_MODES:
        return env_mode
    config_mode = config.get("GITHUB_INTEGRATION_MODE", "legacy").strip().lower()
    return config_mode if config_mode in GITHUB_MODES else "legacy"


def filter_workflow_files(files: list[Path], github_mode: str) -> list[Path]:
    if github_mode == "ocean":
        return files

    filtered: list[Path] = []
    for file_path in files:
        if file_path.name in LEGACY_SKIP_WORKFLOW_FILES:
            identifier = file_path.stem
            try:
                identifier = json.loads(file_path.read_text(encoding="utf-8")).get("identifier", identifier)
            except json.JSONDecodeError:
                pass
            print(f"SKIP workflow (legacy mode): {identifier} ({file_path.name})")
            continue
        filtered.append(file_path)
    return filtered


def resolve_installation_id(variables: dict[str, str]) -> str:
    for key in ("GITHUB_INSTALLATION_ID", "LEGACY_GITHUB_INSTALLATION_ID"):
        value = variables.get(key, "").strip()
        if value:
            return value
    return os.environ.get("GITHUB_INSTALLATION_ID", "").strip()


def prepare_integration_automation_payload(payload: dict, variables: dict[str, str]) -> dict:
    """Hoist GitHub dispatch ref to top-level execution properties for legacy Sunset app."""
    invocation = payload.get("invocationMethod")
    if not isinstance(invocation, dict):
        return payload
    if invocation.get("type") != "INTEGRATION_ACTION":
        return payload
    if invocation.get("integrationActionType") != "dispatch_workflow":
        return payload

    props = dict(invocation.get("integrationActionExecutionProperties") or {})
    workflow_inputs = dict(props.get("workflowInputs") or {})

    ref = props.get("ref") or workflow_inputs.pop("ref", None)
    workflow_inputs.pop("ref", None)
    if not isinstance(ref, str) or not ref.strip():
        ref = (
            variables.get("GITHUB_WORKFLOW_REF")
            or variables.get("GIT_REF_DEFAULT")
            or "dev"
        )

    props["ref"] = ref
    props["workflowInputs"] = workflow_inputs
    invocation["integrationActionExecutionProperties"] = props
    payload["invocationMethod"] = invocation
    return payload


def prepare_action_payload(payload: dict, variables: dict[str, str]) -> dict:
    """Normalize GitHub backends for Port API (hosted GitHub rejects org/repo on type GITHUB)."""
    invocation = payload.get("invocationMethod")
    if not isinstance(invocation, dict):
        return payload

    inv_type = invocation.get("type")
    if inv_type == "INTEGRATION_ACTION":
        return prepare_integration_automation_payload(payload, variables)

    if inv_type != "GITHUB":
        return payload

    workflow_inputs = dict(invocation.get("workflowInputs") or {})
    ref = invocation.pop("ref", None)
    org = invocation.pop("org", None) or variables.get("GITHUB_ORG", "")
    repo = invocation.pop("repo", None) or variables.get("GITHUB_REPO", "")
    workflow = invocation.get("workflow")
    report_status = invocation.get("reportWorkflowStatus", True)

    if ref and "ref" in workflow_inputs:
        workflow_inputs.pop("ref")
    if not ref or (isinstance(ref, str) and not ref.strip()):
        ref = variables.get("GITHUB_WORKFLOW_REF") or variables.get("GIT_REF_DEFAULT") or "dev"

    installation_id = resolve_installation_id(variables)
    if installation_id:
        payload["invocationMethod"] = {
            "type": "INTEGRATION_ACTION",
            "installationId": installation_id,
            "integrationActionType": "dispatch_workflow",
            "integrationActionExecutionProperties": {
                "org": org,
                "repo": repo,
                "workflow": workflow,
                "ref": ref,
                "reportWorkflowStatus": report_status,
                "workflowInputs": workflow_inputs,
            },
        }
        return payload

    payload["invocationMethod"] = {
        "type": "GITHUB",
        "workflow": workflow,
        "reportWorkflowStatus": report_status,
        "workflowInputs": workflow_inputs,
    }
    return payload


def get_access_token(api_url: str, client_id: str, client_secret: str) -> str:
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


def format_api_error(status: int, body: dict | list | str) -> str:
    if isinstance(body, dict):
        message = body.get("message") or body.get("error") or body.get("ok") or body
        return f"{status} {message}"
    return f"{status} {body}"


def api_request(
    method: str,
    url: str,
    token: str,
    body: dict | None = None,
) -> tuple[int, dict | list | str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return response.status, {}
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def update_resource(
    api_url: str,
    token: str,
    resource_label: str,
    update_path_template: str,
    identifier: str,
    payload: dict,
) -> tuple[bool, str]:
    update_url = f"{api_url}{update_path_template.format(identifier=identifier)}"

    for method in ("PUT", "PATCH"):
        update_status, update_body = api_request(method, update_url, token, payload)
        if update_status in {200, 201, 204}:
            return True, f"OK   {resource_label} updated ({method}): {identifier}"
        if update_status == 405 and method == "PUT":
            continue
        return False, f"FAIL {resource_label} update {identifier}: {format_api_error(update_status, update_body)}"

    return False, f"FAIL {resource_label} update {identifier}: PUT/PATCH not supported"


def apply_json_files(
    api_url: str,
    token: str,
    resource_label: str,
    create_path: str,
    update_path_template: str,
    files: list[Path],
    variables: dict[str, str],
    plan_mode: bool,
    *,
    require_installation_id: bool = True,
) -> None:
    for file_path in sorted(files):
        raw = file_path.read_text(encoding="utf-8")
        rendered = substitute(raw, variables)
        issues = find_unresolved_placeholders(
            rendered,
            require_installation_id=require_installation_id,
        )
        if issues:
            print(f"FAIL {file_path}:", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
            sys.exit(1)

        try:
            payload = json.loads(rendered)
        except json.JSONDecodeError as exc:
            print(f"FAIL {file_path}: invalid JSON ({exc})", file=sys.stderr)
            sys.exit(1)

        if resource_label in {"action", "automation"}:
            payload = prepare_action_payload(payload, variables)

        identifier = payload.get("identifier")
        if not identifier:
            print(f"SKIP {file_path}: missing identifier", file=sys.stderr)
            continue

        if plan_mode:
            print(f"PLAN {resource_label}: {identifier} ({file_path.name})")
            continue

        create_status, create_body = api_request("POST", f"{api_url}{create_path}", token, payload)
        if create_status in {200, 201}:
            print(f"OK   {resource_label} created/upserted: {identifier}")
            continue

        if create_status == 409:
            ok, message = update_resource(
                api_url,
                token,
                resource_label,
                update_path_template,
                identifier,
                payload,
            )
            print(message)
            if not ok:
                print(message, file=sys.stderr)
                sys.exit(1)
            continue

        print(
            f"FAIL {resource_label} create {identifier}: {format_api_error(create_status, create_body)}",
            file=sys.stderr,
        )
        sys.exit(1)


def collect_json_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.json"))


def parse_resources(raw: str | None) -> set[str]:
    if not raw:
        return set(ALL_RESOURCES)
    selected = {part.strip().lower() for part in raw.split(",") if part.strip()}
    unknown = selected - set(ALL_RESOURCES)
    if unknown:
        raise ValueError(f"Unknown resources: {', '.join(sorted(unknown))}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Port configuration from Git")
    parser.add_argument("--env", required=True, choices=["dev", "qa", "prod"])
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--dry-run", action="store_true", help="Validate and list resources without calling Port")
    parser.add_argument("--plan", action="store_true", help="Alias for --dry-run")
    parser.add_argument(
        "--resources",
        help="Comma-separated resource types: blueprints,actions,automations,workflows",
    )
    parser.add_argument("--skip-legacy", action="store_true", help="Skip legacy actions/automations")
    parser.add_argument(
        "--github-mode",
        choices=GITHUB_MODES,
        help="GitHub integration mode: legacy (Sunset) skips github-ocean workflows",
    )
    args = parser.parse_args()

    plan_mode = args.dry_run or args.plan
    try:
        selected_resources = parse_resources(args.resources)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    repo_root = Path(args.repo_root)
    env_root = repo_root / "port" / "environments"
    config_path = env_root / "config.env"
    config_values = load_config(config_path)
    port_env = config_values.get("PORT_ENV", "").strip().lower()
    if port_env and port_env != args.env:
        print(
            f"FAIL: --env {args.env} does not match PORT_ENV={port_env} in {config_path}",
            file=sys.stderr,
        )
        sys.exit(1)
    if not port_env:
        print(f"WARNING: PORT_ENV not set in {config_path}", file=sys.stderr)
    variables = build_variables(config_path)
    github_mode = resolve_github_mode(config_values, args.github_mode)
    require_installation_id = github_mode == "ocean"

    client_id = os.environ.get("PORT_CLIENT_ID", "")
    client_secret = os.environ.get("PORT_CLIENT_SECRET", "")
    api_url = os.environ.get("PORT_API_URL", "https://api.port.io").rstrip("/")

    if not plan_mode and (not client_id or not client_secret):
        print("PORT_CLIENT_ID and PORT_CLIENT_SECRET are required", file=sys.stderr)
        sys.exit(1)

    print(f"{'Planning' if plan_mode else 'Applying'} Port config for environment: {args.env}")
    print(f"GitHub integration mode: {github_mode}")
    if config_path.is_file():
        print(f"Loaded defaults from {config_path} (env vars override when set)")
    else:
        print(f"WARNING: missing config file {config_path}", file=sys.stderr)

    token = "plan-mode-token" if plan_mode else get_access_token(api_url, client_id, client_secret)

    if "blueprints" in selected_resources:
        apply_json_files(
            api_url,
            token,
            "blueprint",
            "/v1/blueprints",
            "/v1/blueprints/{identifier}",
            collect_json_files(repo_root / "port" / "resources"),
            variables,
            plan_mode,
        )

    if not args.skip_legacy:
        if "actions" in selected_resources:
            apply_json_files(
                api_url,
                token,
                "action",
                "/v1/actions",
                "/v1/actions/{identifier}",
                collect_json_files(env_root / "actions"),
                variables,
                plan_mode,
            )

        if "automations" in selected_resources:
            apply_json_files(
                api_url,
                token,
                "automation",
                "/v1/actions",
                "/v1/actions/{identifier}",
                collect_json_files(env_root / "automations"),
                variables,
                plan_mode,
            )

    if "workflows" in selected_resources:
        workflow_files = filter_workflow_files(
            collect_json_files(env_root / "workflows"),
            github_mode,
        )
        apply_json_files(
            api_url,
            token,
            "workflow",
            "/v1/workflows",
            "/v1/workflows/{identifier}",
            workflow_files,
            variables,
            plan_mode,
            require_installation_id=require_installation_id,
        )

    print("Port config apply completed successfully")


if __name__ == "__main__":
    main()
