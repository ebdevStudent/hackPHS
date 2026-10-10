from dataclasses import asdict, dataclass


@dataclass
class Settings:
    width: int = 640
    height: int = 480
    processing_hz: float = 20
    control_hz: float = 20
    preview_hz: float = 10
    acquire_frames: int = 3
    stale_ms: int = 250
    ack_ms: int = 250
    watchdog_ms: int = 250
    hue_low: int = 35
    hue_high: int = 85
    saturation_min: int = 100
    value_min: int = 80
    min_area: int = 100
    max_area: int = 50000
    gain: float = 700
    smoothing: float = .35
    deadband: float = .04
    max_yaw: int = 650
    slew_per_s: float = 1800
    direction: int = 1
    # Live camera only: a frozen or blank picture for this long is a source fault.
    picture_ms: int = 500
    # Assistance enabled through the API needs an operator heartbeat within this window.
    lease_ms: int = 1500

    def dict(self):
        return asdict(self)

