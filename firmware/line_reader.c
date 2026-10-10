#include "line_reader.h"
#include <string.h>

void ball_line_init(ball_line *reader) { memset(reader, 0, sizeof(*reader)); }

void ball_line_tick(ball_line *reader, uint32_t now_ms) {
    if (reader->used && (uint32_t)(now_ms - reader->partial_started_ms) >= BALL_WATCHDOG_MS) {
        reader->used = 0;
        reader->discard = true;
    }
}

bool ball_line_feed(ball_line *reader, ball_core *core, int byte, uint32_t now_ms,
                    char *reply, size_t capacity) {
    ball_line_tick(reader, now_ms);
    if (byte < 0 || byte > 255) return false;
    if (byte == '\n') {
        bool replied = false;
        if (!reader->discard) {
            reader->line[reader->used++] = '\n';
            replied = ball_receive(core, reader->line, reader->used, now_ms, reply, capacity);
        }
        reader->used = 0;
        reader->discard = false;
        return replied;
    }
    if (reader->discard) return false;
    if (!reader->used) reader->partial_started_ms = now_ms;
    if (reader->used >= BALL_MAX_FRAME - 1) {
        reader->used = 0;
        reader->discard = true;
    } else {
        reader->line[reader->used++] = (char)byte;
    }
    return false;
}
