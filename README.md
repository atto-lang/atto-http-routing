# Oreslang HTTP Routing

Transport-neutral HTTP route matching written in Oreslang.

This package deliberately does **not** implement sockets, HTTP framing, URI parsing, redirects, or handler execution. Those belong to Oreslang `net.http` and the server/runtime layer. The router consumes a canonical HTTP method plus already-normalized path segments and produces immutable dispatch metadata.

## Why this boundary

The route table is data, not a graph of handler closures. A successful match returns:

- the route snapshot generation;
- an operation key;
- a route-group key;
- a middleware-chain key;
- captured named path parameters.

That makes the result safe to hand to the API/RPC dispatch layer, an actor group, an isoactor, or an untrusted execution domain without giving the router ambient runtime authority. It also keeps AOT/tree-shaking behavior predictable because operation keys are explicit dispatch identities.

## Example

~~~ores
import class {RouteMatch, RouteSnapshot} from "./src/http_routing.ores";
import fnc {literal_segment, param_segment, route_in_group, build_snapshot}
  from "./src/http_routing.ores";

val RouteSnapshot router = build_snapshot(
  7,
  arr[
    route_in_group(
      "GET",
      arr[literal_segment("users"), param_segment("id")],
      "users.show",
      "users",
      "auth.required"
    )
  ]
).expect("valid routes");

val RouteMatch matched = router
  .resolve("GET", arr["users", "42"])
  .expect("route");

val String id = matched.param("id").expect("id");
~~~

## Matching contract

Routes are checked in declaration order. That ordering is intentional and deterministic: put more-specific routes before parameter routes when both can match the same path.

A segment is either:

- `literal`: it must equal the corresponding canonical request segment;
- `param`: it matches one segment and records it by name.

The current contract intentionally omits tail splats/wildcards. A tail capture needs an explicit representation for multi-segment values and URI-decoding policy; adding it later is safer than silently joining path bytes into a string.

The method `"*"` is the only method wildcard. Otherwise methods match exactly; callers should pass the canonical uppercase method produced by the HTTP layer.

The root path is represented by an empty path list, `arr[]`.

## Snapshot invariants

`build_snapshot` rejects:

- negative generations;
- empty methods;
- empty operation keys;
- unknown segment kinds;
- empty segment values;
- duplicate parameter names inside one route;
- duplicate method + path patterns, including patterns that differ only by parameter name.

A snapshot has no mutation API. Hot reload should construct a fresh `RouteSnapshot` and atomically publish it in the owning runtime/actor. `RouteMatch` carries the snapshot generation so dispatch can remain pinned to the code/config generation that produced the match.

## URI normalization and security

Do not pass a raw request-target string to this router.

The HTTP/URI layer must first establish segment boundaries and its policy for percent decoding, encoded slashes, dot segments, repeated slashes, and invalid encodings. Query strings and fragments are not route path segments. Keeping that policy outside this package prevents routing from accidentally reparsing security-sensitive HTTP bytes differently from `net.http`.

## Middleware and async handlers

`middleware_chain_key` is metadata only. The outer server/dispatch layer is responsible for resolving that key, running middleware, invoking the operation, and awaiting async work. This avoids storing closures or scheduler/runtime objects inside the route snapshot.

## Verification

The repo pins the compiler/runtime revision in `SOURCE_REF`.

Run:

~~~bash
just verify
~~~

or:

~~~bash
bash scripts/verify.sh
~~~

Set `ORESLANG_SOURCE_DIR` to test against an explicit local `oreslang-source.java` checkout.
