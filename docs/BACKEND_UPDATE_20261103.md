# Compiler tip update — 2026-11-03

`SOURCE_REF` pins `oreslang-source.java` at `273dafad1ba8fd48ebe3a66b58b6d4c5649f77d9`:
Java `main` `eb02a86348` plus the formatting-borrow fix for module-imported classes
([oreslang-source.java#2497](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/2497)).
Unpatched Java `main` rejects `tests/router_semantics.ores` with
`projected borrow requires a known owned field type for 'handler_id'`, because
`stdio.println(decision.handler_id)` reads a field of a class reached through
`import module`. Repin to that PR's merge commit once it lands.

Current Java rejects the legacy call-site spelling `rt borrow mut x`; the one call
site in `src/http_routing.ores` now uses `rt mut borrow x`. Parameter declarations
(`borrow mut SearchBudget budget`) are unchanged and still valid.

`LLVM_SOURCE_REF` pins `oreslang-source.llvm` `main` at
`de7dec73d0ba15fa851a95eef2b53da51986b5d8`, built against LLVM 21.1.8. LLVM 22
removed `Intrinsic::getDeclaration`, so this compiler does not build against it.
The routing package still does **not** compile natively. Its entry points reject
at new, earlier boundaries, recorded exactly in `BACKENDS.json`:

- `tests/router_semantics.ores`: scalar locals need explicit `: int`/`: bool` types.
- `src/http_routing.ores`: branch-local class owners need destructor/drop lowering.

The checker accepts only these named boundaries, optionally followed by the new
`[file: name.ores]` suffix; crashes, internal errors and any other text still fail.

## Local evidence (macOS arm64, JDK 21.0.12)

- `scripts/check-backend.py java` against a clean checkout at `SOURCE_REF`: router semantics PASS.
- `scripts/check-backend.py llvm` at `LLVM_SOURCE_REF`: positive control plus both exact rejections PASS.
- `scripts/test-backend-checker.py`: 17 tests OK. `scripts/test-runner.sh`: PASS.

Hosted CI is not evidence for this change: workflows on the compiler repositories
currently finish with zero executed steps (runner admission failure).
