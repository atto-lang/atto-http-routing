"""Host subprocess outcome and budget regression matrix; no guest execution."""
from pathlib import Path
import importlib.util
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("bounded", Path(__file__).with_name("bounded_process.py"))
bounded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bounded)


class BoundedProcessOutcomeWave21(unittest.TestCase):
    def run_child(self, body, **kwargs):
        return bounded.run_bounded([sys.executable, "-c", body], **kwargs)

    def test_stdout_and_stderr_are_not_conflated(self):
        value = self.run_child("import os;os.write(1,b'out\\n');os.write(2,b'err\\n')")
        self.assertEqual((value.returncode, value.stdout, value.stderr), (0, "out\n", "err\n"))

    def test_nonzero_exit_preserves_error_code(self):
        value = self.run_child("import sys;sys.stderr.write('failure');sys.exit(23)")
        self.assertEqual((value.returncode, value.stderr), (23, "failure"))

    def test_empty_output_admitted_when_child_exits_successfully(self):
        value = self.run_child("pass", max_bytes=1)
        self.assertEqual((value.returncode, value.stdout, value.stderr), (0, "", ""))

    def test_exact_one_byte_budget(self):
        value = self.run_child("import os;os.write(2,b'z')", max_bytes=1)
        self.assertEqual((value.stderr, value.stdout), ("z", ""))

    def test_two_bytes_over_one_byte_budget(self):
        with self.assertRaisesRegex(RuntimeError, "output budget exceeded"):
            self.run_child("import os;os.write(2,b'zz')", max_bytes=1)

    def test_invalid_stderr_encoding_is_rejected(self):
        with self.assertRaises(UnicodeDecodeError):
            self.run_child("import os;os.write(2,bytes([255]))")

    def test_invalid_timeout_never_starts_process(self):
        with patch.object(bounded.subprocess, "Popen", side_effect=AssertionError("spawned")):
            with self.assertRaises(ValueError):
                self.run_child("pass", timeout=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
