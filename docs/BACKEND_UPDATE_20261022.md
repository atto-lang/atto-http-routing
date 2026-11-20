# Runtime compatibility update — 2026-10-22

The Java pin includes the pointerless borrow parser and fixes the accompanying
regressions to use `rt borrow mut owner`. The runtime ownership checks themselves
are unchanged by that spelling repair: shared/exclusive aliases still reject,
distinct owners execute, and the shared Java/LLVM source corpus remains identical.
The production Java baseline passed 317 tests across 38 ownership, actor, HTTP,
mutex and asynchronous I/O suites, without skips. Its later test-only update
expands the shared corpus to 162 vectors and passes the affected four-method suite.

The LLVM pin integrates current main with bounded module linking, scalar class
methods, receiver loans and bool fields. Conditions use the canonical bool AST;
linked calls inside conditions and ternary arms are resolved and checked. Linked
contract conformance remains rejected until cross-unit identity is verified.

The routing package still does **not** compile as a native LLVM application.
The backend checker executes a native positive control and checks the exact,
no-IR rejections of the real routing entrypoints. This pin update is compatibility
work toward full AOT; it does not provide String, HTTP or Future lowering.

Local checks: router semantics and all 16 backend harness tests pass. No GitHub
Actions execution is claimed for these new revisions.

The compiler pins now include the [successful exact-tree alias-matrix follow-up](https://github.com/led-dynamo/leddy-e2e/actions/runs/40007239817): 144 direct Java/native comparisons, 162 identical shared corpus vectors, native release/sanitizer checks and mandatory manifest gates. Routing package checks remain separately executed locally.
