# Backend integration handoff

The Python server implements the visual/mission subset of this contract in `ball_demo/ui_api.py`, registered by the existing FastAPI app. It shares the engine's single mission ledger and does not add physical output. WebRTC/audio and aircraft execution remain deferred/unavailable. UI fixtures establish no physical behavior.

## Replaceable boundary

Implement OperatorGateway or satisfy RestOperatorGateway. Widgets contain no routes. MediaPort can be replaced independently of screens; the initial real adapter negotiates LAN WebRTC.

| Endpoint | Behavior |
| --- | --- |
| GET /api/ui/v1/snapshot | Implemented. Typed snapshot, monotonic process-local sequence, UTC observations and operator authorization state. Anonymous read is allowed. |
| POST /api/ui/v1/commands | Implemented. Strict request ID/kind/payload and token-required mutation; accepted/rejected result. |
| GET /api/ui/v1/commands/<request_id> | Implemented. Reconciles a retained request; unknown after restart/eviction. Anonymous read is allowed. |
| POST /api/ui/v1/camera/still | Implemented as read-only capture of a fresh frame; returns an immutable frame descriptor. Anonymous read is allowed. |
| GET <frame.image_path> | Implemented. Immutable cached JPEG, same-origin path, bounded cache; anonymous read is allowed. |
| POST /api/ui/v1/media/offer | Not implemented. WebRTC media remains unavailable. |

HTTP 401/403 invalidates operator access; 404 identifies an incompatible API. GET state polling is currently one second and may recover within a manually opened session. Explicit disconnect ends it. Mutations are never retried automatically after a timeout.

Responses exceeding 2 MiB or containing malformed typed state are rejected. Snapshot freshness is at most four seconds; frame validity is server-provided, 1–15,000 ms. Timestamps more than two seconds in the future are rejected. Synchronize clocks, or explicitly negotiate an offset before altering this rule.

The implemented Python API permits anonymous reads; it sets `operator_authorized` false when no valid bearer token is supplied. A supplied invalid token is rejected. All commands require `Authorization: Bearer <token>`. The app sends a random X-Operator-Client value, but the current API does not use it because it has no media/audio lease state. No credentials appear in URLs. CORS allows the published GitHub Pages origin by default; configure other trusted origins with `BALL_OPERATOR_ORIGINS`. An HTTPS-hosted web app still needs an HTTPS-accessible backend; browsers may require local-network permission. A local HTTP host can reach a local HTTP Pi endpoint subject to browser policy.

## Snapshot ownership

- source is live or mock; mock is always labelled.
- Every capability has strict supported/ready booleans and a reason when unavailable.
- The backend owns the prepared roster, stable person_id, tag family/ID, detection state and availability. Editing the roster is outside this initial app.
- A camera session has a unique session_id; frame camera_session_id must match. A frame ID names an immutable image. Image paths are same-origin paths without credentials, queries or external hosts.
- width/height describe the original frame. crop describes which normalized original area the encoded image covers. rotation/mirrored describe display orientation. Detection boxes are original-frame normalized rectangles.
- Mission snapshots provide mission_id, type, phase and the current causal request_id. Pending/unknown outcomes reconcile against that identity. Provide actual safe abort behavior in abort_summary; an absent meaning disables Abort.
- Audio includes actual readiness, provided voices, a Unicode scalar-value text limit (at most 2,000), and queued/playing/completed/rejected/failed speech records.
- Component/event dates are observations. Missing battery/contact evidence stays absent. The client creates no level meters, telemetry or collision score.

See contract/example-snapshot.json and contract/schema.json. Response additions may be ignored; required fields remain strict and versioned. Reject unknown fields in all commands server-side.

## Commands and cancellation

All requests contain request_id, kind, payload. Stop remains available for a pending or unknown follow request, including after reauthorization on the same endpoint. Reauthorization does not resend the mission. The request ID is an idempotency key: duplicates return the original outcome. Never retry a new ID for an uncertain task automatically.

| Kind | Payload |
| --- | --- |
| follow | Prepared person_id, tag_id and tag_family; validate identity and readiness. |
| stop | Nullable mission_id and pending_request_id. A stop targeting a pending start must prevent its later activation. |
| abort | mission_id; apply documented mission abort and report lifecycle. No implied motor kill/disarm. |
| land | mode=current_position, or camera_point/apriltag with frame_id and original normalized point={x,y}; tag mode includes tag identity. |
| speak | text and optional provided voice_id. ElevenLabs calls and secrets stay backend-side. |
| audio_uplink | enabled boolean, monotonic sequence, lease_ms=600 while enabled and 0 disabled, scoped to operator/media session. |

The client initially admits one high-level mission at a time while concurrency remains open. Acceptance does not show Following; only an active snapshot does. Stop remains available during a pending follow. Backend snapshots must report target loss/reacquisition, stopping, aborting and completion.

Land here requests landing at the aircraft's current location, chosen by when the operator issues the task. Additional camera-point/tag flows capture a fresh backend still, reverse its display transform and review the proposed target. The backend rejects expired, cross-session, unsuitable or unreachable targets. Pixels never become local world setpoints.

## Media and microphone lifecycle

WebRTC receives remote video/audio. Enable microphone requests only a local audio track, initially disabled; no phone camera or recording. Held talk starts after accepted uplink intent. Release mutes locally immediately, independent of REST completion. Navigation, focus/gesture cancellation, app interruption, permission/transport loss, stale server state and disconnect also release uplink. Keyboard and accessible interaction use the same task logic.

Enabled uplink leases renew approximately every 250 ms. The server must reject older sequences and expire after at most 600 ms without renewal. A later disable supersedes a delayed enable. Physical routing, board, power, codec compatibility, echo behavior and LED functions remain backend/hardware work.

The initial LAN adapter uses host ICE candidates and non-trickle negotiation. STUN/TURN, media session authentication and real interoperability need backend agreement and device checks. Fixture media opens no microphone or peer and produces no audio.

## Integration work still needed

- Add and validate the final FPV camera calibration and measured camera-to-aircraft transform before exposing relative person/pad pose through the live snapshot. The independent pose worker is configured with --target-calibration and --target-delay-ms; example optics are refused for camera/recorded sources. The --portable-demo generated scene proves the software path, not the final optics.
- Hardware-free REST gateway and phone/desktop widget tests use the real Python HTTP service (tools/portable_checks.py). Verify parsing on the actual connected device/browser and confirm freshness/clock behavior over both intended network profiles.
- Agree idempotency, cancellation order, token expiry, clock synchronization and uplink watchdogs.
- Define target-loss, Stop/Abort, landing envelope and radio/pilot authority before physical execution.
- Verify camera identity/crop/rotation, captured-still expiry and WebRTC performance on the actual Pi.
- Audio/TTS is outside the current plan; this handoff's audio details are deferred.
- Supply real collision/contact events if instrumented.
- Later TODO: interactive measured CAD model after an explicit request.
- Mac/Linux shells are provided; Mac packaging and actual Pi/Linux compatibility need their own evidence.
