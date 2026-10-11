#include "core.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static bool send(ball_core *c, const char *line, uint32_t now) {
    char reply[160];
    return ball_receive(c, line, strlen(line), now, reply, sizeof(reply));
}
int main(void) {
    ball_core c;
    ball_init(&c);
    assert(!c.enabled && c.yaw == 0);
    assert(!strcmp(c.output_mode, "NO_OUTPUT") && !strcmp(c.session_output, "NO_OUTPUT"));
    {   /* Output mode is latched at HELLO: a mid-session change is neither advertised nor armed. */
        ball_core o; char r[160];
        memset(&o, 0x5a, sizeof(o)); ball_init(&o);
        assert(ball_receive(&o, "HELLO 1 s1\n", 11, 0, r, sizeof(r)) && !strcmp(r, "READY 1 s1 NO_OUTPUT\n"));
        ball_set_output_mode(&o, "PPM_YAW");
        assert(!strcmp(o.session_output, "NO_OUTPUT"));
        assert(ball_receive(&o, "HELLO 1 s2\n", 11, 0, r, sizeof(r)) && !strcmp(r, "READY 1 s2 PPM_YAW\n"));
        assert(!strcmp(o.session_output, "PPM_YAW"));
        ball_set_output_mode(&o, NULL);
        assert(!strcmp(o.session_output, "PPM_YAW") && !strcmp(o.output_mode, "NO_OUTPUT"));
        assert(ball_receive(&o, "HELLO 1 s3\n", 11, 0, r, sizeof(r)) && !strcmp(r, "READY 1 s3 NO_OUTPUT\n"));
    }
    assert(!send(&c, "CMD 1 abc 1 1 10\n", 0));
    assert(send(&c, "HELLO 1 abc\n", 0));
    assert(send(&c, "CMD 1 abc 1 1 650\n", 10));
    assert(c.yaw == 650 && c.enabled);
    assert(send(&c, "CMD 1 abc 1 1 800\n", 200));
    assert(c.yaw == 650 && c.last_valid_ms == 10);
    const char *invalid[] = {"CMD 2 abc 2 1 10", "CMD 1 abc 2 1 1001", "CMD 1 abc 2 0 12",
        "CMD 1 wrong 2 1 0", "CMD 1 abc 2 2 0", "CMD 1 abc 0 1 0", "CMD 1 abc 2 1 0 extra",
        "CMD 1 abc 2 1 2.5", "CMD 1 abc 2 1 +3", "CMD 1 abc 2 1 01", "CMD 1 abc 2 1 1\t",
        "CMD  1 abc 2 1 1", "CMD 1 abc 2147483648 1 0", "CMD 1 abc 21474836470 1 0",
        "CMD 1 abc 99999999999999999 1 0", "CMD 1 abc 2 1 -0"};
    for (size_t i = 0; i < sizeof(invalid)/sizeof(invalid[0]); ++i)
        assert(!send(&c, invalid[i], 220));
    assert(c.last_valid_ms == 10);
    ball_tick(&c, 260);
    assert(c.yaw == 0 && !c.enabled && c.watchdog_fault);
    assert(send(&c, "CMD 1 abc 2 0 0\n", 300));
    assert(!c.enabled && c.yaw == 0 && !c.watchdog_fault);
    assert(send(&c, "HELLO 1 xyz\n", 400));
    assert(!c.enabled && c.seq == 0 && !c.has_command);
    assert(send(&c, "CMD 1 xyz 1 1 -1000\n", 0xffffff80u));
    ball_tick(&c, 122u); /* uint32 rollover: exactly 250 ms */
    assert(c.yaw == 0 && c.watchdog_fault);
    char huge[130]; memset(huge, 'A', sizeof(huge));
    char reply[160]; assert(!ball_receive(&c, huge, sizeof(huge), 0, reply, sizeof(reply)));
    const char embedded[] = {'H','E','L','L','O',' ','1',' ','a',0,'b'};
    assert(!ball_receive(&c, embedded, sizeof(embedded), 0, reply, sizeof(reply)));
    /* Reproducible arbitrary byte/length corpus for host sanitizers. */
    uint32_t seed = 20261004u;
    for (unsigned trial = 0; trial < 10000; ++trial) {
        char frame[130];
        seed = seed * 1664525u + 1013904223u;
        size_t length = seed % sizeof(frame);
        for (size_t i = 0; i < length; ++i) {
            seed = seed * 1664525u + 1013904223u;
            frame[i] = (char)(seed >> 24);
        }
        ball_init(&c);
        (void)ball_receive(&c, frame, length, trial, reply, sizeof(reply));
        assert(c.yaw >= -1000 && c.yaw <= 1000);
        if (!c.enabled) assert(c.yaw == 0);
    }
    for (int yaw = -1000; yaw <= 1000; yaw += 100) {
        char command[80];
        ball_init(&c);
        assert(send(&c, "HELLO 1 bounds\n", 0));
        snprintf(command, sizeof(command), "CMD 1 bounds 2147483647 1 %d\n", yaw);
        assert(send(&c, command, 1));
        assert(c.yaw == yaw && c.seq == 2147483647u);
        ball_tick(&c, 251);
        assert(!c.enabled && c.yaw == 0 && c.watchdog_fault);
    }
    puts("PASS: 10000 seeded arbitrary frames and full command-boundary sweep.");
    puts("PASS: portable C parsing, bounds, sequence, session, watchdog and clock rollover. No transmitter output.");
    return 0;
}
