# Direct portable-C sanitizer follow-up — 2026-10-09

The final full profiles used UBSan and passed. One default full-profile ASan/UBSan child process exited `-11` without diagnostics. These exact local checks preserve the follow-up output for that intermittent runtime result.

## Portable command core

Build command:

```sh
clang -std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer firmware/core.c firmware/test_core.c -o /tmp/mission-status-firmware-tests
```

The [build log](core-build.txt) is empty with exit code 0. Running the binary exited 0 and printed that 10,000 seeded arbitrary frames, command boundaries, parsing, bounds, session, watchdog and clock rollover passed: [run output](core-run.txt).

## Mega line reader

Build command:

```sh
clang -std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer firmware/core.c firmware/line_reader.c firmware/test_line_reader.c -o /tmp/mission-status-line-reader-tests
```

The [build log](line-reader-build.txt) is empty with exit code 0. Two normal direct runs exited 139 with empty output ([first](line-reader-run.txt), [retry](line-reader-run-retry.txt)). Running the same binary with `ASAN_OPTIONS=verbosity=1:abort_on_error=1` exited 0, reached `AddressSanitizer Init done`, and printed `LINE READER TESTS PASSED`: [verbose output](line-reader-asan-verbose.txt). The full UBSan core and desktop profiles also passed the Mega line-reader checks.

This is inconsistent ASan runtime behavior in this environment; no code diagnostic was produced by the failed invocations. The complete UBSan profiles remain the reproducible full-suite result. No hardware, Pi, transmitter or flight checks were performed.
