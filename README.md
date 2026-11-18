# atto-http-routing

Reusable HTTP routing abstractions and request dispatch for AttoLang applications.

## Responsibilities

Routing semantics, handler integration, HTTP actor compatibility, and request lifecycle.

## Design guidelines

- Keep application-facing contracts separate from hosted Atto services.
- Explicitly specify error, cancellation, concurrency, and resource-lifecycle behavior where applicable.
- Document supported compiler backends, host restrictions, wire formats, and compatibility constraints.

## Development and verification

Use the source tree and CI for verified build/test commands. Tests should cover positive cases, invalid inputs, lifecycle behavior, and cross-backend interoperability where relevant.

## Status

This README describes the project's intended role. It does not imply that the listed APIs or platforms are already implemented or supported.

## Related

- [AttoLang](https://github.com/atto-lang)
- [Language specification](https://github.com/atto-lang/atto-spec)
- [Platform conformance](https://github.com/atto-lang/atto-platform-conformance)

## Repository ownership and contribution routing

**Belongs here:** Reusable HTTP route matching/precedence, path decoding, method mismatch, handler integration and immutable route snapshots.

**Belongs elsewhere:** Full servers in atto-api-server.atto or atto-demo-restful-server; front/reverse proxy demos in their separate example repos; cloud ingress in atto-co.

**Security and portability boundary:** Reject ambiguous captures, traversal, malformed percent encodings and conflicting routes; protect borrow-only request views through asynchronous handler lifetimes.

AttoLang is the public name; preserve existing Oreslang/.ores compatibility and use canonical .atto for new portable library source. This README defines scope, not feature readiness.

**Acceptance:** name exact source SHA/tree, runtime/toolchain, positive and negative checks and execution receipt before claiming support. Host-only tests and empty CI steps do not prove guest execution.

## Native Atto router proposal (PR #2)

This branch contains a **targeted Atto source port**, not an ownership transfer.
The initial `src/http_routing.atto` was copied from
`ores-truffle-oreslang/oreslang-http-routing` at main commit
`a8e994dc6fc24fec48509679d01491c1f4210c60`
(original source blob `4e1760c26f904728550f1defbe44cf96a93cd3de`).
The Atto port now intentionally **differs** from that original: string key and
method comparisons use Atto value equality (`eq`/`neq`) rather than
reference identity (`==`/`!=`). Rust policy tests guard this distinction.
The original repository, history, and migration approvals remain unchanged.

The Atto router accepts **already split, already decoded path segments**, not raw
request URLs. The HTTP adapter must parse/validate the method and request-target,
split before decoding, percent-decode each segment exactly once, reject malformed
encodings and traversal, and preserve repeated/trailing separators. The native
router supports precedence with bounded backtracking, wildcard/parameter
captures, HEAD/OPTIONS handling, HTTP method outcomes, and detached snapshots.
It is not an HTTP server.

All supporting tests here are in Rust, with native `.atto` guest fixtures and
exact stdout goldens. There is no Python runtime implementation or test harness.

```sh
cargo test --test router_contract
ATTO_COMPILER=/path/to/compatible/atto-compiler \
ATTO_COMPILER_SOURCE_DIR=/path/to/clean/compiler-checkout \
ATTO_COMPILER_SHA=<exact-40-character-commit-sha> \
cargo test --test router_contract run_native_atto_guest_suite -- --ignored --exact --nocapture
```

The first command checks repository language policy (including symlinks, Python
dependencies, and workflow commands), Atto string value-equality rules, fixture
integrity, and
a **Rust-only HTTP adapter admission model** in `tests/adapter_contract.rs`.
That model checks 4,096-byte request-target limits, 128 segments, 128-byte
segment limits, strict percent-escape decoding, NUL/control/encoded-separator
rejection, traversal/double-decoding defenses, preserved empty segments, and
HTTP-method/capture-name tokens. The adapter checks are **test-only**:
they do not make the Atto router safe to call with unvalidated raw URLs.
The adapter deliberately rejects encoded slashes and nested percent escapes.
**Passing Rust tests is not guest execution.** The ignored integration test runs a compatible Atto
compiler against five guest fixtures (check then execute, exact golden stdout),
but first requires a clean compiler source checkout at the exact pinned Git
commit. A pinned checkout is necessary for provenance, but alone does not
independently prove binary provenance; the chosen binary/build receipt must
also be audited. Its
`--platform=server` convention is inherited from the original Oreslang runner
and must be verified against the selected Atto backend. No current-backend or
multi-backend execution is claimed until actual CI receipts are produced.
Keep this PR draft until runtime and API compatibility are independently checked.

## Atto request-boundary hardening (PR #2)

The Atto source now enforces ASCII `snake_case` capture-name characters
(first character `a`–`z`; subsequent characters `a`–`z`, `0`–`9`, or `_`),
rejects malformed incoming method tokens **before** an `any("*")` route can
dispatch, and caps `request_path_checked` at 128 decoded segments before copying.
`Decision.is_invalid_method()` (kind 5) is separate from HTTP 404, 405 and
route-budget exhaustion.

**Important limitations:** portable Atto String byte-length checking has not
yet been implemented in this module, so the production `.atto` capture-name
gate does **not** enforce the Rust test model's 64-byte name length restriction.
The adapter must impose total raw URL and per-segment byte limits and validate
UTF-8 and percent decoding before calling Atto. The test-only Rust adapter model
uses a deliberately stricter policy for encoded slash and nested `%` sequences.
It is not production code and its passing tests cannot validate actual Atto
request parsing or module execution.

See [the adapter boundary contract](docs/ADAPTER_CONTRACT.md) for the explicit
trusted/untrusted split and remaining compiler requirements.
