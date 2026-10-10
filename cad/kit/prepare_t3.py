"""Verify and center ten native Fusion T3 hubs with the selected T1B #2 bore."""
import hashlib
import itertools
import json
from pathlib import Path

import manifold3d as mf
import numpy as np

import audit_t4
from test_pieces import box

OUT=audit_t4.CAD/'print_now'


def cylinder(a,b,diameter):
    a,b=np.asarray(a,float),np.asarray(b,float)
    z=(b-a)/np.linalg.norm(b-a)
    x=np.cross(z,[0,0,1]);x/=np.linalg.norm(x)
    y=np.cross(z,x)
    return mf.Manifold.cylinder(np.linalg.norm(b-a),diameter/2,diameter/2,128).transform(np.column_stack([x,y,z,a]).tolist())


def prepare():
    tools=audit_t4.load_plate_module()
    native=json.loads((OUT/'T3_native_hub_manifest.json').read_text())
    for name,digest in native['sources'].items():
        assert hashlib.sha256((audit_t4.CAD/name).read_bytes()).hexdigest()==digest
    part_path=OUT/native['file']
    assert hashlib.sha256(part_path.read_bytes()).hexdigest()==native['sha256']
    triangles=tools.read(part_path)
    body=audit_t4.solid(triangles)
    assert len(body.decompose())==1
    assert abs(body.volume()-native['native_volume_mm3'])/native['native_volume_mm3']<.001
    bore=native['bore_mm'];p=native['parameters_mm'];paths=[]
    for direction in native['arms']:
        d=np.array(direction);d/=np.linalg.norm(d)
        # Native endpoints use the generator's rounded arm vectors.
        tip=np.array(direction)*p['hub_arm_len']
        start=tip-np.array(direction)*(p['socket_depth']-.03)
        small=cylinder(start,tip+d*.4,bore-.006)
        assert (body ^ small).volume()<1e-5, 'Socket is blocked or too small'
        large=cylinder(tip-d*.5,tip-d*.1,bore+.05)
        assert (body ^ large).volume()>.01, 'Socket lacks its expected rim'
        floor_probe=cylinder(tip-np.array(direction)*(p['socket_depth']+.12),
                             tip-np.array(direction)*(p['socket_depth']+.04),.4)
        assert (body ^ floor_probe).volume()>.008, 'Blind floor missing'
        paths.append({'direction':direction,'open_probe_mm':bore-.006,'rim_probe_mm':bore+.05,'blind_floor_present':True})
    vertices=triangles.reshape(-1,3)
    low,high=vertices.min(0),vertices.max(0)
    centered=triangles-np.array([(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]])
    size=high-low;gap=12.0
    placements=[((column-2)*(size[0]+gap),(row-.5)*(size[1]+gap)) for row in range(2) for column in range(5)]
    placed=np.concatenate([centered+np.array([x,y,0]) for x,y in placements])
    target=OUT/'T3_cage_section_socket_2_checked.stl'
    tools.write(target,placed)
    written=tools.read(target)
    solid=audit_t4.solid(written)
    parts=solid.decompose()
    assert len(parts)==10
    assert all(abs(part.bounding_box()[2])<1e-5 for part in parts)
    assert all(abs(part.volume()-body.volume())<.002 for part in parts)
    assert all((a ^ b).volume()<1e-5 for a,b in itertools.combinations(parts,2))
    contact=box((-75,-75,0),(75,75,.01))
    contacts=[(part ^ contact).volume()/.01 for part in parts]
    assert min(contacts)>35
    bounds=np.array(solid.bounding_box());extent=bounds[3:]-bounds[:3]
    margins=((150-extent[:2])/2-5.4).tolist()
    assert min(margins)>12
    sha=hashlib.sha256(target.read_bytes()).hexdigest()
    result={'date':'2026-10-09','file':target.name,'sha256':sha,
            'source_hub_sha256':native['sha256'],'source_hub_manifest':'T3_native_hub_manifest.json',
            'part_count':10,'bore_mm':bore,'socket_depth_mm':p['socket_depth'],
            'fit_source':'User T1B rod socket #2','screw_holes':False,
            'size_mm':extent.tolist(),'layout_columns_rows':[5,2],'part_gap_mm':gap,
            'brim_mm':5,'extra_path_allowance_mm':.4,
            'bed_margin_xy_mm':margins,'base_contact_area_mm2_min':min(contacts),
            'socket_mesh_checks':paths,
            'checks':{'native_generator_and_fit_sources_match':True,'watertight_and_consistently_oriented':True,
                      'ten_separate_hubs_flat_at_z0':True,'positive_base_contact':True,
                      'all_three_sockets_open_with_blind_floors':True,
                      'five_mm_brim_fits_bed':True,'no_part_intersections':True},
            'physical_status':'T1B fit selected by user; actual T3 section strength and rod retention pending'}
    (OUT/'T3_checked_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    sums=OUT/'SHA256SUMS'
    lines=[line for line in sums.read_text().splitlines() if not line.endswith('  '+target.name)]
    sums.write_text('\n'.join(lines+[sha+'  '+target.name])+'\n')
    return result


if __name__=='__main__':
    print(json.dumps(prepare(),indent=2))
