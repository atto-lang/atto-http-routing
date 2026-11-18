# Atto HTTP routing adapter boundary

This package's production routing logic lives exclusively in `src/http_routing.atto`.
The Rust files in `tests/` are test harnesses and a test-only protocol admission
model; they do **not** implement the production router.

## Caller/adapter responsibilities

An HTTP transport must accept a bounded raw request target, validate its syntax,
separate query/fragment data (fragments are not sent in HTTP request targets),
split on *raw* forward slashes, and percent-decode each segment **once**.
It must validate UTF-8, reject NUL/control bytes, and define strict policy for
encoded slashes, backslashes, and nested percent escapes. Do not split or decode
again after routing; do not collapse `//` or remove trailing empty segments.
For strict adapters, use the Rust-only `tests/adapter_contract.rs` policy as
a supporting test reference, not as the runtime parser.

The adapter must also enforce raw URL byte length, decoded segment byte length,
and total number of segments *before* building `Array<String>`. A returned
`RequestPath` is decoded structured input and must not be treated as an
authentication or authorization capability.

## What the Atto router enforces

- Route registration checks HTTP method token characters, nonnegative handler
  identifiers, maximum segments, duplicate capture names, wildcard position,
  conflicting route shapes, and malformed capture names.
- Capture name character contract: ASCII lowercase initial letter, followed
  by lowercase ASCII letters, digits, or underscores. This excludes uppercase,
  leading underscore/digit, hyphen, Unicode, or embedded control bytes.
- Capture names currently **lack a portable byte-length bound** in the Atto
  implementation. This remains a compiler/runtime and registration API gap,
  not a claimed pass. The Rust test-only model caps names at 64 bytes.
- A `Router.resolve` rejects an invalid HTTP method with decision kind 5
  (`is_invalid_method()`) before trie lookup, including on catch-all routes.
- A `request_path_checked` rejects exact already-decoded `.` and `..`
  segments and rejects more than 128 segments before copying. It does **not**
  validate raw percent escapes, raw total bytes, or decoded segment byte lengths.
- The unchecked `request_path` is retained for compatibility; untrusted
  transport inputs must not reach it without adapter validation.
- Resolution is path-first; static > named parameter > terminal wildcard.
  A found path with a mismatched method yields a method-not-allowed decision.
  Search-budget exhaustion remains distinct from a 404.

## Response mapping and lifetimes

A typical adapter maps matched decisions to handler dispatch, not-found to
404, method-not-allowed to 405, invalid-method to 400, and budget exhaustion
to a bounded 400/414 policy. Generate `Allow` only for validated
method-not-allowed or automatic OPTIONS decisions.

`Decision`, `Router`, and `PathCapture` are not authorization tokens and
must not cross isolated actor boundaries. Extract validated immutable values
and pass only permitted scalar data into the actor capability. Authorize the
requested resource separately from matching its route.

## Verification

`cargo test --all-targets -- --nocapture` executes Rust-only source/fixture
policy and adapter-model tests. The separate ignored native Atto integration
test requires a **compatible pinned compiler**, explicit source checkout, and
actual guest execution against `.expected` outputs. The compiler/runtime
currently lacks portions of the required collection/string/import support,
tracked in `atto-source.rs#348`. Do not claim production Atto execution,
native AOT readiness, actor-lifetime safety, or backend parity from host tests.
