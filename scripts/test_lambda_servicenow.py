#!/usr/bin/env python3
"""Unit tests for the ServiceNow request handler in the Lambda."""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lambda" / "teams-approval"))

import handler  # noqa: E402

SERVICENOW_ENV = {
    "SERVICENOW_INSTANCE_URL": "https://dev123456.service-now.com",
    "SERVICENOW_USERNAME": "admin",
    "SERVICENOW_PASSWORD": "secret",
    "SERVICENOW_CATALOG_ITEM_SYS_ID": "item-sys-id",
}

ORDER_RESPONSE = {
    "result": {
        "request_number": "REQ0010042",
        "request_id": "req-sys-id",
    }
}


def body(payload: dict) -> dict:
    return {"body": json.dumps(payload)}


class TestResolveServiceNowUser(unittest.TestCase):
    @patch.object(handler, "_servicenow_request")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_returns_sys_id(self, mock_request) -> None:
        mock_request.return_value = {"result": [{"sys_id": "user-sys-id"}]}
        self.assertEqual(handler.resolve_servicenow_user("a@b.com"), "user-sys-id")

    @patch.object(handler, "_servicenow_request")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_returns_empty_when_absent(self, mock_request) -> None:
        mock_request.return_value = {"result": []}
        self.assertEqual(handler.resolve_servicenow_user("nobody@b.com"), "")


class TestHandleServiceNowCreateRequest(unittest.TestCase):
    def test_missing_entity_id(self) -> None:
        result = handler.handle_servicenow_create_request(body({}))
        self.assertEqual(result["statusCode"], 400)

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "resolve_servicenow_user", return_value="user-sys-id")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_creates_ticket_and_writes_back(
        self, mock_get_entity, _mock_resolve, mock_sn, mock_patch
    ) -> None:
        mock_get_entity.return_value = {"properties": {"status": "pending"}}
        mock_sn.return_value = ORDER_RESPONSE

        result = handler.handle_servicenow_create_request(
            body(
                {
                    "entityId": "wfr_1",
                    "requested_for_email": "abel@example.com",
                    "service": "AWS dev account",
                    "justification": "needs access",
                }
            )
        )

        self.assertEqual(result["statusCode"], 200)

        sn_args = mock_sn.call_args
        self.assertEqual(sn_args.args[0], "POST")
        self.assertIn("/api/sn_sc/servicecatalog/items/item-sys-id/order_now", sn_args.args[1])
        payload = sn_args.args[2]
        self.assertEqual(payload["sysparm_requested_for"], "user-sys-id")
        self.assertEqual(payload["variables"]["service"], "AWS dev account")
        self.assertEqual(payload["variables"]["justification"], "needs access")

        properties = mock_patch.call_args.args[2]
        self.assertEqual(properties["ticketNumber"], "REQ0010042")
        self.assertEqual(properties["ticketSysId"], "req-sys-id")
        self.assertEqual(properties["status"], "submitted")
        self.assertIn("req-sys-id", properties["ticketUrl"])

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_existing_ticket_is_not_recreated(
        self, mock_get_entity, mock_sn, mock_patch
    ) -> None:
        mock_get_entity.return_value = {
            "properties": {"ticketNumber": "REQ0010042", "status": "submitted"}
        }

        result = handler.handle_servicenow_create_request(
            body({"entityId": "wfr_1", "requested_for_email": "abel@example.com"})
        )

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["ticketNumber"], "REQ0010042")
        mock_sn.assert_not_called()
        mock_patch.assert_not_called()

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "resolve_servicenow_user", return_value="")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_unknown_user_fails_without_creating_ticket(
        self, mock_get_entity, _mock_resolve, mock_sn, mock_patch
    ) -> None:
        mock_get_entity.return_value = {"properties": {"status": "pending"}}

        result = handler.handle_servicenow_create_request(
            body({"entityId": "wfr_1", "requested_for_email": "nobody@example.com"})
        )

        self.assertEqual(result["statusCode"], 400)
        self.assertIn("No ServiceNow user found", json.loads(result["body"])["error"])
        mock_sn.assert_not_called()
        self.assertEqual(mock_patch.call_args.args[2]["status"], "failed")

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "resolve_servicenow_user", return_value="user-sys-id")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_servicenow_error_marks_entity_failed(
        self, mock_get_entity, _mock_resolve, mock_sn, mock_patch
    ) -> None:
        mock_get_entity.return_value = {"properties": {"status": "pending"}}
        mock_sn.side_effect = urllib.error.HTTPError(
            "https://dev123456.service-now.com", 403, "Forbidden", {}, None
        )

        result = handler.handle_servicenow_create_request(
            body({"entityId": "wfr_1", "requested_for_email": "abel@example.com"})
        )

        self.assertEqual(result["statusCode"], 502)
        self.assertEqual(mock_patch.call_args.args[2]["status"], "failed")

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "resolve_servicenow_user", return_value="user-sys-id")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_unparseable_response_marks_entity_failed(
        self, mock_get_entity, _mock_resolve, mock_sn, mock_patch
    ) -> None:
        mock_get_entity.return_value = {"properties": {"status": "pending"}}
        mock_sn.return_value = {"result": {}}

        result = handler.handle_servicenow_create_request(
            body({"entityId": "wfr_1", "requested_for_email": "abel@example.com"})
        )

        self.assertEqual(result["statusCode"], 502)
        self.assertEqual(mock_patch.call_args.args[2]["status"], "failed")

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_missing_email_fails(self, mock_get_entity, mock_patch) -> None:
        mock_get_entity.return_value = {"properties": {"status": "pending"}}

        result = handler.handle_servicenow_create_request(body({"entityId": "wfr_1"}))

        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(mock_patch.call_args.args[2]["status"], "failed")


class TestRouteThroughLambdaHandler(unittest.TestCase):
    """Exercise the three end-to-end cases through the real route matching."""

    @staticmethod
    def event(payload: dict) -> dict:
        return {
            "requestContext": {"http": {"method": "POST"}},
            "rawPath": "/servicenow/create-request",
            "body": json.dumps(payload),
        }

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "resolve_servicenow_user", return_value="user-sys-id")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_happy_path(self, mock_get_entity, _mock_resolve, mock_sn, mock_patch) -> None:
        mock_get_entity.return_value = {"properties": {"status": "pending"}}
        mock_sn.return_value = ORDER_RESPONSE

        result = handler.lambda_handler(
            self.event(
                {
                    "entityId": "wfr_1",
                    "requested_for_email": "abel@example.com",
                    "service": "AWS dev account",
                    "justification": "needs access",
                }
            ),
            None,
        )

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["ticketNumber"], "REQ0010042")
        self.assertEqual(mock_patch.call_args.args[2]["status"], "submitted")

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "resolve_servicenow_user", return_value="")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_unknown_requester_email(
        self, mock_get_entity, _mock_resolve, mock_sn, mock_patch
    ) -> None:
        mock_get_entity.return_value = {"properties": {"status": "pending"}}

        result = handler.lambda_handler(
            self.event({"entityId": "wfr_2", "requested_for_email": "nobody@example.com"}),
            None,
        )

        self.assertEqual(result["statusCode"], 400)
        mock_sn.assert_not_called()
        self.assertEqual(mock_patch.call_args.args[2]["status"], "failed")

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "_servicenow_request")
    @patch.object(handler, "_get_port_entity")
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_retry_does_not_duplicate(self, mock_get_entity, mock_sn, mock_patch) -> None:
        mock_get_entity.return_value = {
            "properties": {"status": "submitted", "ticketNumber": "REQ0010042"}
        }

        result = handler.lambda_handler(
            self.event({"entityId": "wfr_1", "requested_for_email": "abel@example.com"}),
            None,
        )

        self.assertEqual(result["statusCode"], 200)
        mock_sn.assert_not_called()
        mock_patch.assert_not_called()


class TestServiceNowTicketUrl(unittest.TestCase):
    @patch.dict("os.environ", SERVICENOW_ENV, clear=False)
    def test_builds_nav_to_url(self) -> None:
        url = handler._servicenow_ticket_url("req-sys-id")
        self.assertTrue(url.startswith("https://dev123456.service-now.com/nav_to.do?uri="))
        self.assertIn("req-sys-id", url)


if __name__ == "__main__":
    unittest.main()
