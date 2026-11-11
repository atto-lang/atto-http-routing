# HTTP adapter contract

The core router deliberately starts after raw HTTP parsing. An adapter MUST
normalize requests consistently with route registration.

## Method

Supply the canonical uppercase method token, for example GET, POST, HEAD, or a
custom extension method. Matching is case-sensitive in the core.

Do not silently rewrite an unknown method to GET.

Registration fails on CR, LF, TAB, NUL, spaces, commas, and colons in
method names. This is a defense-in-depth guard because registered methods
can be emitted in HTTP `Allow` headers. Extension methods such as
`M-SEARCH` remain supported. The adapter and HTTP response writer **must**
still enforce the full HTTP `token` grammar (and reject all other control
characters) at the raw-wire boundary; these routing checks are not a
replacement for that mandatory protocol validation.

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
