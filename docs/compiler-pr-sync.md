# Compiler PR compatibility checkpoint — 2026-10-06

## Sealed-state/frame integration checkpoint — 2026-11-10

`SOURCE_REF` now pins `e6098659c2e1641564bb5835b4dbb92a6a00b1a8`, the
current-main sealed-state/actor-frame integration with execution-scope guards in
[Java PR #2796](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/2796).
It preserves #2781/#2747 ancestry, passes 306 focused tests plus four updated
main admission tests and 31 low-stack guest tests, and retains the unrelated
unsupported source gates. Concurrent-default guest scheduling remains open.
The real `.atto` routing semantics suite passes locally against this exact,
clean compiler checkout. This is an unmerged compiler snapshot, not a claim that
its features are on main, fully native, or proof of complete actor heap/stack
isolation. The historical checklist below refers to its original review date.

**Component:** HTTP route semantics, error handling and request dispatch.

Compiler source PRs **all open** at review: [#398](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/398), [#399](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/399), [#404](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/404), [#405](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/405), [#406](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/406), [#408](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/408), [#409](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/409), [#410](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/410), [#411](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/411), [#412](https://github.com/ores-truffle-oreslang/oreslang-source.java/pull/412).

## Integration dependency constraints

- `do select` stack: #405 -> #406 -> #408 -> #412; do not compile downstream tests against only one stack head.
- `do match` #404 is itself on a match feature branch; #398 is a separate map/exhaustiveness proposal.
- Actor isolation #399, SelectPlan #409, task-safe channels #410 and orthogonal binding qualifiers #411 are separate feature changes.
- Keep all current compiler pins, public exports, baseline files and default test behavior stable until exact source SHAs pass.

## oreslang-http-routing-specific tests and hardening

- Keep routing and streaming error responses serialized and data-only across actors; never transport handler functions through actor mailboxes (#399/#410/#411).
- Nested Option pattern matching must distinguish missing route, rejected match and route result, never silently map all three states into 404 (#398/#404).
- Preserve request cancellation and do-select return semantics before introducing channel-based dispatch (#405/#406/#408/#412).
- Do not change SOURCE_REF until exact compiler tests pass.

## Verification gate

- Expected baseline check: `bash scripts/test.sh`. This PR does **not** claim that check has been run.
- Add exact-head branch-specific integration tests before feature rollout. Negative tests must reject callable-bearing mailbox payloads, unsafe actor aliases, and discarded-return scope leaks.
- `const` is fixed readonly; `val` is fixed mutable (`const mut`); `let` is rebindable readonly; `let mut` is rebindable mutable, subject to borrow checking.
- Public Oreslang should use `rt copy`, `rt borrow`, `rt take`, `rt share` (and checked `rt proxy`) rather than `&`/`*` pointer syntax.
- If CI has no runner (runner ID zero, steps empty), no result was executed. Mirror the exact source tree to an organization with available GitHub Actions minutes, validate tree/blob hashes, and retain proof of executed jobs. Do not propagate secrets to the test org.

This checklist documents required follow-up **without pretending unmerged compiler semantics are available on main**.
