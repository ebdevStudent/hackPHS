#include "core.h"
#include "pico/stdlib.h"
#include "pico/stdio_usb.h"
#include <string.h>

/* Deliberately no GPIO/trainer implementation. USB ACKs report internal state only. */
int main(void) {
    stdio_init_all();
    ball_core core;
    ball_init(&core);
    char line[BALL_MAX_FRAME + 1], reply[160];
    size_t used = 0;
    bool discard = false, was_connected = false;
    uint32_t partial_started = 0;
    
    for (;;) {
        uint32_t now = to_ms_since_boot(get_absolute_time());
        ball_tick(&core, now);
        bool connected = stdio_usb_connected();
        if (was_connected && !connected) { ball_init(&core); used = 0; discard = false; }
        was_connected = connected;
        if (used && (uint32_t)(now - partial_started) >= BALL_WATCHDOG_MS) { used = 0; discard = true; }
        int value = getchar_timeout_us(0);
        if (value == PICO_ERROR_TIMEOUT) { sleep_ms(1); continue; }
        if (value == '\n') {
            if (!discard) {
                line[used++] = '\n';
                if (ball_receive(&core, line, used, now, reply, sizeof(reply))) {
                    stdio_put_string(reply, (int)strlen(reply), false, false);
                }
            }
            used = 0; discard = false;
        } else if (!discard) {
            if (!used) partial_started = now;
            if (used >= BALL_MAX_FRAME - 1) { used = 0; discard = true; }
            else line[used++] = (char)value;
        }
    }
}
