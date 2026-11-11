# Router decision safety + Java compiler integration

Status: **candidate, NOT_EXECUTED at this combined head** (2026-11-10).

## Source identity
- Router base security branch: PR #43, after decision path-shape checks,
  local-table lookup replay, and rejection of empty named segments.
- Compiler pin: `SOURCE_REF=e6098659c2e1641564bb5835b4dbb92a6a00b1a8`,
  copied from router PR #49 / Spin PR #39; this is a compiler PR snapshot,
  not an assertion that the compiler patch has merged.
- `LLVM_SOURCE_REF` is unchanged.

## Fail-closed route contract
The router checks decision indexes before accessing arrays, checks target
metadata, validates literal and nonempty named path segments, and replays the
immutable route table with a bounded search budget. A foreign Decision whose
selected endpoint differs from the receiving router is rejected for capture
and Allow access.

**Security limit:** a Decision is still a data object, not a cryptographic
or unforgeable generation capability. Two distinct router instances with
identical paths, indexes, handlers and policy metadata may still accept each
other's data. Treat Decisions as supervisor-local results, not authorizations.
Never send the Decision itself across actor boundaries; transfer validated,
immutable scalar route data using a separately owned request capability.
A future breaking API should keep routing authority private to the router.

## Mandatory exact-head evidence
1. Verify current PR head, tree SHA, `SOURCE_REF`, `LLVM_SOURCE_REF`
   and all dependency content before execution.
2. Use a clean compiler checkout at exactly `SOURCE_REF`, verify its
   physical Git tree, and run `scripts/test.sh`.
3. Capture actual compiler frontend result, real guest `.atto` execution
   and byte-identical `tests/expected.txt`, including rejection of empty
   named captures, false foreign captures and bogus Allow.
4. Record nonzero workflow steps, runner, run attempt, compiler and router
   head/tree, full test logs and exit codes. A source-free host canary
   proves runner capacity only.
5. Obtain independent review before marking this candidate merge-ready.

Do not infer Native Image, LLVM/.NET HTTP parity, complete request-target
parsing, or hot-upgrade generation fencing from these tests.
