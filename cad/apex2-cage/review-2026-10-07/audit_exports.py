from pathlib import Path
import json, struct, math, collections, hashlib
folder=Path(__file__).resolve().parent
cad=folder.parent
inventory=json.loads((folder/'model-inventory-before.json').read_text())
native={b['name']:b for c in inventory['components'] for b in c['bodyData']}
out=[]
for category in ('exports_p1b','plates_p1b'):
    for path in sorted((cad/category).glob('*.stl')):
        raw=path.read_bytes()
        n=struct.unpack_from('<I',raw,80)[0]
        if len(raw)!=84+50*n: raise ValueError('Bad binary STL length: '+str(path))
        edges=collections.Counter(); oriented=collections.Counter(); coords=[]
        volume=0.0
        for i in range(n):
            vals=struct.unpack_from('<12fH',raw,84+50*i)
            vertices=[tuple(vals[k:k+3]) for k in (3,6,9)]
            if not all(math.isfinite(v) for p in vertices for v in p): raise ValueError('Nonfinite vertex')
            coords.extend(vertices)
            a,b,c=vertices
            volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
            for u,v in zip(vertices,vertices[1:]+vertices[:1]):
                edge=tuple(sorted((u,v)));edges[edge]+=1;oriented[(u,v)]+=1
        low=[min(p[k] for p in coords) for k in range(3)]
        high=[max(p[k] for p in coords) for k in range(3)]
        size=[high[k]-low[k] for k in range(3)]
        row={"file":str(path.relative_to(cad)),"sha256":hashlib.sha256(raw).hexdigest(),"triangles":n,"min_mm":low,"max_mm":high,"size_mm":size,"boundary_edges":sum(c==1 for c in edges.values()),"nonmanifold_edges":sum(c>2 for c in edges.values()),"inconsistent_winding_edges":sum(oriented[(e[0],e[1])]!=oriented[(e[1],e[0])] for e in edges),"signed_volume_mm3":volume}
        if category=='plates_p1b':
            row['within_140mm_xy']=max(size[:2])<=140.001
            row['on_bed_z0']=abs(low[2])<0.001
        if path.stem in native:
            nb=native[path.stem]
            row['native_volume_mm3']=nb['volume_cm3']*1000
            row['relative_volume_error']=abs(volume-row['native_volume_mm3'])/row['native_volume_mm3']
            row['native_size_mm']=nb['box']['size_mm']
            row['max_size_difference_mm']=max(abs(size[k]-row['native_size_mm'][k]) for k in range(3))
        out.append(row)
manifest={"scope":"Binary STL edge incidence, winding, bounds and approximate volume; excludes self-intersection, toolpath, overhang, layer adhesion and physical fit.","results":out}
(folder/'export-audit.json').write_text(json.dumps(manifest,indent=2)+'\n')
sources={str(p.relative_to(cad)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (cad/'build_p1a.py',cad/'build_p1b.py',cad/'vendor_specs.json',cad/'measurements.json')}
(folder/'source-sha256.json').write_text(json.dumps(sources,indent=2)+'\n')
print(json.dumps({"files":len(out),"nonclosed":[r['file'] for r in out if r['boundary_edges'] or r['nonmanifold_edges'] or r['inconsistent_winding_edges']],"bad_plates":[r['file'] for r in out if r.get('within_140mm_xy') is False or r.get('on_bed_z0') is False],"largest_native_volume_error":max(r.get('relative_volume_error',0) for r in out),"largest_native_size_difference_mm":max(r.get('max_size_difference_mm',0) for r in out),"plates":[{"name":r['file'],"size":r['size_mm']} for r in out if r['file'].startswith('plates_p1b')]}))

