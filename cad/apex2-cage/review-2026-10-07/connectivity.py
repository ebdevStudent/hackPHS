import adsk.core, adsk.fusion, json, os
def run(_context: str):
    app=adsk.core.Application.get(); d=adsk.fusion.Design.cast(app.activeProduct); measure=app.measureManager
    tbm=adsk.fusion.TemporaryBRepManager.get()
    entries=[(o.fullPathName,b) for o in d.rootComponent.allOccurrences for b in o.bRepBodies]
    def distance(a,b):return measure.measureMinimumDistance(a,b).value*10
    def overlap(a,b):
        body=tbm.copy(a)
        if not tbm.booleanOperation(body,tbm.copy(b),adsk.fusion.BooleanTypes.IntersectionBooleanType):raise RuntimeError('Press-fit intersection failed')
        return body.volume*1000 if body.faces.count else 0
    result={"junctions":[],"pivots":[]}
    for group in ('Inner ring','Outer ring'):
        ring=[(path,b) for path,b in entries if path.startswith(group)]
        quarters=[(path,b) for path,b in ring if 'quarter' in b.name]
        for path,b in ring:
            if 'junction' not in b.name:continue
            ds=[{"quarter":p,"distance_mm":round(distance(b,q),6)} for p,q in quarters]
            result["junctions"].append({"junction":path,"quarter_distances":ds,"touching_quarter_count":sum(x["distance_mm"]<0.01 for x in ds)})
    partners={0:('arm_pivot_block','inner_junction_X_bearing'),1:('arm_pivot_block','inner_junction_X_bearing'),2:('inner_junction_Y_pin','outer_junction_Y_bearing'),3:('inner_junction_Y_pin','outer_junction_Y_bearing'),4:('hub_pole_5way_pivot','outer_junction_Z_bearing'),5:('hub_pole_5way_pivot','outer_junction_Z_bearing')}
    for i,(press_name,seat_name) in partners.items():
        pin=next(b for _,b in entries if b.name=='pin_'+str(i))
        bearing=next(b for _,b in entries if b.name=='MR52ZZ_'+str(i))
        press=max(((overlap(pin,b),path) for path,b in entries if b.name==press_name),key=lambda x:x[0])
        seat=min(((distance(bearing,b),path) for path,b in entries if b.name==seat_name),key=lambda x:x[0])
        result["pivots"].append({"index":i,"pin_press_part":press[1],"pin_press_overlap_mm3":press[0],"pin_to_bearing_mm":distance(pin,bearing),"bearing_seat":seat[1],"bearing_to_seat_contact_mm":seat[0]})
    result["all_expected_geometric_contacts"]=all(x["touching_quarter_count"]==2 for x in result["junctions"]) and all(x["pin_press_overlap_mm3"]>1e-6 and x["pin_to_bearing_mm"]<0.01 and x["bearing_to_seat_contact_mm"]<0.01 for x in result["pivots"])
    result["note"]="Use Boolean volume for press parts: MeasureManager returned uninitialized near-zero distances for overlapping solids in the initial pass; see connectivity-initial.json."
    result["scope"]="Geometric proximity/contact only; excludes fit retention, joint constraints, fastening strength and physical friction."
    with open('/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/connectivity.json','w') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
