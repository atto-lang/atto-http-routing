"""Regression for bounded compiler-wrapper process-tree retirement (POSIX)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bounded_process import run_bounded


@unittest.skipUnless(os.name == 'posix' and Path('/proc').is_dir(),
                     'requires POSIX/Linux process-state inspection')
class BoundedDescendantTests(unittest.TestCase):
    @staticmethod
    def assert_not_running(pid):
        stat_path = Path(f'/proc/{pid}/stat')
        if stat_path.exists():
            state = stat_path.read_text().split(') ', 1)[1][0]
            if state not in ('Z', 'X'):
                raise AssertionError(f'descendant {pid} remains running: {state}')

    def test_normal_and_output_budget(self):
        result = run_bounded([sys.executable, '-c',
                              'import sys;print("ok");sys.stderr.write("err\\n")'])
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, 'ok\n', 'err\n'))
        with self.assertRaisesRegex(RuntimeError, 'output budget exceeded'):
            run_bounded([sys.executable, '-c', 'print("x"*16384)'],
                        max_bytes=128)

    def test_timeout_retires_compiler_descendant(self):
        with tempfile.TemporaryDirectory() as temp:
            pidfile = Path(temp, 'descendant.pid')
            parent = (
                'import subprocess,sys,time\n'
                'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],'
                'stdout=sys.stdout,stderr=sys.stderr)\n'
                f'open({str(pidfile)!r},"w").write(str(p.pid))\n'
                'time.sleep(30)\n'
            )
            with self.assertRaises(subprocess.TimeoutExpired):
                run_bounded([sys.executable, '-c', parent], timeout=2)
            self.assertTrue(pidfile.exists(), 'compiler did not spawn descendant')
            self.assert_not_running(int(pidfile.read_text()))

    def test_orphaned_pipe_is_rejected_and_descendant_reaped(self):
        with tempfile.TemporaryDirectory() as temp:
            pidfile = Path(temp, 'descendant.pid')
            parent = (
                'import os,subprocess,sys\n'
                'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],'
                'stdout=sys.stdout,stderr=sys.stderr)\n'
                f'open({str(pidfile)!r},"w").write(str(p.pid))\n'
                'os._exit(0)\n'
            )
            with self.assertRaisesRegex(RuntimeError, 'output pipes remained open'):
                run_bounded([sys.executable, '-c', parent], timeout=3)
            self.assertTrue(pidfile.exists())
            self.assert_not_running(int(pidfile.read_text()))


if __name__ == '__main__':
    unittest.main()
