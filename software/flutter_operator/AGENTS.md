# Flutter operator client

Read ../../UIDEVPLAN.md and BACKEND_HANDOFF.md before changing behavior.

- Push completed work directly to main, as the user requires.
- Keep Android and desktop compositions distinct, with shared models/controller/commands.
- Keep the operational build disconnected on startup. UI fixtures require explicit development compilation and visible provenance; no in-app demo switch.
- Every visible element must serve an operator task, reported state, or navigation. Keep copy concise and use named tokens.
- Widgets use the gateway/controller. Do not implement a Pi server here or bypass authorization/readiness.
- Acceptance, timeout, stale frames, and fixtures never prove physical success.
- Never add joystick/axis, ARM/DISARM, motor, or continuous position controls.
- Release local microphone tracks immediately on interruption. A later stop must supersede a pending start. Reject expired/cross-session landing frames.
- Record UI choices in the root UIDEVPLAN.md and dated decision log.
- Verify with the Flutter profile of tools/verify.py and preserve failed evidence. Browser/emulator inspection follows completion of app code.
