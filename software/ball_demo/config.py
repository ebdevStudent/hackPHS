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
    # What the yaw controller steers toward: 'color' (HSV ball), 'tag' (follow an AprilTag) or
    # 'landing' (line up on a landing-pad AprilTag; descent stays with the pilot).
    target_mode: str = 'color'
    # Tag to steer toward; -1 picks from the roster (people for 'tag', pads for 'landing').
    tag_id: int = -1
    # Printed black-square edge used for range estimates when the tag is not in the roster.
    tag_size_m: float = .10
    # Approximate horizontal field of view of the processed frame (Caddx Ant ≈ 160°), for range estimates.
    camera_hfov_deg: float = 160
    # Landing mode: estimated range at which the pilot is told to descend.
    land_range_m: float = .6
    # Live camera only: the mode requested from the capture device (resized to width x height afterwards).
    # The MS2106 USB capture card (534d:0021) offers only YUYV 720x480@30 (NTSC) and 720x576@25 (PAL);
    # OpenCV silently ignores any other request, so the opened mode is read back and checked.
    capture_width: int = 720
    capture_height: int = 480
    capture_fps: float = 30
    capture_fourcc: str = 'YUYV'
    # Live camera only: a frozen or blank picture for this long is a source fault.
    picture_ms: int = 500
    # Assistance enabled through the API needs an operator heartbeat within this window.
    lease_ms: int = 1500

    def dict(self):
        return asdict(self)

