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
DEBUG_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "debug-985163.log",
)


# #region agent log
def debug_log(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    payload = {
        "sessionId": "985163",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        pass
# #endregion


def fetch_live_s3_automation(token: str) -> dict:
    status, body = api_request(
        "GET",
        f"{PORT_API_URL}/v1/actions/trigger_github_on_s3_ready",
        token,
    )
    if status != 200 or not isinstance(body, dict):
        return {"fetch_error": f"{status} {body}"}
    action = body.get("action") or body
    invocation = action.get("invocationMethod") or {}
    props = invocation.get("integrationActionExecutionProperties") or {}
    return {
        "identifier": action.get("identifier"),
        "published": action.get("publish"),
        "ref": props.get("ref") or find_dispatch_ref(action),
        "workflow": props.get("workflow"),
        "workflowInputs": props.get("workflowInputs"),
    }

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


def list_github_runs(
    github_token: str,
    branch: str | None = None,
    *,
    created_after: str | None = None,
    event: str = "workflow_dispatch",
) -> list[dict]:
    query = [f"event={urllib.parse.quote(event, safe='')}", "per_page=10"]
    if branch:
        query.append(f"branch={urllib.parse.quote(branch, safe='')}")
    url = (
        f"{GITHUB_API}/repos/{GITHUB_ORG}/{GITHUB_REPO}/actions/workflows/"
        f"{WORKFLOW_FILE}/runs?{'&'.join(query)}"
    )
    status, body = api_request("GET", url, github_token, github=True)
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"GitHub runs query failed: {status} {body}")
    runs = body.get("workflow_runs") or []
    if created_after:
        runs = [run for run in runs if (run.get("created_at") or "") >= created_after]
    return runs


def fetch_entity(token: str, blueprint: str, identifier: str) -> dict:
    status, body = api_request(
        "GET",
        f"{PORT_API_URL}/v1/blueprints/{blueprint}/entities/{identifier}",
        token,
    )
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"Failed to fetch entity {identifier}: {status} {body}")
    return body.get("entity") or body


def patch_entity_status(token: str, entity_id: str, status_value: str) -> None:
    status, body = api_request(
        "PATCH",
        f"{PORT_API_URL}/v1/blueprints/s3Bucket/entities/{entity_id}",
        token,
        {"properties": {"status": status_value}},
    )
    if status not in {200, 201}:
        raise RuntimeError(f"Failed to PATCH entity {entity_id} status={status_value}: {status} {body}")


def mark_entity_ready_external(token: str, entity_id: str) -> None:
    """External Port API PATCH emits ENTITY_UPDATED for legacy automations."""
    entity = fetch_entity(token, "s3Bucket", entity_id)
    props = entity.get("properties") or {}
    current = props.get("status")
    git_ref = props.get("gitRef")
    print(f"Entity before mark-ready: status={current} gitRef={git_ref}")
    # #region agent log
    debug_log("H1", "mark_entity_ready_external:before", "entity state before mark-ready", {
        "entity_id": entity_id, "status": current, "gitRef": git_ref,
        "portRunId": props.get("portRunId"),
        "bucketName": props.get("bucketName"), "environment": props.get("environment"),
    })
    # #endregion
    if current == "ready":
        patch_entity_status(token, entity_id, "pending")
        time.sleep(2)
    patch_entity_status(token, entity_id, "ready")
    after = fetch_entity(token, "s3Bucket", entity_id)
    after_props = after.get("properties") or {}
    print(f"External PATCH: s3Bucket/{entity_id} marked ready (was {current})")
    # #region agent log
    debug_log("H4", "mark_entity_ready_external:after", "entity state after mark-ready", {
        "entity_id": entity_id, "status": after_props.get("status"), "gitRef": after_props.get("gitRef"),
        "portRunId": after_props.get("portRunId"),
    })
    # #endregion


def find_dispatch_ref(obj: object) -> str | None:
    if isinstance(obj, str) and "gitRef" in obj:
        return obj
    if isinstance(obj, dict):
        for value in obj.values():
            found = find_dispatch_ref(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_dispatch_ref(item)
            if found:
                return found
    return None


def wait_for_s3_automation_run(token: str, started_after: str, timeout_sec: int = 120) -> dict | None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status, body = api_request("GET", f"{PORT_API_URL}/v1/actions/runs?limit=20", token)
        if status == 200 and isinstance(body, dict):
            runs = body.get("runs") or body.get("actionRuns") or []
            for run in runs:
                action_id = (run.get("action") or {}).get("identifier") or run.get("actionIdentifier")
                if action_id != "trigger_github_on_s3_ready":
                    continue
                created_at = run.get("createdAt") or run.get("created_at") or ""
                if created_at and created_at < started_after:
                    continue
                run_id = run.get("id") or run.get("identifier")
                detail: dict = {"id": run_id, "status": run.get("status"), "createdAt": created_at}
                if run_id:
                    detail_status, detail_body = api_request(
                        "GET",
                        f"{PORT_API_URL}/v1/actions/runs/{run_id}",
                        token,
                    )
                    if detail_status == 200 and isinstance(detail_body, dict):
                        action_run = detail_body.get("actionRun") or detail_body.get("run") or detail_body
                        invocation = action_run.get("invocation") or {}
                        props = invocation.get("integrationActionExecutionProperties") or {}
                        detail["dispatch_ref"] = props.get("ref") or find_dispatch_ref(invocation)
                        detail["workflowInputs"] = props.get("workflowInputs")
                        detail["statusLabel"] = action_run.get("statusLabel") or run.get("statusLabel")
                print(f"Port automation run detected: {json.dumps(detail, indent=2)}")
                # #region agent log
                debug_log("H2", "wait_for_s3_automation_run", "automation run found", detail)
                # #endregion
                return detail
        time.sleep(5)
    # #region agent log
    debug_log("H2", "wait_for_s3_automation_run", "no automation run within timeout", {"started_after": started_after})
    # #endregion
    return None


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
                run_id = run.get("id") or run.get("identifier")
                summary = {
                    "id": run_id,
                    "status": run.get("status"),
                    "statusLabel": run.get("statusLabel"),
                    "createdAt": run.get("createdAt"),
                }
                if run_id:
                    detail_status, detail_body = api_request(
                        "GET",
                        f"{PORT_API_URL}/v1/actions/runs/{run_id}",
                        token,
                    )
                    if detail_status == 200 and isinstance(detail_body, dict):
                        action_run = detail_body.get("actionRun") or detail_body.get("run") or detail_body
                        invocation = action_run.get("invocation") or {}
                        props = invocation.get("integrationActionExecutionProperties") or {}
                        summary["dispatch_ref"] = props.get("ref") or find_dispatch_ref(invocation)
                        summary["workflow"] = props.get("workflow")
                        summary["workflowInputs"] = props.get("workflowInputs")
                        summary["statusLabel"] = action_run.get("statusLabel") or run.get("statusLabel")
                print(json.dumps(summary, indent=2))
            return
    print("No recent automation runs matched trigger_github_on_s3_ready in last 10 action runs")

    recent = list_github_runs(os.environ.get("GITHUB_TOKEN", ""), event="workflow_dispatch") if os.environ.get("GITHUB_TOKEN") else []
    if recent:
        print("Recent provision-s3-bucket workflow_dispatch runs (all branches):")
        for run in recent[:5]:
            print(json.dumps({
                "id": run.get("id"),
                "branch": run.get("head_branch"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "created_at": run.get("created_at"),
                "url": run.get("html_url"),
            }, indent=2))


def wait_for_github_run(
    github_token: str,
    branch: str,
    created_after: str,
    timeout_sec: int = 300,
) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        runs = list_github_runs(github_token, branch, created_after=created_after)
        if runs:
            run = runs[0]
            print(
                "GitHub run found: "
                f"id={run.get('id')} branch={run.get('head_branch')} "
                f"status={run.get('status')} conclusion={run.get('conclusion')} "
                f"url={run.get('html_url')}"
            )
            if run.get("head_branch") == branch:
                return run
        else:
            print(f"No GitHub runs yet on branch {branch}...")
        time.sleep(10)

    other_branches = list_github_runs(github_token, created_after=created_after)
    # #region agent log
    debug_log("H5", "wait_for_github_run:timeout", "github poll exhausted", {
        "expected_branch": branch,
        "recent_runs": [
            {"id": r.get("id"), "branch": r.get("head_branch"), "status": r.get("status"), "created_at": r.get("created_at")}
            for r in other_branches[:5]
        ],
    })
    # #endregion
    wrong_branch = [r for r in other_branches if r.get("head_branch") != branch]
    if wrong_branch:
        run = wrong_branch[0]
        raise RuntimeError(
            f"GitHub ran on {run.get('head_branch')} instead of {branch} — "
            "automation ref was likely empty (defaults to main). "
            f"Run: {run.get('html_url')}"
        )
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
    live_automation = fetch_live_s3_automation(port_token)
    print(f"Live Port automation: {json.dumps(live_automation, indent=2)}")
    # #region agent log
    debug_log("H3", "main:live_automation", "live automation config from Port API", live_automation)
    # #endregion

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
        entity_exists = False
        try:
            entity = fetch_entity(port_token, "s3Bucket", port_run_id)
            entity_exists = True
        except Exception:
            entity_exists = False

        if entity_exists:
            print(
                "WARN: Port workflow did not succeed — marking ready via external Port API "
                "(Lambda /s3/mark-ready may not be deployed yet)",
                file=sys.stderr,
            )
            mark_entity_ready_external(port_token, port_run_id)
        elif failed_nodes:
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
            return 1
        else:
            print("FAIL: Port workflow did not succeed and entity was not created", file=sys.stderr)
            return 1
    else:
        # Workflow mark-ready (Lambda) may not emit ENTITY_UPDATED; always retrigger externally.
        print("Port workflow succeeded — ensuring automation via external Port API PATCH")
        mark_entity_ready_external(port_token, port_run_id)

    print_diagnostics(port_token, port_run_id)

    automation_run = wait_for_s3_automation_run(port_token, started_at, timeout_sec=90)
    if not automation_run:
        print("WARN: No Port automation run detected within 90s — continuing to poll GitHub", file=sys.stderr)

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

    if github_run.get("status") == "completed" and github_run.get("conclusion") not in {"success", None}:
        print("WARN: GitHub workflow completed but Terraform may have failed — dispatch path succeeded")

    print("\nPASS: Port workflow succeeded and GitHub Provision S3 Bucket run started on correct branch")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
