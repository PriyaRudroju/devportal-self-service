#!/usr/bin/env python3
"""Trigger Port S3 self-service workflow and verify GitHub dispatch."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

PORT_API_URL = os.environ.get("PORT_API_URL", "https://api.port.io").rstrip("/")
GITHUB_API = "https://api.github.com"
GITHUB_ORG = os.environ.get("GITHUB_ORG", "PriyaRudroju")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "devportal-self-service")
WORKFLOW_FILE = "provision-s3-bucket.yml"


def api_request(
    method: str,
    url: str,
    token: str | None,
    body: dict | None = None,
    *,
    github: bool = False,
) -> tuple[int, dict | list | str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if github:
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
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


def get_port_token() -> str:
    client_id = os.environ.get("PORT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("PORT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("PORT_CLIENT_ID and PORT_CLIENT_SECRET are required")
    status, body = api_request(
        "POST",
        f"{PORT_API_URL}/v1/auth/access_token",
        None,
        {"clientId": client_id, "clientSecret": client_secret},
    )
    if status != 200:
        raise RuntimeError(f"Port auth failed: {status} {body}")
    token = body.get("accessToken") if isinstance(body, dict) else None
    if not token:
        raise RuntimeError("Port auth response missing accessToken")
    return token


def trigger_port_workflow(token: str, bucket_name: str, git_ref: str) -> str:
    payload = {"inputs": {"bucket_name": bucket_name, "git_ref": git_ref}}
    status, body = api_request(
        "POST",
        f"{PORT_API_URL}/v1/workflows/provision_s3_request/runs",
        token,
        payload,
    )
    if status not in {200, 201}:
        raise RuntimeError(f"Port workflow trigger failed: {status} {body}")
    if not isinstance(body, dict):
        raise RuntimeError(f"Unexpected Port response: {body}")
    run_id = (
        body.get("workflowRun", {}).get("identifier")
        or body.get("run", {}).get("identifier")
        or body.get("identifier")
    )
    if not run_id:
        raise RuntimeError(f"Port response missing run id: {json.dumps(body)}")
    print(f"Port workflow run started: {run_id}")
    return run_id


def wait_for_port_run(token: str, run_id: str, timeout_sec: int = 180) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status, body = api_request("GET", f"{PORT_API_URL}/v1/workflows/runs/{run_id}", token)
        if status != 200 or not isinstance(body, dict):
            raise RuntimeError(f"Failed to fetch Port run: {status} {body}")
        run = body.get("workflowRun") or body
        run_status = run.get("status")
        run_result = run.get("result")
        print(f"Port run {run_id}: status={run_status} result={run_result}")
        if run_status in {"COMPLETED", "FAILED", "CANCELLED"}:
            node_runs = run.get("nodeRuns") or body.get("nodeRuns") or []
            if node_runs:
                print("Port node runs:")
                for node in node_runs:
                    print(json.dumps({
                        "identifier": node.get("identifier"),
                        "status": node.get("status"),
                        "result": node.get("result"),
                        "error": node.get("error"),
                    }, indent=2))
            return run
        time.sleep(5)
    raise RuntimeError(f"Timed out waiting for Port run {run_id}")


def list_github_runs(github_token: str, branch: str, created_after: str) -> list[dict]:
    url = (
        f"{GITHUB_API}/repos/{GITHUB_ORG}/{GITHUB_REPO}/actions/workflows/"
        f"{WORKFLOW_FILE}/runs?branch={urllib.parse.quote(branch, safe='')}"
        f"&created=>{created_after}&per_page=5"
    )
    status, body = api_request("GET", url, github_token, github=True)
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"GitHub runs query failed: {status} {body}")
    return body.get("workflow_runs") or []


def fetch_entity(token: str, blueprint: str, identifier: str) -> dict:
    status, body = api_request(
        "GET",
        f"{PORT_API_URL}/v1/blueprints/{blueprint}/entities/{identifier}",
        token,
    )
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"Failed to fetch entity {identifier}: {status} {body}")
    return body.get("entity") or body


def print_diagnostics(token: str, port_run_id: str) -> None:
    print("\n--- Diagnostics ---")
    try:
        entity = fetch_entity(token, "s3Bucket", port_run_id)
        props = entity.get("properties") or {}
        print(
            json.dumps(
                {
                    "entity_id": entity.get("identifier"),
                    "gitRef": props.get("gitRef"),
                    "environment": props.get("environment"),
                    "status": props.get("status"),
                    "bucketName": props.get("bucketName"),
                },
                indent=2,
            )
        )
        if props.get("status") != "ready":
            print(
                "WARN: entity status is not ready — automation expects pending → ready update",
                file=sys.stderr,
            )
    except Exception as exc:
        print(f"Entity lookup failed: {exc}")

    status, body = api_request("GET", f"{PORT_API_URL}/v1/actions/runs?limit=10", token)
    if status == 200 and isinstance(body, dict):
        runs = body.get("runs") or body.get("actionRuns") or []
        s3_runs = [
            run for run in runs
            if (run.get("action") or {}).get("identifier") == "trigger_github_on_s3_ready"
            or run.get("actionIdentifier") == "trigger_github_on_s3_ready"
        ]
        if s3_runs:
            print("Recent S3 automation runs:")
            for run in s3_runs[:3]:
                print(json.dumps({
                    "id": run.get("id") or run.get("identifier"),
                    "status": run.get("status"),
                    "statusLabel": run.get("statusLabel"),
                    "createdAt": run.get("createdAt"),
                }, indent=2))
            return
    print("No recent automation runs matched trigger_github_on_s3_ready in last 10 action runs")

def wait_for_github_run(
    github_token: str,
    branch: str,
    created_after: str,
    timeout_sec: int = 300,
) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        runs = list_github_runs(github_token, branch, created_after)
        if runs:
            run = runs[0]
            print(
                "GitHub run found: "
                f"id={run.get('id')} branch={run.get('head_branch')} "
                f"status={run.get('status')} conclusion={run.get('conclusion')} "
                f"url={run.get('html_url')}"
            )
            if run.get("status") == "completed":
                return run
        else:
            print(f"No GitHub runs yet on branch {branch}...")
        time.sleep(10)
    raise RuntimeError(f"No GitHub workflow run appeared on branch {branch} within {timeout_sec}s")


def main() -> int:
    git_ref = os.environ.get("GIT_REF", "feature/s3-git-ref-test")
    bucket_env = os.environ.get("BUCKET_NAME", "").strip()
    bucket_name = bucket_env or f"devportal-s3-e2e-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is required")

    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("=== S3 Port E2E test ===")
    print(f"bucket_name={bucket_name}")
    print(f"git_ref={git_ref}")
    print(f"started_at={started_at}")

    port_token = get_port_token()
    port_run_id = trigger_port_workflow(port_token, bucket_name, git_ref)
    port_run = wait_for_port_run(port_token, port_run_id)

    print("\n--- Port workflow result ---")
    print(json.dumps(
        {
            "run_id": port_run_id,
            "status": port_run.get("status"),
            "result": port_run.get("result"),
            "url": f"https://app.port.io/organization/run?runId={port_run_id}",
        },
        indent=2,
    ))

    if port_run.get("result") != "SUCCESS":
        node_runs = port_run.get("nodeRuns") or []
        failed_nodes = [
            n for n in node_runs
            if n.get("result") not in {None, "SUCCESS"} or n.get("status") in {"FAILED", "CANCELLED"}
        ]
        if failed_nodes:
            print("FAIL: Port workflow node(s) failed:", file=sys.stderr)
            for node in failed_nodes:
                print(
                    json.dumps(
                        {
                            "identifier": node.get("identifier"),
                            "title": node.get("title"),
                            "status": node.get("status"),
                            "result": node.get("result"),
                            "error": node.get("error"),
                        },
                        indent=2,
                    ),
                    file=sys.stderr,
                )
        else:
            print("FAIL: Port workflow did not succeed", file=sys.stderr)
        return 1

    print_diagnostics(port_token, port_run_id)

    try:
        github_run = wait_for_github_run(github_token, git_ref, started_at)
    except RuntimeError as exc:
        print_diagnostics(port_token, port_run_id)
        raise

    print("\n--- GitHub workflow result ---")
    print(json.dumps(
        {
            "id": github_run.get("id"),
            "branch": github_run.get("head_branch"),
            "status": github_run.get("status"),
            "conclusion": github_run.get("conclusion"),
            "url": github_run.get("html_url"),
            "event": github_run.get("event"),
        },
        indent=2,
    ))

    if github_run.get("head_branch") != git_ref:
        print(f"FAIL: GitHub ran on {github_run.get('head_branch')}, expected {git_ref}", file=sys.stderr)
        return 1

    if github_run.get("conclusion") not in {"success", None} and github_run.get("status") == "completed":
        print("WARN: GitHub workflow completed but Terraform may have failed — dispatch path succeeded")

    print("\nPASS: Port workflow succeeded and GitHub Provision S3 Bucket run started on correct branch")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
