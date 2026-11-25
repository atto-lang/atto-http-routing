# PR #10 reconciliation

Historical head 8ab029124a4c725dd2187508449f7713ebc21851; current main 5d9b2a72997e334c0aec518ef2cf243694d0d177.

All non-comment nonblank historical adversarial fixture lines are present in main's canonical guest_router_adversarial.atto. The 103-line golden is identical. The current implementation already has a read-only registration preflight, nonempty named capture admission, bounded decision replay and a per-snapshot identity fence. Preserve those instead of restoring the old .ores implementation. Migrate the existing fixture's call-site borrowing and string-literal comparisons without changing goldens. PR #2 is the overlapping full source syntax migration; integrate and retest together after sequencing. Historic native test harness/doc deltas require review for unique behavior. No native execution or merge claim for this commit.
