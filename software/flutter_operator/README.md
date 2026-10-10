# Ball Drone Flutter operator client

The canonical screen, visual, content and integration plan is [UIDEVPLAN.md](../../UIDEVPLAN.md). Android and desktop use distinct compositions and the same controller/protocol/commands.

The normal app starts disconnected. The Python server implements the visual mission portion of `/api/ui/v1` for snapshots, captured stills, frame bytes, follow/stop/abort and landing requests/results. Audio/WebRTC and physical mission execution remain unavailable. Read [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md) and [contract/schema.json](contract/schema.json) for the implemented and deferred boundary. UI fixtures establish no physical flight, camera, mic/speaker or ElevenLabs behavior.

## Run

Flutter 3.47.1 / Dart 3.13.1; dependencies are locked in pubspec.lock.

```sh
cd software/flutter_operator
flutter pub get
flutter run -d web-server --web-port 8765
# Manually launch an AVD, then:
flutter run -d <emulator-device-id>
# On Mac:
flutter run -d macos
```

Enter the Pi address and an operator token in Connection settings. Blank token requests read-only access. Tokens are memory-only. Both network profiles use an operator-supplied address. The app never starts a backend server.

## Hardware-free backend rehearsal

Start `PYTHONPATH=software python -m ball_demo.cli serve --portable-demo --data runs/portable-demo` from the repository root, then enter `http://127.0.0.1:8080` and the saved token. This uses the normal app against generated AprilTag images and explicitly mock missions. It does not require a fixture build. For a browser served from another local port, configure `BALL_OPERATOR_ORIGINS` to that exact origin before launching the backend. See [completion instructions](../../docs/28-hardware-free-completion.md).

## Development fixtures

Fixtures require a separate build flag; the operational app has no demo switch.

```sh
flutter run -d web-server --web-port 8765 --dart-define=UI_PREVIEW=true
flutter build apk --debug --dart-define=UI_PREVIEW=true
```

Fixture builds display UI preview · fixture data and mock camera provenance. The camera is a labelled test card; microphone/listening/TTS transitions produce no audio or aircraft commands. Web scenarios use a development-only query such as ?fixture=stale; Android uses --dart-define=UI_FIXTURE=stale. Supported scenarios: ready, empty, stale, offline, denied, lost, rejected, audio_fault.

## Verify after coding

From the repo root:

```sh
python3 tools/verify.py --profile flutter --output evidence/verification/<new-directory>
```

The Flutter profile records host/tool versions, source hashes, logs, the existing tests, real Python HTTP/Dart gateway and phone/desktop contract-render checks, web builds, x64 emulator APKs, a universal Android phone APK, and a Mac release build on macOS. It never launches an emulator. Browser/emulator inspection follows separately. Use a fresh evidence directory each time.

## Structure

- lib/domain: typed protocol and frame transforms.
- lib/data: gateway, REST adapter and injected fixtures.
- lib/application: shared controller/state and command lifecycle.
- lib/media: replaceable WebRTC adapter.
- lib/ui: tokens, compact/desktop screens and contextual flows.
- test: protocol, async task, input and adaptive-layout regressions.
- tool: evidence runner and reproducible icons/test-card generation.

Inspector dividers support pointer, keyboard and semantics resizing. Landing-marker arrows alter the local image selection only; no aircraft command is sent until Request landing.

CAD remains a later TODO requiring measured geometry and an explicit request. Collision/contact events appear only when reported by the backend.

## Published review

[Operational client](https://chessdroid108.github.io/hackphs-operator-web/) · [Labelled UI preview](https://chessdroid108.github.io/hackphs-operator-web/preview/)

The source repository's plan blocks private-repository Pages. Compiled files are published in chessdroid108/hackphs-operator-web on main; project source remains in chessdroid108/HackPHS on main. Source CI uploads an operator-web-site artifact with the correct publication base paths. Publish its contents to the deployment repository's main branch to update the website; that repository's Pages workflow deploys the static files.

The installed-phone artifact from the recorded build is build/android-phone/ball-drone.apk (debug signed, universal ABIs). Actual phone/backend/media operation remains unverified.
