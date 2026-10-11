#ifndef BALL_PPM_ESP32_H
#define BALL_PPM_ESP32_H
/*
 * CPPM trainer-signal generator for ESP32-S3 (Freenove board).
 *
 * Produces an 8-channel Combined PPM waveform on GPIO 4 using a hardware timer interrupt.  Only the
 * yaw channel (RC channel 4, array index 3) varies; every other channel is fixed at 1500 us.
 *
 * Neutral is a signal, not silence.  EdgeTX keeps applying the LAST trainer value for about 1 s after
 * the PPM stops (TRAINER_IN_VALID_TIMEOUT), so stopping the stream on disable would hold the last yaw.
 * While streaming is allowed the generator therefore keeps sending frames and puts yaw at 1500 us
 * whenever the bridge is not enabled (host disable, target loss, watchdog).  When streaming is
 * withdrawn (safety jumper pulled) it sends PPM_TAIL_FRAMES neutral frames, then holds the line idle
 * HIGH with no edges, which the radio treats as "trainer lost".
 *
 * Yaw authority is capped here: protocol yaw +/-1000 maps to +/-PPM_YAW_LIMIT_US around 1500 us.
 * The EdgeTX trainer weight on Rud is the second, radio-side cap (firmware/README.md).
 *
 * 3.3 V logic.  Driving the Pocket's trainer input (an STM32 timer pin) at 3.3 V is expected to work
 * but has not been verified on this radio; check the jack pinout (tip = PPM, sleeve = GND) with a
 * meter before connecting.  GPIO 4/5 double as camera SIOD/SIOC on this board: leave the camera
 * ribbon unplugged.
 */
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PPM_CHANNELS     8
#define PPM_CH_YAW       3      /* RC channel 4 = rudder/yaw (0-indexed) */
#define PPM_CENTER_US    1500
#define PPM_YAW_LIMIT_US 150    /* protocol yaw 1000 -> 1500 +/- 150 us   */
#define PPM_FRAME_US     22500  /* 22.5 ms frame period, about 44 Hz       */
#define PPM_SEP_US       300    /* LOW separator between channel pulses     */
#define PPM_TAIL_FRAMES  3      /* neutral frames sent before going idle    */
#define PPM_FRESH_FRAMES 5      /* yaw not refreshed for ~112 ms -> 1500 us */

/* GPIO assignments: avoid SD, USB, strapping (0/3/45/46) and UART0 (43/44) pins. */
#define PPM_OUTPUT_PIN   4      /* PPM signal out: 3.5 mm plug tip          */
#define PPM_SAFETY_PIN   5      /* safety jumper: bridge to any GND pin     */

/* Call once in setup(). */
void ppm_init(void);

/* Call on every loop() pass.  stream: output allowed (PPM session and jumper fitted).
 * enabled/yaw: the core's accepted command; yaw is ignored unless enabled. */
void ppm_update(bool stream, bool enabled, int yaw);

/* Returns true when the safety jumper bridges the safety pin to GND. */
bool ppm_safety_ok(void);

/* Protocol yaw (-1000..1000, clamped) to the yaw channel pulse width in us. */
int ppm_yaw_us(bool enabled, int yaw);

#ifdef __cplusplus
}
#endif
#endif
