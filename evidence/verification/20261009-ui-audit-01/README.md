# Flutter UI inspection — 2026-10-09

Linux host, Flutter 3.47.1; code and first complete builds preceded all browser/emulator inspection. The emulator was launched with its window visible after planning/coding and baseline compilation.

## Passed checks

- [Build/tests](../20261009-flutter-05/report.json): analysis, 79 tests, production/fixture web, x64 emulator and universal phone APKs.
- [Android final workflow](android-integration-04.txt): prepared roster, active follow/stop, abort review/cancel, captured-frame landing request/result, receive preference, enable microphone, held talk/release, TTS completion and System.
- [Final Android captures](android-final/): screenshots from the passing instrumented run.
- [Desktop complete](desktop-complete.jpg), [following](desktop-following.jpg), [speech](desktop-speech.jpg), [system](desktop-system.jpg).
- [Readonly](web-readonly.jpg), [stale video](web-stale.jpg), [disconnected production](web-production-disconnected.jpg), [production Android](android-production.png).

The internal browser's 1.2 pixel scale requires explicit screenshot clips. Earlier default captures may clip the render and are preserved as intermediate evidence rather than final layout proof. Desktop final captures cover the full surface. The emulator is Pixel_10_Pro_XL / x86_64, 1344 × 2992 physical pixels, 480 dpi.

## Development failures and repairs

- Initial formatting/analysis failures and style repairs are retained in the preflight directory and first Flutter profile.
- android-integration-01 failed from missing imports in the added test helper; imports were repaired.
- android-integration-02/03 failed because text entry had not pumped a widget rebuild before tapping the formerly disabled Speak button. The driver now pumps after input, asserts the action is enabled, then polls the reported completion over successive frames. android-integration-04 passes.
- Web source/bootstrap and unknown/stale/auth states were inspected through the actual compiled app. A test connection across the two localhost ports lacks CORS and reports an unreachable server; it establishes error presentation, not API integration.
- A Playwright text-content wait could not locate canvas/semantics text; subsequent accessibility/screenshot observations show Completed. No browser console errors were observed in that speech check.

## Scope

Fixture video is a labelled test card. Fixture audio/PTT/TTS produce no audio, open no microphone and send no aircraft commands. Real WebRTC/ElevenLabs/Pi/aircraft behavior remains unverified. No simulator or CAD model is embedded in the operator UI.

Reference comparison: [Google adaptive Flutter/Material 3 codelab](https://codelabs.developers.google.com/codelabs/flutter-animated-responsive-layout) and the user's dossier. Public reference screenshots containing account chrome are excluded from maintained evidence; the reference URL is sufficient.

## Published verification

Source commit 8844b2a / CI 37998164572 passes. Compiled deployment commit 11f86dd / Pages 37998272856 passes. The operational and preview routes both load in the internal browser: [app](https://chessdroid108.github.io/hackphs-operator-web/) and [preview](https://chessdroid108.github.io/hackphs-operator-web/preview/). See published-app.jpg and published-preview.jpg. Source-project visibility remains private; only compiled website files were published separately.
