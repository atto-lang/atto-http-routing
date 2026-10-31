# Issue #22 — pure router acceptance matrix (proposed, unverified guest)

Scope: `src/http_routing.ores` is a **decoded-segment trie and method
dispatcher**. It is not a request-target parser, percent decoder, HTTP server,
TLS endpoint, or actor scheduler. No transport/security claim follows from
passing these guest tests.

**Pin:** `SOURCE_REF=10792c332e6a31d685ca65960f841543fe95fbb8`
(Java/Graal compiler source checkout). Run `ORESLANG_SOURCE_DIR` pointing to
a **clean exact checkout** and `ORESLANG_COMPILER` pointing to an executable
built from and independently identified with that SHA:

```sh
ORESLANG_SOURCE_DIR=/absolute/path/to/pinned/clean/compiler-checkout \
ORESLANG_COMPILER=/absolute/path/to/verified/oreslang-compiler \
bash scripts/test.sh
```

For exact-head native acceptance, prefer the wrapper below **from a clean
checkout of the reviewed PR head**, with the full independently recorded head
SHA supplied by the reviewer:

```sh
ROUTER_EXPECTED_HEAD=<full-40-character-reviewed-PR-head> \
ORESLANG_SOURCE_DIR=/absolute/path/to/pinned/clean/compiler-checkout \
bash scripts/test-native.sh
```

The wrapper rejects dirty or mismatched router/compiler checkouts, prints
router/compiler commits and tree IDs plus Maven/Java versions, performs a
fresh Maven `clean package` / launcher-classpath build from the pinned compiler
source, then launches the actual compiler via `scripts/compiler.sh`. Its
exit status must be captured with executed job step metadata and stdout.
Dependency provenance and independent runner admission remain separate.

`scripts/test.sh` checks the SHA/clean checkout, checks each guest
(`--check --platform=server`), **executes each guest**
(`--platform=server`), and diffs deterministic stdout with committed golden
files. Host runner double: `bash scripts/test-runner.sh`. The double tests
invocation/failure propagation only, not guest correctness; the script alone
does not attest that the compiler executable was built from the checkout.

## Exact guest mapping

`tests/router_semantics.ores` → `tests/expected.txt` keeps the existing
semantics baseline. The added `tests/router_adversarial.ores` →
`tests/expected_adversarial.txt` has **74 boolean assertions**, each with
expected stdout `true` in declaration order. A false, crash, compiler
rejection, different line count, or nonzero process exit fails the suite.
The Rxx comments group the guest assertions as follows:

| Case | Input / mutation | Expected native guest result | Admission scope |
| --- | --- | --- | --- |
| R01 | Register same five trie shapes and six method targets in opposite orders | all registration `Ok`; both routers have five endpoints | valid guest |
| R02 | `GET /a/fixed`, `/a/x`, `/a/x/y`, `/a/fixed/details`, `/a/fixed/edit`, `/a` | static 101, param 102, wildcard 103, deeper static 104, backtracking 105 with `id=fixed`, empty wildcard capture; same result in both orders | valid guest |
| R03 | `POST /a/fixed` when param permits POST; `POST /a/x`; HEAD/OPTIONS explicit and automatic; unknown path; small matching budget and segment limit | 405 (no method fallback), handler 106, HEAD via GET with body suppression, explicit HEAD/OPTIONS override, automatic OPTIONS, 404, and distinct limit-exceeded decisions | valid guest with expected negative decisions |
| R04 | `[a,fixed,""]` and `[a,"",x]` | wildcard 103; trailing and repeated empty segment retained in capture | valid guest; **no automatic slash collapse** |
| R05 | duplicate GET, alternate param name, alternate wildcard name, duplicate capture | `Err` on each; old snapshot unchanged **and rebuilt builder remains at five endpoints** | valid guest with negative registrations |
| R06 | retain an old captured Decision; append route and toggle HEAD/OPTIONS after build | old captures intact; old snapshot unchanged; new snapshot sees route 120 and disabled method synthesis | valid guest; **no concurrent actors exercised** |
| R07 | already-decoded `[esc,"/"]`, `[esc,"%2F"]`, `[esc,"%252F"]`, `[esc,"%GG"]` | distinct literal matches 301/302; opaque capture 303 retains exact `%252F`/`%GG` strings; **no second decode or split** | valid guest at decoded boundary, not raw percent validation |
| R08 | already-decoded `[esc,".."]` | captures `..` unchanged; demonstrates why adapter must reject traversal before routing | **negative security witness; rejection NOT supplied by router** |

## Boundary negatives that remain unproven

These inputs belong to the **raw adapter / application validation** layer and
cannot be distinguished or rejected from decoded `Array<String>` alone:

| Negative boundary case | Required outcome | Why router-only guest cannot certify |
| --- | --- | --- |
| Raw `/esc/%GG`, `/esc/%2`, trailing `%` | reject malformed percent sequence before `request_path` | decoded `%GG` might validly come from raw `%25GG` |
| Raw `/esc/%2F` vs `/esc/%252F` | split first, decode once; segments `/` vs `%2F`, never split the decoded slash | R07 tests only the supplied decoded result |
| Raw `/a/./x`, `/a/../x`, encoded dot segments `%2e`, `%2e%2e` | reject/normalize per explicit security policy **before router lookup**, without traversal ambiguity | R08 proves dot input may be captured; the router cannot certify request-target validation |
| NUL, invalid UTF-8, controls, double encoding, backslash or mixed separators | reject before construction, per adapter contract | no raw bytes, decoding, Unicode validation or filesystem semantics in this library |
| Multiple readers on separate actors during builder hot-reload | no mutable alias/borrow escapes; old decisions stay generation-scoped | R06 tests value detachment in one guest, **not actor parallelism** |

**Do not close #22 on the proposed corpus alone.** The raw adapter negatives
need a concrete adapter fixture; concurrent snapshot transfer needs an actor
conformance fixture on a backend with actual actor execution. Build and
validate the exact pinned compiler and collect executed-step, exit-code,
stdout, head SHA, tree SHA, and toolchain evidence. CI jobs with
`steps=[]` are runner-admission failures, never test passes.

## Related open reconciliation

PRs #11 and #18 have compiler pin/reconciliation work and must be assessed
against the exact selected compiler revision before integration. Draft PR #25
hardens stale/foreign decisions but is **not merged**; this test-only branch
does not include or attest its source changes. A foreign decision must never
be considered an authorization capability; retain the exact producing router
generation during dispatch. None of these PRs is accepted on a host-test
double or a zero-step workflow.
