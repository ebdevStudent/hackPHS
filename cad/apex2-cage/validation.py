"""Geometric acceptance gates shared by both Fusion generators. All dimensions remain vendor/provisional.
Use world-coordinate BRep proxies; hidden alternative batteries are tested individually. No physical certification.
"""
import itertools, math
import adsk.core, adsk.fusion

EPS = 1e-6                         # mm^3 for unwanted intersections

def pool(occurrences):
    out=[]
    def walk(o):
        out.extend(o.bRepBodies)
        for child in o.childOccurrences: walk(child)
    for o in occurrences: walk(o)
    return out


def intersection(a,b,offset=(0,0,0)):
    tb=adsk.fusion.TemporaryBRepManager.get(); a=tb.copy(a); b=tb.copy(b)
    if any(offset):
        m=adsk.core.Matrix3D.create(); m.translation=adsk.core.Vector3D.create(*(x/10 for x in offset)); tb.transform(a,m)
    if not tb.booleanOperation(a,b,adsk.fusion.BooleanTypes.IntersectionBooleanType):
        raise RuntimeError('Validation Boolean failed')
    return a.volume*1000 if a.faces.count else 0


def gap(a,b):
    if intersection(a,b)>EPS: return 0
    return adsk.core.Application.get().measureManager.measureMinimumDistance(a,b).value*10


def assert_clear(a,b,offset=(0,0,0)):
    v=intersection(a,b,offset)
    if v>EPS: raise RuntimeError(f'{a.name} / {b.name} at offset {offset}: {v:.6f} mm3 intrusion')


def span_and_rods(bodies,p):
    structural=[b for b in bodies if b.name.startswith(('rods_', 'hub_'))]
    boxes=[b.boundingBox for b in structural]
    spans=[10*(max(getattr(b.maxPoint,a) for b in boxes)-min(getattr(b.minPoint,a) for b in boxes)) for a in 'xyz']
    if not 245-1e-5 <= max(spans) <= 250+1e-5: raise RuntimeError('Cage outside span: '+str(spans))
    if abs(p['rod_dia']-1)>1e-5: raise RuntimeError('Rod diameter differs from the adopted 1 mm baseline')
    rods={b.name:b.lumps.count for b in bodies if b.name.startswith('rods_')}
    if sum(rods.values())!=100: raise RuntimeError('Rod solids missing: '+str(rods))
    return {'outside_span_mm':spans,'rod_solids':rods}


def battery_hardware(bodies,p):
    nut_sets=[b for b in bodies if b.name.startswith('M2_nut')]
    pad=next(b for b in bodies if b.name=='BATTERY_PAD_foam')
    dx=p['adj_y'] if p.get('arm_axis')=='y' else 0
    dy=0 if dx else p['adj_y']
    result=[]
    for nuts in nut_sets:
        offsets=[(0,0),(-dx,-dy),(dx,dy)]
        if '_arm_' in nuts.name:
            offsets=[(0,0),(0,-p['adj_x']),(0,p['adj_x'])]
        for x,y in offsets:
            off=(x,y,0)
            assert_clear(nuts,pad,off)
            tb=adsk.fusion.TemporaryBRepManager.get(); moved=tb.copy(nuts);m=adsk.core.Matrix3D.create();m.translation=adsk.core.Vector3D.create(x/10,y/10,0);tb.transform(moved,m)
            for pack in ('450','1100'):
                batt=next(b for b in bodies if b.name==f'battery_{pack}mAh_PLACEHOLDER')
                assert_clear(moved,batt)
                result.append({'nuts':nuts.name,'pack':pack,'offset_mm':off,'nut_gap_mm':gap(moved,batt),'foam_gap_mm':gap(moved,pad)})
    return result


def pin_engagement(bodies,p):
    """Prove six compensated holes are coaxial and engage the full press depth.

    Selected FDM holes exceed nominal pin diameter in CAD. Native interference
    is not a valid retention test: printed coupon evidence establishes the fit.
    Missing, misaligned, shallow or wrong-diameter seats still fail this check.
    """
    names={0:'arm_pivot_block',1:'arm_pivot_block',2:'inner_junction_X_pin',
           3:'inner_junction_X_pin',4:'hub_pole_5way_pivot',5:'hub_pole_5way_pivot'}
    rows=[]
    def limits(bounds,axis):
        values=[sum(v[i]*axis[i] for i in range(3))*10 for v in itertools.product(
            (bounds.minPoint.x,bounds.maxPoint.x),(bounds.minPoint.y,bounds.maxPoint.y),
            (bounds.minPoint.z,bounds.maxPoint.z))]
        return min(values),max(values)
    for index,name in names.items():
        pin=next(b for b in bodies if b.name==f'pin_{index}')
        shaft=next(adsk.core.Cylinder.cast(f.geometry) for f in pin.faces if adsk.core.Cylinder.cast(f.geometry))
        axis=shaft.axis.asArray();origin=shaft.origin.asArray()
        assert abs(shaft.radius*20-p['pin_d'])<1e-5
        expected=p['pin_press_horizontal_d'] if name=='inner_junction_X_pin' else p['pin_press_vertical_d']
        matches=[]
        for part in (b for b in bodies if b.name==name):
            for face in part.faces:
                hole=adsk.core.Cylinder.cast(face.geometry)
                if hole is None or abs(hole.radius*20-expected)>1e-5:continue
                if abs(sum(x*y for x,y in zip(axis,hole.axis.asArray())))<.999999:continue
                delta=[x-y for x,y in zip(hole.origin.asArray(),origin)]
                along=sum(x*y for x,y in zip(delta,axis))
                radial=math.sqrt(sum((x-along*y)**2 for x,y in zip(delta,axis)))*10
                if radial>1e-4:continue
                hlo,hhi=limits(face.boundingBox,axis);plo,phi=limits(pin.boundingBox,axis)
                engagement=min(hhi,phi)-max(hlo,plo)
                if engagement>=p['pin_press_depth']-1e-4:
                    matches.append({'part':name,'diameter_mm':expected,'engagement_mm':engagement,'axis_error_mm':radial})
        if len(matches)!=1:raise RuntimeError('Missing or ambiguous compensated pin seat: '+pin.name+' '+str(matches))
        rows.append({'pin':pin.name,**matches[0]})
    return {'geometrically_engaged_seats':rows,'fit_basis':'User-reported T2 coupon fit; CAD clearance compensates FDM hole shrinkage; loaded retention remains physical'}


def bearing_engagement(bodies,p):
    """Prove all six selected bearing seats are coaxial with full axial seating."""
    names={0:'inner_junction_Y_bearing',1:'inner_junction_Y_bearing',
           2:'outer_junction_X_bearing',3:'outer_junction_X_bearing',
           4:'outer_junction_Z_bearing',5:'outer_junction_Z_bearing'}
    rows=[]
    def limits(bounds,axis):
        values=[sum(v[i]*axis[i] for i in range(3))*10 for v in itertools.product(
            (bounds.minPoint.x,bounds.maxPoint.x),(bounds.minPoint.y,bounds.maxPoint.y),
            (bounds.minPoint.z,bounds.maxPoint.z))]
        return min(values),max(values)
    for index,name in names.items():
        bearing=next(b for b in bodies if b.name==f'MR52ZZ_{index}')
        shaft=next(c for c in (adsk.core.Cylinder.cast(f.geometry) for f in bearing.faces)
                   if c and abs(c.radius*20-p['bearing_od'])<1e-5)
        axis=shaft.axis.asArray();origin=shaft.origin.asArray()
        expected=p['bearing_od']+p['bearing_seat_clear'];matches=[]
        for part in (b for b in bodies if b.name==name):
            for face in part.faces:
                hole=adsk.core.Cylinder.cast(face.geometry)
                if hole is None or abs(hole.radius*20-expected)>1e-5:continue
                if abs(sum(x*y for x,y in zip(axis,hole.axis.asArray())))<.999999:continue
                delta=[x-y for x,y in zip(hole.origin.asArray(),origin)]
                along=sum(x*y for x,y in zip(delta,axis))
                radial=math.sqrt(sum((x-along*y)**2 for x,y in zip(delta,axis)))*10
                if radial>1e-4:continue
                hlo,hhi=limits(face.boundingBox,axis);blo,bhi=limits(bearing.boundingBox,axis)
                engagement=min(hhi,bhi)-max(hlo,blo)
                if engagement>=p['bearing_w']-1e-4:
                    matches.append({'part':name,'seat_diameter_mm':expected,'engagement_mm':engagement,'axis_error_mm':radial})
        if len(matches)!=1:raise RuntimeError('Missing or ambiguous compensated bearing seat: '+bearing.name+' '+str(matches))
        rows.append({'bearing':bearing.name,**matches[0]})
    return {'geometrically_engaged_seats':rows,'fit_basis':'User-reported T2 #4 bearing fit; loaded retention remains physical'}


def static(bodies,p=None):
    # Aircraft primitives intentionally overlap each other. Check structure, props, nuts and foam separately.
    ignored=('CAMERA_VIEW','battery_','frame_plate','motors_','stack_','camera_','ANTENNA','STRAP')
    tested=[b for b in bodies if b.isVisible and not b.name.startswith(ignored)]
    press=[]
    valid={0:'arm_pivot_block',1:'arm_pivot_block',2:'inner_junction_X_pin',3:'inner_junction_X_pin',4:'hub_pole_5way_pivot',5:'hub_pole_5way_pivot'}
    for a,b in itertools.combinations(tested,2):
        if not a.boundingBox.intersects(b.boundingBox): continue
        v=intersection(a,b)
        if v<=EPS: continue
        pin=next((q for q in (a,b) if q.name.startswith('pin_')),None)
        other=b if pin is a else a
        if pin is not None and valid.get(int(pin.name.split('_')[1]))==other.name:
            press.append({'pin':pin.name,'part':other.name,'volume_mm3':v})
        else: raise RuntimeError(f'Unexpected static intersection {a.name}/{b.name}: {v:.6f} mm3')
    pins=any(b.name.startswith('pin_') for b in bodies)
    if pins and p is None:raise RuntimeError('Pin seat validation requires orientation-specific parameters')
    return {'bodies_tested':len(tested),'nominal_interference_pairs':press,'unexpected_intersections':0,
            'pin_seats':pin_engagement(bodies,p) if pins else None,
            'bearing_seats':bearing_engagement(bodies,p) if pins else None}


def radial_limits(body):
    """Continuous bounds using origin/body distance and enclosing-sphere Boolean containment.
    Rotation about any origin-centred joint preserves radial distance. Upper bound rounds outward.
    """
    tb=adsk.fusion.TemporaryBRepManager.get(); origin=adsk.core.Point3D.create(0,0,0)
    rmin=adsk.core.Application.get().measureManager.measureMinimumDistance(origin,body).value*10
    box=body.boundingBox
    hi=max(math.sqrt(x*x+y*y+z*z)*10 for x in (box.minPoint.x,box.maxPoint.x) for y in (box.minPoint.y,box.maxPoint.y) for z in (box.minPoint.z,box.maxPoint.z))+.01
    lo=0
    for _ in range(23):
        mid=(lo+hi)/2
        probe=tb.copy(body)
        if not tb.booleanOperation(probe,tb.createSphere(origin,mid/10),adsk.fusion.BooleanTypes.DifferenceBooleanType):
            raise RuntimeError('Radial containment Boolean failed')
        if probe.faces.count and probe.volume*1000>EPS: lo=mid
        else: hi=mid
    return rmin,hi+.001


def prop_support_travel(bodies,p,configuration):
    props=[b for b in bodies if b.name.startswith('PROP_DISK')]
    support_names=('support_arm_p1b','arm_pivot_block') if configuration=='p1b' else ('support_arm','x_bracket')
    supports=[b for b in bodies if b.name in support_names]
    tx,ty=(p['adj_y'],p['adj_x']) if configuration=='p1b' else (p['adj_x'],p['adj_y'])
    minimum=1e9;tests=0
    tb=adsk.fusion.TemporaryBRepManager.get()
    for off in itertools.product((-tx,tx),(-ty,ty)):
        for prop,part in itertools.product(props,supports):
            moved=tb.copy(prop);m=adsk.core.Matrix3D.create();m.translation=adsk.core.Vector3D.create(off[0]/10,off[1]/10,0);tb.transform(moved,m)
            assert_clear(moved,part);minimum=min(minimum,gap(moved,part));tests+=1
    # Prop disks and adjustable support-arm surfaces are parallel in Z. Vertical carrier/arm travel is common.
    # The pivot blocks stay fixed in Z, so cover their relative Z travel separately.
    if configuration=='p1b':
        for ox,oy,oz in itertools.product((-tx,tx),(-ty,ty),(-p['cg_slot'],p['cg_slot'])):
            for prop,part in itertools.product(props,[b for b in supports if b.name=='arm_pivot_block']):
                assert_clear(prop,part,(ox,oy,oz));tests+=1
    continuous=[]
    for prop,part,face in ((prop,part,face) for prop,part in itertools.product(props,supports) for face in part.faces):
        pb,qb=prop.boundingBox,face.boundingBox
        t=(tx,ty,p['cg_slot'] if configuration=='p1b' and part.name=='arm_pivot_block' else 0)
        distances=[]
        for i,axis in enumerate('xyz'):
            lo=getattr(pb.minPoint,axis)*10-t[i];hi=getattr(pb.maxPoint,axis)*10+t[i]
            qlo=getattr(qb.minPoint,axis)*10;qhi=getattr(qb.maxPoint,axis)*10
            distances.append(max(qlo-hi,lo-qhi,0))
        if max(distances)<=.01:
            raise RuntimeError('No continuous AABB separation for prop/support travel: '+part.name)
        continuous.append(max(distances))
    return {'tests':tests,'minimum_sampled_support_gap_mm':minimum,
            'continuous_face_AABB_separation_min_mm':min(continuous),'continuous_scope':'Each support boundary face is outside every expanded prop box. Nominal props are outside supports, so no continuous translated prop can enter. Arms share vertical movement, pivot blocks do not.'}


def validate_fixed(design,p,occ):
    bodies=pool(occ)
    cage=[b for b in bodies if b.name.startswith(('rods_','hub_'))]
    cage_min=min(adsk.core.Application.get().measureManager.measureMinimumDistance(adsk.core.Point3D.create(0,0,0),b).value*10 for b in cage)
    tip=math.hypot(p['motor_diag']/2/math.sqrt(2)+p['adj_x'],p['motor_diag']/2/math.sqrt(2)+p['adj_y'])+p['prop_dia']/2
    bound=math.hypot(tip,p['prop_z']+p['prop_disk_h'])
    if cage_min-bound<=.01:raise RuntimeError('Fixed-cage continuous prop bound failed')
    return {'cage':span_and_rods(bodies,p),'static':static(bodies,p),'battery_hardware':battery_hardware(bodies,p),
            'prop_support_travel':prop_support_travel(bodies,p,'p1a'),
            'continuous_prop_to_cage_lower_bound_mm':cage_min-bound,
            'physical_pending':'Strap routing/closure, battery removal, wires, antenna retention, material strength, mass and thrust require delivered parts.'}


def validate_gimbal(design,p,groups,report,dz):
    h=__file__.rsplit('/',1)[0]; scope={'__file__':h+'/build_p1b.py'}
    exec(compile(open(scope['__file__']).read(),scope['__file__'],'exec'),scope)
    s=scope['A']['Solids'](); bodies=pool(groups.values())
    radial={key:radial_limits(scope['group_temp'](s,groups[key])) for key in ('cage','outer','inner')}
    clearances={'inner_to_outer_mm':radial['outer'][0]-radial['inner'][1],
                'outer_to_cage_mm':radial['cage'][0]-radial['outer'][1],
                'props_to_inner_mm':radial['inner'][0]-scope['aircraft_radius'](p,dz)}
    if min(clearances.values())<=.01: raise RuntimeError('Continuous radial clearance failed: '+str(clearances))
    if not report['cg']['within_cg_slot']: raise RuntimeError('Estimated CG shift exceeds vertical slots')
    return {'cage':span_and_rods(bodies,p),'static':static(bodies,p),'battery_hardware':battery_hardware(bodies,p),
            'prop_support_travel':prop_support_travel(bodies,p,'p1b'),'continuous_radial_bounds_mm':radial,
            'continuous_radial_clearances_mm':clearances,'scope':'Origin-centred rigid CAD bodies, excluding coaxial pins/bearings; nominal material dimensions; no wires/flex.',
            'physical_pending':'Strap routing/closure, battery removal, wires, antenna retention, full aircraft fit, strength, mass and thrust require delivered parts.'}


def validate_materials(design):
    wrong=[];envelope_mass=0;fixture_mass=0
    for c in design.allComponents:
        fixture=c.name in ('Socket fit strip (print first)','Rod cutting jig','Gimbal test fixtures')
        for b in c.bRepBodies:
            if fixture or b.name.startswith(('PROP_DISK','CAMERA_VIEW','battery_','frame_plate','motors_','stack_','camera_','ANTENNA','BATTERY_PAD','M2_nut','HUB_ENVELOPE')):
                if b.material.name!='Analysis envelope (massless)':wrong.append(c.name+'/'+b.name)
                if fixture:fixture_mass+=b.physicalProperties.mass*1000
                else:envelope_mass+=b.physicalProperties.mass*1000
        for b in c.meshBodies:
            if 'original, 3 mm rod' in c.name and b.material.name!='Analysis envelope (massless)':wrong.append(b.name)
    if wrong:raise RuntimeError('Non-aircraft bodies contribute mass: '+str(wrong))
    if envelope_mass>.01 or fixture_mass>.001:raise RuntimeError('Near-massless density exceeds audit allowance')
    return {'analysis_native_mass_g':envelope_mass,'fixtures_native_mass_g':fixture_mass,'reference_meshes_massless':True}
