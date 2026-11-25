# PR #2 reconciliation candidate

Base 5d9b2a72997e334c0aec518ef2cf243694d0d177; prior PR head f2ac617c4aa843be9f7d450d0ed4bc0d98ec5a20.

Preserve main's generation witness, decision replay, registration preflight, dot rejection, fixtures and historical runner contracts. Forward-port implicit borrowing, string value comparison, capture-name validation, request-method rejection, absolute resource ceilings and Rust contract tests.

Inherited Python host-admission harness remains intact pending equivalent Rust migration; the Rust Python prohibition test is enabled and expected to flag it. Guest syntax migration and real compiler execution remain mandatory. Do not count ignored guest tests or host-only tests as production evidence.
