# Router-generation identity fence: candidate guest acceptance gate

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
replacement-snapshot rejection checks. On historical baseline #51 this fixture was deliberately failing. The candidate
adds a per-snapshot private object-identity witness to `Router` and `Decision`.
The exact-blob Java guest run [#43155812579](https://github.com/gha-indie-worker/gha-indie-worker-docs/actions/runs/43155812579)
ran the baseline and patched router scripts, passed all ten secure golden lines,
and proved that deleting the witness admission check makes the prior six
security assertions fail again. The candidate source blob was `1616ab5d...`.
The ten-line secure golden remains **unchanged** and is now run from the default
`scripts/test.sh`. This was verified as a selected original source blob on the
private mirror, not as a full Git tree recreation of the new PR head.

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

## Candidate scope and completion contract

The current candidate uses **guest object-reference identity** (`is`) to fence
snapshot metadata inspection. This is stronger than route-table replay and
rejects identically configured foreign routers under same-runtime identity
semantics, but is **not** a runtime-minted capability, has no supervisor epoch,
and does not independently enforce actor/tenant authorization. It is a staged
mitigation, NOT completion of issue #52.

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
established independently. The existing `scripts/test.sh` remains the green behavioral regression suite;
`test-router-generation-authority.sh` is now invoked by `scripts/test.sh`.
It proves only same-runtime snapshot separation. Independent security review,
exact new PR-head/tree reconstruction and further runtime authority testing
remain pending; the full #52 release gate remains OPEN.
