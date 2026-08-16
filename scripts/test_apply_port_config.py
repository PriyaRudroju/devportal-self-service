#!/usr/bin/env python3
"""Unit tests for Port config apply helpers."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

sys_path = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(sys_path))

from apply_port_config import (  # noqa: E402
    is_port_runtime_template,
    prepare_integration_automation_payload,
    prepare_action_payload,
    prepare_workflow_payload,
    substitute,
)


class TestPortRuntimeTemplate(unittest.TestCase):
    def test_detects_event_template(self) -> None:
        self.assertTrue(
            is_port_runtime_template("{{ .event.diff.before.properties.gitRef }}")
        )

    def test_detects_outputs_template(self) -> None:
        self.assertTrue(
            is_port_runtime_template("{{ .outputs.trigger.git_ref }}")
        )

    def test_rejects_static_placeholder(self) -> None:
        self.assertFalse(is_port_runtime_template("{{GIT_REF_DEFAULT}}"))
        self.assertFalse(is_port_runtime_template("dev"))


class TestS3AutomationPayload(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        automation_path = (
            repo_root / "port" / "environments" / "automations" / "trigger-github-on-s3-ready.json"
        )
        config_path = repo_root / "port" / "environments" / "config.env"
        from apply_port_config import build_variables

        self.variables = build_variables(config_path)
        raw = automation_path.read_text(encoding="utf-8")
        self.payload = json.loads(substitute(raw, self.variables))

    def test_preserves_diff_before_ref_template(self) -> None:
        result = prepare_action_payload(self.payload, self.variables)
        props = result["invocationMethod"]["integrationActionExecutionProperties"]
        self.assertEqual(
            props["ref"],
            "{{ .event.diff.before.properties.gitRef }}",
        )
        self.assertFalse(result.get("publish"))

    def test_ref_not_in_workflow_inputs(self) -> None:
        result = prepare_action_payload(self.payload, self.variables)
        props = result["invocationMethod"]["integrationActionExecutionProperties"]
        self.assertNotIn("ref", props.get("workflowInputs", {}))

    def test_unchanged_fields_use_diff_before(self) -> None:
        result = prepare_action_payload(self.payload, self.variables)
        inputs = result["invocationMethod"]["integrationActionExecutionProperties"]["workflowInputs"]
        self.assertIn("diff.before.properties.bucketName", inputs["bucket_name"])
        self.assertIn("diff.before.properties.environment", inputs["environment"])
        self.assertIn("diff.before.properties.portRunId", inputs["port_run_id"])


class TestPrepareIntegrationAutomationPayload(unittest.TestCase):
    def test_hoists_ref_from_workflow_inputs(self) -> None:
        payload = {
            "invocationMethod": {
                "type": "INTEGRATION_ACTION",
                "integrationActionType": "dispatch_workflow",
                "integrationActionExecutionProperties": {
                    "workflow": "provision-s3-bucket.yml",
                    "workflowInputs": {
                        "ref": "{{ .event.diff.before.properties.gitRef }}",
                        "bucket_name": "x",
                    },
                },
            }
        }
        result = prepare_integration_automation_payload(payload, {"GIT_REF_DEFAULT": "dev"})
        props = result["invocationMethod"]["integrationActionExecutionProperties"]
        self.assertEqual(props["ref"], "{{ .event.diff.before.properties.gitRef }}")
        self.assertNotIn("ref", props["workflowInputs"])

    def test_empty_ref_uses_default(self) -> None:
        payload = {
            "invocationMethod": {
                "type": "INTEGRATION_ACTION",
                "integrationActionType": "dispatch_workflow",
                "integrationActionExecutionProperties": {
                    "workflow": "provision-s3-bucket.yml",
                    "workflowInputs": {},
                },
            }
        }
        result = prepare_integration_automation_payload(payload, {"GIT_REF_DEFAULT": "dev"})
        props = result["invocationMethod"]["integrationActionExecutionProperties"]
        self.assertEqual(props["ref"], "dev")


class TestPrepareWorkflowPayload(unittest.TestCase):
    def test_hoists_ref_in_workflow_integration_node(self) -> None:
        payload = {
            "identifier": "provision_s3_after_ready",
            "nodes": [
                {
                    "identifier": "dispatch_github",
                    "config": {
                        "type": "INTEGRATION_ACTION",
                        "integrationActionType": "dispatch_workflow",
                        "integrationActionExecutionProperties": {
                            "workflow": "provision-s3-bucket.yml",
                            "workflowInputs": {
                                "ref": "{{ .outputs.trigger.diff.before.properties.gitRef }}",
                                "bucket_name": "x",
                            },
                        },
                    },
                }
            ],
        }
        result = prepare_workflow_payload(payload, {"GIT_REF_DEFAULT": "dev"})
        props = result["nodes"][0]["config"]["integrationActionExecutionProperties"]
        self.assertEqual(props["ref"], "{{ .outputs.trigger.diff.before.properties.gitRef }}")
        self.assertNotIn("ref", props["workflowInputs"])


class TestS3RequestWorkflowPayload(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        workflow_path = (
            repo_root / "port" / "environments" / "workflows" / "provision-s3-request.json"
        )
        config_path = repo_root / "port" / "environments" / "config.env"
        from apply_port_config import build_variables

        self.variables = build_variables(config_path)
        raw = workflow_path.read_text(encoding="utf-8")
        self.payload = json.loads(substitute(raw, self.variables))

    def _dispatch_props(self, payload: dict) -> dict:
        for node in payload["nodes"]:
            if node.get("identifier") == "dispatch_github":
                return node["config"]["integrationActionExecutionProperties"]
        self.fail("dispatch_github node not found")

    def test_preserves_validated_git_ref(self) -> None:
        result = prepare_workflow_payload(self.payload, self.variables)
        props = self._dispatch_props(result)
        self.assertEqual(props["ref"], "{{ .outputs.trigger.git_ref }}")
        self.assertNotIn("ref", props.get("workflowInputs", {}))

    def test_workflow_inputs_do_not_include_ref(self) -> None:
        result = prepare_workflow_payload(self.payload, self.variables)
        inputs = self._dispatch_props(result)["workflowInputs"]
        self.assertIn("bucket_name", inputs)
        self.assertIn("environment", inputs)
        self.assertIn("port_run_id", inputs)
        self.assertNotIn("ref", inputs)


if __name__ == "__main__":
    unittest.main()
