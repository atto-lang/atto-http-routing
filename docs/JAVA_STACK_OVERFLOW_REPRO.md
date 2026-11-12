# Java evaluator stack overflow reproduction — 2026-11-12

Runtime P0: https://github.com/ores-truffle-oreslang/oreslang-source.java/issues/2996.

Two real pinned-compiler router guest runs failed with `StackOverflowError`
in `OresEvalRootNode$Evaluator`, including `ores-control-plane-*` threads.
An unchanged exact-tree isolated rerun passed. Neither a retry nor the test
script described here is proof of runtime containment or a root-cause fix.

## Exact-pinned reproduction (Linux with GNU timeout)

```sh
export ORESLANG_SOURCE_DIR=/checkout/of/oreslang-source.java
export ORESLANG_COMPILER="$PWD/scripts/compiler.sh"
ROUTER_STRESS_ATTEMPTS=32 ROUTER_STRESS_TIMEOUT_SECONDS=30 \
  bash scripts/stress-router-guest.sh
```

The harness runs the original 101-case `tests/router_semantics.atto`
in a fresh compiler/JVM process on **every** iteration. It requires a pinned
clean Java source checkout, compares exact committed stdout, and fails on any
nonzero exit, timeout, golden mismatch, or `StackOverflowError` in stderr.
Attempts are bounded 1..128; per-process deadline is bounded 5..120 seconds.
It NEVER retries a failing iteration into green; it reports the failing
iteration, status and stderr tail.

Even a green 32-process run is not a proof of actor-level stack containment.
Release requires diagnosis and a deliberately overflowing actor test showing
its sibling and control plane survive, with deterministic supervisor cleanup.
Do not equate an external shell/JVM timeout with actor-owned frame quotas.
Record original Router and Java Git trees plus nonzero Actions step receipts.
Source-org zero-step jobs are runner-admission failures.
