// Ball Drone flight-assistance bridge for ESP32-S3 (Freenove): protocol version 1 over USB serial.
//
// Speaks the same ASCII HELLO/READY/CMD/ACK protocol as firmware/PROTOCOL.md using the shared C core
// (src/core.c) and line framing (src/line_reader.c), byte-identical copies of firmware/core.* and
// firmware/line_reader.*.
//
// PPM TRAINER OUTPUT on GPIO 4 (ppm.h).  Only the yaw channel (RC ch 4) varies, capped at
// 1500 +/- 150 us; all other channels are fixed at 1500 us.  Output is armed per session:
//   - READY reports PPM_YAW only if the safety jumper (GPIO 5 to GND) is fitted at HELLO; otherwise
//     NO_OUTPUT and the line stays idle for that whole session, even if the jumper is fitted later.
//   - Pulling the jumper disarms the session for good: 3 neutral frames, then idle.  Refitting it
//     takes a new HELLO (restart the host app).
//   - While armed the stream never stops on its own: disable, target loss and the 250 ms watchdog
//     send yaw 1500 us, because EdgeTX holds the last trainer value for ~1 s if the PPM stops.
//
// RADIO SETUP IS PART OF THE SAFETY CASE (firmware/README.md has the full steps).  Every CPPM frame
// carries 8 channels and EdgeTX decides per stick whether to use them:
//   - MODEL > Setup > Trainer mode = Master/Jack.  The trainer socket is the 3.5 mm jack on the TOP
//     of the RadioMaster Pocket, not the headphone jack.
//   - SYS > Trainer: Rud mode += with a small weight (radio-side yaw cap; 1500 us adds nothing, so
//     neutral = pilot's own rudder), source CH4.  Ele, Thr and Ail mode OFF.  If Thr takes the
//     trainer, flipping the trainer switch commands mid-stick throttle.
//   - Special Function: Trainer (Rud) on a switch.  That switch is the pilot override: off = the
//     bridge has no effect.
//   Props-off check before any flight: trainer switch ON, Channel Monitor open; throttle, roll and
//   pitch sticks still move their channels and only CH4 follows the bridge.
//
// 3.3 V logic into the Pocket's trainer input is expected to work but is unverified on this radio;
// the pinout (tip = PPM, sleeve = GND) is inferred, so check it with a meter before connecting.
//
// Serial: Serial0 is UART0 (GPIO 43/44) behind the board's CH343 USB-UART chip, the USB-C port next
// to the BOOT button (Linux: 1a86:55d3, /dev/ttyACM*; use /dev/serial/by-id).  Serial0 keeps the
// bridge on that port even if "USB CDC On Boot" is enabled, which would move Serial to native USB.
// The ROM boot banner at reset is discarded by the host's HELLO retry.
#include <string.h>
#include "src/core.h"
#include "src/line_reader.h"
#include "ppm.h"

static const char PPM_MODE[] = "PPM_YAW";

static ball_core core;
static ball_line reader;
static char reply[160];
static bool session_armed;  // this session's READY said PPM_YAW and the jumper has stayed in

void setup() {
    // Must match DEFAULT_BAUD in software/ball_demo/bridge.py.  9600 is too slow: one CMD frame
    // (~53 bytes) takes ~55 ms on the wire, longer than the host's 50 ms (20 Hz) command period.
    Serial0.begin(115200);
    ball_init(&core);
    ball_line_init(&reader);
    ppm_init();
}

void loop() {
    uint32_t now = millis();
    ball_tick(&core, now);
    ball_line_tick(&reader, now);

    bool jumper = ppm_safety_ok();
    ball_set_output_mode(&core, jumper ? PPM_MODE : BALL_NO_OUTPUT);

    while (Serial0.available() > 0) {
        int value = Serial0.read();
        now = millis();
        if (ball_line_feed(&reader, &core, value, now, reply, sizeof(reply))) {
            if (!strncmp(reply, "READY ", 6)) session_armed = !strcmp(core.session_output, PPM_MODE);
            Serial0.write(reply, strlen(reply));
        }
    }

    if (!jumper || strcmp(core.session_output, PPM_MODE)) session_armed = false;
    ppm_update(session_armed, core.enabled, core.yaw);
}
