#!/usr/bin/env python3
"""Unit tests for S3 git branch validation helpers in Lambda handler."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lambda" / "teams-approval"))

import handler  # noqa: E402


class TestResolveGitRef(unittest.TestCase):
    def test_uses_explicit_ref(self) -> None:
        with patch.dict("os.environ", {"GIT_REF_DEFAULT": "dev"}, clear=False):
            self.assertEqual(handler._resolve_git_ref("feature/x"), "feature/x")

    def test_defaults_when_empty(self) -> None:
        with patch.dict("os.environ", {"GIT_REF_DEFAULT": "dev"}, clear=False):
            self.assertEqual(handler._resolve_git_ref(""), "dev")
            self.assertEqual(handler._resolve_git_ref(None), "dev")


class TestHandleS3ValidateGitRef(unittest.TestCase):
    def test_missing_entity_id(self) -> None:
        result = handler.handle_s3_validate_git_ref({"body": "{}"})
        self.assertEqual(result["statusCode"], 400)

    @patch.object(handler, "github_branch_exists", return_value=False)
    @patch.object(handler, "_get_port_entity")
    @patch.dict(
        "os.environ",
        {
            "GITHUB_ORG": "org",
            "GITHUB_REPO": "repo",
            "GIT_REF_DEFAULT": "dev",
        },
        clear=False,
    )
    def test_invalid_branch_returns_400(self, mock_get_entity, _mock_exists) -> None:
        mock_get_entity.return_value = {"properties": {"gitRef": "feature/missing"}}
        result = handler.handle_s3_validate_git_ref({"body": '{"entityId":"run-1"}'})
        self.assertEqual(result["statusCode"], 400)
        body = __import__("json").loads(result["body"])
        self.assertIn("not found", body["error"])

    @patch.object(handler, "_patch_port_entity")
    @patch.object(handler, "github_branch_exists", return_value=True)
    @patch.object(handler, "_get_port_entity")
    @patch.dict(
        "os.environ",
        {
            "GITHUB_ORG": "org",
            "GITHUB_REPO": "repo",
            "GIT_REF_DEFAULT": "dev",
        },
        clear=False,
    )
    def test_valid_branch_returns_200(self, mock_get_entity, _mock_exists, mock_patch) -> None:
        mock_get_entity.return_value = {"properties": {"gitRef": "dev"}}
        result = handler.handle_s3_validate_git_ref({"body": '{"entityId":"run-1"}'})
        self.assertEqual(result["statusCode"], 200)
        mock_patch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
