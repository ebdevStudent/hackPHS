"""Decode the ESP32's CPPM output on a Raspberry Pi 5 GPIO (no scope needed).

Wiring: ESP32 GPIO4 -> 2 kOhm -> Pi GPIO17 (header pin 11); ESP32 GND -> any Pi GND (pin 39 was used).
Both sides are 3.3 V logic.

Each channel is the time between consecutive falling edges; a gap over SYNC_MIN_US ends a frame.
Usage: python3 ppm_probe.py [--gpio 17] [--seconds 2]
"""
import argparse
import statistics
import time

import lgpio

SYNC_MIN_US = 3000
CHANNELS = 8


def open_header_chip():
    """Pi 5 header GPIOs live on the RP1 chip; its gpiochip number differs between kernels."""
    for n in (0, 4):
        try:
            h = lgpio.gpiochip_open(n)
        except lgpio.error:
            continue
        if "rp1" in lgpio.gpio_get_chip_info(h)[3]:  # [status, lines, name, label]
            return h
        lgpio.gpiochip_close(h)
    raise SystemExit("! RP1 gpiochip not found")


def capture(gpio, seconds):
    h = open_header_chip()
    falls = []
    lgpio.gpio_claim_alert(h, gpio, lgpio.FALLING_EDGE)
    cb = lgpio.callback(h, gpio, lgpio.FALLING_EDGE, lambda _c, _g, _l, tick: falls.append(tick))
    time.sleep(seconds)
    level = lgpio.gpio_read(h, gpio)
    cb.cancel()
    lgpio.gpiochip_close(h)
    return falls, level


def decode(falls_ns):
    """Split falling-edge timestamps into frames of channel widths in microseconds."""
    gaps = [(b - a) / 1000 for a, b in zip(falls_ns, falls_ns[1:])]
    frames, cur = [], None
    for g in gaps:
        if g > SYNC_MIN_US:
            if cur is not None and len(cur) == CHANNELS:
                frames.append(cur)
            cur = []
        elif cur is not None:
            cur.append(g)
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpio", type=int, default=17)
    ap.add_argument("--seconds", type=float, default=2.0)
    args = ap.parse_args()

    falls, level = capture(args.gpio, args.seconds)
    if not falls:
        state = "HIGH (idle: disarmed / no session)" if level else "LOW (stuck low or not wired?)"
        print(f"no edges in {args.seconds:.1f} s; line is {state}")
        return
    frames = decode(falls)
    print(f"{len(falls)} falling edges, {len(frames)} complete 8-channel frames in {args.seconds:.1f} s")
    if not frames:
        return
    period_ms = (falls[-1] - falls[0]) / 1e6 / max(1, len(falls) - 1) * (CHANNELS + 1)
    print(f"frame period ~{period_ms:.1f} ms (expect 22.5)")
    for ch in range(CHANNELS):
        vals = [f[ch] for f in frames]
        flag = "  <- yaw" if ch == 3 else ""
        print(f"CH{ch + 1}: mean {statistics.mean(vals):7.1f} us  min {min(vals):7.1f}  max {max(vals):7.1f}{flag}")


if __name__ == "__main__":
    main()
