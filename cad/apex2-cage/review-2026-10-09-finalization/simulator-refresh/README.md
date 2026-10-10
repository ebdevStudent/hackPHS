# Simulator final-CAD refresh snapshot

These files match the local simulator builder, generated model and headless test at CAD finalization on 2026-10-09. The simulator is a separate Git checkout with pre-existing staged and unstaged changes; this snapshot commits the relevant final sources in the parent CAD history without changing that checkout’s index. `manifest.json` records original paths and SHA-256 hashes. Run the builder and test from their original workspace paths; this evidence folder is not a standalone simulator distribution.

The builder uses the authoritative top-level CAD and guards source/export identity. The regenerated model accounts for 144.68 / 166.68 g under the native material and hardware allowance scenarios. The headless checks passed after moving the collision wall out of the unobstructed-speed test. See `../simulation-physics-check.txt` and `../simulation-test-before-fixture-fix.json`. No actual hardware masses, strengths or flight performance were measured.
