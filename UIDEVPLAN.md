# Flutter UI development plan

**Status:** Flutter client implemented and inspected on web and Android emulator. Backend and physical media/aircraft integration remain separate work.
**Updated:** 2026-10-09
**Scope:** Flutter Android and desktop operator applications. The backend and aircraft-control implementation are separate work.

This file is the working source of truth for the Flutter screens, user-visible behavior, and the contract the future backend must provide. It records the user's UI decisions and distinguishes them from capabilities that exist or have been physically verified today.

## Recommended planning sequence

Keep this file as the canonical product and integration plan. Plan in this order so visual polish follows the actual task model:

1. Freeze the operator tasks, command authority, data sources, and backend responses. No screen should display a value or action without an identified source and state owner.
2. Draw low-fidelity screen compositions and the transitions between them. Start with the live-operations task because it combines video, roster selection, mission commands, and landing.
3. Specify normal, loading, empty, permission-denied, stale, offline, rejected, and recovery states before selecting detailed colors or motion.
4. Set a small visual system from the UI dossier: spacing, type roles, density, surfaces, status colors, focus, and motion.
5. Prototype those compositions with Flutter widgets and typed fixture data. Share view models and interaction rules while allowing separate phone and desktop shells.
6. Inspect rendered layouts at actual window sizes and with touch, pointer, keyboard, text scaling, and accessibility features. Revise the hierarchy before adding more surface styling.

Text-first annotated wireframes are the planning reference. They expose content order, alignment, action priority, and state behavior more reliably than a polished bitmap. Generated images may help compare art direction after layout and copy settle; exact labels, data, controls, and spacing must come from the written spec and Flutter render.

## Product direction and authority

- Build one Flutter codebase for an Android app and a desktop app. Use deliberately different layouts and navigation on phone and desktop; do not merely stretch one layout across both.
- Flutter is intended to replace the current browser and native Qt operator interfaces when the new app is ready. Until then, those existing interfaces remain the implemented software. The current desktop workstation is documented in [docs/14-desktop-app.md](docs/14-desktop-app.md).
- The Raspberry Pi-hosted server is a separate backend work item. The Flutter app must call a typed client/service layer so screen widgets do not depend on API details. This plan does not implement that server.
- The app serves routine operation during team work and judging; it has no scripted judge flow or fake demo mode. Judges should be able to invoke the same supported actions as the team. Do not add simulated aircraft data or a simulator tab. If the connected backend reports a mock/synthetic source, label it clearly.
- The independent industrial/3D simulator stays separate from both Flutter layouts. The root `server.py` and `static/` simulation are not an operator backend or an aircraft telemetry source.
- The operator may request high-level tasks. The app must not expose direct joystick/axis controls, pitch/roll/throttle/ARM controls, or continuous in-air position/setpoint control. Manual piloting and physical override remain on the RC transmitter.
- A high-level follow or landing task can still cause the backend to move the aircraft. Those tasks are planned UI capabilities, not currently verified flight capabilities. The backend/control-authority plan and physical gates must be updated before enabling them on hardware.
- Treat server-reported state as authoritative. Distinguish requested, accepted, active, completed, rejected, and failed commands. Never turn a local button press, mock ACK, stale frame, or timeout into a claim that the aircraft acted.
- Do not restrict normal app features to a “judge” role. The backend remains responsible for operator authentication, readiness, capability checks, and safe rejection.

## Decisions captured for the UI

### Following and prepared roster

- The operator selects a person from a prepared roster before starting a follow task. Do not ask the operator to type a person's name or create a roster entry in the field.
- The backend supplies roster entries and the current person-to-AprilTag association. The UI displays the available name and, when supplied, the tag ID and assignment/detection status. The source and lifetime of that association (preassigned or session-specific) remain backend decisions.
- Starting follow submits the selected stable person ID and the relevant target identity. The app reports “Following [name]” only after the backend reports the mission active. Target loss, reacquisition, and stopping are explicit states, not inferred from the video alone.
- Provide distinct high-level **Start**, **Stop**, and **Abort mission** actions where applicable. “Abort” means the backend's documented safe mission-abort behavior; it must not be presented as an emergency motor kill or assumed to disarm the aircraft.

### Landing target selection

- The main **Land here** flow requests landing at the aircraft's current location. The operator chooses when to issue that high-level task, as clarified by the user. It needs no image-to-world inference. Offer camera-point selection and AprilTag assistance as additional backend-advertised methods.
- From the live camera view, the operator may select a visible landing point and request **Land here**. The selection is a single high-level landing target, not a stream of position commands.
- Offer an arbitrary visible-point path and an AprilTag-aided path when the backend advertises that capability. Show a marker on the selected video frame and require a review/confirmation step before submitting the request.
- A tap is meaningful only with its source frame ID and the display-to-frame transform. The backend must resolve the image point into a valid landing target and accept or reject it; the app must not convert a pixel into a world-coordinate setpoint on its own.
- Disable target selection on stale/unavailable video. Show the backend's rejection reason or landing progress. Show “landed” only from an authoritative backend/aircraft state.

### Audio and text-to-speech

- Two-way audio is in the intended app scope. The app includes operator-to-drone microphone audio, drone-to-operator audio, and ElevenLabs text-to-speech (TTS): the operator types text and requests playback through the drone speaker.
- Use **press-and-hold push-to-talk** as the initial UI interaction for operator microphone audio, with a separate incoming-audio player and TTS composer. Full-duplex talk is not assumed. This is a provisional interaction choice because the user said either mode is acceptable; revisit it after the audio device and backend transport are selected.
- Keep ElevenLabs credentials and provider calls on the backend. The Flutter app submits text and displays queued/playing/completed/rejected/failed status; it does not call ElevenLabs directly.
- Hardware is undecided: one device will handle microphone, speaker, and possibly an LED; candidates mentioned are ESP32, Pico, and Raspberry Pi Zero, with Pico considered likely. Do not hard-code a board name, pinout, power design, or transport into the UI. Display the actual device/capabilities reported by the backend.
- Do not record or retain audio by default. A later recording feature would need an explicit product decision and retention/privacy behavior.

### Other requested features

- **Camera streaming:** core live-operations content on phone and desktop. Show source, freshness, and unavailable/stale states clearly.
- **Collision tolerance:** the demonstration method and backend evidence are not defined. Reserve space for verified collision/contact events in mission events/status; do not invent a collision animation, score, sensor, or successful-contact claim.
- **Interactive CAD model:** a later TODO, after the operational screens. Use measured as-built dimensions and a separate explicit request before implementation. It is not the industrial simulation.
- **Manual flight controls:** intentionally absent from Flutter. The user pilots with the transmitter.

## Reconciliation with current repository documentation

| Existing repo/source statement | Flutter plan | Boundary or follow-up |
| --- | --- | --- |
| The implemented operator tools are a browser UI and native Qt workstation. | Flutter desktop and Android are the planned replacement operator interfaces. | Existing tools remain the current implementation until replacement; see [desktop workstation](docs/14-desktop-app.md). |
| The project baseline describes Pico wireless audio as deferred. | The user has since put two-way audio and ElevenLabs TTS in the intended Flutter feature set. | This does not select Pico or approve a wireless implementation. The audio device, link, and backend remain open. The old Pico-specific deferral should not be read as deferring the app requirement. |
| Current physical assistance is yaw-only; the current navigation guidance does not write to the flight bridge. | The app plan includes roster-based following and high-level landing requests. | These are future mission capabilities. They require explicit control-authority documentation and verified sensing, command, override, and failsafe behavior before hardware execution. UI presence alone does not authorize flight. |
| The existing AprilTag/navigation work is guidance/advisory software. | A selected roster person can be the target of a follow mission. | Person-following is a separate future backend/aircraft capability; do not present the existing advisory navigator as implementing it. |
| CAD implementation requires a request and measured dimensions. | Interactive CAD is a later UI TODO. | Keep it out of the initial screen set until the model and request are ready. |
| The simulator is separate from the operator workstation. | Keep it separate from Flutter too. | No game, industrial map, or simulated flight path in the operational app. |

The user clarification captured here resolves the UI scope for audio and Flutter even where older source material says otherwise. It does not override the repository's physical safety gates or establish that any backend/device behavior already works.

## Screen plan

### Android app

Use a phone-first hierarchy, large touch targets, safe-area-aware controls, and bottom navigation for **Live**, **Audio**, and **System**. Keep mission actions close to the video and selected person. Do not shrink the desktop workspace into a phone layout.

1. **Connect / session**
   - Enter or choose the Raspberry Pi server address and establish an authenticated operator session.
   - Show connection progress, backend identity/version, and any authentication or compatibility error.
   - Keep credentials in platform secure storage when persistence is enabled; never put them in URLs, logs, screenshots, or share cards.
   - No “demo mode” toggle. Show any backend-reported mock/synthetic source conspicuously.
2. **Live operations** (default after connecting)
   - Put the live camera stream first, with a visible freshness/source label and clear no-signal, stale, reconnecting, and mock states.
   - Show the selected roster person and tag/detection status, followed by the contextual Start/Stop/Abort mission actions.
   - Keep **Land here** available as a separate high-level action. Enter a target-selection view, place a marker on the current frame, review the choice, then confirm the backend request.
   - Show current mission state and recent authoritative status near the controls. Never put joystick or direct position controls on this screen.
3. **Prepared roster picker** (full-screen sheet/page from Live)
   - List backend-provided people by display name, with tag ID/assignment and availability when provided.
   - Selecting an entry returns to Live with that person selected. Do not expose roster editing or arbitrary name entry in the initial app.
4. **Audio**
   - Show audio-node connection/capabilities and microphone permission state.
   - Provide a prominent hold-to-talk control, incoming drone-audio playback/status, and a text composer with **Speak** for ElevenLabs TTS.
   - Surface queue/playback/errors and avoid implying that text was spoken until the backend confirms it.
5. **System**
   - Show Pi/backend, camera, tracker, audio node, aircraft/bridge link, and battery only when each is actually reported by the backend.
   - Include timestamp/freshness, capability/readiness, and fault reason for each available subsystem. Keep settings limited to connection/session and UI preferences in the first release; no hidden flight tuning controls.

### Desktop app

Use a desktop operations workspace rather than the phone's bottom-navigation composition. Initial desktop target is Mac. Linux/Pi-hosted Flutter desktop support remains unconfirmed and must be checked before it becomes a release requirement.

1. **Operations workspace** (default)
   - Persistent top strip: backend connection, source mode (live/mock), freshness, and aircraft/link readiness.
   - Left pane: prepared roster, selected person, tag/detection details, and follow Start/Stop/Abort actions.
   - Center pane: large live video with frame status and the landing-point selection overlay.
   - Right pane: current mission/landing state, backend-reported system health, and recent events/rejection reasons.
   - Use resizable panes and compact, readable status rows. No joystick, direct axis, or position-setpoint panel.
2. **Audio workspace/dock**
   - Keep a compact push-to-talk and incoming-audio dock accessible from Operations; open an expanded Audio workspace for the TTS composer, playback queue, and audio-node status.
   - Use the same backend-confirmed delivery states as Android.
3. **System workspace**
   - Show detailed subsystem freshness, capability availability, faults, and connection information without implying unsupported aircraft telemetry.
4. **Roster selection and landing target selection**
   - Use desktop lists/dialogs and pointer selection on the video, preserving the selected person and mission state while panes resize or views change.
   - Confirm a selected landing point in a review dialog before sending it.

### Shared interaction and visual principles

- Follow the supplied [Universal UI Reference Library and Design Principles Dossier](https://docs.google.com/document/d/1G-fn3NKXPNHM3SvV-kJ-FSS-DbW-Bsi5XZqqHb1pezg/edit): distinct mobile/desktop information architecture, state preservation across resizing, accessible contrast and reduced-motion support, and deliberate layouts without generic card clutter.
- Use at least 48 dp touch targets on Android (and respect platform safe areas). Desktop supports pointer and keyboard navigation, focus visibility, and resizable multi-pane work.
- Reflow without losing connection, roster selection, or mission state. Never treat a responsive layout change as a new command or a reset.
- Use explicit labels and text for mission state; color is supplemental. Make unavailable actions explain why they are disabled.
- Do not add global key bindings that launch, stop, or abort missions. Focused buttons remain keyboard operable through standard platform activation. Escape may dismiss a selection/review surface when that does not discard entered work or send a command.

## Visual system and content rules

### Composition, type, and surfaces

- Carry forward the project's earlier compact light-interface direction. Use a quiet light application shell and a dark camera viewport that frames the actual video. Keep exact brand/accent hues open until contrast and rendered hierarchy are reviewed.
- Start with neutral surfaces and one accent role. Reserve semantic colors for reported states such as ready, warning, fault, and selected; pair status color with a word or icon. Do not use gradients or colors to decorate unrelated groups.
- Use a 4 dp base with an 8 dp working rhythm. Start with 16–20 dp mobile edge insets, 16–24 dp desktop panel padding, 8–12 dp between related controls, and 20–24 dp between distinct groups. Use larger gaps to separate sections rather than placing every group in a container.
- Use three or four text roles: page/section heading, primary body, label, and secondary metadata. Starting sizes from the dossier are 16–17 sp mobile body with 21–24 sp line height, 13–15 logical px desktop body with 18–22 px line height, and larger page titles only where hierarchy needs them. Respect user text scaling; secondary information must remain readable.
- Use sentence case and tabular figures for changing times/counters. Align recurring labels, values, and status text to stable rails. Keep list density consistent within each region.
- Use a plain page background plus a raised surface only where content is independently interactive or overlaps other content. Prefer spacing and low-contrast dividers over a card for every section. Keep a small radius family: 4–6 dp controls, 8–12 dp popovers, and 16–24 dp sheets/dialogs. Use elevation to show overlap, not as decoration.

### Action hierarchy and microcopy

- At each decision, make the next operator action visually clear. Follow, landing, and audio are separate tasks; within an active task, elevate only the action relevant to its current state.
- Put a control beside the video, roster entry, or message it affects. Use text labels on consequential controls; do not rely on an icon, color, tooltip, or gesture alone.
- Use short operational labels such as **Select person**, **Start following**, **Stop following**, **Abort mission**, **Land here**, **Hold to talk**, and **Speak**. Screen titles are **Live**, **Audio**, and **System**.
- Status copy names the observed condition and, when available, its source/time: **Camera disconnected**, **Video stale · last frame 2.4 s ago**, **Target not visible**, or **Follow request rejected: [backend reason]**. Never invent reassurance, telemetry, capability, or a successful outcome.
- Remove slogans, filler captions, generic welcome copy, decorative labels, fake user/avatar details, duplicated status text, and marketing language. Every visible phrase must identify content, an action, a consequence, or a backend-reported state.
- Confirm consequential commands only where the backend risk model and user decision call for it. A confirmation must name the selected person/target and consequence. Backend readiness and authorization remain mandatory regardless of confirmation UI.

### Interaction feedback and motion

- Define hover, focus, pressed, selected, disabled, loading, error, and success appearances for each custom control. Preserve the action label while loading where possible; keep unavailable actions legible and state why they are unavailable.
- Put errors and recovery next to the field or action that caused them. Success updates the same row or control. Use determinate progress only when the backend supplies measurable progress.
- Animate only a meaningful change of state, origin, destination, or continuity. Use restrained button feedback (about 70–120 ms), popovers (120–180 ms), sheets/panels (180–280 ms), and larger transitions (240–420 ms) as starting ranges from the dossier. Avoid bounce, parallax, pulsing decoration, unrelated celebration, and repeated shimmer.
- Under reduced-motion preferences, remove travel and repeated animation while retaining the same status and controls. Keep focus visible through every transition.

## Annotated screen compositions

These are content and hierarchy specifications, not finished visual assets.

### Android: Live

1. **Top bar:** title **Live**; compact backend connection state and last update. No slogan, project pitch, or row of unsupported aircraft metrics.
2. **Video viewport:** preserve the stream's aspect ratio by default. Keep target/tag overlays in the image coordinate system. Show live/mock source and frame age in one quiet overlay; render no-signal/stale states in the viewport itself.
3. **Selected-person row:** label **Follow target**. With no selection, show **Select person**. With a selection, show the roster name and backend-provided tag/detection state. Do not invent initials, photos, roles, or tag assignments.
4. **Mission area:** when a person is selected and follow is available, elevate **Start following [name]**. Keep **Land here** visible as a separate task action. During an active mission, show its state and **Stop following** as the primary action; keep **Abort mission** distinct and available with backend-defined semantics.
5. **Bottom navigation:** **Live**, **Audio**, **System**. Keep labels visible; selected state must be apparent without color alone.

Keep the video as the spatial anchor while the roster picker or landing workflow is open. If the screen is too short to show all controls, keep mission state and its relevant action reachable; do not shrink text to fit.

### Android: prepared roster and landing flow

- **Roster picker:** open a context-preserving bottom sheet for the prepared roster. Each row contains the supplied name, tag association when available, and availability/reason. Selecting a person updates Live and closes the sheet. Use a full route only if roster length, text scaling, or keyboard use makes the sheet materially harder to operate.
- Define collapsed/expanded, keyboard-open, back-button, and dismissal behavior. Dismissal preserves the selected person. If a sheet would cover the only content needed to complete selection, expand it or promote it to a route rather than hiding necessary information.
- **Landing selection:** from Live, open a focused selection state over the current video. Show **Choose landing point** and only backend-supported methods, such as **Any visible point** and **AprilTag aided**. A tap selects one point on the displayed frame; show a marker and the concise label **Selected landing point**. Keep the video context visible.
- **Landing review:** show the selected frame/point, method, and **Request landing** / **Choose again** actions. The source frame must still be valid when submitted. Backend resolution and rejection remain authoritative.
- A dismissed review preserves enough context to repeat or change the selection. Do not show pixel coordinates or claim world position unless the backend provides and identifies a meaningful coordinate system.

### Android: Audio and System

- **Audio:** title **Audio**; audio-node state; an incoming-audio control; a lower-reach **Hold to talk** control; then **Text to speak**, a persistent field label, and **Speak**. Show input/output levels only when the backend provides actual levels.
- Releasing push-to-talk stops uplink. Navigation away, app pause, permission loss, or audio-link loss also stops uplink and updates status. Incoming audio and TTS have distinct state labels so the operator can tell which channel is active.
- On microphone permission denial, explain the permission and offer the platform Settings path; never draw a fake operating-system prompt.
- **System:** use aligned status rows grouped by backend, camera/tracking, audio node, aircraft link, and battery only when available. Each row shows name, reported state, update age, and a useful fault reason. Unknown remains **Unknown**; no zero-filled gauges, placeholder charts, or assumed green status.

### Desktop: Operations

- **Navigation rail:** **Operations**, **Audio**, **System**. Keep the current destination selected while resizing. Avoid adding a command palette for the small initial route set.
- **Top status rail:** backend/server, live/mock source, video freshness, and aircraft-link state, all with text labels. Status values show update age when supplied.
- **Left inspector:** prepared roster and selected-person/tag state. Keep selection and scroll position when the inspector collapses.
- **Center work surface:** largest available column for live video and its real target overlays. Landing-point selection and review remain anchored to the current frame.
- **Right inspector:** current mission state, relevant Stop/Abort actions, backend-reported readiness/faults, and a short event list ordered by source time. No generic KPI cards or unsupported plots.
- A narrow push-to-talk/receive strip may remain at the edge of Operations when it fits without competing with the video. The Audio destination holds the complete receive, talk, and TTS controls.
- Use menus/context actions only where they shorten a known flow. Pointer hover may reveal secondary actions; keyboard focus and context menus expose equivalent paths.

### Responsive composition rules for Flutter

- Share destinations, typed state, content, and commands; use different composition widgets for phone and wide desktop. Phone: single-column content and bottom navigation. Mid-width window: navigation rail with one main column and inspectors promoted to a sheet or collapsible pane. Wide desktop: navigation rail plus roster, video, and mission/status panes.
- Determine layout from app-window constraints with `LayoutBuilder`/`MediaQuery.sizeOf`, not a phone/tablet label or portrait/landscape check. Keep route identity, selected person, active mission, scroll, and TTS draft while the presentation changes.
- Review layouts around 360, 390, and 430 dp for phones; 600, 800, and 1,024 dp for intermediate/narrow windows; and 1,280 and 1,440 dp for wide desktop. These are inspection sizes, not universal breakpoints. Set actual breakpoints when the roster and video minimum widths stop fitting cleanly.
- Apply `SafeArea` and platform insets to phone controls; support landscape and multi-window. Desktop supports mouse, trackpad, keyboard focus, text selection, and window resizing.
- Use standard Flutter Material controls where their semantics and input behavior fit, with project-specific tokens and composition. Preserve Android conventions for permissions, system back, text entry, and focus; avoid a stock starter-template appearance.

## UI review and verification plan

Review the actual Flutter layouts with typed fixture states before connecting a live backend. A fixture must identify whether its values are measured, backend-reported, mock, stale, or unknown; never use realistic-looking fake telemetry without a visible mock label.

### State walkthroughs

- **Connection:** initial connection, reconnecting, expired session, incompatible API, degraded backend, and recovery while a mission is active. Check that a timeout leaves command outcome unknown until refreshed state resolves it.
- **Camera:** first frame, fresh stream, delayed/stale frame, frozen image, disconnect, reconnect, and mock source. Check that landing selection is disabled unless the selected frame is still valid.
- **Roster and follow:** loading roster, empty roster, unavailable entry, no tag association, visible target, target lost, reacquiring, rejected start, active follow, stop pending, abort pending, and backend recovery. Check that the selected identity survives resize and navigation.
- **Landing:** supported and unsupported modes, point selection, choose-again, expired source frame, backend rejection, accepted/in-progress, cancellation, landed, and failure. Check that the review names the exact selected target and method.
- **Audio:** microphone permission prompt/denial, push-to-talk press/release, focus loss, app pause, navigation away, incoming audio, uplink/downlink loss, TTS empty/over-limit input, queued/playing/completed/rejected, and device disconnect. Check that uplink stops on every interruption path.
- **System:** healthy, degraded, faulted, stale, and unknown subsystem values, with event timestamps and recovery. Check that unknown and old observations do not appear healthy.

### Platform and usability passes

- Inspect phone sizes around 360, 390, and 430 dp, including landscape, keyboard open, display cutouts, multi-window, and larger text settings.
- Inspect desktop widths around 600, 800, 1,024, 1,280, and 1,440 dp. Confirm inspectors collapse/reflow without losing selection, draft text, route, or mission state.
- Exercise touch, mouse, keyboard-only focus, text selection, platform back/escape behavior, TalkBack semantics, and reduced motion. Verify minimum touch targets and that no command fires from focus movement or resize.
- Check video crop/rotation transforms by selecting known points in fixture frames; confirm the request identifies the same source-frame point after resize and display rotation.
- Capture real Flutter renders for review at each chosen size. Treat the wireframes and written rules as the source; generated images can support art direction but cannot define control behavior, copy, or spacing.

### Anti-vibe review

Before visual sign-off, inspect each screen for one clear task hierarchy, stable alignment, purposeful spacing, consistent type and radius roles, and color that reports meaning. Remove any element that cannot be tied to an operator task, backend state, or required navigation. Check for card inflation, unsupported metrics, placeholder copy, repeated status, decorative gradients, generic icon tiles, arbitrary animation, and filler captions. Verify every label against the exact strings and state rules in this plan.

## Screen states and command semantics

| Area | States the UI must represent |
| --- | --- |
| Connection | Disconnected, connecting, connected, authentication required/failed, incompatible backend, reconnecting, degraded. |
| Camera | Live/fresh, stale, no signal, reconnecting, mock/synthetic, unsupported. Freshness threshold comes from the backend contract; the UI shows age/source. |
| Roster/target | No selection, selected, tag association unavailable, target visible, target lost, reacquiring, unavailable. |
| Follow mission | Ready, request pending, rejected (reason), accepted, active, stopping, stopped, abort pending, aborted, failed. |
| Landing | Choosing point, point selected, review required, request pending, rejected (reason), accepted/in progress, landed, failed/cancelled. |
| Audio | Node unavailable/connecting/ready, microphone permission needed, transmitting, receiving, TTS queued/playing/completed/rejected/failed. |
| Subsystem health | Backend-provided state, observation time/freshness, capability, and fault/degraded reason. Unknown stays unknown; it is not displayed as healthy. |

**Command rules:**

- Commands are high-level intent only: select/follow a roster person, stop/abort that mission, request a landing at a selected visual target, transmit microphone audio, or request TTS playback.
- Every mutating command needs an authenticated backend response and a stable command/mission ID. The UI waits for backend events/status and handles duplicate, delayed, rejected, and out-of-order updates.
- Stop and Abort are separate actions with backend-defined outcomes. Abort is not an emergency stop. The interface must explain the meaning supplied by the backend before the operator confirms it.
- A network timeout leaves the outcome **unknown** until the app reconciles with backend state. Do not retry a non-idempotent action blindly.
- If backend readiness/capabilities say a command is unavailable, disable it with the returned reason. Backend rejection must remain visible and must not be converted to local success.

## Backend contract for a clean Flutter integration

The concrete transport is not selected here. Implement a typed Dart client/repository boundary so REST, WebSocket/SSE, and a video/audio transport can be chosen by the backend team without rewriting screen widgets. Version the API and reject unknown/incompatible protocol versions visibly.

The backend must provide these concepts (names are illustrative, not a mandate for a specific route or JSON spelling):

| Contract data/action | Minimum information and behavior |
| --- | --- |
| Capabilities and readiness | API version; live/mock source; supported screens/actions; subsystem readiness; unavailable reason; operational mode. Do not infer support from app version. |
| System status/events | Component state, event timestamp, freshness/staleness, fault/degraded reason, and only telemetry actually measured/reported. Events must be ordered or carry sequence/version information. |
| Prepared roster | Stable `person_id`, display name, current AprilTag family/ID when known, association validity, and whether the entry can be followed now. Backend owns the roster and tag association. |
| Video | Stream/session information plus frame ID, capture timestamp, dimensions, orientation/crop/display transform, and live/mock/fresh status. The app needs enough provenance to map a tap back to the exact source frame. |
| Follow mission | Start request with stable roster identity; command/mission ID; accepted/rejected reason; active/stopped/aborted/lost/failed progress; target identity and freshness. Backend defines target-loss and safe stop/abort behavior. |
| Landing request | Source frame ID, normalized point in that frame after reversing display rotation/crop, requested mode (`arbitrary point` or `AprilTag aided`), and any selected tag identity. Backend resolves/validates the point, returns accepted/rejected reason, and reports progress/result. Do not accept phone/desktop world-coordinate or joystick setpoints from this screen. |
| Audio | Negotiation/connection state, operator microphone uplink, drone audio downlink, push-to-talk start/stop semantics, device status, and playback/transmission errors. Avoid logging or retaining audio by default. |
| TTS | Text request, provider-side ElevenLabs integration, command ID, queue/playback status, and rejection/failure reason. Secrets remain server-side; the backend reports any text/length/voice constraints. |
| Authentication | Operator-session creation/expiry and least-privilege mutation authorization. App stores any token using OS secure storage and excludes it from diagnostics/URLs. No judge-only role is required by the UI. |

### Suggested typed client boundary

Keep widgets dependent on interfaces such as `ConnectionRepository`, `OperationsRepository`, `MediaRepository`, and `AudioRepository`, backed by typed models for `Capabilities`, `SystemSnapshot`, `RosterEntry`, `VideoFrameInfo`, `MissionSnapshot`, `CommandResult`, `LandingTargetRequest`, and `AudioStatus`. Names can change with the API; behavior and state distinctions above should remain.

The Flutter client must never expose or send throttle, roll, pitch, ARM/DISARM, raw motor, joystick-axis, or continuous position-setpoint fields. A clicked landing target is a single backend-resolved mission request, not a low-level position control channel.

## Open backend/product decisions

These are recorded rather than guessed in the UI:

1. Which device actually handles mic, speaker, and LED (ESP32, Pico, or Pi Zero), how it is powered/connected, and whether the LED is merely status or has user controls.
2. Audio codecs/transport, echo handling, audio permissions, and whether later testing warrants full duplex instead of the initial push-to-talk UI.
3. Where the prepared roster lives and whether AprilTag IDs are fixed per person or assigned for each session; who edits the roster outside the first app.
4. The authoritative mapping from a tapped camera point to a safe landing target, supported landing envelope, AprilTag-aided mode semantics, and backend confirmation/rejection rules.
5. The safe behavior and exact meaning of Stop versus Abort, including target loss and communication loss during follow/landing. Abort must not be described as motor kill unless a separately verified mechanism exists.
6. Control-authority and hardware acceptance needed before automated following or landing can run on the aircraft; the current verified scope remains yaw-only with pilot authority described in [docs/04-software.md](docs/04-software.md).
7. Collision/contact sensing, evidence, and what the operator should see; no method has been selected.
8. Whether the desktop app must run on Linux/Raspberry Pi itself or only on Mac while the Pi stays headless.
9. The backend's authentication/session model, network profile, capability API, and freshness thresholds.
10. The measured CAD model and explicit request needed before adding the later interactive model.
11. Whether Follow and Landing are mutually exclusive missions, and what the operator can request while either is active. The UI should present backend-advertised availability until this is defined.

## Initial UI acceptance checklist

- Android and desktop have intentionally distinct screen layouts and navigation while preserving state across resizing/reflow.
- Operator can select only from a backend-provided prepared roster and can see the selected person's association/status.
- Follow, Stop, Abort, and landing actions are high-level, capability-gated, authenticated requests with backend-confirmed lifecycle states.
- Landing supports a reviewed point selected from a fresh video frame and can expose AprilTag-aided mode only when advertised by the backend.
- Two-way audio and ElevenLabs TTS have visible connection, permission, queued/transmitting/playing, and failure states; the UI does not expose provider secrets.
- No direct manual flight or continuous position controls exist in Flutter.
- Mock/stale/unavailable states are unmistakable; the app never presents the separate simulator as live aircraft operation.
- Collision visualization and CAD remain out of the initial operational build until their open prerequisites are resolved.

## Implementation specification — 2026-10-09

The user authorized all five workflow stages, with coding completed before browser/emulator inspection. Desktop web and Android must expose the same core capabilities through distinct layouts. Runtime remains disconnected until the operator connects. A separately compiled, clearly labelled UI-fixture build supports development inspection.

### Operator tasks and state ownership

| Task | UI-owned state | Backend-owned state | Outcome shown |
| --- | --- | --- | --- |
| Connect | Endpoint, network profile, in-memory token, local connection progress | Protocol version, explicit authorization, capabilities, server identity | Connected, rejected authorization, incompatible, reconnecting |
| Select person | Selected stable person ID | Prepared roster, tag association, detection availability | Selected name and reported tag state |
| Follow | Request identifier and local pending status | Accepted command and mission lifecycle, target loss/reacquisition | Following only on active mission snapshot |
| Stop / Abort | Local pending request; abort review | Documented stop/abort result, mission identity | Requested, accepted, stopped/aborted, failed, unknown |
| Land here | Selected method and review | Current-position landing request resolution and lifecycle | Accepted, landing, landed only when reported |
| Choose landing point | Frozen frame identity, tap transform, selected point/tag, review | Captured still and safe target resolution | Selected target, rejected reason, mission lifecycle |
| Listen / Talk | User listen preference, local microphone permission, held gesture | Media session and audio-node capability/status | Receiving/transmitting only when transport and request permit |
| Speak | Draft text and selected provided voice | ElevenLabs request, queue, playback result | Queued, playing, completed, rejected/failed |
| Inspect system/events | Destination, scroll, expanded detail | Component state, observations and chronological events | Actual reported values; unknown remains unknown |

### Screen map and transitions

```text
Android                         Desktop web / native
Live                            Operations
  Select person -> roster sheet   Prepared roster inspector
  Land here -> landing review     Video + landing controls
  Choose point -> selection       Mission + recent-events inspector
Audio                           Audio
  Receive / microphone / TTS       Receive and microphone beside composer
System                          System
  Subsystems + connection          Aligned subsystem and connection rows
Connect -> session sheet        Connect -> session dialog
```

All destinations remain reachable while disconnected. Their empty states explain the missing connection locally. A successful manual connection retains the current destination. Navigation or app interruption releases microphone uplink immediately. TTS draft and selected person persist across destination and layout changes.

### Annotated wireframes

```text
ANDROID / LIVE                    ANDROID / AUDIO
+-----------------------------+   +-----------------------------+
| Live              Connect   |   | Audio             Connect   |
| connection / source         |   | audio-node state            |
+-----------------------------+   +-----------------------------+
|                             |   | Incoming audio     Listen   |
|       CAMERA VIEWPORT       |   | received state              |
| source / age / target box   |   +-----------------------------+
|                             |   | Microphone                  |
+-----------------------------+   | Enable microphone (if needed)|
| Follow target    Select >   |   |        Hold to talk         |
| selected name / tag state   |   | local transmission state    |
| [Start following]           |   +-----------------------------+
| [Land here]   Choose point  |   | Text to speak               |
| mission state / local fault |   | persistent multiline label  |
| recent backend events       |   | [Speak]  queue / result     |
+-----------------------------+   +-----------------------------+
| Live     Audio     System   |   | Live     Audio     System   |
+-----------------------------+   +-----------------------------+

DESKTOP / OPERATIONS
+------------------+---------------------------------------------------+
| Ball Drone       | Operations                    connection / source |
| Operations       +---------------+---------------------+-------------+
| Audio            | People        | Camera              | Mission     |
| System           | roster rows   | large video         | state       |
|                  | tag state     | source / freshness  | Stop / Abort|
|                  | selection     | landing selection   | events      |
|                  |               | follow / Land here  |             |
| connection       |               | audio dock          |             |
+------------------+---------------+---------------------+-------------+
```

The wireframes specify order and role; final constraints determine exact geometry. Keep the video visually dominant. Connection/source labels describe actual provenance. No promotional header, synthetic telemetry grid, decorative drone render, avatar, gradient, or additional destination is required.

### Concrete design tokens

| Role | Initial token |
| --- | --- |
| Page | `#F6F7F4` |
| Surface | `#FFFFFF` |
| Primary text | `#202824` |
| Secondary text | `#657069` |
| Divider | `#DDE3DC` |
| Action / focus | `#295D4D` |
| Selected surface | `#E8F0EA` |
| Video background | `#111B18` |
| Warning text | `#805719` |
| Error text | `#AD3535` |
| Spacing | 4, 8, 12, 16, 24, 32 logical pixels |
| Radii | 6 controls, 10 video/popover, 20 sheets/dialogs |
| Font | Bundled Inter; preserve user text scaling |
| Body | 14/20 desktop, 16/24 compact |
| Metadata | 12/18 desktop, 13/20 compact |
| Heading | 28 desktop, 24 compact; semibold |
| Controls | Minimum 48 logical pixel touch target |
| Transition | 120 ms local feedback; zero travel under reduced motion |

Color roles remain semantic. Disabled controls retain legible labels and adjacent reasons. Headings carry no decorative icon tiles. Static groups use spacing/dividers. Opaque dialogs/sheets use elevation only to establish overlap. Use standard Material interaction/focus/semantics with these project tokens.

### Layout decisions

- Below 680 logical pixels: a compact shell with labelled bottom navigation and 16-pixel content edges. Live, Audio, and System are vertically scrollable; no fixed-height control regions conceal content at large text sizes.
- From 680 to 1,279: a slim navigation rail and one main content column; roster selection opens a sheet/dialog and mission controls sit next to the video where constraints permit.
- At 1,280 and wider: a 184-pixel desktop sidebar, 192–224-pixel roster inspector, flexible camera column, and 240–264-pixel mission/event inspector. Inspectors can be resized within sensible minimums; narrow windows return to the intermediate composition.
- Expand the required width with text scale. Layout selection uses available constraints, including window resize. Share controller/models instead of duplicating task logic by platform.
- Desktop Audio uses a two-column audio-control/composer composition when it fits. Compact Audio stacks the same features.
- Android system back dismisses transient work first. Cancelling a connection form preserves its inputs while it is open; leaving a landing review sends no command. Pending request status remains visible after dismissal.
- Follow and landing initially permit one mission at a time. This is a provisional client behavior while concurrency remains an open backend decision. A pending follow request still exposes Stop so a later neutral/cancel request cannot be dropped.
- Changing a person during an active follow requires stopping first. Roster selection never silently retargets an active mission.

### Exact content and controls

- Destinations: **Live**, **Audio**, **System** on compact layouts; **Operations**, **Audio**, **System** on desktop.
- Connection: **Server address**, **Operator token**, **Network**, **Shared network**, **BallDrone-Demo hotspot**, **Connect**, **Disconnect**, **Cancel**.
- Target and mission: **People**, **Follow target**, **Select person**, **Start following**, **Stop following**, **Abort mission**, **No mission active**.
- Landing: **Land here**, **Choose landing point**, **Current location**, **Camera point**, **AprilTag aided**, **Choose again**, **Request landing**, **Cancel**.
- Audio: **Incoming audio**, **Listen**, **Mute**, **Microphone**, **Enable microphone**, **Hold to talk**, **Text to speak**, **Voice**, **Speak**.
- Operational empty states: **Camera offline** / **Connect a server to view the camera.**; **No people available** / **The server has not supplied a roster.**; **No recent events**; **Audio unavailable**.
- Faults stay beside their affected task and use concise causes and recovery. Accepted requests remain distinct from completed tasks.
- Development builds display **UI preview · fixture data** and **Mock source**. Fixtures never appear in the normal build.
- No marketing descriptions, slogans, generic welcome text, random captions, fake photographs/initials, celebratory routine feedback, or unsupported metrics.

### Client architecture and integration decisions

Implement `software/flutter_operator/` with domain models, a replaceable `OperatorGateway`, controller/view model, media adapter, design tokens, shared widgets, and separate compact/desktop compositions. Keep schemas/examples and a backend handoff next to the app. Widgets never construct HTTP routes or aircraft commands.

The proposed client contract is `/api/ui/v1`; the existing Python server does not implement it. Snapshot polling establishes authoritative state; commands have stable request IDs and explicit accepted/rejected results. Snapshot sequence and observation time guard delayed/out-of-order data. Requests time out to unknown outcomes and reconcile by ID instead of resubmitting a mission. Explicit boolean authorization and strict bounded numeric/date validation are mandatory.

Use WebRTC as the initial replaceable real-media adapter for remote video and two-way audio. The Pi backend must implement offer/answer negotiation; the app acquires only its microphone, never the phone camera. A backend-captured still provides provenance for camera-point landing; unsynchronized live-stream pixels are not mission coordinates. Microphone tracks start disabled, uplink starts only after acceptance, release disables the local track immediately, and interruption/connection loss closes transmission. Backend uplink leases/watchdogs are part of the handoff.

Credentials remain in memory for this initial implementation. There is no token persistence feature or token in URLs/logs. HTTP on private LANs is supported for the prepared Pi network profiles; hosted HTTPS browser clients need an HTTPS-accessible Pi endpoint and CORS. A published app cannot bypass browser mixed-content or private-network restrictions.

Prepared-roster data, voice options, readiness, telemetry, event/contact evidence, and mission results come from the backend. Local fixtures are dependency injection for development; the normal app has no demo switch. CAD remains a visible development TODO in this document and the app handoff, pending the later user request and measured geometry.

### Implementation sequence and final inspection

1. Complete this task/state/layout/copy specification and preserve the UI dossier reference.
2. Scaffold Flutter Android, web, Mac, and Linux shells; implement typed models, strict protocol parsing, gateway, controller, and media adapter.
3. Implement all compact and desktop screens, target selection, mission review, audio input/composer, system/session UI, and fixture injection.
4. Add focused protocol, concurrency, state preservation, coordinate-transform, and adaptive-layout checks; write backend schema/examples and integration instructions.
5. After coding: format/analyze and run meaningful tests, build web/Android, inspect actual rendered browser layouts, then launch the visible Android emulator and exercise the APK. Preserve failure evidence and repairs; publish/push only the app/docs changes.

The existing `tools/verify.py` will delegate a Flutter-specific profile to the app's evidence runner. This avoids representing Qt/core checks as Flutter evidence. Browser/emulator results identify Linux host, fixture source, actual viewport/device, and unverified physical media/backend limits.

## Final UI and code audit — 2026-10-09

### Changes from the first rendered implementation

- Desktop uses a compact Start action beside its selected target; Android keeps the wider reachable touch action.
- The desktop audio dock stays pinned below the independently scrolling camera/task surface.
- The three-pane workspace starts at 1,280 logical pixels, multiplied by capped text scale, so narrower windows give the camera more space.
- Camera source appears in the video overlay; duplicate source text above it was removed.
- Navigation tooltips exclude redundant semantics; visible destinations keep clear selection and keyboard paths.
- Inspector dividers show focus/hover and accept keyboard/semantics resize actions.
- Landing review names the selected task and consequence. Changed camera sessions/expired stills show Capture again. Abort review includes the active task name and detects a changed mission.
- Microphone acquisition and media negotiation use generation guards. Incoming audio starts muted. Release/interruption neutralizes local uplink immediately, independently of a delayed response.
- Reauthorization on the same server retains uncertain requests. Stop remains available for a pending or unknown follow. Switching servers during an active/pending mission is blocked.
- Each real connection has a random X-Operator-Client header, scoped alongside its token, so desktop and Android audio leases do not share sequence state.
- Speech state is backend-owned; pending/unknown outcomes cannot be repeated blindly. Text limits use Unicode scalar values; whitespace-only drafts do not enable Speak.
- Decoded frame dimensions must agree with original dimensions/crop before frames reach point selection.
- HTTPS-hosted web clients get explicit guidance when entering an HTTP backend. Private-LAN HTTP remains supported for native/local hosting.
- Sheets and dialogs use reduced-motion styles where configured. Token storage remains memory-only.
- Exact additional labels include **Read only**, **Refresh mission status**, **Refresh playback status**, **Capture again**, **Reconnect media**, **Open settings**, **Close**, and the associated local fault/recovery text in the client source.

### Reference comparison and verification

Compared the rendered app with the user's dossier and Google's [animated responsive Flutter/Material 3 codelab](https://codelabs.developers.google.com/codelabs/flutter-animated-responsive-layout). Adopted adaptive navigation, stable list/detail context, clear selection, meaningful surfaces, persistent field labels and native interaction. The operational workspace uses sparse rows and dividers appropriate to video/tasks.

- Flutter 3.47.1 / Dart 3.13.1 on Linux x86_64.
- **79 focused tests pass**, including 24 destination/width combinations, larger text/landscape/keyboard, state preservation, auth/type validation, frame transforms and delayed command/microphone ordering. Parameter-grid operations inside one test are not counted as separate tests.
- Production/fixture web, x64 Android and universal Android phone APK builds pass: [final build evidence](evidence/verification/20261009-flutter-05/report.json).
- The visible Pixel_10_Pro_XL emulator (1344 × 2992, 480 dpi) passes one instrumented workflow covering roster, follow/stop, abort review, landing-point request, listening, held talk/release, speech completion and System: [Android log](evidence/verification/20261009-ui-audit-01/android-integration-04.txt).
- Actual browser checks cover the desktop workspace, speech completion, system rows, readonly state, stale video and disconnected production startup. A cross-origin test endpoint fails clearly when CORS is absent. Captures use explicit pixel-scale clips because the internal browser uses a 1.2 scale factor.
- Earlier failed analysis/test-driver attempts and captures are retained; test-driver import and frame-pump sequencing repairs are identified in the [audit record](evidence/verification/20261009-ui-audit-01/README.md).
- No physical backend, media route, microphone/speaker node, camera, aircraft or ElevenLabs call was used. Fixture transitions represent UI behavior only.

### Delivery and remaining integration

- Published app: https://chessdroid108.github.io/hackphs-operator-web/
- Labelled UI preview: https://chessdroid108.github.io/hackphs-operator-web/preview/
- Source main delivery: 8844b2a; source CI run 37998164572 passes.
- Compiled-site main delivery: 11f86dd; Pages run 37998272856 passes. Both published routes were opened and inspected in the internal browser.

Project source changes are pushed directly to **main**, per the user. GitHub Pages is blocked for the source repository by its current plan. A separate public deployment repository, **chessdroid108/hackphs-operator-web**, holds only compiled website files and also uses main. The source repository's CI verifies/builds and uploads the website artifact.

**Backend handoff:** [software/flutter_operator/BACKEND_HANDOFF.md](software/flutter_operator/BACKEND_HANDOFF.md). The current Python server does not implement the proposed operator API.

**Visible TODO:** interactive measured CAD integration remains deferred until the user's later request and supplied dimensions. Collision/contact instrumentation remains a backend/physical decision; verified backend events can already appear in Recent events.

## References

- [Project documentation index](docs/README.md)
- [Current software architecture and authority limits](docs/04-software.md)
- [Current native desktop workstation](docs/14-desktop-app.md)
- [Navigation software and current advisory limits](docs/23-navigation-software.md)
- [HackPHS project Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit)
- [Universal UI Reference Library and Design Principles Dossier](https://docs.google.com/document/d/1G-fn3NKXPNHM3SvV-kJ-FSS-DbW-Bsi5XZqqHb1pezg/edit)
- [Flutter adaptive and responsive design](https://docs.flutter.dev/ui/adaptive-responsive) — Fit content and choose usable layouts for available space.
- [Flutter adaptive design best practices](https://docs.flutter.dev/ui/adaptive-responsive/best-practices) — Touch-first, keyboard/pointer support, and preserving state.
- [Flutter adaptive app approach](https://docs.flutter.dev/ui/adaptive-responsive/general) — Abstract, measure available constraints, then branch layout.
- [Flutter large-screen guidance](https://docs.flutter.dev/ui/adaptive-responsive/large-screens) — Navigation and content patterns for desktop-sized windows.
- [Flutter SafeArea and MediaQuery](https://docs.flutter.dev/ui/adaptive-responsive/safearea-mediaquery) — Insets and available display space.

## Hardware-free contract integration — 2026-10-10

The existing screens now have real Python REST contract tests at 390 px and 1280 px, plus authenticated still/JPEG, follow/loss/Stop and reconciliation checks against a separate generated-image backend process. No screen redesign was introduced. The operational app still starts disconnected; generated backend missions carry mock provenance, and physical mission/audio capabilities remain unavailable. The updated verifier and CI build web, Android and Mac artifacts. See [completion evidence](docs/28-hardware-free-completion.md). Device/network/FPV/flight acceptance remains separate.
