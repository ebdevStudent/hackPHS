/* Line framing + protocol core checks shared by the host build (sanitizers) and the AVR
 * simulator build (8-bit int/long sizes, ATmega2560). Report goes through report(). */
#include "line_reader.h"
#include <stdio.h>
#include <string.h>

#ifdef __AVR__
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
static void put(char c) { while (!(UCSR0A & (1 << UDRE0))) {} UDR0 = (uint8_t)c; }
static void report(const char *s) { while (*s) put(*s++); }
static void finish(void) { cli(); sleep_enable(); sleep_cpu(); for (;;) {} }
#else
static void report(const char *s) { fputs(s, stdout); }
static void finish(void) {}
#endif

static int failures;
static char reply[160];
static void check(int ok, const char *name) {
    if (!ok) { failures++; report("FAIL "); report(name); report("\n"); }
}

/* Feed a string byte by byte; return the number of replies and keep the last in reply[]. */
static int feed(ball_line *r, ball_core *c, const char *text, uint32_t now) {
    int replies = 0;
    for (; *text; ++text)
        if (ball_line_feed(r, c, (unsigned char)*text, now, reply, sizeof(reply))) replies++;
    return replies;
}

int main(void) {
#ifdef __AVR__
    UBRR0 = 0; UCSR0B = (1 << TXEN0);
#endif
    ball_core core; ball_line reader;
    ball_init(&core); ball_line_init(&reader);

    check(sizeof(int) == 2 || sizeof(int) == 4, "int size");
    check(feed(&reader, &core, "HELLO 1 mega\n", 0) == 1 && !strcmp(reply, "READY 1 mega NO_OUTPUT\n"), "hello");
    check(feed(&reader, &core, "CMD 1 mega 1 1 -650\r\n", 10) == 1 && !strcmp(reply, "ACK 1 mega 1 1 -650 NONE\n"), "crlf command");
    check(core.yaw == -650 && core.enabled, "accepted yaw");
    check(feed(&reader, &core, "CMD 1 mega 2147483647 1 1000\n", 20) == 1 && core.seq == 2147483647UL, "max sequence");
    check(feed(&reader, &core, "CMD 1 mega 2147483648 1 0\n", 30) == 0 && core.yaw == 1000, "sequence overflow rejected");
    check(feed(&reader, &core, "CMD 1 mega 5 1 1\n", 30) == 1 && strstr(reply, "SEQUENCE") != 0, "old sequence");

    /* Partial frame expires after the watchdog period and is discarded through the next LF. */
    ball_init(&core); ball_line_init(&reader);
    feed(&reader, &core, "HELLO 1 s\n", 0);
    check(feed(&reader, &core, "CMD 1 s 1 1 300", 100) == 0, "partial held");
    ball_line_tick(&reader, 350);
    check(reader.discard && reader.used == 0, "partial expired");
    check(feed(&reader, &core, "\n", 360) == 0 && core.yaw == 0, "expired partial not accepted");
    check(feed(&reader, &core, "CMD 1 s 1 1 300\n", 370) == 1 && core.yaw == 300, "next frame accepted");

    /* Oversized input is discarded through LF; a command-looking suffix is never accepted. */
    ball_init(&core); ball_line_init(&reader);
    feed(&reader, &core, "HELLO 1 s\n", 0);
    for (int i = 0; i < BALL_MAX_FRAME + 10; ++i) ball_line_feed(&reader, &core, 'X', 1, reply, sizeof(reply));
    check(feed(&reader, &core, "CMD 1 s 1 1 999\n", 2) == 0 && core.yaw == 0, "oversize suffix rejected");
    check(feed(&reader, &core, "CMD 1 s 1 1 999\n", 3) == 1 && core.yaw == 999, "recovers after discard");

    /* Watchdog neutralises 250 ms after the last valid command, across 32-bit rollover. */
    ball_init(&core); ball_line_init(&reader);
    feed(&reader, &core, "HELLO 1 w\n", 0xFFFFFF00UL);
    feed(&reader, &core, "CMD 1 w 1 1 500\n", 0xFFFFFF00UL);
    ball_tick(&core, 0xFFFFFF00UL + 249UL);
    check(core.yaw == 500, "before watchdog");
    ball_tick(&core, 0xFFFFFF00UL + 250UL);
    check(core.yaw == 0 && !core.enabled && core.watchdog_fault, "watchdog neutral at rollover");

    /* Out-of-range bytes are ignored; NUL and high bytes make the frame invalid. */
    ball_init(&core); ball_line_init(&reader);
    feed(&reader, &core, "HELLO 1 b\n", 0);
    check(!ball_line_feed(&reader, &core, -1, 1, reply, sizeof(reply)) && !ball_line_feed(&reader, &core, 256, 1, reply, sizeof(reply)), "out-of-range ints");
    check(feed(&reader, &core, "CMD 1 b 1 1 4\xff\n", 2) == 0 && core.yaw == 0, "high byte rejected");

    /* Pseudo-random bytes never leave a non-neutral disabled state or an out-of-range yaw. */
    uint32_t seed = 20261008UL;
    ball_init(&core); ball_line_init(&reader);
    feed(&reader, &core, "HELLO 1 r\n", 0);
    for (uint16_t i = 0; i < 4000; ++i) {
        seed = seed * 1664525UL + 1013904223UL;
        int byte = (int)((seed >> 24) & 0xFF);
        if ((seed & 0x1F) == 0) byte = '\n';
        ball_line_feed(&reader, &core, byte, i, reply, sizeof(reply));
        if (core.yaw < -1000 || core.yaw > 1000 || (!core.enabled && core.yaw != 0)) { check(0, "random bytes"); break; }
    }

#ifdef BALL_FORCE_FAILURE
    check(0, "forced failure (harness self-test)");
#endif
    report(failures ? "LINE READER TESTS FAILED\n" : "LINE READER TESTS PASSED\n");
    finish();
    return failures != 0;
}
