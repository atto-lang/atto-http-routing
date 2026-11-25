# Historical PR #10 — registration and capture hardening reconciliation

The production preflight, nonempty named capture rule and bounded decision inspection are present in canonical main at 5d9b2a72997e334c0aec518ef2cf243694d0d177. Every non-comment statement in the historical adversarial guest is present in `tests/guest_router_adversarial.atto`, with a byte-identical 103-line golden. The standard guest runner checks the compiler pin and runs this fixture along with the other guest fixtures. No production code or golden is replaced by this disposition.

The original standalone exact-head build wrapper is retained below as a forward-ported companion script. It builds the pinned compiler and executes the existing test suite, and is not itself evidence of guest execution. The new Atto syntax migration and native compiler results remain on PR #2. This PR does not certify transport admission, OOM atomicity, concurrent actor transfer, or backend parity.

Squash integration is necessary to avoid bringing unrelated earlier stacked commits into main.
