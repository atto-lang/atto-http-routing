# Router-generation authority: pending negative acceptance gate

Security issue: [#52](https://github.com/ores-truffle-oreslang/oreslang-http-routing/issues/52). Parent integration: Router #51.

## What this fixture actually tests

`tests/router_generation_authority.atto` builds two *different* routers with
bit-identical route paths, endpoint order, handler IDs and target metadata.
It resolves on router A and asks router B to expose a named capture, Allow count,
and Allow method from A's public `Decision`. It then builds another identical
route snapshot and checks that the earlier decision cannot authorize it.

The secure `tests/router_generation_authority.expected.txt` requires **ten
`true` lines**. The first three are positive controls, followed by three
foreign-router rejection checks, a construction control and three
replacement-snapshot rejection checks. The test presently is a **deliberately
failing security acceptance test**, not a passing regression or shipped feature.
Do not add it to the default all-green suite or weaken the golden.

## Execute with the exact pinned compiler

```sh
export ORESLANG_SOURCE_DIR=/path/to/clean/oreslang-source.java
export ORESLANG_COMPILER="$PWD/scripts/compiler.sh"
bash scripts/test-router-generation-authority.sh
```

The script checks the actual compiler HEAD against `SOURCE_REF`, rejects dirty
compiler source, runs actual `.atto` frontend/guest execution, and compares
stdout to the *secure* golden. A nonzero result indicates either the current
security gap or another error; capture both stderr and actual stdout in the
test receipt to distinguish them. Preserve original Git head/tree identities
for the router and compiler. This fixture has **not** been executed merely by
committing it.

## Completion contract (not implemented in this PR)

A runtime-minted opaque capability, inaccessible to guest constructors, must
bind route authorization to an immutable router snapshot, tenant, supervisor
epoch, actor/request lifetime and explicit owner. Public `Decision` fields,
deterministic IDs, table hashes, static secrets and handler IDs are *not*
capabilities. A valid owner-only claim must use single-owner/borrow semantics,
generation fencing, bounded checks and exactly-once response transfer.

Additional runtime/compiler-backed negative cases are needed before closing
#52: cancelled/stale claims, forged/replayed grants, identical tables across
tenants and supervisors, actor restart/endpoint reuse, hot-upgrade in-flight
drain/abort, immutable reader/exclusive writer safety, physical quiescence
and mutated authority-check deletion. LLVM, .NET and NativeAOT parity must be
established independently. The existing `scripts/test.sh` remains the green
behavioral regression suite; this file is an explicit **unmet release gate**.
