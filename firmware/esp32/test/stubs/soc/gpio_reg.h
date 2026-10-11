/* Host stand-in for the ESP32-S3 GPIO set/clear registers: the simulator records pin edges. */
#ifndef SIM_GPIO_REG_H
#define SIM_GPIO_REG_H
#include <stdint.h>

#define GPIO_OUT_W1TS_REG 1
#define GPIO_OUT_W1TC_REG 2
#define BIT(n) (1UL << (n))

void sim_reg_write(int reg, unsigned long mask);
#define REG_WRITE(reg, val) sim_reg_write((reg), (val))
#endif
