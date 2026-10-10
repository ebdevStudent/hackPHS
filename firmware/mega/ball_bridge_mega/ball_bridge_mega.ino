// Ball Drone protocol bridge scaffold for the Arduino Mega 2560: protocol version 1 over USB serial.
//
// Speaks the same ASCII HELLO/READY/CMD/ACK protocol as firmware/PROTOCOL.md using the shared C core
// (src/core.c) and line framing (src/line_reader.c).
//
// NO TRAINER OUTPUT. ACKs report accepted internal state only. Do not add GPIO, PPM or trainer output
// until the transmitter protocol, electrical interface, connector pinout and channel mapping are
// verified and the physical override/failsafe gates are authorized.
//
// Opening the USB port resets the Mega (DTR). The bootloader ignores the first ~1.5 s of input, so the
// host repeats HELLO until READY. On host loss the 250 ms watchdog returns the internal state to neutral
// and reports the accepted state as neutral; it does not drive any aircraft output.
#include "src/core.h"
#include "src/line_reader.h"

static ball_core core;
static ball_line reader;
static char reply[160];

void setup() {
    Serial.begin(115200);
    ball_init(&core);
    ball_line_init(&reader);
}

void loop() {
    uint32_t now = millis();
    ball_tick(&core, now);
    ball_line_tick(&reader, now);

    while (Serial.available() > 0) {
        int value = Serial.read();
        now = millis();
        if (ball_line_feed(&reader, &core, value, now, reply, sizeof(reply))) {
            Serial.write(reply, strlen(reply));
        }
    }

}
