import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bootstrap_bucket", ROOT / "scripts/bootstrap-bucket.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def response(data=None, code=0, error=""):
    return subprocess.CompletedProcess([], code, json.dumps(data or {}), error)


class BootstrapTests(unittest.TestCase):
    def run_with(self, values):
        with patch.dict(os.environ, {"TF_STATE_BUCKET": "the-store-tfstate-test", "TF_STATE_REGION": "us-east-1"}), patch.object(bootstrap.subprocess, "run", side_effect=values) as run:
            bootstrap.main()
            return [call.args[0] for call in run.call_args_list]

    def test_existing_owned_project_bucket_is_reused(self):
        calls = self.run_with([response({"Account": "123456789012"}), response(), response({"TagSet": [{"Key": "Project", "Value": "the-store"}, {"Key": "ManagedBy", "Value": "terraform"}]})])
        self.assertFalse(any("create-bucket" in call for call in calls))
        self.assertIn("--expected-bucket-owner", calls[1])

    def test_access_denied_is_not_mistaken_for_missing_bucket(self):
        with self.assertRaisesRegex(RuntimeError, "no se modifica"):
            self.run_with([response({"Account": "123456789012"}), response(code=1, error="(403) AccessDenied")])

    def test_only_missing_bucket_is_created(self):
        calls = self.run_with([response({"Account": "123456789012"}), response(code=1, error="(404) NotFound"), response(), response()])
        self.assertIn("create-bucket", calls[2])
        self.assertIn("put-bucket-tagging", calls[3])

    def test_unrelated_bucket_is_not_adopted(self):
        with self.assertRaisesRegex(RuntimeError, "otro uso"):
            self.run_with([response({"Account": "123456789012"}), response(), response({"TagSet": [{"Key": "Project", "Value": "other"}]})])


if __name__ == "__main__":
    unittest.main()
