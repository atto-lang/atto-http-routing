#!/usr/bin/env python3
"""Negative contracts for backend admission; never substitutes for package tests."""
import importlib.util
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

    def test_symlinked_compiler_checkout_is_rejected(self):
        compiler = self.root/'source'
        compiler.mkdir()
        (self.root/'source-link').symlink_to(compiler, target_is_directory=True)
        (self.root/'SOURCE_REF').write_text('0'*40)
        with patch.dict(os.environ, {'BACKEND_TEST_SOURCE':str(self.root/'source-link')}):
            with self.assertRaisesRegex(RuntimeError, 'Compiler checkout path must not be a symlink'):
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

if __name__ == '__main__': unittest.main()
