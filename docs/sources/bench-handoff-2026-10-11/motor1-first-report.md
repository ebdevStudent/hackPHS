# Motor 1 USB command check — 2026-10-11

Actual local Linux laptop, Betaflight STM32F411 USB serial, firmware 4.4.2.
User confirmed propeller removed. One motor reported connected to Motor 1.
ESP32 trainer output was left untouched during this check.

A direct MSP command applied Motor 1 = 1020 for approximately 0.7 s.
An independent 0.8 s stop timer and finally cleanup sent stop commands.
Normal arming was blocked through MSP. No EEPROM save, calibration or firmware changes.

Returned data:

```json
{"voltage":7.46,"rc":[1505,1500,1500,1293,1000],"armed":false,"motors_before":[1000,1000,1000,1000]}
{"commanded":[1020,1000,1000,1000],"reported_during":[1020,1000,1000,1000]}
{"motors_after":[1000,1000,1000,1000]}
```

FC accepted and reported the motor command, then reported all outputs stopped.
Actual rotation, RPM, direction and smooth startup are not established by these replies.
Physical user observation remains pending. Bidirectional DShot telemetry was off.

Earlier browser keyboard attempt triggered its keyboard emergency stop; displayed outputs
remained at 1000. It did not establish a successful motor start.

Temporary command script: /tmp/hackphs_motor1_pulse.py. Running it repeats the physical
pulse; do not run for inspection. The script must not be used unattended.
