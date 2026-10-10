"""Run in Fusion: generate T3's candidate hub using the exact current hub builder.

Creates temporary BRep geometry and local evidence/STL files only. Does not
modify any document, user parameter, original STL or current export manifest.
"""
import hashlib
import importlib.util
import json
import math
import struct
from pathlib import Path

import adsk.core
import adsk.fusion

ROOT = Path('/Users/devk/Documents/HackPHS26')
CAD = ROOT/'cad/apex2-cage'
OUT = CAD/'print_now'


def run(context):
    app=adsk.core.Application.get()
    document=app.activeDocument
    assert document.name == 'Apex2 Ball Cage P1B Gimbal'
    was_modified=document.isModified
    design=adsk.fusion.Design.cast(app.activeProduct)
    namespace={'__name__':'t3_source','__file__':str(CAD/'build_p1a.py')}
    exec(compile((CAD/'build_p1a.py').read_text(),namespace['__file__'],'exec'),namespace)
    # Read actual design values, without calling the mutating parameters helper.
    p={prm.name:prm.value*10 for prm in design.userParameters if prm.unit=='mm'}
    for prm in design.userParameters:
        if prm.unit!='mm': p[prm.name]=prm.value
    graph=namespace['cage_graph'](p)
    frames=namespace['hub_frames'](p,graph)
    keys={frame['key'] for frame in frames if len(frame['key'][0])==3 and frame['key'][1] is None}
    assert len(keys)==1
    arms,boss=next(iter(keys))
    fit=json.loads((CAD/'fit_results.json').read_text())
    coupon=json.loads((OUT/'T1B_refinement_manifest.json').read_text())
    chosen=next(row for row in coupon['socket_holes'] if row['dots']==fit['rod_socket']['dots'])
    bore=chosen['diameter_mm']
    assert bore==fit['rod_socket']['bore_diameter_mm']
    selected=p.copy()
    selected['rod_bore_clear']=(bore-p['rod_dia'])/2
    s=namespace['Solids']()
    old=namespace['hub_body'](s,p,arms,boss)
    body=namespace['hub_body'](s,selected,arms,boss)
    assert body.isSolid
    original_row=next(row for row in json.loads((CAD/'exports_p1b/manifest.json').read_text())['parts'] if row['name']=='hub_3way')
    assert abs(old.volume*1000-original_row['native_volume_mm3'])<1e-5
    # Shrinking the sockets must add material only; outer geometry is retained.
    removed=s.copy(old)
    s.cut(removed,body)
    assert removed.volume*1000<1e-6
    paths=[]
    for d in arms:
        tip=namespace['mul'](d,selected['hub_arm_len'])
        start=namespace['sub'](tip,namespace['mul'](d,selected['socket_depth']-.02))
        tool=s.cyl(start,namespace['add'](tip,namespace['mul'](d,.5)),bore-.001)
        test=s.copy(body)
        assert s.tbm.booleanOperation(test,tool,adsk.fusion.BooleanTypes.IntersectionBooleanType)
        assert test.volume*1000<1e-6
        paths.append({'direction':list(d),'bore_diameter_mm':bore,'depth_mm':selected['socket_depth'],'probe_overlap_mm3':test.volume*1000})
    calc=body.meshManager.createMeshCalculator()
    calc.setQuality(adsk.fusion.TriangleMeshQualityOptions.VeryHighQualityTriangleMesh)
    calc.surfaceTolerance=.0001 # 0.001 mm, below the coupon's 0.025 mm step
    calc.maxNormalDeviation=math.radians(5)
    mesh=calc.calculate()
    assert mesh is not None and mesh.triangleCount>100
    coords=[v*10 for v in mesh.nodeCoordinatesAsDouble]
    indices=mesh.nodeIndices
    data=bytearray(b'Ball Drone T3 - T1B socket #2 native Fusion'.ljust(80,b' '))
    data.extend(struct.pack('<I',mesh.triangleCount))
    for i in range(0,len(indices),3):
        vertices=[coords[3*j:3*j+3] for j in indices[i:i+3]]
        a=[vertices[1][k]-vertices[0][k] for k in range(3)]
        b=[vertices[2][k]-vertices[0][k] for k in range(3)]
        n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        length=math.sqrt(sum(v*v for v in n))
        assert length>1e-12
        data.extend(struct.pack('<12fH',*[v/length for v in n],*[v for pt in vertices for v in pt],0))
    path=OUT/'T3_hub_socket_2_native.stl'
    path.write_bytes(data)
    assert document.isModified==was_modified
    report={'document':document.name,'document_modified_by_export':False,
        'part':'hub_3way','arms':list(arms),'boss':boss,
        'old_bore_mm':p['rod_dia']+2*p['rod_bore_clear'],
        'bore_mm':bore,'rod_bore_clear_mm_per_side':selected['rod_bore_clear'],
        'socket_depth_mm':selected['socket_depth'],'parameters_mm':selected,
        'original_native_volume_mm3':old.volume*1000,'native_volume_mm3':body.volume*1000,
        'socket_probes':paths,'file':path.name,'sha256':hashlib.sha256(data).hexdigest(),
        'mesh_surface_tolerance_mm':calc.surfaceTolerance*10,
        'sources':{name:hashlib.sha256((CAD/name).read_bytes()).hexdigest() for name in ('build_p1a.py','build_p1b.py','fit_results.json')}}
    (OUT/'T3_native_hub_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('bore_mm','rod_bore_clear_mm_per_side','native_volume_mm3','file','document_modified_by_export')}))
