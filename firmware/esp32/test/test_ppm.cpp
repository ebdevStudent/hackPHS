/* Host simulation of the ESP32-S3 CPPM generator (ppm.cpp) against stub Arduino/GPIO headers.
 * Steps the timer ISR on a simulated 2 MHz clock, records the output pin, and decodes the waveform
 * the way EdgeTX does (falling edge to falling edge, sync gap 4-19 ms, channels 800-2200 us).
 *
 * Build: c++ -std=c++17 -Wall -Wextra -Werror -I stubs -I ../ball_bridge_esp32 test_ppm.cpp
 */
#include "../ball_bridge_esp32/ppm.cpp"

#include <cassert>
#include <cstdio>
#include <vector>

int sim_safety_level = HIGH;
uint64_t sim_alarm_ticks;
void (*sim_isr)(void);
hw_timer_t sim_timer;

static const uint64_t US = 2; /* ticks per microsecond */
static uint64_t now;          /* loop() wall clock */
static uint64_t isr_time;     /* when the timer last fired; edges happen then */
static int level = -1;        /* -1 = not driven yet */
static bool went_low_before_start;
static std::vector<uint64_t> falls;

void sim_reg_write(int reg, unsigned long mask) {
  assert(mask == BIT(PPM_OUTPUT_PIN));
  int next = reg == GPIO_OUT_W1TS_REG ? 1 : 0;
  if (level == 1 && next == 0) falls.push_back(isr_time);
  if (level == -1 && next == 0) went_low_before_start = true;
  level = next;
}

static void run_until(uint64_t t) {
  while (isr_time + sim_alarm_ticks <= t) { /* auto-reload: each alarm counts from the last fire */
    isr_time += sim_alarm_ticks;
    sim_isr();
  }
  now = t;
}

/* loop() at 1 kHz for ms milliseconds, publishing the same request every pass. */
static void loop_for(int ms, bool stream, bool enabled, int yaw) {
  for (int i = 0; i < ms; ++i) {
    ppm_update(stream, enabled, yaw);
    run_until(now + 1000 * US);
  }
}

/* loop() stalled: the ISR keeps running on its own. */
static void stall_for(int ms) { run_until(now + (uint64_t)ms * 1000 * US); }

struct Frame { uint64_t start; std::vector<int> ch; };

/* Decodes the whole capture (it starts from idle, so it is frame-aligned) and checks every frame:
 * 8 channels in range, non-yaw channels at 1500 us, sync gap 4-19 ms, and a constant 22.5 ms period
 * within each burst.  A frame cut off by the end of the capture is dropped. */
static std::vector<Frame> decode() {
  std::vector<Frame> frames;
  Frame cur{0, {}};
  bool burst = false; /* previous frame ended in a sync gap, not idle */
  for (size_t i = 1; i < falls.size(); ++i) {
    uint64_t d = falls[i] - falls[i - 1];
    if (cur.ch.size() == PPM_CHANNELS) {
      assert(d >= 4000 * US);
      if (burst) assert(cur.start - frames.back().start == PPM_FRAME_US * US);
      frames.push_back(cur);
      burst = d <= 19000 * US; /* longer is idle: the radio sees the trainer signal stop */
      cur = Frame{0, {}};
      continue;
    }
    assert(d < 4000 * US); /* no sync in the middle of a frame */
    if (cur.ch.empty()) cur.start = falls[i - 1];
    cur.ch.push_back((int)(d / US));
  }
  if (cur.ch.size() == PPM_CHANNELS) frames.push_back(cur);
  for (const Frame &f : frames)
    for (int c = 0; c < PPM_CHANNELS; ++c) {
      assert(f.ch[c] >= 800 && f.ch[c] <= 2200);
      if (c != PPM_CH_YAW) assert(f.ch[c] == PPM_CENTER_US);
    }
  return frames;
}

static std::vector<Frame> frames_since(uint64_t t) {
  std::vector<Frame> out;
  for (const Frame &f : decode()) if (f.start >= t) out.push_back(f);
  return out;
}

static size_t falls_since(uint64_t t) {
  size_t n = 0;
  for (uint64_t f : falls) n += f >= t;
  return n;
}

static int yaw_of(const Frame &f) { return f.ch[PPM_CH_YAW]; }

static void expect_idle_for(int ms) {
  uint64_t mark = now;
  loop_for(ms, false, true, 1000);
  assert(falls_since(mark) == 0 && level == 1);
}

int main() {
  ppm_init();
  assert(level == 1 && !went_low_before_start); /* latched HIGH before the driver is enabled */
  assert(ppm_safety_ok() == false);
  sim_safety_level = LOW;
  assert(ppm_safety_ok() == true);

  /* Mapping: protocol +/-1000 -> 1500 +/- PPM_YAW_LIMIT_US, clamped; disabled is neutral. */
  assert(ppm_yaw_us(true, 1000) == 1650 && ppm_yaw_us(true, -1000) == 1350);
  assert(ppm_yaw_us(true, 5000) == 1650 && ppm_yaw_us(true, -5000) == 1350);
  assert(ppm_yaw_us(true, 0) == 1500 && ppm_yaw_us(false, 800) == 1500);
  assert(ppm_yaw_us(true, 650) == 1597);

  /* Not streaming: no edges at all, line held HIGH. */
  expect_idle_for(500);

  /* Streaming: every frame is 22.5 ms and only the yaw channel moves. */
  int cases[][3] = {{1, 1000, 1650}, {1, -1000, 1350}, {1, 4000, 1650}, {1, 0, 1500}, {0, 800, 1500}};
  for (auto &k : cases) {
    uint64_t mark = now;
    loop_for(500, true, k[0], k[1]);
    std::vector<Frame> frames = frames_since(mark);
    assert(frames.size() >= 20);
    for (const Frame &f : frames) assert(yaw_of(f) == k[2]);
  }

  /* Disable while armed keeps the stream running at neutral; it never goes silent. */
  loop_for(200, true, true, 1000);
  uint64_t mark = now;
  loop_for(2000, true, false, 1000);
  std::vector<Frame> frames = frames_since(mark);
  assert(frames.size() >= 85 && frames.back().start + 2 * PPM_FRAME_US * US > now);
  for (const Frame &f : frames) assert(yaw_of(f) == 1500);

  /* Main loop stalls: at most PPM_FRESH_FRAMES frames keep the last yaw, then neutral, and the
   * stream keeps running. */
  loop_for(200, true, true, -1000);
  mark = now;
  stall_for(1000);
  frames = frames_since(mark);
  assert(frames.size() >= 40);
  for (size_t i = 0; i < frames.size(); ++i) {
    if (i >= PPM_FRESH_FRAMES) assert(yaw_of(frames[i]) == 1500);
    else if (i + 1 < PPM_FRESH_FRAMES) assert(yaw_of(frames[i]) == 1350); /* one may be pre-latched */
  }

  /* Withdraw streaming (jumper pulled): the frame already started finishes, then exactly
   * PPM_TAIL_FRAMES neutral frames, then silence with the line HIGH. */
  loop_for(300, true, true, 1000);
  mark = now;
  loop_for(1000, false, true, 1000);
  frames = frames_since(mark);
  assert(frames.size() == PPM_TAIL_FRAMES);
  for (const Frame &f : frames) assert(yaw_of(f) == 1500);
  assert(level == 1 && falls.back() + PPM_FRAME_US * US < now);
  expect_idle_for(500);

  /* And it restarts cleanly from idle. */
  mark = now;
  loop_for(300, true, true, 500);
  frames = frames_since(mark);
  assert(frames.size() >= 10);
  for (const Frame &f : frames) assert(yaw_of(f) == 1575);

  puts("PASS: ESP32 PPM host simulation (frame timing, yaw cap, neutral on disable/stall, tail then idle).");
  return 0;
}
