# Borrow-hardened native/compiler compatibility

Java is pinned to `3f679db71f392d461dd5cb6f8a15e36dd1dcf5e6`, combining
current main's ownership/constructor rules with the existing NIO/performance
branch. This preserves native asynchronous outbound HTTP completion and avoids
regressing the older framework pin to blocking worker HTTP. The source checker
also rejects returned-loan receivers whose root/lifetime is unknown.

LLVM is pinned to `817069a2b422f77ee91e7f5d49b5791f8b5e5527`: zero-GC,
full-AOT scalar classes/methods and typed bool. Full routing source is still
unsupported. Exact rejection probes now reach the required initializer/type
boundaries, and the positive control verifies the current i32 OS entrypoint.
Internal errors, malformed offsets and partial IR do not qualify as rejection
compatibility. Bounded compiler subprocess handling is retained.

Validation: router semantics and sixteen backend/harness tests passed; the
native compiler itself passed 434 Linux CTests and 423 macOS CTests. The combined
Java runtime passed 317 tests. These counts certify their respective recorded
sources, not full native routing execution. Spin moves its router factory call
into its no-argument constructor for the newer Java initializer rules.
