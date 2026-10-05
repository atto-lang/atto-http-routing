# Routing design

## Data flow

`net.http` parses and normalizes the request target.

The routing package receives:

1. canonical method;
2. `List<String>` path segments;
3. an immutable `RouteSnapshot`.

It returns `Option<RouteMatch>`. It does not invoke application code.

`RouteMatch` is then consumed by the dispatch layer, which resolves `operation_key` against the generation-pinned operation catalog and applies the route-group / middleware policy.

## AOT and hot reload

Handler functions are intentionally not stored in `Route`.

A string operation key is stable data that can be validated against a compiler-generated operation catalog. This avoids retaining arbitrary closures, avoids accidental lexical captures, and lets a build/tree-shaker reason about which operation identities are reachable.

Each snapshot has a generation supplied by its owner. The router requires only that it is non-negative; ordering and atomic publication belong to the runtime. A match copies the generation into `RouteMatch` so the caller can reject cross-generation dispatch instead of racing a hot reload.

## Actor/isolate boundary

`RouteSnapshot` is intended to live in the outer server/control plane or a dedicated routing actor. `RouteMatch` contains only owned data and immutable parameter nodes. No OresVM, OresContext, scheduler, socket, actor cell, or host object is stored in a route.

The group key is the indirection point for execution-domain policy such as shared actor, isoactor/private-memory, or untrusted isolate placement.

## Parameter representation

Captured parameters use a persistent `RouteParams` list rather than `DynamicStruct`. The public surface is `param(name) -> Option<String>`. This keeps the implementation aligned with the direction that open-ended key/value state belongs to a map-like abstraction rather than dynamic object shapes.

When the canonical Oreslang `Map<K,V>` surface is available, `RouteParams` can switch storage without changing `RouteMatch.param`.

## Deterministic precedence

Matching is first-match wins.

The builder rejects the same method + match shape twice. Parameter names are capture labels, not part of the match shape, so `/users/:id` and `/users/:name` are duplicates.

The builder deliberately does not invent a hidden specificity score. If both:

- `/users/me`
- `/users/:id`

are valid, declaration order decides which route receives `/users/me`. This makes precedence visible in source/config and avoids behavior changing when a new matcher kind is introduced.

## Non-goals

This package does not own:

- raw HTTP parsing;
- URI parsing or percent-decoding;
- query/header/cookie matching;
- network I/O;
- response serialization;
- middleware execution;
- handler invocation;
- retries/redirects;
- TLS/HTTP2/WebSocket protocol logic.
