# PR #11 reconciliation

Historical head 202466f66261f16f189f36546c341279b840f6b1; current main 5d9b2a72997e334c0aec518ef2cf243694d0d177.

Every non-comment nonblank statement in the historical 10-assertion generation fixture is present in main's canonical 16-assertion guest_generation_witness.atto. Main also provides a separate decision-kind matrix and bounded structural decision checks. Retain current code and goldens; migrate the existing witness fixture to implicit borrowing. PR #2 overlaps the full syntax migration and needs combined retesting. The old standalone runner is superseded by the main guest glob for this fixture, but historical runner differences still require audit. The scope in docs/GENERATION_FENCE_SCOPE.md remains binding: snapshot identity is not runtime-minted authority, tenant/supervisor revocation, actor ownership or cross-isolate safety. No guest execution or release-readiness claim for this commit.
