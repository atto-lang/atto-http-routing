# PR #11 — compiler pin and router runner reconciliation

Historical head 6b51e8f7d3fbe36a075063626b31010285c39e38, latest routing main 6c5413221d29f790b691ab9c1ad17b3160aeac9d.

The old feature branch requested moving from the stable compiler revision to edea24f9bf980025b68650b749a3ef0fc1813c20. Current routing main deliberately pins 62646c4372244723813ab06f2d122a6b2f5c0995 and already carries the strengthened `scripts/test.sh` compiler source status, exact SHA, compile-only and server-runtime error gates. Preserve the newer pin and existing stronger `scripts/test-runner.sh` negative fault-injection fixtures; do not restore the old compiler or overwrite those tests.

Add only a minimal Rust/Python-independent shell preflight for the presence of immutable compiler pin and runner gates. This is structural validation, not compiler identity attestation or route runtime conformance. Exact-head HTTP route/actor tests, generated contract ABI and independently confirmed source runner execution are required before release.
