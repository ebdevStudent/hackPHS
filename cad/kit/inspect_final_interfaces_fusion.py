"""Read-only Fusion audit of all sixteen ring-splice screw axes and current T4."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import adsk.core
import adsk.fusion

ROOT = Path('/Users/devk/Documents/HackPHS26')
CAD = ROOT/'cad/apex2-cage'


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    assert doc.name == 'Apex2 Ball Cage P1B Gimbal'
    design = adsk.fusion.Design.cast(app.activeProduct)
    ns = {'__file__': str(CAD/'validation.py')}
    exec(compile((CAD/'validation.py').read_text(), ns['__file__'], 'exec'), ns)
    bodies = ns['pool'](design.rootComponent.occurrences)
    quarters = [b for b in bodies if b.name in ('inner_ring_quarter', 'outer_ring_quarter')]
    junctions = [b for b in bodies if '_junction_' in b.name]
    assert len(quarters) == len(junctions) == 8
    p = {r.name: r.value*(10 if r.unit == 'mm' else 1) for r in design.userParameters}

    def cylinders(body, diameter):
        return [(face, c) for face in body.faces
                if (c := adsk.core.Cylinder.cast(face.geometry)) and abs(c.radius*20-diameter) < 1e-5]

    def axial_limits(face, axis):
        box = face.boundingBox
        dots = [sum(v[k]*axis[k] for k in range(3))*10 for v in itertools.product(
            (box.minPoint.x,box.maxPoint.x), (box.minPoint.y,box.maxPoint.y), (box.minPoint.z,box.maxPoint.z))]
        return min(dots), max(dots)

    rows = []
    for quarter in quarters:
        holes = cylinders(quarter, p['m2_tap'])
        assert len(holes) == 2
        for q_face, q_cylinder in holes:
            axis = q_cylinder.axis.asArray()
            origin = q_cylinder.origin.asArray()
            matches = []
            for junction in junctions:
                if junction.name.split('_')[0] != quarter.name.split('_')[0]:
                    continue
                for j_face, j_cylinder in cylinders(junction, p['m2_clear']):
                    if abs(sum(a*b for a,b in zip(axis, j_cylinder.axis.asArray()))) < .999999:
                        continue
                    delta = [a-b for a,b in zip(j_cylinder.origin.asArray(), origin)]
                    along = sum(a*b for a,b in zip(delta, axis))
                    error = math.sqrt(sum((a-along*b)**2 for a,b in zip(delta, axis)))*10
                    if error > 1e-4:
                        continue
                    qlo, qhi = axial_limits(q_face, axis)
                    jlo, jhi = axial_limits(j_face, axis)
                    assert abs((qhi-qlo)-p['ring_t']) < 1e-4
                    assert abs((jhi-jlo)-p['splice_t']) < 1e-4
                    assert min(abs(qlo-jhi), abs(qhi-jlo)) < 1e-4
                    assert abs(max(qhi,jhi)-min(qlo,jlo)-5.) < 1e-4
                    matches.append({'junction': junction.name, 'coaxial_error_mm': error,
                                    'quarter_pilot_mm': p['m2_tap'], 'splice_clearance_mm': p['m2_clear'],
                                    'joined_stack_mm': 5.})
            assert len(matches) == 1, (quarter.name, matches)
            rows.append({'quarter': quarter.name, **matches[0]})
    assert len(rows) == 16
    out = CAD/'review-2026-10-09-finalization'
    report = {'document': doc.name, 'modified': doc.isModified, 'ring_splice_axes': rows,
              'sources': {n: hashlib.sha256((CAD/n).read_bytes()).hexdigest()
                          for n in ('build_p1a.py','build_p1b.py','fit_results.json')},
              'limitations': 'Coaxial passages and stack only. Screw-head/washer envelopes, actual screw thread grip and loaded splice strength need physical checks.'}
    (out/'ring-splice-interfaces.json').write_text(json.dumps(report, indent=2)+'\n')
    names = ('carrier_plate','nut_shield_plate','support_arm_p1b','arm_pivot_block')
    live = {'document': doc.name, 'modified': doc.isModified,
            'parameters': {r.name: {'expression': r.expression, 'value_mm': p[r.name]}
                           for r in design.userParameters if r.unit == 'mm'},
            'bodies': [{'name': b.name, 'solid': b.isSolid, 'volume_mm3': b.volume*1000,
                        'min_mm': [x*10 for x in b.boundingBox.minPoint.asArray()],
                        'max_mm': [x*10 for x in b.boundingBox.maxPoint.asArray()]}
                       for b in bodies if b.name in names]}
    path = ROOT/'cad/kit/reports/t4-fusion-inspection-2026-10-09.json'
    (out/'t4-fusion-inspection-before-finalization.json').write_bytes(path.read_bytes()) if not (out/'t4-fusion-inspection-before-finalization.json').exists() else None
    path.write_text(json.dumps(live, indent=2)+'\n')
    print(json.dumps({'ring_splice_axes_passed': len(rows), 't4_bodies': len(live['bodies']), 'document_modified': doc.isModified}))
