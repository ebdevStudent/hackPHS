# Development regressions — 2026-10-04

These partial development runs preserve failing assertions before the corrections. They are not complete verification runs or release evidence. The current 260-test Mac/ARM64 reports are linked in the [verification index](../README.md).

- `source-race-before-fix.txt`: late failure from the old source remained attached to the replacement source; one failed and 80 passed. This first targeted run imported the preceding installed runtime; its behavior matched the pre-fix source. Subsequent checks ran from `software/` against current source.
- `serial-framing-before-fix.txt`: oversized-message suffix was accepted as an ACK; one failed and 14 passed against source.
- `source-race-targeted-after-fix.txt`: 81 cases pass after source generation guards.
- `serial-and-harness-targeted-after-fix.txt`: 26 cases pass after serial discard state and verification-harness isolation corrections.

No full source manifest was captured for these partial debugging invocations. They identify assertions and development ordering; use the latest full reports for current source provenance, coverage and environment.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Parent verification report](../README.md) — The run-specific report retains its own date, hash, environment and test scope.
- [Verification procedure](../../../docs/15-verification.md) — Current command and interpretation guide.
