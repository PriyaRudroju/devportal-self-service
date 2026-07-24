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
    "GITHUB_ORG",
    "GITHUB_REPO",
    "AWS_REGION",
    "TFC_WORKSPACE",
}

ALL_RESOURCES = ("blueprints", "actions", "automations", "workflows")


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


def build_variables(config_path: Path) -> dict[str, str]:
    """Load config.env first, then allow environment variable overrides."""
    variables = load_config(config_path)
    for key in ENV_OVERRIDE_KEYS:
        env_value = os.environ.get(key)
        if env_value:
            variables[key] = env_value
    return variables


def substitute(content: str, variables: dict[str, str]) -> str:
    result = content
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def find_unresolved_placeholders(content: str) -> list[str]:
    issues: list[str] = []
    for match in PLACEHOLDER_PATTERN.finditer(content):
        issues.append(f"unreplaced placeholder: {{{{{match.group(1)}}}}}")
    for match in REPLACE_LITERAL_PATTERN.finditer(content):
        issues.append(f"unreplaced literal: {match.group(0)}")
    return issues


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
) -> None:
    for file_path in sorted(files):
        raw = file_path.read_text(encoding="utf-8")
        rendered = substitute(raw, variables)
        issues = find_unresolved_placeholders(rendered)
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
    args = parser.parse_args()

    plan_mode = args.dry_run or args.plan
    try:
        selected_resources = parse_resources(args.resources)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    repo_root = Path(args.repo_root)
    env_root = repo_root / "port" / "environments" / args.env
    config_path = env_root / "config.env"
    variables = build_variables(config_path)

    client_id = os.environ.get("PORT_CLIENT_ID", "")
    client_secret = os.environ.get("PORT_CLIENT_SECRET", "")
    api_url = os.environ.get("PORT_API_URL", "https://api.port.io").rstrip("/")

    if not plan_mode and (not client_id or not client_secret):
        print("PORT_CLIENT_ID and PORT_CLIENT_SECRET are required", file=sys.stderr)
        sys.exit(1)

    print(f"{'Planning' if plan_mode else 'Applying'} Port config for environment: {args.env}")
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
            collect_json_files(repo_root / "port" / "blueprints"),
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
        apply_json_files(
            api_url,
            token,
            "workflow",
            "/v1/workflows",
            "/v1/workflows/{identifier}",
            collect_json_files(env_root / "workflows"),
            variables,
            plan_mode,
        )

    print("Port config apply completed successfully")


if __name__ == "__main__":
    main()
