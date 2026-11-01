#!/usr/bin/env python3
"""Negative contracts for backend admission; never substitutes for package tests."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('checker', Path(__file__).with_name('check-backend.py'))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
guest_spec = importlib.util.spec_from_file_location('guest_runner', Path(__file__).with_name('run-guest.py'))
guest_runner = importlib.util.module_from_spec(guest_spec)
guest_spec.loader.exec_module(guest_runner)

class BackendChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.patch = patch.object(checker, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.root/'suite.sh').write_text('exit 0\n')
        (self.root/'probe.ores').write_text('import unsupported;\n')
        self.contract = {'java': {'pin': 'SOURCE_REF', 'suite': 'suite.sh', 'execution': 'supported'},
                         'llvm': {'pin': 'LLVM_SOURCE_REF', 'execution': 'unsupported', 'rejection_probes': [
                             {'path': 'probe.ores', 'diagnostic': 'oreslang-llvmc: expected fnc or routine at byte 0'}]}}
    def load(self):
        (self.root/'BACKENDS.json').write_text(json.dumps(self.contract))
        return checker.load_contract()
    def test_valid_contract(self):
        self.assertEqual(self.load(), self.contract)
    def test_precise_final_field_boundary(self):
        prefix='oreslang-llvmc: final class field requires declaration-site initializer at byte '
        self.contract['llvm']['rejection_probes'][0]['diagnostic']=prefix+'570'
        self.assertEqual(self.load(), self.contract)
        for suffix in ('bad', '570 extra error', ''):
            self.contract['llvm']['rejection_probes'][0]['diagnostic']=prefix+suffix
            with self.subTest(suffix=suffix), self.assertRaises(RuntimeError): self.load()
    def test_native_i32_os_entrypoint(self):
        valid='define i32 @main() {\n ret i32 42\n}\n'
        checker.check_positive(subprocess.CompletedProcess([],0,valid,''))
        for code,ir in [(1,valid),(-11,valid),(0,''),(0,'define i64 @main() { ret i64 42 }')]:
            with self.subTest(code=code,ir=ir), self.assertRaises(RuntimeError):
                checker.check_positive(subprocess.CompletedProcess([],code,ir,'failure'))
    def test_empty_probes_rejected(self):
        self.contract['llvm']['rejection_probes'] = []
        with self.assertRaises(RuntimeError): self.load()
    def test_duplicate_probes_rejected(self):
        self.contract['llvm']['rejection_probes'] *= 2
        with self.assertRaises(RuntimeError): self.load()
    def test_missing_probe_rejected(self):
        (self.root/'probe.ores').unlink()
        with self.assertRaises(RuntimeError): self.load()
    def test_escape_paths_rejected(self):
        for path in ('../outside', str(self.root/'probe.ores')):
            with self.subTest(path=path), self.assertRaises(RuntimeError): checker.local_file(path)
    def test_symlink_escape_rejected(self):
        (self.root/'escape').symlink_to('/etc/hosts')
        with self.assertRaises(RuntimeError): checker.local_file('escape')
    def test_in_repository_symlink_file_is_rejected(self):
        (self.root/'linked.ores').symlink_to(self.root/'probe.ores')
        with self.assertRaisesRegex(RuntimeError, 'Symlinked contract path'):
            checker.local_file('linked.ores')

    def test_in_repository_symlink_parent_is_rejected(self):
        (self.root/'real').mkdir()
        (self.root/'real'/'probe.ores').write_text('valid')
        (self.root/'alias').symlink_to(self.root/'real', target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'Symlinked contract path'):
            checker.local_file('alias/probe.ores')

    def test_parent_traversal_even_when_normalized_inside_is_rejected(self):
        (self.root/'sub').mkdir()
        for candidate in ('sub/../probe.ores', 'sub/../../probe.ores', ''):
            with self.subTest(candidate=candidate), self.assertRaises(RuntimeError):
                checker.local_file(candidate)

    def test_symlinked_backend_contract_file_is_rejected(self):
        self.load()
        actual = self.root/'BACKENDS.json'
        actual.rename(self.root/'saved-contract.json')
        actual.symlink_to(self.root/'saved-contract.json')
        with self.assertRaisesRegex(RuntimeError, 'Symlinked contract path'):
            checker.load_contract()

    def test_symlinked_compiler_pin_is_rejected(self):
        compiler = self.root/'source'
        compiler.mkdir()
        def git(*args):
            return subprocess.check_output(['git','-C',str(compiler),*args],text=True).strip()
        git('init','-q')
        (compiler/'tracked').write_text('source')
        git('add','tracked')
        git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','source')
        (self.root/'pinned-sha').write_text(git('rev-parse','HEAD'))
        (self.root/'SOURCE_REF').symlink_to(self.root/'pinned-sha')
        with patch.dict(os.environ, {'BACKEND_TEST_SOURCE':str(compiler)}):
            with self.assertRaisesRegex(RuntimeError, 'Symlinked contract path'):
                checker.require_source('BACKEND_TEST_SOURCE', 'SOURCE_REF')

    def test_symlinked_ancestor_of_compiler_checkout_is_rejected(self):
        real_parent = self.root/'real-parent'
        real_parent.mkdir()
        source = real_parent/'compiler'
        source.mkdir()
        (self.root/'compiler-parent-link').symlink_to(real_parent, target_is_directory=True)
        (self.root/'SOURCE_REF').write_text('0'*40)
        via_alias = self.root/'compiler-parent-link'/'compiler'
        self.assertFalse(via_alias.is_symlink())
        with patch.dict(os.environ, {'BACKEND_TEST_SOURCE':str(via_alias)}):
            with self.assertRaisesRegex(RuntimeError, 'Compiler checkout path must not contain symlinks'):
                checker.require_source('BACKEND_TEST_SOURCE', 'SOURCE_REF')

    def test_symlinked_compiler_checkout_is_rejected(self):
        compiler = self.root/'source'
        compiler.mkdir()
        (self.root/'source-link').symlink_to(compiler, target_is_directory=True)
        (self.root/'SOURCE_REF').write_text('0'*40)
        with patch.dict(os.environ, {'BACKEND_TEST_SOURCE':str(self.root/'source-link')}):
            with self.assertRaisesRegex(RuntimeError, 'Compiler checkout path must not contain symlinks'):
                checker.require_source('BACKEND_TEST_SOURCE', 'SOURCE_REF')

    def test_changed_execution_status_rejected(self):
        self.contract['llvm']['execution'] = 'supported'
        with self.assertRaises(RuntimeError): self.load()
    def test_malformed_contract_rejected(self):
        for value in ([], None, {'java': None, 'llvm': []}):
            self.contract = value
            with self.subTest(value=value), self.assertRaises(RuntimeError): self.load()
    def test_internal_error_not_expected_rejection(self):
        probe=self.contract['llvm']['rejection_probes'][0]
        for code,out,err in [(0,'',probe['diagnostic']), (1,'IR',probe['diagnostic']),
                             (1,'','oreslang-llvmc: internal compiler error'), (-11,'',probe['diagnostic']),
                             (1,'',probe['diagnostic']+'\nadditional failure')]:
            with self.subTest(code=code,out=out,err=err), self.assertRaises(RuntimeError):
                checker.check_rejection(subprocess.CompletedProcess([],code,out,err),probe)
        checker.check_rejection(subprocess.CompletedProcess([],1,'',probe['diagnostic']+'\n'),probe)
    def test_provenance_fails_closed(self):
        source=self.root/'source'
        source.mkdir()
        def git(*args):
            return subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
        git('init','-q')
        (source/'tracked').write_text('original')
        git('add','tracked')
        git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture')
        pin=self.root/'SOURCE_REF'
        pin.write_text(git('rev-parse','HEAD'))
        with patch.dict(os.environ, {'BACKEND_TEST_SOURCE':str(source)}):
            self.assertEqual(checker.require_source('BACKEND_TEST_SOURCE','SOURCE_REF'),source)
            for revision in ('main','0'*40):
                pin.write_text(revision)
                with self.assertRaises(RuntimeError): checker.require_source('BACKEND_TEST_SOURCE','SOURCE_REF')
            pin.write_text(git('rev-parse','HEAD'))
            (source/'untracked').write_text('dirty')
            with self.assertRaises(RuntimeError): checker.require_source('BACKEND_TEST_SOURCE','SOURCE_REF')
            (source/'untracked').unlink()
            (source/'tracked').write_text('changed')
            with self.assertRaises(RuntimeError): checker.require_source('BACKEND_TEST_SOURCE','SOURCE_REF')
            with patch.object(checker,'git',side_effect=subprocess.CalledProcessError(128,['git'])):
                with self.assertRaises(subprocess.CalledProcessError): checker.require_source('BACKEND_TEST_SOURCE','SOURCE_REF')

class BoundedCompilerOutput(unittest.TestCase):
    def test_real_process_streams_preserved(self):
        result = checker.run_bounded([sys.executable, '-c', "import sys;print('IR');print('diagnostic',file=sys.stderr);sys.exit(1)"])
        self.assertEqual((result.returncode, result.stdout, result.stderr), (1, 'IR\n', 'diagnostic\n'))
    def test_output_floods_fail_before_contract_admission(self):
        for fd in (1, 2):
            with self.subTest(fd=fd), self.assertRaisesRegex(RuntimeError, 'output budget'):
                checker.run_bounded([sys.executable, '-c', f"import os;os.write({fd},b'x'*2000000)"], max_bytes=32768)
    def test_timeout_kills_process(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            checker.run_bounded([sys.executable, '-c', 'import time;time.sleep(10)'], timeout=0.1)
    def test_invalid_utf8_rejected(self):
        with self.assertRaises(UnicodeDecodeError):
            checker.run_bounded([sys.executable, '-c', "import os;os.write(1,bytes([255]))"])

class CompilerLauncherContracts(unittest.TestCase):
    """Exercise the actual Bash launcher with Git and Java-mock receipts."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        scripts = self.root/'scripts'
        scripts.mkdir()
        launcher = Path(__file__).with_name('compiler.sh')
        (scripts/'compiler.sh').write_text(launcher.read_text())
        self.script = scripts/'compiler.sh'
        self.source = self.root/'source'
        self.source.mkdir()
        subprocess.run(['git', '-C', str(self.source), 'init', '-q'], check=True)
        (self.source/'pom.xml').write_text('fixture')
        subprocess.run(['git', '-C', str(self.source), 'add', 'pom.xml'], check=True)
        subprocess.run(['git', '-C', str(self.source), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid',
                        'commit', '-qm', 'source'], check=True)
        self.commit = subprocess.check_output(
            ['git', '-C', str(self.source), 'rev-parse', 'HEAD'], text=True
        ).strip()
        # The compiler's target/ output is generated/ignored, not untracked
        # source. Ensure source cleanliness checks still catch other changes.
        (self.source/'.git/info/exclude').write_text('target/\n')
        (self.root/'SOURCE_REF').write_text(self.commit + '\n')
        self.classes = self.source/'target/classes'
        self.main_class = self.classes/'dev/oreslang/launcher/OresMain.class'
        self.main_class.parent.mkdir(parents=True)
        self.main_class.write_bytes(b'fixture-class')
        self.classpath = self.source/'target/classpath.txt'
        self.classpath.write_text('dependency.jar\n')
        self.java_log = self.root/'java-log'
        self.java = self.root/'java-mock'
        self.java.write_text('#!/bin/sh\nprintf "invoked\\n" >> "$COMPILER_LAUNCH_LOG"\n')
        self.java.chmod(0o755)

    def execute(self, checkout=None):
        env = dict(os.environ,
                   ORESLANG_SOURCE_DIR=str(checkout or self.source),
                   ORES_JAVA=str(self.java),
                   COMPILER_LAUNCH_LOG=str(self.java_log))
        return subprocess.run(['bash', str(self.script), '--check', 'test.ores'],
                              capture_output=True, text=True, env=env)

    def assert_no_java(self, result, expected):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)
        self.assertFalse(self.java_log.exists(), 'untrusted compiler invoked Java')

    def test_exact_pinned_compiler_launcher_runs(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.java_log.read_text(), 'invoked\n')

    def test_wrong_compiler_revision_never_invokes_java(self):
        (self.root/'SOURCE_REF').write_text('0'*40 + '\n')
        self.assert_no_java(self.execute(), 'compiler revision differs')

    def test_empty_compiler_classpath_is_rejected(self):
        self.classpath.write_text('')
        self.assert_no_java(self.execute(), 'classpath must be nonempty')

    def test_missing_compiler_entrypoint_is_rejected(self):
        self.main_class.unlink()
        self.assert_no_java(self.execute(), 'entrypoint class is missing')

    def test_symlinked_compiler_classpath_is_rejected(self):
        external = self.root/'external-classpath'
        external.write_text('preserved')
        self.classpath.unlink()
        self.classpath.symlink_to(external)
        self.assert_no_java(self.execute(), 'classpath must be nonempty')
        self.assertEqual(external.read_text(), 'preserved')

    def test_symlinked_classes_directory_is_rejected(self):
        external = self.root/'external-classes'
        external.mkdir()
        self.classes.rename(self.source/'target/saved-classes')
        self.classes.symlink_to(external, target_is_directory=True)
        self.assert_no_java(self.execute(), 'output directory must not be a symlink')

    def test_symlinked_compiler_checkout_is_rejected(self):
        alias = self.root/'source-alias'
        alias.symlink_to(self.source, target_is_directory=True)
        self.assert_no_java(self.execute(alias), 'compiler checkout path must not contain symlinks')

    def test_symlinked_checkout_parent_is_rejected(self):
        alias = self.root/'parent-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        via_alias = alias/'source'
        self.assertFalse(via_alias.is_symlink())
        self.assert_no_java(self.execute(via_alias), 'compiler checkout path must not contain symlinks')

    def test_parent_traversal_checkout_path_is_rejected(self):
        via_parent = self.source/'..'/'source'
        self.assert_no_java(self.execute(via_parent), 'compiler checkout must not contain parent traversal')

    def test_untracked_source_file_is_rejected_before_java(self):
        (self.source/'untracked').write_text('unreviewed')
        self.assert_no_java(self.execute(), 'compiler checkout must be clean')

    def test_modified_tracked_source_is_rejected_before_java(self):
        (self.source/'pom.xml').write_text('modified since pin')
        self.assert_no_java(self.execute(), 'compiler checkout must be clean')

    def test_nested_directory_cannot_claim_pinned_git_root(self):
        nested = self.source/'nested'
        nested.mkdir()
        self.assert_no_java(self.execute(nested), 'compiler checkout must be its own Git root')

    def test_symlinked_compiler_pin_is_rejected(self):
        pin = self.root/'SOURCE_REF'
        pin.rename(self.root/'saved-pin')
        pin.symlink_to(self.root/'saved-pin')
        self.assert_no_java(self.execute(), 'SOURCE_REF is missing or is a symlink')

class GuestProcessAdmission(unittest.TestCase):
    """Executed host subprocess tests: no Oreslang guest semantics implied."""

    def run_guest(self, args, *, timeout=2, max_bytes=32768):
        with patch.object(guest_runner, 'TIMEOUT_SECONDS', timeout), \
             patch.object(guest_runner, 'MAX_OUTPUT_BYTES', max_bytes), \
             patch.object(sys, 'argv', ['run-guest.py', *args]), \
             patch('sys.stdout', new_callable=io.StringIO) as stdout, \
             patch('sys.stderr', new_callable=io.StringIO) as stderr:
            code = guest_runner.main()
            return code, stdout.getvalue(), stderr.getvalue()

    def test_missing_compiler_arguments_rejected(self):
        code, stdout, stderr = self.run_guest([])
        self.assertEqual(code, 64)
        self.assertEqual(stdout, '')
        self.assertIn('usage:', stderr)

    def test_host_stdout_and_stderr_preserved(self):
        program = "import sys;print('output');print('diagnostic',file=sys.stderr)"
        code, stdout, stderr = self.run_guest([sys.executable, '-c', program])
        self.assertEqual((code, stdout, stderr), (0, 'output\n', 'diagnostic\n'))

    def test_nonzero_exit_preserved_without_false_pass(self):
        code, stdout, stderr = self.run_guest(
            [sys.executable, '-c', "import sys;print('invalid',file=sys.stderr);sys.exit(17)"]
        )
        self.assertEqual((code, stdout, stderr), (17, '', 'invalid\n'))

    def test_stdout_budget_overflow_rejects_all_partial_output(self):
        code, stdout, stderr = self.run_guest(
            [sys.executable, '-c', "import os;os.write(1,b'A'*200000)"],
            max_bytes=4096
        )
        self.assertEqual(code, 70)
        self.assertEqual(stdout, '')
        self.assertIn('budget exceeded', stderr)

    def test_stderr_budget_overflow_rejects_all_partial_output(self):
        code, stdout, stderr = self.run_guest(
            [sys.executable, '-c', "import os;os.write(2,b'B'*200000)"],
            max_bytes=4096
        )
        self.assertEqual(code, 70)
        self.assertEqual(stdout, '')
        self.assertIn('budget exceeded', stderr)

    def test_timeout_rejects_guest_without_partial_success(self):
        code, stdout, stderr = self.run_guest(
            [sys.executable, '-c', "import time;time.sleep(3)"],
            timeout=0.1
        )
        self.assertEqual(code, 124)
        self.assertEqual(stdout, '')
        self.assertIn('process timeout', stderr)

    def test_non_utf8_output_is_never_treated_as_diagnostic_success(self):
        code, stdout, stderr = self.run_guest(
            [sys.executable, '-c', "import os;os.write(1,bytes([255]))"]
        )
        self.assertEqual(code, 70)
        self.assertEqual(stdout, '')
        self.assertIn('UnicodeDecodeError', stderr)


if __name__ == '__main__': unittest.main()
