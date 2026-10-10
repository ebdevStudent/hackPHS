"""Printable test pieces for the representative rod/hub section test and pin cutting.

Every interface comes from the generator parameters (cad/apex2-cage via cage_model):
  bend_test_block      x2  hub-arm socket (arm OD, bore = rod + 2 x clearance, depth) on a clamp block
  bend_test_jig        x1  holds both blocks so the exposed rod span equals the cage's (edge - 2 x arm length),
                           with a 0.5 mm deflection scale at mid-span and a slot for the load string
  load_hook            x1  hangs on the rod at mid-span; carries a cup or weights on a string
  pin_cut_gauge        x1  blind holes at the P1B pin length (press depth + gap + bearing + 1.5 mm) and 16 mm stock
STLs are written to test-pieces/ with a manifest of the parameters used. Print in PETG at the same
settings as the hubs. These pieces test joints; they are not cage parts.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import manifold3d as mf
import numpy as np

import cage_model

SEGMENTS = 64
CHANNEL_FLOOR = 1.5     # mm above the bed under the rod (the pockets keep a 4 mm floor)
OUT = Path(__file__).resolve().parent / 'test-pieces'


def box(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))


def cylinder_x(x0, x1, y, z, diameter):
    return mf.Manifold.cylinder(x1 - x0, diameter / 2, diameter / 2, SEGMENTS).rotate((0, 90, 0)).translate((x0, y, z))


def cylinder_z(x, y, z0, z1, diameter):
    return mf.Manifold.cylinder(z1 - z0, diameter / 2, diameter / 2, SEGMENTS).translate((x, y, z0))


def cylinder_y(x, y0, y1, z, diameter):
    return mf.Manifold.cylinder(y1 - y0, diameter / 2, diameter / 2, SEGMENTS).rotate((-90, 0, 0)).translate((x, y0, z))


def dimensions(values, p1b):
    block = {'length': 12.0, 'width': 10.0, 'height': 9.0}
    axis_z = 6.0
    arm_out = values['hub_arm_len'] - 2.0      # arm length beyond the block face; the hub core supplies the rest
    span = values['cage_edge'] - 2 * values['hub_arm_len']
    pin_cut = p1b['pin_press_depth'] + p1b['pivot_gap'] + p1b['bearing_w'] + 1.5
    return block, axis_z, arm_out, span, pin_cut


def bend_test_block(values, block, axis_z, arm_out):
    """Clamp block (bed face down) with a horizontal hub arm and keel, socket opening at +X."""
    body = box((0, 0, 0), (block['length'], block['width'], block['height']))
    y = block['width'] / 2
    tip = block['length'] + arm_out
    body = body + cylinder_x(block['length'] - 1, tip, y, axis_z, values['hub_arm_od'])
    body = body + box((block['length'] - 1, y - values['hub_keel_w'] / 2, 0), (tip, y + values['hub_keel_w'] / 2, axis_z))
    bore = values['rod_dia'] + 2 * values['rod_bore_clear']
    body = body - cylinder_x(tip - values['socket_depth'], tip + 1, y, axis_z, bore)
    return body, tip


def bend_test_jig(values, block, axis_z, arm_out, span, clearance=0.3):
    """Two pockets facing each other; arm tips span apart. Deflection scale post beside mid-span."""
    base_t, wall = 4.0, 3.0
    pocket_l, pocket_w = block['length'] + 2 * clearance, block['width'] + 2 * clearance
    tip_gap = span
    left_face = 0.0                                   # inner end of the left pocket (arm side)
    length = 2 * (pocket_l + wall) + 2 * arm_out + tip_gap
    width = pocket_w + 2 * wall + 14
    body = box((0, 0, 0), (length, width, base_t + 6))
    y0 = wall
    left = (wall, y0)
    right_x = length - wall - pocket_l
    for x in (left[0], right_x):
        body = body - box((x, y0, base_t), (x + pocket_l, y0 + pocket_w, base_t + 7))
    # Clear the arms and rod path between the pockets (rod axis at base_t + axis_z)
    channel_x0, channel_x1 = left[0] + pocket_l, right_x
    # The channel is cut deeper than the pockets so the rod can deflect and the load hook hangs clear.
    body = body - box((channel_x0, y0, CHANNEL_FLOOR), (channel_x1, y0 + pocket_w, base_t + 7))
    # Load string slot through the base under mid-span
    mid = (channel_x0 + channel_x1) / 2
    body = body - box((mid - 4, y0 + pocket_w / 2 - 1.5, -1), (mid + 4, y0 + pocket_w / 2 + 1.5, base_t + 1))
    # Deflection scale post at mid-span, beside the rod: grooves every 0.5 mm, deeper every 1 mm,
    # from the rod axis down 8 mm. Read the rod against it with a magnifier or a macro photo.
    # The scale is engraved in the channel's side wall (facing the rod) and a post continuing it above
    # the base top, so every groove opens onto a visible face.
    post_y0 = y0 + pocket_w
    rod_z = base_t + axis_z                         # blocks sit on the pocket floor
    post = box((mid - 3, post_y0, base_t + 6 - 0.01), (mid + 3, post_y0 + 4, rod_z + 3))
    body = body + post
    for k in range(0, 17):
        z = rod_z + 2 - k * 0.5
        if z <= CHANNEL_FLOOR + 0.5: break
        depth = 1.2 if k % 4 == 0 else 0.6          # deep groove every 2 mm, starting 2 mm above the rod axis
        body = body - box((mid - 2.5, post_y0 - 0.01, z - 0.1), (mid + 2.5, post_y0 + depth, z + 0.1))
    # Blocks pushed toward the middle (against the inner pocket ends) give the cage span exactly;
    # pushed outward, the pocket clearance adds 2 x clearance.
    inward = (left[0] + pocket_l + arm_out, right_x - arm_out)
    return body, {'tip_gap_pushed_inward_mm': round(inward[1] - inward[0], 3),
                  'tip_gap_pushed_outward_mm': round(inward[1] - inward[0] + 2 * clearance, 3),
                  'rod_axis_height_mm': round(rod_z, 3),
                  'scale_step_mm': 0.5, 'deep_groove_every_mm': 2.0, 'jig_length_mm': round(length, 2)}


HOOK = {'thick': 2.0, 'width': 5.0, 'height': 6.0, 'rod_z': 4.5, 'string_z': 1.6}


def load_hook(values):
    """Small tab threaded on the rod at mid-span (rod along its 2 mm thickness, X); a string through the
    lower hole drops through the jig's slot to a cup. Short, so it hangs clear of the channel floor."""
    tab = box((0, 0, 0), (HOOK['thick'], HOOK['width'], HOOK['height']))
    tab = tab - cylinder_x(-1, HOOK['thick'] + 1, HOOK['width'] / 2, HOOK['rod_z'], values['rod_dia'] + 0.6)
    tab = tab - cylinder_x(-1, HOOK['thick'] + 1, HOOK['width'] / 2, HOOK['string_z'], 1.6)
    return tab


def pin_cut_gauge(pin_cut, pin_len, pin_d):
    """Blind holes: drop the pin in, mark or cut flush with the top face."""
    height = max(pin_cut, pin_len) + 2
    body = box((0, 0, 0), (24, 10, height))
    hole = pin_d + 0.1
    body = body - cylinder_z(6, 5, height - pin_cut, height + 1, hole)
    body = body - cylinder_z(18, 5, height - pin_len, height + 1, hole)
    # one dimple marks the cut-length hole, two the full-length reference
    for k, x in enumerate((6, 16.5, 19.5)):
        body = body - cylinder_y(x, -1, 0.6, height - 3, 1.2)
    return body, height


def read_mesh_stl(path):
    """Triangles (N, 3, 3) from a binary STL."""
    data = Path(path).read_bytes()
    count = struct.unpack('<I', data[80:84])[0]
    if len(data) != 84 + 50 * count: raise ValueError('Not a binary STL: ' + str(path))
    return np.frombuffer(data[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))['v'].reshape(-1, 3, 3).astype(float)


def write_stl(manifold, path):
    mesh = manifold.to_mesh()
    vertices = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    triangles = vertices[np.asarray(mesh.tri_verts)]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    record = np.zeros(len(triangles), dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    record['n'], record['v'] = normals, triangles.reshape(-1, 9)
    path.write_bytes(b'Ball Drone test piece'.ljust(80, b' ') + struct.pack('<I', len(triangles)) + record.tobytes())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output=OUT, measurements=None):
    values = cage_model.parameters('p1a', measurements)
    p1b = cage_model.parameters('p1b', measurements)
    block, axis_z, arm_out, span, pin_cut = dimensions(values, p1b)
    parts = {}
    parts['bend_test_block'], tip = bend_test_block(values, block, axis_z, arm_out)
    parts['bend_test_jig'], jig_info = bend_test_jig(values, block, axis_z, arm_out, span)
    parts['load_hook'] = load_hook(values)
    parts['pin_cut_gauge'], gauge_h = pin_cut_gauge(pin_cut, p1b['pin_len'], p1b['pin_d'])
    output.mkdir(parents=True, exist_ok=True)
    quantities = {'bend_test_block': 2, 'bend_test_jig': 1, 'load_hook': 1, 'pin_cut_gauge': 1}
    manifest = {'source': 'cad/kit/test_pieces.py (read-only use of cad/apex2-cage generator parameters)',
                'parameters': {k: round(values[k], 4) for k in ('rod_dia', 'rod_bore_clear', 'hub_arm_od', 'hub_arm_len',
                                                                'hub_keel_w', 'socket_depth', 'cage_edge', 'rod_cut_len')},
                'exposed_rod_span_mm': round(span, 3), 'rod_cut_for_test_mm': round(values['rod_cut_len'], 3),
                'pin_cut_length_mm': round(pin_cut, 2), 'jig': jig_info, 'parts': []}
    for name, part in parts.items():
        pieces = part.decompose()
        bounds = part.bounding_box()
        sha = write_stl(part, output / f'{name}.stl')
        manifest['parts'].append({'name': name, 'qty': quantities[name], 'volume_mm3': round(part.volume(), 2),
                                  'mass_g_solid_petg': round(part.volume() / 1000 * values['petg_density'], 2),
                                  'bodies': len(pieces), 'genus': part.genus(),
                                  'size_mm': [round(bounds[i + 3] - bounds[i], 2) for i in range(3)], 'sha256': sha})
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', type=Path, default=OUT)
    print(json.dumps(build(parser.parse_args().output), indent=2))
