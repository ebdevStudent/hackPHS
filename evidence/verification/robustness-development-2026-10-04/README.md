# Additional regression development — 2026-10-04

Preserved partial test runs, not complete verification runs. No full source manifest is attached; use the [current full reports](../README.md) for authoritative outcomes.

- [Protocol before fixes](parity-before.txt): six failures include reordered ACK, repeated READY and float watchdog-boundary disagreement with actual C; [after](parity-after.txt) passes 54 targeted cases.
- [Desktop before validation fixes](nested-before.txt): 27 failures show accepted malformed snapshots/traces, coerced authorization and incomplete neutral replies; [after](nested-after.txt) passes 141 Qt cases.
- [IO/bridge/parity regressions](more-core-targeted.txt), [actual desktop module subprocess](native-module.txt), [verification-runner failure injection](runner-extra.txt) preserve targeted passing output.

All use software inputs, local host processes and offscreen Qt. No device or physical control-path result is implied.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Parent verification report](../README.md) — The run-specific report retains its own date, hash, environment and test scope.
- [Verification procedure](../../../docs/15-verification.md) — Current command and interpretation guide.
