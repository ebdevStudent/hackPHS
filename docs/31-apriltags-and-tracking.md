# AprilTags, follow and landing guidance — how to use (2026-10-11)

Computer authority is still **yaw only**. AprilTag follow and landing use the same safety path as the
coloured ball: same controller, same 250 ms freshness and ACK watchdogs, target loss → yaw 0, and
assistance starts disabled. **Landing is a pilot cue**: the software tells the pilot when to descend.
It never touches throttle (the ESP32 only drives CH4 yaw).

## 1. Make tags (laptop, once)

```bash
cd ~/Documents/ChatGPT/hackPHS-esp32-trainer/software
.venv/bin/python -m ball_demo.cli tags wizard        # f = person to follow, l = landing pad, d = done
```

The wizard picks free tag IDs, saves the roster (`~/.config/ball-drone/roster.json`) and writes
`runs/apriltags.pdf`. Other commands:

```bash
.venv/bin/python -m ball_demo.cli tags add person "Rahul" --size-cm 12
.venv/bin/python -m ball_demo.cli tags add pad "Landing pad" --size-cm 16
.venv/bin/python -m ball_demo.cli tags list
.venv/bin/python -m ball_demo.cli tags remove 3
.venv/bin/python -m ball_demo.cli tags print --output runs/apriltags.pdf          # all roster tags
.venv/bin/python -m ball_demo.cli tags print --page tabloid --ids 1                # up to 21 cm
```

**Printing:**
- Print at **100% / "Actual size"**. Check that the 5 cm bar on each page measures exactly 5.0 cm.
- Size means the **outer edge of the black square**.
- Glue the tag flat on stiff card and keep the white border.
- Maximum size: 16 cm on letter, 15 cm on A4, 21 cm on tabloid.

**Bigger tags are seen from farther away.** Rough range on this analog camera, in good light:
- 12 cm tag: about 1.5–2 m
- 16 cm tag: about 2–2.5 m

## 2. Put the tags on the Pi

```bash
tools/pi/push-roster.sh                 # copies the roster to /var/lib/ball-drone/roster.json and reloads it
```

Or, in the Pi monitor (http://172.16.240.48:8080): **Operator access → AprilTags → Reload tags**.

## 3. Check detection without flying

With the Pi in FPV mode (`drone-mode fpv`, the default) and the drone camera pointed at a tag:

```bash
.venv/bin/python -m ball_demo.cli tags detect --url http://172.16.240.48:8090/snapshot.jpg --annotate runs/seen.png
```

The output lists each tag ID, its roster name (or `NOT in roster`), its size in pixels and its
estimated range.

## 4. Track / follow / land (Pi)

Only one program can use the capture card at a time, so `drone-mode` switches between them over SSH:

| Command | What runs | Steering output |
| --- | --- | --- |
| `drone-mode fpv` | Live FPV viewer on :8090 (dashboard Camera tab). Tracking app on fake video | none |
| `drone-mode track tag` | Tracking app on the real camera, following the roster person tag | **none** (ESP32 ACKs only) |
| `drone-mode track landing` | Same, lining up on the roster landing-pad tag | **none** |
| `drone-mode track color` | Same, coloured ball | **none** |
| `drone-mode assist <target>` | Same, plus `--trainer-output`: yaw reaches the radio | **yes**. Team decision; asks you to type YES |
| `drone-mode status` | Shows which mode is active, ESP32/capture presence, tag count | — |

If the ESP32 is unplugged, `track` falls back to the mock bridge with a loud warning, and `assist` refuses to start.

In the monitor (http://172.16.240.48:8080, operator token from `sudo cat /etc/ball-drone/operator.env`),
open **Controller and detector settings**:

| Field | Meaning |
| --- | --- |
| **Target** | Colored ball / Follow AprilTag / Land at AprilTag pad (switch live) |
| **Tag ID** | A specific tag; −1 = choose from the roster |
| **Descend cue range** | Range at which the landing cue says DESCEND |
| **Camera FOV** | Used for the range estimate (Caddx Ant ≈ 160°) |

The laptop dashboard's **Camera** tab switches by itself to the tracking app's annotated video and cue
when the Pi is in track/assist mode.

### Landing cues (shown under the video and on the overlay)

| Stage | Meaning |
| --- | --- |
| SEARCH | Pad tag not in view |
| ALIGN | Pad is off-centre: turn toward it. Assistance can hold yaw on it |
| APPROACH | Centred: fly forward slowly. Shows the estimated distance |
| DESCEND | Within *descend cue range*: lower throttle smoothly and land |
| OVER PAD | A close pad dropped out of the bottom of the frame: you are over it, so descend |

**The camera faces forward**, so a tag lying flat on the floor is seen at a grazing angle and disappears
under the drone. Two layouts work:
- **Recommended:** stand the pad tag **upright at the far edge of the pad**, facing the approach. Set
  *descend cue range* ≈ (tag-to-pad-centre distance + 0.2 m).
- Tag flat at the pad centre: use the **OVER PAD** cue when it slides out of the bottom of the image.

## 5. What is estimated vs measured

- **Range** = approximate focal length × tag size ÷ size in pixels, using a fisheye model of the 160° lens.
  It isn't calibrated, so treat it as roughly ±30%. Calibration (`nav-calibrate`) is optional, and only
  the advisory 3D pose features need it.
- **No tag can command throttle, pitch or roll.**
- Follow = yaw toward the tag. The pilot flies forward/back.
- First real use: props off, `drone-mode track …`. Then check on the radio's channel monitor that only
  CH4 moves, and that SD up cuts it.

Code: `software/ball_demo/tag_target.py` (detection + cues), `tag_kit.py` (wizard/print/detect),
`tools/pi/drone-mode`, `tools/pi/push-roster.sh`. Tests: `software/tests/test_apriltag_targets.py`.

## 6. Judge yaw slider (`/judge`)

Judges can steer **yaw only**, from their phone:
1. Operator: monitor → Operator access → **Judge yaw slider** → note the **PIN**, set the limit
   (default ±300 of 1000), **Turn judge mode on**. This disables vision assistance (the two are exclusive).
2. Judges open **http://<pi>:8080/judge**, enter the PIN and drag the slider. Releasing it snaps to 0.
3. Safety: a command older than 0.5 s → yaw 0; a bridge fault or stale ESP32 ACK switches judge mode off;
   20 wrong PINs per minute locks the PIN; judges can't reach any other setting (the PIN isn't an
   operator token); the pilot's SD switch and all other controls are untouched. Yaw reaches the radio only
   in `drone-mode assist` (`--trainer-output`).
Set a fixed PIN with `BALL_JUDGE_PIN` (otherwise a random 6-digit PIN at each start).
