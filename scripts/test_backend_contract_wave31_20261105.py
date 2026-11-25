"""Source-backed host checker tests only; no compiler invocation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("wave31_backend_checker", SCRIPTS / "check-backend.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class BackendContractWave31(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root.joinpath("suite.sh").write_text("exit 0\n")
        self.root.joinpath("probe.atto").write_text("not a supported LLVM program\n")
        self.fixture = {
            "java": {"pin": "SOURCE_REF", "execution": "supported", "suite": "suite.sh"},
            "llvm": {"pin": "LLVM_SOURCE_REF", "execution": "unsupported",
                     "rejection_probes": [{"path": "probe.atto",
                       "diagnostic": "oreslang-llvmc: expected fnc or routine at byte 0"}]},
        }
        self.root_patch = patch.object(checker, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def load(self):
        self.root.joinpath("BACKENDS.json").write_text(json.dumps(self.fixture))
        return checker.load_contract()

    def test_valid_minimal_contract_is_only_a_host_manifest(self):
        self.assertEqual(self.load(), self.fixture)

    def test_aliases_and_outside_repository_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as outer:
            outside = Path(outer).resolve() / "probe.atto"
            outside.write_text("untrusted")
            self.root.joinpath("external.atto").symlink_to(outside)
            self.fixture["llvm"]["rejection_probes"][0]["path"] = "external.atto"
            with self.assertRaisesRegex(RuntimeError, "outside-repository"):
                self.load()
        self.fixture["llvm"]["rejection_probes"][0]["path"] = "../probe.atto"
        with self.assertRaises(RuntimeError):
            self.load()

    def test_duplicate_canonical_probe_cannot_create_two_evidence_entries(self):
        self.root.joinpath("probe-alias.atto").symlink_to(self.root / "probe.atto")
        probes = self.fixture["llvm"]["rejection_probes"]
        probes.append(dict(probes[0], path="probe-alias.atto"))
        with self.assertRaisesRegex(RuntimeError, "Duplicate LLVM rejection probe"):
            self.load()

    def test_rejection_must_match_exit_code_and_exact_expected_diagnostic(self):
        expected = self.fixture["llvm"]["rejection_probes"][0]
        good = subprocess.CompletedProcess([], 1, "", expected["diagnostic"] + "\n")
        checker.check_rejection(good, expected)
        for wrong in (
            subprocess.CompletedProcess([], 0, "", expected["diagnostic"]),
            subprocess.CompletedProcess([], 1, "unexpected stdout", expected["diagnostic"]),
            subprocess.CompletedProcess([], 1, "", "unrelated failure"),
        ):
            with self.assertRaises(RuntimeError):
                checker.check_rejection(wrong, expected)

    def test_llvm_positive_control_rejects_wrong_main_abi(self):
        checker.check_positive(subprocess.CompletedProcess([], 0, "define i32 @main() { ret i32 0 }\n", ""))
        for code, stdout in ((0, "define i64 @main() { ret i64 0 }"), (1, "define i32 @main() {}"), (0, "")):
            with self.assertRaises(RuntimeError):
                checker.check_positive(subprocess.CompletedProcess([], code, stdout, ""))


if __name__ == "__main__":
    unittest.main()
