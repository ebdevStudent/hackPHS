"""Copy the verified final package into print_now and build its download ZIP.

Run after prepare_final_package, save_final_profiles, slicing and verification.
No printer job is started. Diagnostic generic-startup G-code is excluded.
"""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / 'cad/apex2-cage'
SOURCE = CAD / 'print_ready_p1b'
PRINT_NOW = CAD / 'print_now'
DEST = PRINT_NOW / 'FINAL_P1B'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    verification = json.loads((SOURCE / 'verification.json').read_text())
    assert verification['status'] == 'PASS'
    assert verification['production_parts'] == 84
    copied = []
    for line in (SOURCE / 'SHA256SUMS').read_text().splitlines():
        expected, relative = line.split('  ', 1)
        src = SOURCE / relative
        assert digest(src) == expected, relative
        assert src.suffix != '.g', 'Diagnostic G-code must not enter the print package'
        dst = DEST / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append({'file': relative, 'source_sha256': expected})
    # Only the guide needs relative-link updates at its new location.
    guide = DEST / 'README.md'
    text = guide.read_text().replace('../print_now/T3_cage_section_socket_2_checked.stl', '../T3_cage_section_socket_2_checked.stl')
    text = text.replace('../PRINT_AND_TEST_PLAN.md', '../../PRINT_AND_TEST_PLAN.md')
    text = text.replace('../review-2026-10-09-finalization/', '../../review-2026-10-09-finalization/')
    guide.write_text(text)
    manifest = json.loads((SOURCE / 'manifest.json').read_text())
    rows = []
    for name in ['T3', 'T4', 'KIT-bend_test_block', 'KIT-bend_test_jig', 'KIT-load_hook', 'KIT-pin_cut_gauge', 'H1-01', 'H1-02', 'H2', 'G1a', 'G1b', 'G2']:
        plate = next(p for p in manifest['plates'] if p['name'] == name)
        rows.append(f"| {name} | [{name}.stl](FINAL_P1B/{plate['file']}) | **{plate['profile']}** |")
        assert digest(DEST / plate['file']) == plate['sha256']
    start = '''# Start printing here — final P1B files

**Print T3 next.** Load its STL and select the matching saved profile in FlashPrint with **Voxel** selected. All twelve current plates, fourteen individual production designs, fixtures, saved profiles, native CAD, assembly instructions and validation records are in **FINAL_P1B/**. The older files alongside this guide are earlier coupons or layouts; use the FINAL files for production.

| Print | Load this STL | Select this profile |
| --- | --- | --- |
''' + '\n'.join(rows) + '''

Keep **100% scale and the supplied orientation/layout**. FINAL settings are 0.15 mm layers, 0.27 mm first layer, three shells, five top/bottom layers, 25% hexagon, 35 mm/s print, 10 mm/s first-layer maximum, and a 5 mm one-layer brim at 25% speed. Use the successful T1B temperature/retraction and bed preparation; the saved starters are 235 °C nozzle, 60 °C bed, 1.5 mm retraction at 30 mm/s. Supports, raft and XY compensation are off. Slice in FlashPrint to create the actual printer job and read its time estimate.

[Full settings and plate inventory](FINAL_P1B/README.md) · [Assembly and hardware](FINAL_P1B/ASSEMBLY.md) · [Profile backups](FINAL_P1B/profiles/) · [Individual replacement parts](FINAL_P1B/parts/) · [Native Fusion model](FINAL_P1B/P1B_final.f3d) · [Download the entire final package](FINAL_P1B.zip)

T3 prints ten hubs. Assemble nine with **ten 44.50 mm rods**, leaving one hub spare, then check socket retention and the section load/sag/drop tests before the full cage batches. T4 can be checked independently against the actual frame. M2 #5 is **2.00 mm on the combined seven-hole T1B strip**; rod #2 is **1.275 mm**. Physical strength, hardware grip, actual-frame fit and flight acceptance remain pending.

Earlier test coupons, if a retest is needed: [T0](T0_stringing_towers.stl), [T1](T1_socket_strip_and_rod_jig.stl), [combined T1B](T1B_socket_and_screw_refinement.stl), [T2](T2_gimbal_fit_coupon.stl). The standalone five-hole scratch coupon uses different numbering and was not the source of the selected M2 fit.

Regenerate this folder with `python3 cad/kit/prepare_print_now.py` after the final source package has passed its checks. Diagnostic generic-startup G-code is excluded from this folder and ZIP.
'''
    (PRINT_NOW / 'START_HERE.md').write_text(start)
    report = {'status': 'PASS', 'source': 'print_ready_p1b', 'files_copied': copied,
              'guide_relative_links_updated': True, 'all_plate_hashes_equal_verified_sources': True,
              'plates': len(manifest['plates']), 'production_parts': 84,
              'scope': verification['scope']}
    (DEST / 'copy-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    files = sorted(p for p in DEST.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    assert not any(p.suffix == '.g' for p in files)
    (DEST / 'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.relative_to(DEST)}\n' for p in files))
    archive = PRINT_NOW / 'FINAL_P1B.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DEST.rglob('*')):
            if p.is_file():
                z.write(p, str(p.relative_to(PRINT_NOW)))
        z.write(PRINT_NOW / 'START_HERE.md', 'START_HERE.md')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps({'status': 'PASS', 'plates': len(rows), 'production_parts': 84,
                      'directory': str(DEST), 'zip': str(archive), 'zip_bytes': archive.stat().st_size}, indent=2))


if __name__ == '__main__':
    main()
