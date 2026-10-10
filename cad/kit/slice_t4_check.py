"""Offline FlashPrint engine bed-fit check; never sends a job to a printer.

Run with system Python. Output is diagnostic G-code with generic engine startup,
not a Voxel print file. Slice the checked STL in FlashPrint before printing.
"""
import configparser
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / 'cad/kit/reports'
ENGINE = Path('/Applications/FlashPrint-MP.app/Contents/MacOS/engine')
STL = ROOT / 'cad/apex2-cage/print_now/T4_carrier_and_arms_checked.stl'


def check(stl=STL, label='T4', expected_parts=4, layer_height='.20', solid_layers='4', max_height=16.01,
          reports=REPORTS, image_dir=None, min_edge_margin=7):
    tag=label.lower()
    config = configparser.ConfigParser(inline_comment_prefixes=('#',))
    config.optionxform = str
    config.read_string('[global]\n' + (ENGINE/'default.cfg').read_text())
    updates = {
        'global': {'layerHeight':'.20', 'firstLayerHeight':'.27',
                   'baseSpeed':'35', 'travelSpeed':'100', 'rightTemp':'235',
                   'leftTemp':'235', 'platTemp':'60'},
        'shell': {'count':'3'},
        'infill': {'topSolidCnt':'4', 'bottomSolidCnt':'4', 'density':'.25'},
        'preExtrude': {'length':'60'},
        'retract': {'length':'1.5', 'speed':'30'},
        'brim': {'enable':'true', 'extruderId':'0', 'margin':'5',
                 'layerCnt':'1', 'speed':'8.75'},
        'speed': {'firstLayerMax':'10'},
        'fan': {'state':'toPresetHeight', 'turnOnHeight':'.6'},
    }
    updates['global']['layerHeight']=layer_height
    updates['infill'].update(topSolidCnt=solid_layers,bottomSolidCnt=solid_layers)
    for section, values in updates.items():
        config[section].update(values)
    stream = io.StringIO()
    config.write(stream)
    reports.mkdir(parents=True, exist_ok=True)
    cfg = reports/f'{tag}-diagnostic.cfg'
    cfg.write_text(stream.getvalue().replace('[global]\n','',1))
    gcode = reports/f'{tag}-diagnostic-only.g'
    result = subprocess.run([
        str(ENGINE/'ffslicer.exe'), '--config', str(cfg),
        '--maxsize', '150x150x150', '--model',
        f'file:{stl}*format:stl*extruder:0*type:model', '--gcode', str(gcode)
    ], capture_output=True, text=True, check=True)
    (reports/f'{tag}-diagnostic-engine.log').write_text(result.stdout+result.stderr)
    assert gcode.is_file() and gcode.stat().st_size > 10000
    position = dict(X=0.,Y=0.,Z=0.,E=0.,F=0.)
    segments = []
    layer = 0
    category = 'startup'
    shell_group = -1
    first_layer_groups = {}
    for line in gcode.read_text().splitlines():
        if line.startswith(';layer:'):
            layer += 1
        if line in (';brim',';shell',';infill') or line.startswith(';preExtrude:'):
            category = line[1:].split(':')[0]
            if line == ';shell' and layer == 1:
                shell_group += 1
        if line.startswith('G92 '):
            for key, value in re.findall(r'([XYZE])([-+.\d]+)', line):
                position[key] = float(value)
        if not line.startswith('G1 '):
            continue
        old = position.copy()
        for key, value in re.findall(r'([XYZEF])([-+.\d]+)', line):
            position[key] = float(value)
        xy_move = abs(position['X']-old['X'])+abs(position['Y']-old['Y']) > 1e-6
        if position['E'] > old['E']+1e-7 and xy_move:
            assert abs(position['Z']-old['Z']) < 1e-6
            segment = [old['X'],old['Y'],position['X'],position['Y'],position['Z'],
                       layer,category,position['F']/60]
            segments.append(segment)
            if layer == 1 and category in ('shell','infill'):
                first_layer_groups.setdefault(shell_group,[]).append(segment)
    assert len(first_layer_groups) == expected_parts, 'A first-layer part is missing'
    assert all(len(v)>10 for v in first_layer_groups.values())
    xs=[s[i] for s in segments for i in (0,2)]
    ys=[s[i] for s in segments for i in (1,3)]
    bounds=[min(xs),min(ys),max(xs),max(ys)]
    # The purge is wider than normal paths: conservatively apply its half-width
    # to every endpoint. Straight path extrema occur at their endpoints.
    allowance = .8
    margins=[75+bounds[0]-allowance,75-bounds[2]-allowance,
             75+bounds[1]-allowance,75-bounds[3]-allowance]
    assert min(margins)>min_edge_margin, 'An extrusion path is too close to the bed edge'
    assert max(s[4] for s in segments)<=max_height
    brim=[s for s in segments if s[6]=='brim']
    assert len(brim)>100 and all(s[5]==1 for s in brim)
    assert max(s[7] for s in brim)<=10.01
    assert all(s[7]<=10.01 for s in segments if s[5]==1)
    report={
        'stl_sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),
        'engine':'FlashPrint bundled ffslicer 1.14.1',
        'scope':'Offline diagnostic bed-fit slicing; not a Voxel print-ready job',
        'config_overrides':updates,
        'extrusion_centerline_bounds_xy_mm':bounds,
        'conservative_line_halfwidth_mm':allowance,
        'edge_margins_left_right_front_back_mm':margins,
        'first_layer_part_count':len(first_layer_groups),
        'first_layer_part_extrusion_segment_counts':[len(v) for v in first_layer_groups.values()],
        'extrusion_segment_count':len(segments),
        'layer_count':layer, 'brim_first_layer_only':True,
        'max_first_layer_speed_mm_s':max(s[7] for s in segments if s[5]==1),
        'checks':{'engine_exit_success':True,'all_expected_parts_on_first_layer':True,
                  'all_extrusion_paths_with_line_width_inside_bed':True,
                  'first_layer_and_brim_speed_at_most_10':True},
    }
    (reports/f'{tag}-slice-check-2026-10-09.json').write_text(json.dumps(report,indent=2)+'\n')
    # Draw actual first-layer G-code paths, not a guessed brim envelope.
    from PIL import Image,ImageDraw
    im=Image.new('RGB',(980,1030),'#f7f9fc');d=ImageDraw.Draw(im)
    origin=(60,65);scale=5.7
    def point(x,y):return (origin[0]+(x+75)*scale,origin[1]+(75-y)*scale)
    d.rectangle([point(-75,75),point(75,-75)],fill='#e8eef6',outline='#34445c',width=3)
    for v in range(-65,75,10):
        d.line([point(v,-75),point(v,75)],fill='#cbd5e1')
        d.line([point(-75,v),point(75,v)],fill='#cbd5e1')
    colors={'brim':'#846ad3','shell':'#133b59','infill':'#328589','preExtrude':'#cf652a'}
    for s in segments:
        if s[5]==1 or s[6]=='preExtrude':
            d.line([point(s[0],s[1]),point(s[2],s[3])],fill=colors[s[6]],width=1)
    d.text((60,20),label+' - actual first-layer paths on the 150 x 150 mm Voxel bed',fill='#142941')
    d.text((60,945),'Purple: brim   Dark: outlines   Teal: infill   Orange: purge',fill='#142941')
    d.text((60,974),f'All {expected_parts} parts present. Conservative minimum edge clearance: '+f'{min(margins):.1f} mm.',fill='#142941')
    image_dir = image_dir or ROOT/'cad/apex2-cage/print_now'
    image_dir.mkdir(parents=True, exist_ok=True)
    im.save(image_dir/f'{label}_sliced_first_layer.png')
    return report


if __name__ == '__main__':
    print(json.dumps(check(),indent=2))
