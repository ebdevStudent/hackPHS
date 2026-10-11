"""Terminal control for the ESP32-S3 bridge, without ball_demo/bridge.py.

Opens the CH343 USB-UART port, repeats HELLO until READY, then sends a CMD every 50 ms so the
bridge's 250 ms watchdog stays fed.  Starts DISABLED with yaw 0.  Type commands at the prompt:

  on            enable (computer yaw allowed)
  off           disable (yaw forced to 0)
  y <n>         set yaw, -1000..1000 (only sent while enabled)
  pause         stop sending CMDs (watchdog test: bridge must drop to neutral in 250 ms)
  resume        start sending CMDs again
  hello         start a new session (re-samples the GPIO 5 arming jumper)
  status        print current state and the last ACK
  quit          send disabled commands, then exit

Usage:  python esp_term.py [--port COM5 | /dev/ttyACM0] [--baud 115200]
"""
import argparse
import secrets
import sys
import threading
import time

import serial
from serial.tools import list_ports

CH343_VID, CH343_PID = 0x1A86, 0x55D3
PROTOCOL_VERSION = 1
CMD_PERIOD_S = 0.05
HELLO_RETRY_S = 0.5
HELLO_TIMEOUT_S = 10.0
YAW_LIMIT = 1000
QUIT_NEUTRAL_FRAMES = 5
THREAD_EXIT_WAIT_S = 0.25


def find_port():
    for p in list_ports.comports():
        if p.vid == CH343_VID and p.pid == CH343_PID:
            return p.device
    return None


class Bridge:
    def __init__(self, port, baud):
        # DTR/RTS drive the board's EN/BOOT auto-reset; hold both deasserted so opening the port
        # does not reset it or drop it into the bootloader.
        self.ser = serial.Serial(None, baud, timeout=0.1)
        self.ser.dtr = False
        self.ser.rts = False
        self.ser.port = port
        self.ser.open()
        self.lock = threading.Lock()
        self.session = None
        self.mode = None
        self.seq = 0
        self.enable = False
        self.yaw = 0
        self.sending = True
        self.running = True
        self.last_ack = None
        self.ack_count = 0
        self.fault_count = 0

    def write(self, line):
        self.ser.write((line + "\n").encode("ascii"))

    def hello(self):
        """Repeat HELLO until READY. The port open may reset the board, so early lines are boot noise."""
        with self.lock:
            self.session = secrets.token_hex(4)
            self.mode = None
            self.seq = 0
            self.enable = False
            self.yaw = 0
        deadline = time.monotonic() + HELLO_TIMEOUT_S
        while time.monotonic() < deadline and self.mode is None:
            self.write(f"HELLO {PROTOCOL_VERSION} {self.session}")
            time.sleep(HELLO_RETRY_S)
        if self.mode is None:
            print(f"! no READY within {HELLO_TIMEOUT_S:.0f} s (wrong port, baud or firmware?)")
            return False
        print(f"READY session={self.session} mode={self.mode}"
              + ("  <- GPIO5 jumper was OUT, no PPM output" if self.mode == "NO_OUTPUT" else "  <- PPM streaming"))
        return True

    def reader(self):
        while self.running:
            try:
                raw = self.ser.readline()
            except serial.SerialException as exc:
                print(f"\n! serial error: {exc}")
                self.running = False
                return
            if not raw:
                continue
            line = raw.decode("ascii", errors="replace").strip()
            parts = line.split(" ")
            if parts[0] == "READY" and len(parts) == 4 and parts[2] == self.session:
                self.mode = parts[3]
            elif parts[0] == "ACK" and len(parts) == 7 and parts[2] == self.session:
                self.last_ack = line
                self.ack_count += 1
                if parts[6] != "NONE":
                    self.fault_count += 1
                    print(f"\n! {line}")
            elif line:
                print(f"\n< {line}")

    def sender(self):
        while self.running:
            if self.mode is not None and self.sending:
                with self.lock:
                    self.seq += 1
                    en = 1 if self.enable else 0
                    yaw = self.yaw if self.enable else 0
                    line = f"CMD {PROTOCOL_VERSION} {self.session} {self.seq} {en} {yaw}"
                self.write(line)
            time.sleep(CMD_PERIOD_S)

    def quit(self):
        with self.lock:
            self.enable, self.yaw = False, 0
        time.sleep(CMD_PERIOD_S * QUIT_NEUTRAL_FRAMES)
        self.running = False
        # Let the reader's readline (0.1 s timeout) and the sender's sleep finish before closing,
        # otherwise the reader thread raises on the closed port.
        time.sleep(THREAD_EXIT_WAIT_S)
        self.ser.close()


def handle(bridge, text):
    words = text.split()
    if not words:
        return True
    cmd = words[0].lower()
    if cmd == "on":
        bridge.enable = True
        print(f"ENABLED, yaw={bridge.yaw}")
    elif cmd == "off":
        with bridge.lock:
            bridge.enable, bridge.yaw = False, 0
        print("DISABLED, yaw=0")
    elif cmd == "y" and len(words) == 2:
        try:
            val = int(words[1])
        except ValueError:
            print("! yaw must be an integer")
            return True
        if not -YAW_LIMIT <= val <= YAW_LIMIT:
            print(f"! yaw must be within -{YAW_LIMIT}..{YAW_LIMIT}")
            return True
        bridge.yaw = val
        print(f"yaw={val} ({1500 + int(val * 150 / 1000)} us on CH4 while enabled)"
              + ("" if bridge.enable else "  [not sent: disabled, type 'on']"))
    elif cmd == "pause":
        bridge.sending = False
        print("CMDs PAUSED, bridge watchdog should neutralise yaw within 250 ms")
    elif cmd == "resume":
        bridge.sending = True
        print("CMDs resumed")
    elif cmd == "hello":
        bridge.hello()
    elif cmd == "status":
        print(f"session={bridge.session} mode={bridge.mode} seq={bridge.seq} enable={bridge.enable} "
              f"yaw={bridge.yaw} sending={bridge.sending} acks={bridge.ack_count} faults={bridge.fault_count}\n"
              f"last: {bridge.last_ack}")
    elif cmd in ("quit", "exit", "q"):
        return False
    else:
        print("commands: on | off | y <n> | pause | resume | hello | status | quit")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial port; default: auto-detect the CH343 (1a86:55d3)")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    port = args.port or find_port()
    if not port:
        sys.exit("! no CH343 port found. Plug in the USB-C port next to BOOT, or pass --port.")
    bridge = Bridge(port, args.baud)
    print(f"opened {port} @ {args.baud}")
    threading.Thread(target=bridge.reader, daemon=True).start()
    threading.Thread(target=bridge.sender, daemon=True).start()
    if not bridge.hello():
        bridge.quit()
        sys.exit(1)
    print("starts DISABLED. type 'help' for commands.")
    try:
        while bridge.running and handle(bridge, input("> ")):
            pass
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        print("sending disabled commands and closing")
        bridge.quit()


if __name__ == "__main__":
    main()
