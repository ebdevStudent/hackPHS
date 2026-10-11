# Dated bench/handoff source snapshot — 2026-10-11

Preserved reference material, not executable instructions. The current interpretation and
later physical observations are in `docs/29-claude-flight-controller-handoff-2026-10-11.md`.

- `claude-esp32-trainer-handoff.md`: exact earlier Claude handoff supplied by the user;
  its old IP/power-off statements are historical. Current IP was 172.16.240.48.
- `hackphs_motor1_pulse.py.txt`: exact original script executed for ~0.7 seconds.
- `hackphs_motor1_2_then_10.py.txt`: exact original 2-second then 10-second sequence.
- `hackphs_motor1_10_monitor.py.txt`: exact original 10-second retry with command readbacks.
- The `.py.txt` extension is deliberate: originals have top-level physical actions and
  must never be imported or executed simply to inspect them.
- `motor1-first-report.md`: original initial report; its observation-pending caveat predates
  the user's confirmation and is retained intact. See the current handoff for later results.
- `source-adoption-review.md`: original branch/source adoption review, before motor work.
- `pi-v4l2-user-output.txt`: earlier user-pasted capture format/device output, including a
  failed literal `/dev/videoN` command. USB detection is not successful live FPV.
- `betaflight-pre-binding-diff.txt`, if present: old configuration backup; do not restore
  wholesale because later binding and ARM configuration superseded it.
- `original-docs/`: pre-update index and firmware README snapshots.
- `SHA256SUMS`: source snapshot hashes, excluding this README and the manifest itself.

The original scripts ran on the actual Linux laptop connected to the FC. Rotation reports
are human observations, not RPM measurements. New helper code is optional and was not
hardware-tested while preparing this publication. Raw videos, private credentials and
operator tokens are not included. No software suites or physical motor tests were run to
prepare this handoff.
