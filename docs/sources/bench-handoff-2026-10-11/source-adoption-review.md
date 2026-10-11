# ESP32 trainer repository handoff — source review

Date: 2026-10-11 (America/New_York).

## Active source for continued work

The user requested adoption of the GitHub instructions in
`/home/chessdroid108/Downloads/codex-handoff-esp32-trainer.md`.

- Repository: https://github.com/ebdevStudent/hackPHS
- Branch: `esp32-trainer-ppm`
- Commit: `df186f4865aedc61bad246e535e8a785855fa750`
- Local checkout: `/home/chessdroid108/Documents/ChatGPT/hackPHS-esp32-trainer`
- Local branch tracks `origin/esp32-trainer-ppm`; working tree is clean.
- GitHub reports the signed-in account has pull and push permissions. No push was performed.
- History matches the handoff: `0d9974d` initial commit, then `df186f4` trainer overlay.
- Continue from this checkout. The older chat workspace at
  `/home/chessdroid108/Documents/ChatGPT/hackPHS` is retained with its local changes.
  Its origin is `chessdroid108/HackPHS`, which the user has superseded for this work.
- The new repo's `main` remains at `0d9974d`. Do not merge or push to `main` for this
  trainer handoff. Commit or push only when requested by the user.

## Checks performed on the local Linux laptop

These were source inspection and comparison checks, not automated software suites,
firmware execution, or hardware trials.

| Check | Finding |
| --- | --- |
| Remote branch and local HEAD | Both equal the handoff's exact commit |
| Three terminal tools | Text matches section 13 exactly after normalizing line endings |
| ESP sketch shared C sources | `core.c`, `core.h`, `line_reader.c`, `line_reader.h` are byte-identical to their originals in `firmware/` |
| Serial transport | `Serial0.begin(115200)`; host default is also 115200 |
| PPM constants | GPIO4 output, GPIO5 safety input; 8 channels; CH4 yaw; 22,500 us frame; 300 us LOW separator; 1,500 +/- 150 us yaw range |
| Session gating | HELLO selects `PPM_YAW`/`NO_OUTPUT`; removing GPIO5 ground latches the session disarmed until another HELLO |
| Neutral behavior | Disable/watchdog sends neutral frames while armed; ISR stale-request guard also neutralizes; disarm sends a 3-frame neutral tail before idle HIGH |
| CLI merge | Serial/baud/trainer-output flags coexist with portable-demo/target-calibration/target-delay-ms flags |
| Verification sources | The listed pytest files and firmware host simulation sources exist; they were not executed in this task |
| `docs/28-esp32-trainer-wiring.md` | Absent, as the handoff says |

Tool file SHA-256:

```text
5457fd8106ca2e2f59d20766dd29d77e5e9b04bdf2c79581c77bd50bbc1e3ccf  esp_term.py
ceeac6515d467629b0bc5ea2ca9aef8b7e328d1c73be4847b2f839c673421316  ppm_probe.py
d30f52ee2b51a06a02cf07f7b5feba8bad785571c4469106fe3059a585c3ec00  flash.ps1
```

## Stale documentation and known open items

- `docs/README.md` and `AGENTS.md` still describe an ESP32 no-output port. The
  inspected trainer branch implements output. The user's newly adopted repository
  and branch instructions supersede the older instruction to push directly to main.
- `firmware/README.md`, `firmware/PROTOCOL.md`, and sketch comments still describe
  radio/electrical checks as unverified. The handoff reports newer Pi and Pocket
  measurements; this review does not independently reproduce those measurements.
- `ppm_probe.py` still says 1 kOhm and Pi GND pin 6. The handoff specifies the actual
  bench setup used 2 kOhm and Pi GND pin 39. The script matches the handoff's verbatim
  file despite that documented stale comment.
- `esp_term.py` closes its serial port while the reader can still be reading; the
  shutdown race mentioned in the handoff remains present.
- Radio weight 30 and SD override configuration are handoff-reported settings,
  not independently inspected radio state in this task.
- The 20 disarmed, props-off Betaflight trainer trials remain pending. Ordinary
  Pocket-to-FC binding and stick checks from this chat are separate from the pending
  computer-yaw path checks.
- Linux test results remain unestablished here. Run the requested software and
  firmware checks on the actual Pi when proceeding with that part of the handoff.
- No firmware flashing, serial control, radio setting changes, motor operation,
  commits, pushes, or merges were performed during this source-adoption task.

The local checkout is ready for the next trainer verification session. Keep the
handoff's bench results attributed to its author until directly reproduced or
supported by preserved original measurement records.
