import adsk.core,adsk.fusion,json
HERE='/Users/devk/Documents/HackPHS26/cad/apex2-cage'
V={'__file__':HERE+'/validation.py'};exec(compile(open(V['__file__']).read(),V['__file__'],'exec'),V)

def expect_failure(fn,fragment):
    try:fn()
    except RuntimeError as error:
        if fragment not in str(error):raise
        return str(error)
    raise AssertionError('Regression was not rejected: '+fragment)

def run(context):
    app=adsk.core.Application.get();d=adsk.fusion.Design.cast(app.activeProduct)
    bodies=[b for o in d.rootComponent.allOccurrences for b in o.bRepBodies]
    nuts=next(b for b in bodies if b.name.startswith('M2_nut'));pad=next(b for b in bodies if b.name=='BATTERY_PAD_foam')
    tb=adsk.fusion.TemporaryBRepManager.get();box=pad.boundingBox
    old=tb.createBox(adsk.core.OrientedBoundingBox3D.create(adsk.core.Point3D.create((box.minPoint.x+box.maxPoint.x)/2,(box.minPoint.y+box.maxPoint.y)/2,(box.minPoint.z+box.maxPoint.z)/2),adsk.core.Vector3D.create(1,0,0),adsk.core.Vector3D.create(0,1,0),box.maxPoint.x-box.minPoint.x+.4,box.maxPoint.y-box.minPoint.y,box.maxPoint.z-box.minPoint.z))
    out={'old_pad_reconstruction_width_mm':(box.maxPoint.x-box.minPoint.x+.4)*10,
         'old_pad_overlap_mm3':V['intersection'](nuts,old,(2,0,0)),
         'old_pad_rejected':expect_failure(lambda:V['assert_clear'](nuts,old,(2,0,0)),'intrusion'),
         'new_pad_overlap_mm3':V['intersection'](nuts,pad,(2,0,0)),
         'excess_travel_rejected':expect_failure(lambda:V['assert_clear'](nuts,pad,(3,0,0)),'intrusion')}
    p={x.name:x.value*(10 if x.unit=='mm' else 1) for x in d.userParameters};p['rod_dia']=1.5
    out['wrong_rod_size_rejected']=expect_failure(lambda:V['span_and_rods'](bodies,p),'1 mm baseline')
    open(HERE+'/review-2026-10-08/regression-results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out))
