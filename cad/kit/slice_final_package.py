"""Use the bundled FlashPrint engine to verify every final plate, offline only."""
import hashlib
import json
from pathlib import Path
from slice_t4_check import check, ROOT


def main():
    folder = ROOT/'cad/apex2-cage/print_ready_p1b'
    manifest = json.loads((folder/'manifest.json').read_text())
    rows = []
    for plate in manifest['plates']:
        path = folder/plate['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == plate['sha256']
        result = check(stl=path, label=plate['name'], expected_parts=plate['part_count'],
                       layer_height='.15', solid_layers='5', max_height=plate['size_mm'][2]+.15,
                       reports=folder/'checks', image_dir=folder/'previews', min_edge_margin=7)
        rows.append({'plate': plate['name'], 'stl_sha256': result['stl_sha256'],
                     'first_layer_parts': result['first_layer_part_count'],
                     'layers': result['layer_count'], 'segments': result['extrusion_segment_count'],
                     'min_path_edge_clearance_mm': min(result['edge_margins_left_right_front_back_mm']),
                     'checks': result['checks']})
        print(plate['name'], 'PASS', 'parts', rows[-1]['first_layer_parts'],
              'minimum edge clearance', round(rows[-1]['min_path_edge_clearance_mm'], 2), flush=True)
    (folder/'slice-verification.json').write_text(json.dumps({'scope': 'Offline generic-startup diagnostic; slice STLs in FlashPrint for Voxel jobs', 'plates': rows}, indent=2)+'\n')


if __name__ == '__main__':
    main()
