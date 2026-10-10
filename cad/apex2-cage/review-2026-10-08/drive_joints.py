import adsk.core,adsk.fusion,math,json,os
HERE='/Users/devk/Documents/HackPHS26/cad/apex2-cage'
V={'__file__':HERE+'/validation.py'};exec(compile(open(V['__file__']).read(),V['__file__'],'exec'),V)
B={'__file__':HERE+'/build_p1b.py'};exec(compile(open(B['__file__']).read(),B['__file__'],'exec'),B)

def run(context):
 app=adsk.core.Application.get();d=adsk.fusion.Design.cast(app.activeProduct);root=d.rootComponent
 groups={k:next(o for o in root.occurrences if o.component.name.startswith(prefix)) for k,prefix in [('cage','Cage ('),('outer','Outer ring'),('inner','Inner ring'),('side','Aircraft side')]}
 joints=list(root.asBuiltJoints); assert len(joints)==3
 original=[j.jointMotion.rotationValue for j in joints];result=[]
 try:
  for angles in [(30,0,0),(-60,0,0),(0,45,0),(0,-90,0),(0,0,30),(0,0,-120),(45,30,-60),(90,-90,90)]:
   for j,a in zip(joints,angles):j.jointMotion.rotationValue=math.radians(a)
   adsk.doEvents()
   static=V['static'](V['pool'](groups.values())); connected=B['connectivity'](groups)
   if connected:raise RuntimeError(str(connected))
   result.append({'angles_ZXY_deg':angles,'joint_values_deg':[math.degrees(j.jointMotion.rotationValue) for j in joints],
                  'static':static,'connectivity_errors':connected,'group_world_transforms':{k:o.transform2.asArray() for k,o in groups.items()}})
   if angles==(45,30,-60):
    app.activeViewport.fit();app.activeViewport.saveAsImageFile(HERE+'/review-2026-10-08/05-joints-driven.png',1600,1200)
 finally:
  for j,a in zip(joints,original):j.jointMotion.rotationValue=a
  adsk.doEvents()
 out={'cases':result,'reset_joint_values_deg':[math.degrees(j.jointMotion.rotationValue) for j in joints],
      'reset_group_world_transforms':{k:o.transform2.asArray() for k,o in groups.items()},'grounded_cage':groups['cage'].isGrounded}
 open(HERE+'/review-2026-10-08/joint-drive.json','w').write(json.dumps(out,indent=2));print('Joint-drive cases:',len(result),'reset:',out['reset_joint_values_deg'])
