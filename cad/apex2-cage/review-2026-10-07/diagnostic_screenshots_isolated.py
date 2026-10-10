import adsk.core, adsk.fusion, json, math, os
def run(_context: str):
    app=adsk.core.Application.get()
    d=adsk.fusion.Design.cast(app.activeProduct)
    v=app.activeViewport
    original_camera=v.camera
    before=app.activeDocument.isModified
    tbm=adsk.fusion.TemporaryBRepManager.get()
    outdir='/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07'
    allb=[(o,b) for o in d.rootComponent.allOccurrences for b in o.bRepBodies]
    props=[b for o,b in allb if b.name.startswith('PROP_DISK')]
    inner=[b for o,b in allb if o.fullPathName.startswith('Inner ring')]
    outer=[b for o,b in allb if o.fullPathName.startswith('Outer ring')]
    offset=adsk.core.Matrix3D.create()
    offset.translation=adsk.core.Vector3D.create(40,40,0)
    groups=[]
    def draw(group,body,color,opacity=1):
        b=tbm.copy(body)
        tbm.transform(b,offset)
        g=group.addBRepBody(b)
        g.color=adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(*color,255))
        g.setOpacity(opacity,True)
        g.isSelectable=False
        if color == (255,35,35): g.depthPriority=10
    def camera(target,eye,up,extent):
        c=adsk.core.Camera.create()
        c.cameraType=adsk.core.CameraTypes.OrthographicCameraType
        c.eye=adsk.core.Point3D.create(*eye)
        c.target=adsk.core.Point3D.create(*target)
        c.upVector=adsk.core.Vector3D.create(*up)
        c.isSmoothTransition=False
        c.isFitView=False
        c.setExtents(extent,extent)
        v.camera=c
        v.refresh()
    def snap(name):
        options=adsk.core.SaveImageFileOptions.create(os.path.join(outdir,name))
        options.width=1600; options.height=1400
        options.isBackgroundTransparent=False; options.isAntiAliased=True
        if not v.saveAsImageFileWithOptions(options): raise RuntimeError('Screenshot failed')
    overlaps=[]
    try:
        group=d.rootComponent.customGraphicsGroups.add()
        groups.append(group)
        for b in inner: draw(group,b,(70,205,240),0.7)
        move=adsk.core.Matrix3D.create()
        move.translation=adsk.core.Vector3D.create(0.4,0.5,0)
        rot=adsk.core.Matrix3D.create()
        rot.setToRotation(math.radians(-15),adsk.core.Vector3D.create(1,0,0),adsk.core.Point3D.create(0,0,0))
        for b in props:
            p=tbm.copy(b)
            tbm.transform(p,move); tbm.transform(p,rot)
            draw(group,p,(255,190,65),0.45)
            for rb in inner:
                hit=tbm.copy(p)
                if not tbm.booleanOperation(hit,tbm.copy(rb),adsk.fusion.BooleanTypes.IntersectionBooleanType): raise RuntimeError('Intersection failed')
                if hit.faces.count and hit.volume*1000>1e-6:
                    overlaps.append({"prop":b.name,"ring":rb.assemblyContext.fullPathName,"volume_mm3":round(hit.volume*1000,6)})
                    draw(group,hit,(255,35,35),1)
        camera((40,40,0),(45,24,22),(0,0,1),20)
        snap('02-adjusted-prop-collision-overview-isolated.png')
        camera((45.4,45.7,0),(45.4,45.7,20),(0,1,0),4.5)
        snap('03-adjusted-prop-collision-detail-isolated.png')
        group.deleteMe(); groups.remove(group)
        group=d.rootComponent.customGraphicsGroups.add()
        groups.append(group)
        for b in outer: draw(group,b,(70,205,240),0.8)
        cam=next(b for o,b in allb if b.name=='camera_PLACEHOLDER')
        draw(group,cam,(255,190,65),1)
        bb=cam.boundingBox
        apex=adsk.core.Point3D.create(0,bb.maxPoint.y,(bb.minPoint.z+bb.maxPoint.z)/2)
        t=d.userParameters.itemByName('cam_tilt').value
        end=adsk.core.Point3D.create(0,apex.y+math.cos(t)*15,apex.z+math.sin(t)*15)
        ray=tbm.createCylinderOrCone(apex,0.03,end,0.03)
        draw(group,ray,(255,220,40),1)
        for b in outer:
            hit=tbm.copy(b)
            if not tbm.booleanOperation(hit,tbm.copy(ray),adsk.fusion.BooleanTypes.IntersectionBooleanType): raise RuntimeError('Ray intersection failed')
            if hit.faces.count and hit.volume>1e-10: draw(group,hit,(255,35,35),1)
        camera((40,44.5,0),(65,44.5,0),(0,0,1),24)
        snap('04-camera-centerline-obstruction-isolated.png')
    finally:
        for group in groups: group.deleteMe()
        v.camera=original_camera
        v.refresh()
    print(json.dumps({"overlaps":overlaps,"documentModifiedBefore":before,"documentModifiedAfter":app.activeDocument.isModified,"customGraphicsRemaining":d.rootComponent.customGraphicsGroups.count,"screenshots":["02-adjusted-prop-collision-overview-isolated.png","03-adjusted-prop-collision-detail-isolated.png","04-camera-centerline-obstruction-isolated.png"],"note":"Diagnostic copies of current BRep geometry, temporarily drawn 400 mm in X and Y away from the assembly; original model unchanged. Yellow camera ray is thickened to 0.6 mm only for legibility."}))

