"""Rebuild and validate final P1B in Fusion, preserving native baseline evidence."""
import contextlib
import io
import json
import traceback
from pathlib import Path
import adsk.core
import adsk.fusion

ROOT=Path('/Users/devk/Documents/HackPHS26')
CAD=ROOT/'cad/apex2-cage'
OUT=CAD/'review-2026-10-09-finalization'


def run(context):
    OUT.mkdir(exist_ok=True)
    app=adsk.core.Application.get()
    assert app.activeDocument.name=='Apex2 Ball Cage P1B Gimbal'
    d=adsk.fusion.Design.cast(app.activeProduct)
    backup=OUT/'baseline_P1B.f3d'
    if not backup.exists():
        assert not app.activeDocument.isModified, 'Unexpected user edits before baseline backup'
        assert d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(backup)))
    scope={'__name__':'final_p1b','__file__':str(CAD/'build_p1b.py')}
    exec(compile(Path(scope['__file__']).read_text(),scope['__file__'],'exec'),scope)
    log=io.StringIO()
    try:
        with contextlib.redirect_stdout(log):scope['run'](context)
    except Exception:
        (OUT/'generator-failed.txt').write_text(log.getvalue()+'\n'+traceback.format_exc())
        raise
    (OUT/'generator-passed.txt').write_text(log.getvalue())
    report={'document':app.activeDocument.name,'generator_passed':True,
        'parameters':{p.name:{'expression':p.expression,'value':p.value,'unit':p.unit} for p in d.userParameters},
        'bodies':[{'component':c.name,'name':b.name,'solid':b.isSolid,'lumps':b.lumps.count,
                   'volume_mm3':b.volume*1000,'material':b.material.name} for c in d.allComponents for b in c.bRepBodies],
        'joints':[{'name':j.name,'axis':j.jointMotion.rotationAxisVector.asArray()}
                   for c in d.allComponents for j in c.asBuiltJoints],
        'native_baseline_backup':backup.name,
        'physical_status':'Selected physical coupon fits; full assembly acceptance still pending'}
    (OUT/'native-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    archive=OUT/'final_P1B.f3d'
    assert d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(archive)))
    print(json.dumps({'generator_passed':True,'joint_count':len(report['joints']),'body_count':len(report['bodies']),
                      'output':str(OUT),'final_native_archive':str(archive)}))
