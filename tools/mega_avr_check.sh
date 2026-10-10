#!/usr/bin/env bash
# Run the Mega bridge's shared C code as real AVR firmware in the simavr ATmega2560 simulator,
# plus Linux ASan+UBSan host tests. Usage: tools/mega_avr_check.sh [output-file]
# Simulated CPU only: no USB-serial chip, board, radio or trainer output is exercised.
set -euo pipefail
output=${1:-/dev/stdout}
root=$(cd "$(dirname "$0")/.." && pwd)
docker run --rm --platform linux/arm64 -v "$root/firmware":/fw:ro ubuntu:24.04 bash -c '
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null && apt-get install -y -qq gcc-avr avr-libc simavr clang >/dev/null 2>&1
echo "== toolchain"; avr-gcc --version | head -1; dpkg -s simavr | grep ^Version
cd /tmp && cp /fw/core.c /fw/core.h /fw/line_reader.c /fw/line_reader.h /fw/test_line_reader.c /fw/test_core.c .
echo "== Linux host ASan+UBSan"
clang -std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-sanitize-recover=all core.c line_reader.c test_line_reader.c -o host_lr && ./host_lr
clang -std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-sanitize-recover=all core.c test_core.c -o host_core && ./host_core && echo "core tests passed"
echo "== ATmega2560 build"
avr-gcc -mmcu=atmega2560 -std=gnu11 -Os -Wall -Wextra -Werror -pedantic core.c line_reader.c test_line_reader.c -o avr_lr.elf
avr-size --format=avr --mcu=atmega2560 avr_lr.elf | grep -E "Program|Data"
echo "== simavr run (UART0 output)"
timeout 120 simavr -m atmega2560 -f 16000000 avr_lr.elf > sim.log 2>&1 || true
cat sim.log | tr -d "\r" | grep -v "^$" | tail -20
grep -q "LINE READER TESTS PASSED" sim.log && ! grep -q "^FAIL" sim.log && echo "AVR SIMULATION PASSED"
echo "== harness self-test: a forced failure must be reported by the simulator"
avr-gcc -mmcu=atmega2560 -std=gnu11 -Os -DBALL_FORCE_FAILURE core.c line_reader.c test_line_reader.c -o avr_fail.elf
timeout 120 simavr -m atmega2560 -f 16000000 avr_fail.elf > fail.log 2>&1 || true
grep -q "LINE READER TESTS FAILED" fail.log && grep -q "forced failure" fail.log && echo "HARNESS DETECTS FAILURES"
' 2>&1 | tee "$output"
