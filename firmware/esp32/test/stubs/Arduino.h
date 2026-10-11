/* Host stand-in for the parts of Arduino-ESP32 v3 that ppm.cpp uses.  The simulator in
 * test_ppm.cpp owns the clock: it fires the attached ISR whenever the armed alarm expires. */
#ifndef SIM_ARDUINO_H
#define SIM_ARDUINO_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define ESP_ARDUINO_VERSION_MAJOR 3
#define IRAM_ATTR
#define HIGH 1
#define LOW 0
#define OUTPUT 0x03
#define INPUT_PULLUP 0x05

typedef struct { int unused; } hw_timer_t;
typedef struct { int unused; } portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED {0}
#define portENTER_CRITICAL(m) ((void)(m))
#define portEXIT_CRITICAL(m) ((void)(m))
#define portENTER_CRITICAL_ISR(m) ((void)(m))
#define portEXIT_CRITICAL_ISR(m) ((void)(m))

extern int sim_safety_level;
extern uint64_t sim_alarm_ticks;
extern void (*sim_isr)(void);
extern hw_timer_t sim_timer;

static inline void pinMode(uint8_t, uint8_t) {}
static inline int digitalRead(uint8_t) { return sim_safety_level; }
static inline hw_timer_t *timerBegin(uint32_t) { return &sim_timer; }
static inline void timerAttachInterrupt(hw_timer_t *, void (*isr)(void)) { sim_isr = isr; }
static inline void timerAlarm(hw_timer_t *, uint64_t ticks, bool, uint64_t) { sim_alarm_ticks = ticks; }
#endif
