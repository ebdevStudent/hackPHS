import adsk.core, adsk.fusion, json, os, itertools
HERE='/Users/devk/Documents/HackPHS26/cad/apex2-cage'
B={'__file__':HERE+'/build_p1b.py','__name__':'inspect_generator'}
exec(compile(open(B['__file__']).read(),B['__file__'],'exec'),B)

def run(context):
 app=adsk.core.Application.get(); d=adsk.fusion.Design.cast(app.activeProduct); root=d.rootComponent
 s=B['A']['Solids'](); identity=adsk.core.Matrix3D.create()
 pool=[(o.fullPathName,b) for o in root.allOccurrences for b in o.bRepBodies]
 def overlap(a,b,offset=(0,0,0)):
  return B['collide'](s,s.copy(a),s.copy(b),B['translation'](offset),identity)
 p={x.name:x.value*(10 if x.unit=='mm' else 1) for x in d.userParameters}
 nuts=next(b for _,b in pool if b.name.startswith('M2_nut'))
 pad=next(b for _,b in pool if b.name=='BATTERY_PAD_foam')
 isb='P1B' in app.activeDocument.name
 travel=p['adj_y']
 out={'document':app.activeDocument.name,'version':app.activeDocument.dataFile.versionNumber,'nuts_pad':[],'joints':[],'rigidGroups':[],'physical':[],'static':[]}
 for sign in [-1,0,1]:
  off=(sign*travel,0,0) if isb else (0,sign*travel,0)
  out['nuts_pad'].append({'frame_offset_mm':off,'overlap_mm3':overlap(nuts,pad,off)})
 for c in d.allComponents:
  for j in c.asBuiltJoints:
   out['joints'].append({'name':j.name,'one':j.occurrenceOne.fullPathName,'two':j.occurrenceTwo.fullPathName,'axis':j.jointMotion.rotationAxisVector.asArray(),'angle':j.jointMotion.rotationValue,'transform':j.transform.asArray()})
  for g in c.rigidGroups:
   out['rigidGroups'].append({'owner':c.name,'name':g.name,'members':[o.fullPathName for o in g.occurrences],'suppressed':g.isSuppressed})
  out['physical'].append({'component':c.name,'native_mass_g':c.physicalProperties.mass*1000,'meshes':[{'name':b.name,'material':b.material.name} for b in c.meshBodies]})
 # Visible structure, prop disks, fasteners and pad; exclude mutually overlapping aircraft placeholders.
 excluded=('CAMERA_VIEW','battery_','frame_plate','motors_','stack_','camera_','ANTENNA')
 tested=[(path,b) for path,b in pool if b.isVisible and not b.name.startswith(excluded)]
 for i,(ap,a) in enumerate(tested):
  for bp,b in tested[i+1:]:
   if not a.boundingBox.intersects(b.boundingBox): continue
   v=overlap(a,b)
   if v>1e-6: out['static'].append({'a':ap+'/'+a.name,'b':bp+'/'+b.name,'volume_mm3':v})
 out['tested_bodies']=len(tested)
 out['root_mass_g']=root.physicalProperties.mass*1000
 for pack in ['450','1100']:
  batt=next(b for _,b in pool if b.name=='battery_'+pack+'mAh_PLACEHOLDER')
  out['battery_'+pack]={'nuts_overlap_mm3':overlap(nuts,batt),'nut_gap_mm':app.measureManager.measureMinimumDistance(nuts,batt).value*10}
 path=HERE+'/review-2026-10-08/diagnosis-before-'+('p1b' if isb else 'p1a')+'.json'
 open(path,'w').write(json.dumps(out,indent=2));print(json.dumps(out))
