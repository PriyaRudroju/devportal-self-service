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


def _optional_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _port_api_url() -> str:
    return _optional_env("PORT_API_URL", "https://api.port.io").rstrip("/")


def _port_blueprint() -> str:
    return _optional_env("PORT_BLUEPRINT_IDENTIFIER", "ec2ChangeRequest")


def _get_port_access_token() -> str:
    port_api_url = _port_api_url()
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


def _upsert_port_entity(identifier: str, title: str, properties: dict) -> dict:
    port_api_url = _port_api_url()
    blueprint = _port_blueprint()
    token = _get_port_access_token()

    payload = json.dumps(
        {
            "identifier": identifier,
            "title": title,
            "properties": properties,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{port_api_url}/v1/blueprints/{blueprint}/entities",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _approval_urls(api_base_url: str, run_id: str) -> tuple[str, str]:
    base = api_base_url.rstrip("/")
    approve_url = (
        f"{base}/approval-decision?"
        + urllib.parse.urlencode({"runId": run_id, "decision": "approve"})
    )
    reject_url = (
        f"{base}/approval-decision?"
        + urllib.parse.urlencode({"runId": run_id, "decision": "reject"})
    )
    return approve_url, reject_url


def _post_teams_notification(payload: dict, api_base_url: str) -> None:
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

    approve_url, reject_url = _approval_urls(api_base_url, run_id)
    payload_format = _optional_env("TEAMS_PAYLOAD_FORMAT", "workflow").lower()

    if payload_format == "messagecard":
        body = {
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
    else:
        body = {
            "runId": run_id,
            "action_title": action_title,
            "instance_name": instance_name,
            "instance_type": instance_type,
            "environment": environment,
            "requested_by": requested_by,
            "port_run_url": port_run_url,
            "approve_url": approve_url,
            "reject_url": reject_url,
        }

    request = urllib.request.Request(
        teams_webhook_url,
        data=json.dumps(body).encode("utf-8"),
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
    env_url = _optional_env("API_GATEWAY_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    request_context = event.get("requestContext", {})
    domain = request_context.get("domainName")
    stage = request_context.get("stage")
    if domain and stage:
        return f"https://{domain}/{stage}"

    raise ValueError("Unable to determine API Gateway base URL")


def _normalize_ec2_request(payload: dict) -> dict:
    run_id = (payload.get("runId") or payload.get("run_id") or "").strip()
    instance_name = (payload.get("instance_name") or payload.get("instanceName") or "").strip()
    instance_type = (payload.get("instance_type") or payload.get("instanceType") or "").strip()
    environment = (payload.get("environment") or "dev").strip()
    requested_by = (
        payload.get("requested_by")
        or payload.get("requestedBy")
        or "unknown"
    ).strip()
    port_run_url = (
        payload.get("port_run_url")
        or payload.get("portRunUrl")
        or f"https://app.port.io/organization/run?runId={run_id}"
    )

    return {
        "runId": run_id,
        "instanceName": instance_name,
        "instanceType": instance_type,
        "environment": environment,
        "requestedBy": requested_by,
        "portRunUrl": port_run_url,
    }


def handle_teams_notify(event: dict) -> dict:
    """Send Teams approval card only (Port Workflow owns catalog UPSERT)."""
    payload = _normalize_ec2_request(_parse_body(event))
    run_id = payload["runId"]
    instance_name = payload["instanceName"]
    instance_type = payload["instanceType"]

    if not run_id:
        return _response(400, {"error": "runId is required"})
    if not instance_name:
        return _response(400, {"error": "instance_name is required"})
    if not instance_type:
        return _response(400, {"error": "instance_type is required"})

    api_base_url = _api_base_url(event)
    _post_teams_notification(payload, api_base_url)

    return _response(
        200,
        {
            "message": "Teams approval notification sent",
            "runId": run_id,
        },
    )


def handle_ec2_request(event: dict) -> dict:
    payload = _normalize_ec2_request(_parse_body(event))
    run_id = payload["runId"]
    instance_name = payload["instanceName"]
    instance_type = payload["instanceType"]
    environment = payload["environment"]
    requested_by = payload["requestedBy"]

    if not run_id:
        return _response(400, {"error": "runId is required"})
    if not instance_name:
        return _response(400, {"error": "instance_name is required"})
    if not instance_type:
        return _response(400, {"error": "instance_type is required"})

    entity = _upsert_port_entity(
        run_id,
        f"EC2 {instance_name}",
        {
            "instanceName": instance_name,
            "instanceType": instance_type,
            "environment": environment,
            "approvalStatus": "pending",
            "executionStatus": "not_started",
            "requestedBy": requested_by,
            "portRunId": run_id,
        },
    )

    api_base_url = _api_base_url(event)
    _post_teams_notification(payload, api_base_url)

    return _response(
        200,
        {
            "message": "EC2 request recorded and Teams notification sent",
            "runId": run_id,
            "portEntity": entity,
        },
    )


def handle_approval_decision(event: dict) -> dict:
    params = event.get("queryStringParameters") or {}
    run_id = (params.get("runId") or "").strip()
    decision = (params.get("decision") or "").strip().lower()

    if not run_id:
        return _response(400, {"error": "runId query parameter is required"})
    if decision not in {"approve", "reject"}:
        return _response(400, {"error": "decision must be approve or reject"})

    if decision == "approve":
        properties = {
            "approvalStatus": "approved",
            "executionStatus": "in_progress",
        }
        message = "Request approved. Port workflow will trigger GitHub if configured."
    else:
        properties = {
            "approvalStatus": "rejected",
            "executionStatus": "failed",
        }
        message = "Request rejected."

    entity = _upsert_port_entity(run_id, f"EC2 {run_id}", properties)

    return _response(
        200,
        {
            "message": message,
            "runId": run_id,
            "decision": decision,
            "portEntity": entity,
        },
    )


def _route_matches(raw_path: str, suffix: str) -> bool:
    normalized = raw_path.rstrip("/")
    return normalized == suffix or normalized.endswith(suffix)


def lambda_handler(event, context):
    del context

    try:
        method = (event.get("requestContext", {}).get("http", {}) or {}).get("method", "")
        raw_path = event.get("rawPath") or event.get("path") or ""

        if method == "POST" and _route_matches(raw_path, "/teams/notify"):
            return handle_teams_notify(event)

        if method == "POST" and _route_matches(raw_path, "/ec2/request"):
            return handle_ec2_request(event)

        if method in {"GET", "POST"} and _route_matches(raw_path, "/approval-decision"):
            return handle_approval_decision(event)

        return _response(404, {"error": f"Route not found: {method} {raw_path}"})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return _response(exc.code, {"error": "Upstream request failed", "details": body})
    except Exception as exc:  # noqa: BLE001 - Lambda entrypoint returns structured errors
        return _response(500, {"error": str(exc)})
