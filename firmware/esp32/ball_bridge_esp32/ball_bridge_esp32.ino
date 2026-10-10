// Freenove ESP32-S3 WROOM serial protocol bridge, USB-UART, 115200 baud.
// NO TRAINER OUTPUT. READY advertises NO_OUTPUT; ACK means internal state only.
// No GPIO/timer/PPM peripheral is configured. The shared 250 ms watchdog
// neutralizes internal command state. Flashing, USB enumeration, reset behavior
// and all radio/electrical/override gates still need physical verification.
// Compile with esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=default
#include <Arduino.h>
#include <string.h>
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
