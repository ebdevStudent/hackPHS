/*
 * CPPM generator for ESP32-S3: hardware timer interrupt at 2 MHz (0.5 us per tick).
 *
 * Frame: for each channel a LOW separator then HIGH for the rest of the channel time, then a LOW
 * separator and a long HIGH sync gap.  The yaw value and sync length are latched once at the start
 * of every frame, so a frame never mixes two yaw values and its length is always PPM_FRAME_US.
 *
 * The main loop only publishes a request (stream flag, yaw ticks, freshness count) under a spinlock.
 * The ISR decides per frame: fresh request -> its yaw; streaming but stale (loop stalled) -> 1500 us;
 * not streaming -> PPM_TAIL_FRAMES neutral frames, then idle HIGH.
 *
 * Supports both Arduino-ESP32 v2 and v3 core APIs via compile-time version detection.
 */
#include "ppm.h"
#include <Arduino.h>
#include "soc/gpio_reg.h"

#define TICKS_PER_US 2
#define SEP_TICKS (PPM_SEP_US * TICKS_PER_US)       /*    600 */
#define FRAME_TICKS (PPM_FRAME_US * TICKS_PER_US)   /* 45 000 */
#define CENTER_TICKS (PPM_CENTER_US * TICKS_PER_US) /*  3 000 */

static portMUX_TYPE ppm_mux = portMUX_INITIALIZER_UNLOCKED;

/* Request from loop(); only touched under ppm_mux, which also orders the accesses. */
static bool req_stream;
static uint32_t req_yaw_ticks = CENTER_TICKS;
static uint8_t req_fresh;

/* ISR-only state. */
static uint32_t frame_yaw_ticks = CENTER_TICKS;
static uint32_t frame_sync_ticks;
static uint8_t isr_index;
static bool isr_high = true;
static uint8_t tail_left;

static hw_timer_t *ppm_timer = NULL;

/* Direct register writes: IRAM-safe, unlike digitalWrite (flash-resident).  Pin must be < 32. */
#define PPM_PIN_HIGH() REG_WRITE(GPIO_OUT_W1TS_REG, BIT(PPM_OUTPUT_PIN))
#define PPM_PIN_LOW() REG_WRITE(GPIO_OUT_W1TC_REG, BIT(PPM_OUTPUT_PIN))

static inline void IRAM_ATTR set_alarm(uint32_t ticks) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  timerAlarm(ppm_timer, ticks, true, 0);
#else
  timerAlarmWrite(ppm_timer, ticks, true);
  timerAlarmEnable(ppm_timer);
#endif
}

/* Start of a frame: pick its yaw.  Returns false to stay idle for this frame period. */
static bool IRAM_ATTR frame_begin() {
  bool active = true;
  uint32_t yaw = CENTER_TICKS;
  portENTER_CRITICAL_ISR(&ppm_mux);
  if (req_stream) {
    tail_left = PPM_TAIL_FRAMES;
    if (req_fresh) {
      req_fresh--;
      yaw = req_yaw_ticks;
    }
  } else if (tail_left) {
    tail_left--;
  } else {
    active = false;
  }
  portEXIT_CRITICAL_ISR(&ppm_mux);
  frame_yaw_ticks = yaw;
  frame_sync_ticks = FRAME_TICKS - (PPM_CHANNELS - 1) * CENTER_TICKS - yaw - SEP_TICKS;
  return active;
}

static void IRAM_ATTR ppm_isr() {
  if (isr_high) {
    if (isr_index == 0 && !frame_begin()) {
      PPM_PIN_HIGH(); /* idle: no edges */
      set_alarm(FRAME_TICKS);
      return;
    }
    PPM_PIN_LOW();
    set_alarm(SEP_TICKS);
    isr_high = false;
    return;
  }
  PPM_PIN_HIGH();
  uint32_t ticks;
  if (isr_index < PPM_CHANNELS) {
    ticks = (isr_index == PPM_CH_YAW ? frame_yaw_ticks : CENTER_TICKS) - SEP_TICKS;
    isr_index++;
  } else {
    ticks = frame_sync_ticks;
    isr_index = 0;
  }
  set_alarm(ticks);
  isr_high = true;
}

void ppm_init() {
  /* Latch HIGH before enabling the driver so the pin never pulses LOW at start-up. */
  PPM_PIN_HIGH();
  pinMode(PPM_OUTPUT_PIN, OUTPUT);
  PPM_PIN_HIGH();

  pinMode(PPM_SAFETY_PIN, INPUT_PULLUP); /* jumper to GND = output allowed */

#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ppm_timer = timerBegin(2000000);
  timerAttachInterrupt(ppm_timer, &ppm_isr);
  timerAlarm(ppm_timer, FRAME_TICKS, true, 0);
#else
  ppm_timer = timerBegin(0, 40, true); /* timer 0, 80 MHz / 40 = 2 MHz */
  timerAttachInterrupt(ppm_timer, &ppm_isr, true);
  timerAlarmWrite(ppm_timer, FRAME_TICKS, true);
  timerAlarmEnable(ppm_timer);
#endif
}

bool ppm_safety_ok() {
  return digitalRead(PPM_SAFETY_PIN) == LOW;
}

int ppm_yaw_us(bool enabled, int yaw) {
  if (!enabled) return PPM_CENTER_US;
  if (yaw < -1000) yaw = -1000;
  if (yaw > 1000) yaw = 1000;
  return PPM_CENTER_US + yaw * PPM_YAW_LIMIT_US / 1000;
}

void ppm_update(bool stream, bool enabled, int yaw) {
  uint32_t ticks = (uint32_t)ppm_yaw_us(stream && enabled, yaw) * TICKS_PER_US;
  portENTER_CRITICAL(&ppm_mux);
  req_stream = stream;
  req_yaw_ticks = ticks;
  req_fresh = stream ? PPM_FRESH_FRAMES : 0;
  portEXIT_CRITICAL(&ppm_mux);
}
