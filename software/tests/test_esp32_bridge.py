"""Selected-board protocol compatibility without serial hardware or GPIO output."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKETCH = ROOT / 'firmware/esp32/ball_bridge_esp32'


@pytest.mark.parametrize('name', ['core.c', 'core.h', 'line_reader.c', 'line_reader.h'])
def test_selected_board_uses_the_verified_shared_protocol(name):
    assert (SKETCH / 'src' / name).read_bytes() == (ROOT / 'firmware' / name).read_bytes()


def test_actual_sketch_runs_protocol_watchdog_and_framing_against_uart_stub(tmp_path):
    # No GPIO/timer functions exist in this stub: any attempted actuation fails to compile.
    (tmp_path / 'Arduino.h').write_text('''#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string>
extern uint32_t clock_ms;
inline uint32_t millis() { return clock_ms; }
struct UART {
  int baud = 0; std::string input, output;
  void begin(int value) { baud = value; }
  int available() { return static_cast<int>(input.size()); }
  int read() { unsigned char value = input[0]; input.erase(0, 1); return value; }
  void write(const char *bytes, size_t length) { output.append(bytes, length); }
};
extern UART Serial;
''')
    harness = tmp_path / 'sketch.cpp'
    harness.write_text('''#include "Arduino.h"
#include <cassert>
#include <iostream>
uint32_t clock_ms = 0; UART Serial;
#include "''' + str(SKETCH / 'ball_bridge_esp32.ino') + '''"
int main() {
  setup(); assert(Serial.baud == 115200); assert(!core.enabled && core.yaw == 0);
  Serial.input = "HELLO 1 abc\\n"; loop(); assert(Serial.output == "READY 1 abc NO_OUTPUT\\n");
  clock_ms = 10; Serial.input = "CMD 1 abc 1 1 500\\n"; loop(); assert(core.enabled && core.yaw == 500);
  clock_ms = 259; loop(); assert(core.enabled); clock_ms = 260; loop(); assert(!core.enabled && core.yaw == 0);
  Serial.input = std::string(129, 'x') + "CMD 1 abc 2 1 800\\n"; loop(); assert(!core.enabled);
  Serial.input = "CMD 1 abc 3 0 0\\n"; loop(); assert(core.seq == 3 && core.yaw == 0);
  Serial.input = "HELLO 1 reset\\n"; loop(); assert(core.seq == 0 && !core.enabled);
  clock_ms = 0xffffff80u; Serial.input = "CMD 1 reset 1 1 -300\\n"; loop();
  clock_ms = 122; loop(); assert(!core.enabled && core.yaw == 0);
  std::cout << "ESP32 SKETCH UART/WATCHDOG TESTS PASSED\\n";
}
''')
    cc, cpp = shutil.which('clang'), shutil.which('clang++')
    assert cc and cpp
    objects = []
    for name in ('core.c', 'line_reader.c'):
        obj = tmp_path / (name + '.o')
        subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined',
            '-c', str(SKETCH / 'src' / name), '-o', str(obj)], check=True, capture_output=True, timeout=30)
        objects.append(str(obj))
    binary = tmp_path / 'esp32-sketch'
    built = subprocess.run([cpp, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined',
        '-I', str(tmp_path), str(harness), *objects, '-o', str(binary)], capture_output=True, text=True, timeout=30)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    assert 'ESP32 SKETCH UART/WATCHDOG TESTS PASSED' in run.stdout
