"""Real host process checks for bounded compiler output; no compiler guest implied."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "bounded_process_under_test", Path(__file__).with_name("bounded_process.py")
)
bounded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bounded)


class BoundedProcessHostContracts(unittest.TestCase):
    def command(self, source):
        return [sys.executable, "-c", source]

    def test_exact_aggregate_stdout_stderr_budget_passes(self):
        cmd = self.command("import os;os.write(1,b'A'*2048);os.write(2,b'B'*2048)")
        result = bounded.run_bounded(cmd, max_bytes=4096)
        self.assertEqual((result.returncode, len(result.stdout), len(result.stderr)), (0, 2048, 2048))

    def test_one_byte_over_aggregate_budget_fails(self):
        cmd = self.command("import os;os.write(1,b'A'*2048);os.write(2,b'B'*2048)")
        with self.assertRaisesRegex(RuntimeError, "output budget exceeded"):
            bounded.run_bounded(cmd, max_bytes=4095)

    def test_large_stdout_is_killed_without_unbounded_buffering(self):
        cmd = self.command("import os;os.write(1,b'X'*2000000)")
        with self.assertRaisesRegex(RuntimeError, "output budget exceeded"):
            bounded.run_bounded(cmd, max_bytes=32768)

    def test_timeout_raises_instead_of_claiming_success(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            bounded.run_bounded(self.command("import time;time.sleep(2)"), timeout=0.05)

    def test_invalid_utf8_is_not_silently_replaced(self):
        with self.assertRaises(UnicodeDecodeError):
            bounded.run_bounded(self.command("import os;os.write(1,b'\\xff')"))

    def test_nonzero_child_exit_is_preserved(self):
        result = bounded.run_bounded(self.command("import sys;print('failed');sys.exit(7)"))
        self.assertEqual((result.returncode, result.stdout), (7, "failed\n"))

    def test_invalid_limits_fail_before_subprocess_spawn(self):
        for options in ({"timeout": 0}, {"timeout": -1}, {"max_bytes": 0}, {"max_bytes": -1}):
            with self.subTest(options=options):
                with patch.object(bounded.subprocess, "Popen", side_effect=AssertionError("spawned")):
                    with self.assertRaises(ValueError):
                        bounded.run_bounded(self.command("print('not executed')"), **options)


if __name__ == "__main__":
    unittest.main(verbosity=2)
