#!/usr/bin/env python3
"""Check pinned compiler provenance and execute the declared backend contract."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from bounded_process import run_bounded

ROOT = Path(__file__).resolve().parents[1]

def git(directory, *args):
    return subprocess.check_output(['git', '-C', str(directory), *args], text=True).strip()

def require_source(variable, pin):
    raw = os.environ.get(variable)
    if not raw:
        raise RuntimeError(f'Set {variable} to the pinned compiler checkout')
    source_input = Path(raw).absolute()
    # Resolve only after checking every path component. An alias in an
    # ancestor directory is still an indirect compiler checkout and can
    # silently change the source to which an exact commit pin applies.
    for component in (source_input, *source_input.parents):
        if component.is_symlink():
            raise RuntimeError('Compiler checkout path must not contain symlinks')
    source = source_input.resolve()
    expected = local_file(pin).read_text().strip()
    if not re.fullmatch('[0-9a-f]{40}', expected):
        raise RuntimeError(f'Invalid {pin}')
    if Path(git(source, 'rev-parse', '--show-toplevel')).resolve() != source:
        raise RuntimeError('Compiler directory must be its own Git checkout')
    if git(source, 'rev-parse', 'HEAD') != expected:
        raise RuntimeError(f'Compiler revision differs from {pin}')
    if git(source, 'status', '--porcelain', '--untracked-files=all'):
        raise RuntimeError('Compiler checkout must be clean')
    return source

def local_file(relative):
    if not isinstance(relative, str) or not relative:
        raise RuntimeError('Contract path must be a nonempty string')
    requested = Path(relative)
    if requested.is_absolute() or '..' in requested.parts:
        raise RuntimeError('Contract paths must be relative and cannot traverse parents')
    path = ROOT
    # Explicitly reject symlinks at EVERY component, even when the link
    # resolves to an otherwise allowed in-repository file/directory.
    for component in requested.parts:
        path = path / component
        if path.is_symlink():
            raise RuntimeError(f'Symlinked contract path is forbidden: {relative}')
    root = ROOT.resolve()
    resolved = path.resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise RuntimeError(f'Missing or outside-repository contract file: {relative}')
    return resolved

def load_contract():
    contract = json.loads(local_file('BACKENDS.json').read_text())
    if not isinstance(contract, dict) or set(contract) != {'java', 'llvm'}:
        raise RuntimeError('Expected java and llvm backend contracts')
    java, llvm = contract['java'], contract['llvm']
    if not isinstance(java, dict) or not isinstance(llvm, dict):
        raise RuntimeError('Backend contracts must be objects')
    if java.get('pin') != 'SOURCE_REF' or llvm.get('pin') != 'LLVM_SOURCE_REF':
        raise RuntimeError('Unexpected compiler pin files')
    if java.get('execution') not in ('supported', 'partial') or llvm.get('execution') != 'unsupported':
        raise RuntimeError('Unsupported execution contract; update the checker with the tests')
    local_file(java.get('suite'))
    probes = llvm.get('rejection_probes')
    if not isinstance(probes, list) or not probes:
        raise RuntimeError('LLVM rejection probes must be nonempty')
    seen = set()
    for probe in probes:
        if not isinstance(probe, dict) or set(probe) != {'path', 'diagnostic'}:
            raise RuntimeError('Each probe needs a path and exact diagnostic')
        path = local_file(probe['path'])
        if path in seen:
            raise RuntimeError('Duplicate LLVM rejection probe')
        seen.add(path)
        diagnostic = probe['diagnostic']
        if not isinstance(diagnostic, str) or '\n' in diagnostic or not (diagnostic.startswith('oreslang-llvmc: expected ') or re.fullmatch(r'oreslang-llvmc: final class field requires declaration-site initializer at byte [0-9]+', diagnostic)):
            raise RuntimeError('Expected a specific unsupported-syntax diagnostic')
    return contract

def check_rejection(result, probe):
    if result.returncode != 1 or result.stdout.strip() or result.stderr.strip() != probe['diagnostic']:
        raise RuntimeError(f"Unexpected rejection result for {probe['path']}: exit={result.returncode}\n{result.stderr}")

def check_positive(result):
    if result.returncode or not re.search(r'^define i32 @main\(\)', result.stdout, re.MULTILINE):
        raise RuntimeError('LLVM positive control failed; rejection is not evidence of compatibility: ' + result.stderr)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backend', choices=['java', 'llvm'])
    args = parser.parse_args()
    contract = load_contract()
    if args.backend == 'java':
        require_source('ORESLANG_SOURCE_DIR', 'SOURCE_REF')
        env = dict(os.environ)
        env.setdefault('ORESLANG_COMPILER', str(ROOT / 'scripts/compiler.sh'))
        env.setdefault('ORESLANG_BIN', env['ORESLANG_COMPILER'])
        return subprocess.run(['bash', str(local_file(contract['java']['suite']))], cwd=ROOT, env=env, timeout=180).returncode
    source = require_source('ORESLANG_LLVM_SOURCE_DIR', 'LLVM_SOURCE_REF')
    compiler = Path(os.environ.get('ORESLANG_LLVM_COMPILER', str(source / 'build/oreslang-llvmc'))).resolve()
    if not compiler.is_file() or not os.access(compiler, os.X_OK):
        raise RuntimeError(f'Build oreslang-llvmc first: {compiler}')
    with tempfile.TemporaryDirectory(prefix='ores-backend-') as directory:
        baseline = Path(directory) / 'baseline.ores'
        baseline.write_text('pub fnc main(): int { return 42; }\n')
        positive = run_bounded([str(compiler), str(baseline)])
        check_positive(positive)
        for probe in contract['llvm']['rejection_probes']:
            entry = local_file(probe['path'])
            result = run_bounded([str(compiler), str(entry)])
            check_rejection(result, probe)
            print(f"LLVM rejected {probe['path']}: {result.stderr.strip()}")
    print('LLVM rejection contract: PASS (package execution remains unsupported)')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as failure:
        raise SystemExit(f'backend check failed: {failure}')
