import adsk.core, adsk.fusion, json, math, os
def run(_context: str):
    app=adsk.core.Application.get(); d=adsk.fusion.Design.cast(app.activeProduct)
    tbm=adsk.fusion.TemporaryBRepManager.get()
    bs=[b for o in d.rootComponent.allOccurrences for b in o.bRepBodies]
    p={x.name:x.value for x in d.userParameters}
    def radii(name):
        b=next(b for b in bs if b.name==name)
        values=[]
        for f in b.faces:
            c=adsk.core.Cylinder.cast(f.geometry)
            if c: values.append(round(c.radius*20,6))
        return sorted(set(values))
    q=p['frame_hole_pitch']/2
    fast=[]
    for tag in ('450','1100'):
        battery=next(b for b in bs if b.name=='battery_'+tag+'mAh_PLACEHOLDER')
        z=battery.boundingBox.maxPoint.z
        for x in (-q,q):
            for y in (-q,q):
                cap=tbm.createCylinderOrCone(adsk.core.Point3D.create(x,y,z-0.2),0.19,adsk.core.Point3D.create(x,y,z),0.19)
                hit=tbm.copy(battery)
                if not tbm.booleanOperation(hit,cap,adsk.fusion.BooleanTypes.IntersectionBooleanType): raise RuntimeError('Cap-head intersection failed')
                v=hit.volume*1000 if hit.faces.count else 0
                fast.append({"battery":tag,"head_center_xy_mm":[x*10,y*10],"head_diameter_mm":3.8,"head_height_mm":2,"overlap_mm3":round(v,6)})
    m=p['motor_diag']/math.sqrt(8)*10
    tip=p['motor_diag']*5+p['prop_dia']*5
    zprop=(p['prop_z']+p['prop_disk_h'])*10+2.249089746270645
    worsttip=math.hypot(m+p['adj_x']*10,m+p['adj_y']*10)+p['prop_dia']*5
    nominal=math.hypot(tip,zprop)
    adjusted=math.hypot(worsttip,zprop+p['cg_slot']*10)
    pins=[]
    for b in bs:
        if b.name.startswith('pin_'):
            box=b.boundingBox
            pins.append({"name":b.name,"modeled_length_mm":round(max(box.maxPoint.x-box.minPoint.x,box.maxPoint.y-box.minPoint.y,box.maxPoint.z-box.minPoint.z)*10,4)})
    out={"nominal_m2_head_collision_test":fast,"assumption":"Nominal 3.8 mm diameter x 2 mm cap heads directly under carrier at centered frame screws; actual heads/nuts/washer layout is absent from the Fusion design.","cylindrical_feature_diameters_mm":{n:radii(n) for n in ('hub_3way','inner_junction_X_bearing','outer_junction_Y_bearing','outer_junction_Z_bearing','MR52ZZ_0','inner_ring_quarter','outer_ring_quarter')},"pins":pins,"purchased_pin_parameter_mm":p['pin_len']*10,"nominal_prop_sweep_radius_mm":nominal,"full_xyz_adjustment_prop_only_sweep_radius_mm":adjusted,"inner_radius_for_full_adjustment_plus_4mm_reserve":adjusted+p['gimbal_clear']*10,"candidate_rounded_inner_radius_mm":math.ceil(adjusted+p['gimbal_clear']*10),"fit_geometry":{"rod_mm":p['rod_dia']*10,"socket_mm":(p['rod_dia']+2*p['rod_bore_clear'])*10,"rod_insertion_mm":(p['socket_depth']-p['rod_end_gap'])*10,"free_edge_span_mm":(p['cage_edge']-2*p['hub_arm_len'])*10,"bearing_mm":p['bearing_od']*10,"bearing_seat_mm":(p['bearing_od']+p['bearing_seat_clear'])*10,"pin_mm":p['pin_d']*10,"pin_press_hole_mm":p['pin_press_d']*10},"joints":sum(c.joints.count for c in d.allComponents),"asBuiltJoints":sum(c.asBuiltJoints.count for c in d.allComponents),"rigidGroups":sum(c.rigidGroups.count for c in d.allComponents)}
    folder='/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07'
    with open(os.path.join(folder,'fit-hardware-envelope.json'),'w') as f: json.dump(out,f,indent=2)
    print(json.dumps(out))

