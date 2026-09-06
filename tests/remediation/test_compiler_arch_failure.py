"""C06: never overwrite an export after losing the architectural void source."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_compiler as C
from test_level_elevation import building


class ArchitectureFailure(unittest.TestCase):
    def test_architecture_failure_preserves_existing_export(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "model.gltf"
            out.write_bytes(b"previous-reviewed-export")
            with patch("acs_arch.compile_architecture", side_effect=RuntimeError("audit_arch_failure")):
                with self.assertRaisesRegex(RuntimeError, "audit_arch_failure"):
                    C.compile_building(building(), str(out))
            self.assertEqual(out.read_bytes(), b"previous-reviewed-export")

    def test_architecture_failure_creates_no_new_export(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "model.gltf"
            with patch("acs_arch.compile_architecture", side_effect=ValueError("audit_bad_arch")):
                with self.assertRaisesRegex(ValueError, "audit_bad_arch"):
                    C.compile_building(building(), str(out))
            self.assertFalse(out.exists())

    def test_valid_architecture_still_exports_geometry(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "model.gltf"
            C.compile_building(building(), str(out))
            result = json.loads(out.read_text())
            self.assertEqual(result["asset"]["version"], "2.0")
            self.assertTrue(any(n["name"].startswith("FLOOR|") for n in result["nodes"]))
            self.assertTrue(any(n["name"].startswith("DOOR|") for n in result["nodes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
