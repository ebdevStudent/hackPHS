"""Create a centered, checked T4 copy without changing part geometry or originals.

Run: cad/kit/.venv/bin/python cad/kit/prepare_t4.py
Audit T4 first, then translate its entire packed layout in X/Y only. Verify the
written STL, part count, flat bases, original dimensions, pairwise separation
and conservative 5 mm brim clearance on the Voxel's 150 mm square bed.
"""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

import audit_t4

OUT = audit_t4.CAD / 'print_now'
FILENAME = 'T4_carrier_and_arms_checked.stl'


def prepare(output=OUT):
    report = audit_t4.audit()
    tools = audit_t4.load_plate_module()
    source = audit_t4.CAD / report['plate']['file']
    triangles = tools.read(source)
    vertices = triangles.reshape(-1, 3)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    offset = np.array([-(low[0]+high[0])/2, -(low[1]+high[1])/2, 0])
    centered = triangles + offset
    output.mkdir(parents=True, exist_ok=True)
    target = output / FILENAME
    tools.write(target, centered)
    written = tools.read(target)
    assert np.array_equal(written, centered.astype(np.float32))
    assert np.allclose(written-offset, triangles, atol=1e-5, rtol=0), 'Part geometry changed'
    original_body = audit_t4.solid(triangles)
    body = audit_t4.solid(written)
    parts = body.decompose()
    assert len(parts) == 4
    assert abs(body.volume()-original_body.volume()) < 1e-3
    for a,b in itertools.combinations(parts,2):
        assert (a ^ b).volume() < 1e-6
    bounds = np.array(body.bounding_box())
    assert abs(bounds[0]+bounds[3]) < 1e-5
    assert abs(bounds[1]+bounds[4]) < 1e-5
    assert abs(bounds[2]) < 1e-5
    assert all(abs(part.bounding_box()[2]) < 1e-5 for part in parts)
    # Verify a finite, positive contact patch for all four parts near Z=0.
    from test_pieces import box
    contact = box((-80,-80,0),(80,80,0.01))
    contact_areas = [round((part ^ contact).volume()/0.01,3) for part in parts]
    assert min(contact_areas) > 20
    size = bounds[3:]-bounds[:3]
    # 5 mm brim plus 0.4 mm conservative allowance for line discretization.
    allowance = 5.4
    edge_margins = [bounds[0]-allowance+75,75-bounds[3]-allowance,
                    bounds[1]-allowance+75,75-bounds[4]-allowance]
    assert min(edge_margins) > 7.5
    assert np.allclose(size,report['plate']['size_mm'],atol=1e-5)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    result = {
        'date':'2026-10-09','source_file':str(source.relative_to(audit_t4.CAD)),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'file':target.name,'sha256':sha,'translation_xy_mm':offset[:2].tolist(),
        'geometry_changed':False,'scale_percent':100,'part_count':4,
        'size_mm':size.tolist(),'min_mm':bounds[:3].tolist(),'max_mm':bounds[3:].tolist(),
        'bed_size_mm':[150,150,150],'brim_mm':5,'extra_path_allowance_mm':0.4,
        'edge_margins_with_allowance_left_right_front_back_mm':edge_margins,
        'base_contact_area_estimates_mm2':contact_areas,
        'checks':{'current_source_and_exports_match':True,'actual_stl_closed_and_consistently_wound':True,
                  'four_parts_flat_at_z0':True,'positive_base_contact':True,
                  'no_part_intersections':True,'xy_centered':True,
                  'fits_bed_with_brim_and_path_allowance':True,
                  'same_geometry_as_original_after_translation':True},
        'fit_audit':report,
        'physical_status':'Actual frame, fastener stacks and load strength remain to be checked; foam relief required',
    }
    (output/'T4_checked_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    sums=output/'SHA256SUMS'
    lines=sums.read_text().splitlines() if sums.exists() else []
    lines=[line for line in lines if not line.endswith('  '+target.name)]
    sums.write_text('\n'.join(lines+[sha+'  '+target.name])+'\n')
    return result


if __name__ == '__main__':
    result=prepare()
    print(json.dumps({key:result[key] for key in ('file','size_mm','translation_xy_mm','edge_margins_with_allowance_left_right_front_back_mm','base_contact_area_estimates_mm2','checks','physical_status')},indent=2))
