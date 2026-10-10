import adsk.core, adsk.fusion, json, os
def run(_context: str):
    app=adsk.core.Application.get()
    doc=app.activeDocument
    d=adsk.fusion.Design.cast(app.activeProduct)
    def box(b):
        q=b.boundingBox
        lo=q.minPoint; hi=q.maxPoint
        return {"min_mm":[round(lo.x*10,4),round(lo.y*10,4),round(lo.z*10,4)],"max_mm":[round(hi.x*10,4),round(hi.y*10,4),round(hi.z*10,4)],"size_mm":[round((hi.x-lo.x)*10,4),round((hi.y-lo.y)*10,4),round((hi.z-lo.z)*10,4)]}
    out={"document":doc.name,"modified":doc.isModified,"designType":int(d.designType),"version":doc.dataFile.versionNumber if doc.dataFile else None,"root":d.rootComponent.name,"components":[],"occurrences":[],"parameters":[],"timeline":[]}
    for p in d.userParameters:
        out["parameters"].append({"name":p.name,"expression":p.expression,"value":p.value,"unit":p.unit,"comment":p.comment})
    for c in d.allComponents:
        row={"name":c.name,"bodies":c.bRepBodies.count,"meshBodies":c.meshBodies.count,"sketches":c.sketches.count,"joints":c.joints.count,"asBuiltJoints":c.asBuiltJoints.count,"rigidGroups":c.rigidGroups.count,"bodyData":[],"sketchData":[],"attributes":[]}
        for a in c.attributes:
            row["attributes"].append({"group":a.groupName,"name":a.name,"value":a.value})
        for b in c.bRepBodies:
            row["bodyData"].append({"name":b.name,"solid":b.isSolid,"visible":b.isVisible,"lumps":b.lumps.count,"faces":b.faces.count,"volume_cm3":round(b.volume,6),"material":b.material.name if b.material else None,"box":box(b)})
        for s in c.sketches:
            row["sketchData"].append({"name":s.name,"visible":s.isVisible,"fullyConstrained":s.isFullyConstrained,"curves":s.sketchCurves.count,"profiles":s.profiles.count})
        out["components"].append(row)
    for o in d.rootComponent.allOccurrences:
        out["occurrences"].append({"path":o.fullPathName,"visible":o.isVisible,"grounded":o.isGrounded,"referenced":o.isReferencedComponent,"component":o.component.name,"transform":o.transform2.asArray()})
    if d.timeline:
        for i in range(d.timeline.count):
            t=d.timeline.item(i)
            if t.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
                out["timeline"].append({"index":i,"name":t.name,"health":int(t.healthState),"message":t.errorOrWarningMessage})
        out["timelineCount"]=d.timeline.count
        out["timelineMarker"]=d.timeline.markerPosition
    print(json.dumps(out))

