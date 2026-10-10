import adsk.core,adsk.fusion,json,math

def run(context):
 app=adsk.core.Application.get();d=adsk.fusion.Design.cast(app.activeProduct);v=app.activeViewport
 tb=adsk.fusion.TemporaryBRepManager.get();pool=[b for o in d.rootComponent.allOccurrences for b in o.bRepBodies]
 pad=next(b for b in pool if b.name=='BATTERY_PAD_foam'); nuts=tb.copy(next(b for b in pool if b.name.startswith('M2_nut')))
 m=adsk.core.Matrix3D.create();m.translation=adsk.core.Vector3D.create(.2,0,0);tb.transform(nuts,m)
 hit=tb.copy(nuts);assert tb.booleanOperation(hit,tb.copy(pad),adsk.fusion.BooleanTypes.IntersectionBooleanType)
 print('Witness volume mm3:',hit.volume*1000)
 saved=v.camera;g=d.rootComponent.customGraphicsGroups.add()
 try:
  for body,color,op in [(pad,(65,190,240),1),(nuts,(255,190,45),1),(hit,(255,35,35),1)]:
   b=tb.copy(body);m.translation=adsk.core.Vector3D.create(40,40,0);tb.transform(b,m)
   item=g.addBRepBody(b);item.color=adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(*color,255));item.setOpacity(op,False)
  c=adsk.core.Camera.create();c.cameraType=adsk.core.CameraTypes.OrthographicCameraType;c.target=adsk.core.Point3D.create(40,40,-.32);c.eye=adsk.core.Point3D.create(40,40,20);c.upVector=adsk.core.Vector3D.create(0,1,0);c.isSmoothTransition=False;c.isFitView=False;c.setExtents(8,8);v.camera=c;v.refresh();adsk.doEvents()
  opts=adsk.core.SaveImageFileOptions.create('/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-08/02-pad-nut-witness-retry.png');opts.width=1600;opts.height=1200;opts.isBackgroundTransparent=False
  assert v.saveAsImageFileWithOptions(opts)
 finally:
  g.deleteMe();v.camera=saved;v.refresh()
