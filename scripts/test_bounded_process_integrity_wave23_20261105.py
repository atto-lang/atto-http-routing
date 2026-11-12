"""Exact two-stream byte-budget and decoding controls for real run_bounded."""
import subprocess
import sys
import unittest
from bounded_process import run_bounded


class BoundedOutputIntegrityWave23(unittest.TestCase):
    @staticmethod
    def invoke(source, **kwargs):
        return run_bounded([sys.executable, '-c', source], timeout=5, **kwargs)

    def test_two_streams_at_exact_combined_budget_keep_distinct_bytes(self):
        code = "import sys;sys.stdout.buffer.write(b'ABCDEFGH');sys.stderr.buffer.write(b'12345678')"
        result = self.invoke(code, max_bytes=16)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, 'ABCDEFGH', '12345678'))

    def test_combined_stream_budget_cannot_be_applied_per_stream(self):
        code = "import sys;sys.stdout.buffer.write(b'ABCDEFGH');sys.stderr.buffer.write(b'12345678')"
        with self.assertRaisesRegex(RuntimeError, 'budget exceeded'):
            self.invoke(code, max_bytes=15)

    def test_failing_subprocess_keeps_both_diagnostic_streams(self):
        result = self.invoke("import sys;print('out');sys.stderr.write('err\\n');sys.exit(7)", max_bytes=32)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, 'out\n', 'err\n'))

    def test_invalid_utf8_is_rejected_instead_of_lossy_decoded(self):
        with self.assertRaises(UnicodeDecodeError):
            self.invoke("import sys;sys.stderr.buffer.write(bytes([255]))", max_bytes=8)

    def test_invalid_budget_rejected_before_child_spawn(self):
        for value in (0, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.invoke("raise Exception('should not execute')", max_bytes=value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
