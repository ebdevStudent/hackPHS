import adsk.core, adsk.fusion, json, math, os
def run(_context: str):
    app=adsk.core.Application.get()
    d=adsk.fusion.Design.cast(app.activeProduct)
    tbm=adsk.fusion.TemporaryBRepManager.get()
    outdir='/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07'
    def entry(o,b): return {"path":o.fullPathName,"name":b.name,"body":b}
    allb=[entry(o,b) for o in d.rootComponent.allOccurrences for b in o.bRepBodies]
    chosen=[x for x in allb if x['body'].isVisible and not x['name'].startswith(('CAMERA_VIEW','HUB_ENVELOPE','gimbal_fit'))]
    def overlapbox(a,b):
        x=a.boundingBox;y=b.boundingBox
        return all(getattr(x.minPoint,k)<getattr(y.maxPoint,k)+1e-8 and getattr(y.minPoint,k)<getattr(x.maxPoint,k)+1e-8 for k in ('x','y','z'))
    hits=[]; tested=0
    for i,a in enumerate(chosen):
        for b in chosen[i+1:]:
            if not overlapbox(a['body'],b['body']): continue
            c=tbm.copy(a['body'])
            if not tbm.booleanOperation(c,tbm.copy(b['body']),adsk.fusion.BooleanTypes.IntersectionBooleanType):
                raise RuntimeError('Boolean failed '+a['name']+' / '+b['name'])
            tested+=1
            v=c.volume*1000 if c.faces.count else 0
            if v>1e-6: hits.append({"a":a['path']+'/'+a['name'],"b":b['path']+'/'+b['name'],"mm3":round(v,6)})
    cam=next(x for x in allb if x['name']=='camera_PLACEHOLDER')['body']
    box=cam.boundingBox
    apex=adsk.core.Point3D.create((box.minPoint.x+box.maxPoint.x)/2,box.maxPoint.y,(box.minPoint.z+box.maxPoint.z)/2)
    tilt=d.userParameters.itemByName('cam_tilt').value
    axis=adsk.core.Vector3D.create(0,math.cos(tilt),math.sin(tilt))
    end=adsk.core.Point3D.create(apex.x+axis.x*15,apex.y+axis.y*15,apex.z+axis.z*15)
    ray=tbm.createCylinderOrCone(apex,0.001,end,0.001)
    optical=[]
    for x in chosen:
        if not x['path'].startswith(('Outer ring','Inner ring','Cage')): continue
        c=tbm.copy(x['body'])
        if not tbm.booleanOperation(c,tbm.copy(ray),adsk.fusion.BooleanTypes.IntersectionBooleanType): raise RuntimeError('Ray boolean failed')
        if c.faces.count and c.volume>1e-10:
            inside=[]
            for n in range(1,1501):
                t=n/100
                p=adsk.core.Point3D.create(apex.x+axis.x*t,apex.y+axis.y*t,apex.z+axis.z*t)
                if x['body'].pointContainment(p)==adsk.fusion.PointContainment.PointInsidePointContainment:
                    inside.append(round(t*10,3))
            optical.append({"path":x['path'],"body":x['name'],"ray_overlap_mm3":round(c.volume*1000,8),"centerline_inside_mm_from_lens":([min(inside),max(inside)] if inside else None)})
    structural=[x for x in chosen if x['path'].startswith(('Cage','Outer ring','Inner ring')) or x['name'] in ('carrier_plate','support_arm_p1b','arm_pivot_block')]
    bbox_min=[min(getattr(x['body'].boundingBox.minPoint,k)*10 for x in structural) for k in ('x','y','z')]
    bbox_max=[max(getattr(x['body'].boundingBox.maxPoint,k)*10 for x in structural) for k in ('x','y','z')]
    printvol=sum(x['body'].volume for x in structural if not x['name'].startswith('rods_'))
    rodvol=sum(x['body'].volume for x in structural if x['name'].startswith('rods_'))
    out={"document":app.activeDocument.name,"version":app.activeDocument.dataFile.versionNumber,"visible_checked_bodies":len(chosen),"bbox_candidate_pairs":tested,"static_interferences":hits,"optical_axis_origin_mm":[apex.x*10,apex.y*10,apex.z*10],"optical_axis_direction":[axis.x,axis.y,axis.z],"optical_axis_occluders":optical,"assembly_outside_span_mm":[round(hi-lo,4) for lo,hi in zip(bbox_min,bbox_max)],"printed_volume_cm3":printvol,"carbon_rod_volume_cm3":rodvol,"printed_solid_mass_at_1_27_g_cm3":printvol*1.27,"rod_mass_at_1_55_g_cm3":rodvol*1.55,"fusion_total_mass_kg":d.rootComponent.physicalProperties.mass,"fusion_total_volume_cm3":d.rootComponent.physicalProperties.volume,"materials":sorted(set(x['body'].material.name for x in allb)),"documentModified":app.activeDocument.isModified}
    with open(os.path.join(outdir,'static-optics-mass.json'),'w') as f: json.dump(out,f,indent=2)
    app.activeViewport.saveAsImageFile(os.path.join(outdir,'01-nominal-top.png'),1600,1400)
    print(json.dumps(out))

