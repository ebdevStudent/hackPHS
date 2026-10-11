#ifndef BALL_CORE_H
#define BALL_CORE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BALL_MAX_FRAME 128
#define BALL_WATCHDOG_MS 250
typedef struct {
    char session[33];
    uint32_t seq, last_valid_ms;
    bool enabled, has_command;
    int yaw;
    bool watchdog_fault;
    /* Output mode the application can provide right now ("NO_OUTPUT" or "PPM_YAW"), and the
     * mode latched into this session's READY at HELLO.  Output may only be driven while the
     * session advertised it; a hardware change mid-session needs a new HELLO to take effect. */
    const char *output_mode;
    const char *session_output;
} ball_core;

#define BALL_NO_OUTPUT "NO_OUTPUT"

void ball_init(ball_core *core);
/* Keeps across HELLO; NULL means BALL_NO_OUTPUT.  The string must outlive the core. */
void ball_set_output_mode(ball_core *core, const char *mode);
void ball_tick(ball_core *core, uint32_t now_ms);
/* Complete ASCII line only; reply describes internal accepted state, never GPIO output. */
bool ball_receive(ball_core *core, const char *line, size_t length, uint32_t now_ms,
                  char *reply, size_t capacity);

#ifdef __cplusplus
}
#endif
#endif
