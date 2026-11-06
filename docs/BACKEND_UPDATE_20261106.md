# Compiler main tips — 2026-11-06

Both pins move off the temporary `.atto` integration branch to plain `main`:

- `SOURCE_REF`: oreslang-source.java `main` `67ff8ad05b`, which contains #2460 (`.atto`
  admission) and #2497 (formatting-borrow fix).
- `LLVM_SOURCE_REF`: oreslang-source.llvm `main` `16e986c4c7` (LLVM 21.1.8). Both
  `.atto` entry points still reject at the same exact boundaries; `BACKENDS.json` is unchanged.

## Local evidence (macOS arm64, JDK 21.0.12)

- `scripts/check-backend.py java` against a clean checkout at exactly `SOURCE_REF`: router semantics PASS.
- `scripts/check-backend.py llvm` at exactly `LLVM_SOURCE_REF`: PASS.
- `scripts/test-backend-checker.py` and the four `scripts/test_*_2026110*.py` suites: OK.
  `scripts/test-runner.sh`: PASS. `tests/source-ref-forward-port.sh`: PASS.

Java `main` tracks two PR templates whose names differ only in case
([oreslang-source.java#2567](https://github.com/ores-truffle-oreslang/oreslang-source.java/issues/2567)),
so every macOS checkout looks dirty. The local Java checkout used
`git update-index --skip-worktree .github/pull_request_template.md`, for that path only.

Not gated, and failing on both this and the previous Java pin:
`tests/test_std_harness_regressions.ores`. At `67ff8ad05b` it aborts with
`unknown Future instance member passed`; at `00afec5384` it fails to parse
`ores.std/testing` (line 140).
