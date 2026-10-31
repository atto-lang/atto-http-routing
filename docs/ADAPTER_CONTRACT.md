# HTTP adapter contract

The core router deliberately starts after raw HTTP parsing. An adapter MUST
normalize requests consistently with route registration.

## Method

Supply the canonical uppercase method token, for example GET, POST, HEAD, or a
custom extension method. Matching is case-sensitive in the core.

Do not silently rewrite an unknown method to GET.

## Path segmentation

Split the request-target path on '/' before percent-decoding segment contents.

Then decode each segment exactly once.

Do not:

- decode '%2F' into '/' and then split again;
- treat a query string or fragment as part of the path;
- collapse repeated slashes unless the application has explicitly chosen a
  redirect/canonicalization policy;
- drop a trailing empty segment.

Canonical examples:

- '/' -> []
- '/users' -> ['users']
- '/users/' -> ['users', '']
- '/a//b' -> ['a', '', 'b']

The router itself receives only the Array<String> of path segments.

## Validation before routing

A production adapter should reject malformed percent escapes, NUL/control
characters, and invalid request-target encodings before constructing
RequestPath. Backslash handling should be explicit rather than platform
dependent.

The router's max_segments and max_match_steps limits are a second defensive
boundary, not a substitute for protocol parsing limits.

## Responses

Decision is intentionally transport-neutral. A typical adapter maps it as:

- is_match -> invoke handler_id through pipeline_id
- is_not_found -> 404
- is_method_not_allowed -> 405 and emit Allow from allow_method_at()
- is_automatic_options -> adapter-generated OPTIONS response and Allow
- is_limit_exceeded -> defensive 400/414 policy chosen by the server

For HEAD, suppress_body is true whether the match came from an explicit HEAD
route or GET fallback. The handler may still compute headers/status exactly as
for the corresponding request; the transport must suppress body emission.

## Body, headers, query, and typed extraction

Those values intentionally do not participate in path matching.

Typed extractors should run after routing using contract_id and application
metadata. This mirrors the useful separation in extractor-based routers:
matching selects the endpoint; validation/extraction turns protocol data into
typed application inputs.

## Actor adapters

Registration borrows patterns (`routes.get(&pattern, handler_id)`), while the
builder copies pattern data into its own storage. Inspection helpers borrow
matching decisions (`router.capture_one(&decision, "id")`). A decision owns a
detached request-path snapshot, and a capture is a view over that snapshot.

A dispatcher must not send a Decision, PathCapture, or Router object to an
isolated actor. Extract immutable scalar strings and place them in the actor's
request capability before transferring it. Keep handler objects in the host
adapter's registry; routing metadata contains only scalar IDs and operation names.

## Decision provenance and generation scope

A `Decision` is a routing result, **not** a proof of authority or a
generation-stable handle. Keep it together with the exact immutable `Router`
snapshot that produced it. Do not pass a decision from one router generation to
another (including hot-reload replacements), and do not accept a
caller-constructed `Decision` as an authorization signal.

The router now checks a decision's endpoint range, route template, bound handler
metadata, and path shape before `capture`, `capture_one`, `allow_count`,
and `allow_method_at` dereference route data. Invalid decisions fail closed:
captures/Allow entries are `None` and the Allow count is zero. These checks
prevent accidental stale or mismatched data access; they are **not**
cryptographic or unforgeable router-generation attestation. The adapter must
derive authorization solely from its own generation-scoped route/handler
registry and request capability. In-flight requests must retain their original
router snapshot until dispatch completes.
