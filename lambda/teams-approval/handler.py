"""Teams approval Lambda for Port.io EC2 self-service actions."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _get_port_access_token() -> str:
    port_api_url = os.environ.get("PORT_API_URL", "https://api.port.io").rstrip("/")
    payload = json.dumps(
        {
            "clientId": _env("PORT_CLIENT_ID"),
            "clientSecret": _env("PORT_CLIENT_SECRET"),
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{port_api_url}/v1/auth/access_token",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    access_token = data.get("accessToken")
    if not access_token:
        raise ValueError("Port access token response did not include accessToken")
    return access_token


def _patch_port_approval(run_id: str, decision: str) -> dict:
    port_api_url = os.environ.get("PORT_API_URL", "https://api.port.io").rstrip("/")
    token = _get_port_access_token()

    status = "APPROVE" if decision == "approve" else "DECLINE"
    description = (
        "Approved via Microsoft Teams"
        if status == "APPROVE"
        else "Rejected via Microsoft Teams"
    )

    payload = json.dumps({"status": status, "description": description}).encode("utf-8")
    request = urllib.request.Request(
        f"{port_api_url}/v1/actions/runs/{run_id}/approval",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="PATCH",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_teams_card(payload: dict, api_base_url: str) -> None:
    teams_webhook_url = _env("TEAMS_WEBHOOK_URL")
    run_id = payload.get("runId", "")
    action_title = payload.get("actionTitle", "EC2 Change Request")
    requested_by = payload.get("requestedBy", "unknown")
    instance_name = payload.get("instanceName", "")
    instance_type = payload.get("instanceType", "")
    environment = payload.get("environment", "")
    port_run_url = payload.get(
        "portRunUrl", f"https://app.port.io/organization/run?runId={run_id}"
    )

    approve_url = (
        f"{api_base_url.rstrip('/')}/teams/approval-decision?"
        + urllib.parse.urlencode({"runId": run_id, "decision": "approve"})
    )
    reject_url = (
        f"{api_base_url.rstrip('/')}/teams/approval-decision?"
        + urllib.parse.urlencode({"runId": run_id, "decision": "reject"})
    )

    card = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"Approval required: {action_title}",
        "themeColor": "0078D4",
        "title": f"Approval required: {action_title}",
        "text": (
            f"**Requested by:** {requested_by}\n\n"
            f"**Instance name:** {instance_name}\n\n"
            f"**Instance type:** {instance_type}\n\n"
            f"**Environment:** {environment}\n\n"
            f"**Port run:** [Open in Port]({port_run_url})"
        ),
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "Approve",
                "targets": [{"os": "default", "uri": approve_url}],
            },
            {
                "@type": "OpenUri",
                "name": "Reject",
                "targets": [{"os": "default", "uri": reject_url}],
            },
            {
                "@type": "OpenUri",
                "name": "View in Port",
                "targets": [{"os": "default", "uri": port_run_url}],
            },
        ],
    }

    request = urllib.request.Request(
        teams_webhook_url,
        data=json.dumps(card).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status >= 400:
            raise RuntimeError(f"Teams webhook returned status {response.status}")


def _parse_body(event: dict) -> dict:
    body = event.get("body", {})
    if isinstance(body, str):
        if not body:
            return {}
        return json.loads(body)
    return body or {}


def _api_base_url(event: dict) -> str:
    env_url = os.environ.get("API_GATEWAY_BASE_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    request_context = event.get("requestContext", {})
    domain = request_context.get("domainName")
    stage = request_context.get("stage")
    if domain and stage:
        return f"https://{domain}/{stage}"

    raise ValueError("Unable to determine API Gateway base URL")


def handle_approval_request(event: dict) -> dict:
    payload = _parse_body(event)
    api_base_url = _api_base_url(event)
    _post_teams_card(payload, api_base_url)
    return _response(200, {"message": "Teams approval notification sent"})


def handle_approval_decision(event: dict) -> dict:
    params = event.get("queryStringParameters") or {}
    run_id = (params.get("runId") or "").strip()
    decision = (params.get("decision") or "").strip().lower()

    if not run_id:
        return _response(400, {"error": "runId query parameter is required"})
    if decision not in {"approve", "reject"}:
        return _response(400, {"error": "decision must be approve or reject"})

    result = _patch_port_approval(run_id, decision)
    message = (
        "Request approved. GitHub workflow will start if configured."
        if decision == "approve"
        else "Request rejected."
    )
    return _response(
        200,
        {
            "message": message,
            "runId": run_id,
            "decision": decision,
            "portResponse": result,
        },
    )


def lambda_handler(event, context):
    del context

    try:
        method = (event.get("requestContext", {}).get("http", {}) or {}).get("method", "")
        raw_path = event.get("rawPath") or event.get("path") or ""

        if method == "POST" and raw_path.endswith("/teams/approval-request"):
            return handle_approval_request(event)

        if method in {"GET", "POST"} and raw_path.endswith("/teams/approval-decision"):
            return handle_approval_decision(event)

        return _response(404, {"error": f"Route not found: {method} {raw_path}"})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return _response(exc.code, {"error": "Upstream request failed", "details": body})
    except Exception as exc:  # noqa: BLE001 - Lambda entrypoint returns structured errors
        return _response(500, {"error": str(exc)})
