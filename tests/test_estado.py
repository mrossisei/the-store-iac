import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("estado", ROOT / "scripts/estado.py")
estado = importlib.util.module_from_spec(spec)
spec.loader.exec_module(estado)


class BackendTests(unittest.TestCase):
    def test_roots_never_share_state_or_disable_locking(self):
        configs = [estado.backend_config("the-store-tfstate-test", stack) for stack in ("infra", "imagenes", "aplicacion")]
        self.assertEqual(len(set(configs)), 3)
        for value in configs:
            self.assertIn('use_lockfile = true', value)
            self.assertIn('encrypt = true', value)
            self.assertNotIn('key = "the-store/terraform.tfstate"', value)

    def test_bucket_cannot_inject_hcl(self):
        with self.assertRaises(ValueError):
            estado.backend_config('test"\nuse_lockfile=false', 'infra')

    def test_unknown_stack_is_rejected(self):
        with self.assertRaises(ValueError):
            estado.backend_config('the-store-tfstate-test', 'legacy')


if __name__ == "__main__":
    unittest.main()
