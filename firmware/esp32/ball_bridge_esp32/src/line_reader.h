#ifndef BALL_LINE_READER_H
#define BALL_LINE_READER_H
#include "core.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Byte-at-a-time framing around ball_receive: one LF-terminated frame at a time, partial input
 * older than the watchdog period is dropped, and oversized/expired input is discarded through
 * the next LF so a command-looking suffix of a bad frame is never accepted. */
typedef struct {
    char line[BALL_MAX_FRAME + 1];
    size_t used;
    bool discard;
    uint32_t partial_started_ms;
} ball_line;

void ball_line_init(ball_line *reader);
/* Expire stale partial input; call on every loop pass. */
void ball_line_tick(ball_line *reader, uint32_t now_ms);
/* Returns true when reply holds a complete reply to send. */
bool ball_line_feed(ball_line *reader, ball_core *core, int byte, uint32_t now_ms,
                    char *reply, size_t capacity);

#ifdef __cplusplus
}
#endif
#endif
