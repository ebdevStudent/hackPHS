import adsk.core, adsk.fusion, math, json, os
def run(_context: str):
    app=adsk.core.Application.get(); d=adsk.fusion.Design.cast(app.activeProduct); v=app.activeViewport
    tbm=adsk.fusion.TemporaryBRepManager.get()
    allb=[(o,b) for o in d.rootComponent.allOccurrences for b in o.bRepBodies]
    prop=next(b for o,b in allb if b.name=='PROP_DISK_FR_keepout')
    ring=next(b for o,b in allb if o.fullPathName=='Inner ring (Y to outer, X to aircraft):1+inner_ring_quarter:1')
    hit=tbm.copy(prop)
    move=adsk.core.Matrix3D.create(); move.translation=adsk.core.Vector3D.create(0.4,0.5,0)
    tbm.transform(hit,move)
    rot=adsk.core.Matrix3D.create()
    rot.setToRotation(math.radians(-15),adsk.core.Vector3D.create(1,0,0),adsk.core.Point3D.create(0,0,0))
    tbm.transform(hit,rot)
    if not tbm.booleanOperation(hit,tbm.copy(ring),adsk.fusion.BooleanTypes.IntersectionBooleanType): raise RuntimeError('Intersection failed')
    volume=hit.volume*1000
    offset=adsk.core.Matrix3D.create();offset.translation=adsk.core.Vector3D.create(40,40,0)
    tbm.transform(hit,offset)
    group=d.rootComponent.customGraphicsGroups.add()
    original=v.camera
    try:
        g=group.addBRepBody(hit)
        g.color=adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(255,40,40,255))
        box=hit.boundingBox
        target=adsk.core.Point3D.create((box.minPoint.x+box.maxPoint.x)/2,(box.minPoint.y+box.maxPoint.y)/2,0)
        c=adsk.core.Camera.create();c.cameraType=adsk.core.CameraTypes.OrthographicCameraType
        c.eye=adsk.core.Point3D.create(target.x+2,target.y-2,5);c.target=target;c.upVector=adsk.core.Vector3D.create(0,0,1)
        c.isFitView=False;c.isSmoothTransition=False;c.setExtents(2.8,2.8);v.camera=c;v.refresh()
        f='/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/05-collision-intersection-witness.png'
        if not v.saveAsImageFile(f,1600,1400):raise RuntimeError('Screenshot failed')
        print(json.dumps({"intersection_volume_mm3":volume,"file":f}))
    finally:
        group.deleteMe();v.camera=original;v.refresh()

