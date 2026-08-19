#!/usr/bin/env python3
"""Prove the ServiceNow request APIs before wiring Port and Lambda together.

Resolves a requester by email, then orders a catalog item and prints the raw
response so the created-request field names can be confirmed on the instance.

    export SERVICENOW_INSTANCE_URL=https://dev123456.service-now.com
    export SERVICENOW_USERNAME=admin
    export SERVICENOW_PASSWORD=...
    export SERVICENOW_CATALOG_ITEM_SYS_ID=...

    python scripts/servicenow_smoke.py --email abel.tuter@example.com \
        --service "AWS dev account" --justification "smoke test"
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"FAIL: missing required environment variable {name}", file=sys.stderr)
        sys.exit(2)
    return value


def auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def request_json(method: str, url: str, authorization: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": authorization,
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"FAIL: {method} {url} returned {exc.code}\n{detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"FAIL: cannot reach {url}: {exc.reason}", file=sys.stderr)
        sys.exit(1)

    return json.loads(body) if body else {}


def resolve_user(instance_url: str, authorization: str, email: str) -> dict:
    query = urllib.parse.urlencode(
        {
            "sysparm_query": f"email={email}",
            "sysparm_fields": "sys_id,user_name,email,name",
            "sysparm_limit": "1",
        }
    )
    body = request_json(
        "GET",
        f"{instance_url}/api/now/table/sys_user?{query}",
        authorization,
    )
    records = body.get("result") or []
    return records[0] if records else {}


def order_item(
    instance_url: str,
    authorization: str,
    item_sys_id: str,
    requested_for_sys_id: str,
    variables: dict,
) -> dict:
    payload: dict = {"sysparm_quantity": "1", "variables": variables}
    if requested_for_sys_id:
        payload["sysparm_requested_for"] = requested_for_sys_id

    print("\nRequest payload:")
    print(json.dumps(payload, indent=2))

    return request_json(
        "POST",
        f"{instance_url}/api/sn_sc/servicecatalog/items/{item_sys_id}/order_now",
        authorization,
        payload,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test the ServiceNow request APIs")
    parser.add_argument("--email", required=True, help="Requester email to resolve in sys_user")
    parser.add_argument("--service", default="Smoke test service", help="Value for the service variable")
    parser.add_argument(
        "--justification",
        default="Created by scripts/servicenow_smoke.py",
        help="Value for the justification variable",
    )
    parser.add_argument(
        "--lookup-only",
        action="store_true",
        help="Resolve the user and stop, without creating a ticket",
    )
    args = parser.parse_args()

    instance_url = env("SERVICENOW_INSTANCE_URL").rstrip("/")
    authorization = auth_header(env("SERVICENOW_USERNAME"), env("SERVICENOW_PASSWORD"))

    print("=== ServiceNow smoke test ===")
    print(f"Instance: {instance_url}")

    user = resolve_user(instance_url, authorization, args.email)
    if not user:
        print(f"FAIL: no sys_user found with email {args.email}", file=sys.stderr)
        sys.exit(1)

    print(f"Resolved user: {user.get('name')} ({user.get('user_name')}) sys_id={user.get('sys_id')}")

    if args.lookup_only:
        print("PASS credentials and user lookup work (no ticket created)")
        return

    item_sys_id = env("SERVICENOW_CATALOG_ITEM_SYS_ID")
    result = order_item(
        instance_url,
        authorization,
        item_sys_id,
        user.get("sys_id", ""),
        {"service": args.service, "justification": args.justification},
    )

    print("\nRaw order_now response:")
    print(json.dumps(result, indent=2))

    created = result.get("result") or {}
    number = created.get("request_number") or created.get("number") or ""
    sys_id = created.get("request_id") or created.get("sys_id") or ""

    print("\nParsed:")
    print(f"  request number: {number or '<not found>'}")
    print(f"  request sys_id: {sys_id or '<not found>'}")

    if not number or not sys_id:
        print(
            "\nWARNING: could not parse the request number or sys_id. Compare the raw "
            "response above with the parsing in handle_servicenow_create_request.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nPASS created {number}")
    print(f"Open: {instance_url}/nav_to.do?uri=sc_request.do%3Fsys_id%3D{sys_id}")


if __name__ == "__main__":
    main()
