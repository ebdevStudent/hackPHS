class Controller:
    def __init__(self):
        self.state = 'MANUAL'
        self.enabled = False
        self.count = 0
        self.yaw = 0
        self.filtered = 0.
        self.fault = None
        self.events = []

    def transition(self, state, reason):
        if self.state != state:
            self.events.append({'type': 'transition', 'from': self.state, 'to': state, 'reason': reason})
        self.state = state

    def neutral(self):
        self.yaw = 0
        self.filtered = 0.
        self.count = 0

    def enable(self, enabled):
        self.enabled = bool(enabled)
        self.fault = None
        self.neutral()
        self.transition('SEARCHING' if enabled else 'MANUAL', 'operator enable' if enabled else 'operator disable')

    def fail(self, reason):
        self.enabled = False
        self.fault = reason
        self.neutral()
        self.transition('FAULT', reason)

    def frame(self, detection, settings, dt):
        if not self.enabled:
            self.neutral()
            return 0
        if detection is None:
            self.neutral()
            self.transition('SEARCHING', 'target lost')
            return 0
        if detection.get('reacquired'):
            # A jump to a different blob restarts acquisition rather than steering toward it.
            self.neutral()
            self.transition('SEARCHING', 'target changed')
        self.count += 1
        if self.count < settings.acquire_frames:
            self.yaw = 0
            return 0
        self.transition('LOCKED', 'stable acquisition')
        error = detection['error']
        # Weighted form preserves the exact input when smoothing is 1;
        # subtraction cancellation otherwise moved boundary errors outside
        # the inclusive deadband.
        self.filtered = (1 - settings.smoothing) * self.filtered + settings.smoothing * error
        error = 0 if abs(self.filtered) <= settings.deadband else self.filtered
        desired = max(-settings.max_yaw, min(settings.max_yaw, settings.direction * settings.gain * error))
        step = settings.slew_per_s * max(0, min(dt, .1))
        self.yaw = int(round(max(self.yaw - step, min(self.yaw + step, desired))))
        return self.yaw

