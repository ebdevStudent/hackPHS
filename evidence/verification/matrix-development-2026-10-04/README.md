# Matrix regression development — 2026-10-04

Partial runs without full source manifests; use the [full reports](../README.md) for final provenance.

- [Before corrections](before-fixes.txt): 114 failures / 3,445 passes. Controller trajectories exposed cancellation at smoothing 1.0 and inclusive deadband boundaries. API cases exposed accepted coercible operator values and silently ignored unknown fields. These assertions include newly tightened input contracts, not 114 distinct production bugs.
- [After corrections](after-fixes.txt): 3,559 new cases pass. Operator models now reject incorrect types/unknown fields; weighted smoothing preserves exact input at 1.0.
- [Engine deadlines](engine-deadlines.txt): 150 cases pass on injected clocks with no additional runtime change; source/ACK thresholds, fault priority and enable checks at 249/250/251 ms.

No aircraft/device inputs. Parameter cases count individually; seeded steps inside tests are separate from pytest totals.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Parent verification report](../README.md) — The run-specific report retains its own date, hash, environment and test scope.
- [Verification procedure](../../../docs/15-verification.md) — Current command and interpretation guide.
