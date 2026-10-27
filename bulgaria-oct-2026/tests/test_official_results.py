from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("check_official_results", ROOT / "scripts/check_official_results.py")
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
FIXTURES = Path(__file__).parent / "fixtures"


class ProtocolTests(unittest.TestCase):
    def test_combined_machine_total(self) -> None:
        p = module.parse_protocol((FIXTURES / "machine_total.html").read_bytes(), "010100004", "01", 37, "fixture")
        self.assertEqual((p.registered, p.added, p.voted, p.nobody), (210, 1, 211, 13))
        self.assertEqual((p.votes["25"], p.votes["4"]), (78, 81))
        self.assertEqual(sum(p.votes.values()) + p.nobody, p.voted)

    def test_source_discrepancy_is_preserved(self) -> None:
        p = module.parse_protocol((FIXTURES / "abroad_balance.html").read_bytes(), "321320600", "32", 45, "fixture")
        self.assertEqual(sum(p.votes.values()) + p.nobody, 248)
        self.assertEqual(p.voted, 56)

    def test_wrong_identity_and_incomplete_schema_rejected(self) -> None:
        body = (FIXTURES / "machine_total.html").read_bytes()
        with self.assertRaisesRegex(ValueError, "identity"):
            module.parse_protocol(body, "010100099", "01", 37, "fixture")
        with self.assertRaisesRegex(ValueError, "schema"):
            module.parse_protocol(body.replace(b"<td>27</td>", b"<td>28</td>"), "010100004", "01", 37, "fixture")


if __name__ == "__main__":
    unittest.main()
