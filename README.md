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
ATTO_COMPILER=/path/to/compatible/atto-compiler cargo test --test router_contract -- --ignored
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
compiler against guest fixtures (check then execute, exact golden stdout). Its
`--platform=server` convention is inherited from the original Oreslang runner
and must be verified against the selected Atto backend. No current-backend or
multi-backend execution is claimed until actual CI receipts are produced.
Keep this PR draft until runtime and API compatibility are independently checked.
