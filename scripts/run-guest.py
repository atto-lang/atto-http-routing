#!/usr/bin/env python3
"""Execute a pinned Oreslang compiler guest with bounded output and duration.

This is a resource-admission boundary, not a compiler attestation. The caller
must already have verified the checkout revision and tool provenance.
"""
import os
from pathlib import Path
import subprocess
import sys

from bounded_process import run_bounded

TIMEOUT_SECONDS = 120
MAX_OUTPUT_BYTES = 2 * 1024 * 1024


def main():
    if len(sys.argv) < 3:
        print("usage: run-guest.py COMPILER ARG...", file=sys.stderr)
        return 64
    try:
        result = run_bounded(sys.argv[1:], timeout=TIMEOUT_SECONDS, max_bytes=MAX_OUTPUT_BYTES)
    except subprocess.TimeoutExpired:
        print("guest runner: process timeout", file=sys.stderr)
        return 124
    except (RuntimeError, OSError, UnicodeDecodeError, ValueError) as error:
        # Never forward partial output after a budget violation: the negative
        # diagnostic suite must not accept partial stderr as an expected error.
        print(f"guest runner: {error.__class__.__name__}: {error}", file=sys.stderr)
        return 70
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    code = result.returncode
    if code < 0:
        return 128 + (-code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
