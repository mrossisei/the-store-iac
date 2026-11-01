import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("preflight", ROOT / "scripts/preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/entorno.json").read_text())

    def test_contract_has_no_overlapping_subnets(self):
        preflight.validate_contract(self.config)
        self.config["zones"]["b"]["private_cidr"] = self.config["zones"]["a"]["private_cidr"]
        with self.assertRaisesRegex(ValueError, "superponen"):
            preflight.validate_contract(self.config)

    def test_states_cannot_share_a_key(self):
        self.config["state_keys"]["infra"] = self.config["state_keys"]["aplicacion"]
        with self.assertRaisesRegex(ValueError, "estados"):
            preflight.validate_contract(self.config)

    def test_invalid_credentials_are_pending_not_success(self):
        def fake_run(command):
            if command[0] == "docker":
                return {"MemTotal": 16 * 1024**3}, None
            return None, "InvalidClientTokenId"
        with patch.object(preflight, "run", side_effect=fake_run), patch.object(preflight.shutil, "which", return_value="/tool"):
            report = preflight.collect()
        self.assertEqual(report["status"], "PENDING_AWS")
        self.assertFalse(any(r["status"] == "PASS" and r["check"].startswith("aws:") for r in report["results"]))

    def test_error_output_is_not_leaked(self):
        result = subprocess.CompletedProcess([], 254, stdout="SECRET", stderr="SECRET (ExpiredToken) when calling the GetCallerIdentity operation")
        with patch.object(preflight.subprocess, "run", return_value=result):
            value, error = preflight.run(["aws"])
        self.assertIsNone(value)
        self.assertEqual(error, "ExpiredToken")

    def test_offline_never_certifies_aws(self):
        with patch.object(preflight, "run", return_value=({"MemTotal": 16 * 1024**3}, None)), patch.object(preflight.shutil, "which", return_value="/tool"):
            self.assertEqual(preflight.collect(offline=True)["status"], "PENDING_AWS")

    def test_rds_metadata_checks_pinned_versions_and_twenty_gb(self):
        commands = []
        def fake_run(command):
            commands.append(command)
            if command[0] == 'docker':
                return {'MemTotal': 16 * 1024**3}, None
            if 'get-caller-identity' in command:
                return {'Account': 'test'}, None
            if 'describe-orderable-db-instance-options' in command:
                version = command[command.index('--engine-version') + 1]
                return {'OrderableDBInstanceOptions': [{'EngineVersion': version, 'MultiAZCapable': True, 'StorageType': 'gp2', 'MinStorageSize': 5, 'MaxStorageSize': 100}]}, None
            return None, 'NotUnderTest'
        with patch.object(preflight, 'run', side_effect=fake_run), patch.object(preflight.shutil, 'which', return_value='/tool'):
            report = preflight.collect()
        rds = [r for r in report['results'] if r['check'].startswith('aws:rds:')]
        self.assertEqual(len(rds), 2)
        self.assertTrue(all(r['status'] == 'PASS' for r in rds))
        tools = json.loads((ROOT / 'config/herramientas.json').read_text())
        for command in [c for c in commands if 'describe-orderable-db-instance-options' in c]:
            engine = command[command.index('--engine') + 1]
            self.assertEqual(command[command.index('--engine-version') + 1], tools[engine + '_engine_version'])


if __name__ == "__main__":
    unittest.main()
