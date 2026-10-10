"""Read-only access to the Apex-2 cage generators outside Fusion.

The generators (cad/apex2-cage/build_p1a.py, build_p1b.py) are the single source of the cage design.
This module loads them with a stand-in `adsk` package, reads their parameter tables and pure-geometry
functions, and resolves parameter expressions exactly in the order Fusion would: generator defaults,
then vendor_specs.json, then measurements.json, then the P1B overrides when asked. Nothing is written.
"""
import json
import math
import re
import sys
import types
from pathlib import Path

CAGE_DIR = Path(__file__).resolve().parents[1] / 'apex2-cage'


class _Anything:
    """Absorbs any attribute access or call made at generator import time."""
    def __getattr__(self, name): return _Anything()
    def __call__(self, *args, **kwargs): return _Anything()


def _stub_adsk():
    adsk = types.ModuleType('adsk')
    adsk.core, adsk.fusion = _Anything(), _Anything()
    return {'adsk': adsk, 'adsk.core': adsk.core, 'adsk.fusion': adsk.fusion}


def load_generator(name):
    """Execute a generator module with the stub and return its namespace (no Fusion calls are made)."""
    saved = {key: sys.modules.get(key) for key in ('adsk', 'adsk.core', 'adsk.fusion')}
    sys.modules.update(_stub_adsk())
    try:
        path = CAGE_DIR / name
        namespace = {'__name__': name.removesuffix('.py'), '__file__': str(path)}
        exec(compile(path.read_text(), str(path), 'exec'), namespace)
        return namespace
    finally:
        for key, module in saved.items():
            if module is None: sys.modules.pop(key, None)
            else: sys.modules[key] = module


UNIT = re.compile(r'(\d+(?:\.\d+)?)\s*(mm|deg)\b')


def evaluate(expression, values):
    """Evaluate a Fusion parameter expression. Lengths in mm, angles in radians."""
    text = UNIT.sub(lambda m: f'({m.group(1)}*{"1" if m.group(2) == "mm" else "_deg"})', expression)
    text = re.sub(r'(?<![\w.])(mm)(?![\w])', '', text).replace('^', '**')
    scope = {'sin': math.sin, 'cos': math.cos, 'tan': math.tan, 'sqrt': math.sqrt, '_deg': math.pi / 180, **values}
    return float(eval(text, {'__builtins__': {}}, scope))


def overrides(file_name):
    path = CAGE_DIR / file_name
    if not path.exists(): return {}, {}
    data = json.loads(path.read_text())
    params = {k: v for k, v in (data.get('parameters') or {}).items() if v not in (None, '')}
    masses = {k: v for k, v in (data.get('masses_g') or {}).items() if v not in (None, '')}
    return params, masses


def parameters(configuration='p1a', measurements=None):
    """Resolved parameter values {name: float}. measurements: optional dict replacing measurements.json."""
    p1a = load_generator('build_p1a.py')
    table = [(name, expr) for name, expr, _, _ in p1a['PARAMS']]
    if configuration == 'p1b':
        p1b = load_generator('build_p1b.py')
        table += [(name, expr) for name, expr, _, _ in p1b['P1B_PARAMS']]
    expressions = dict(table)
    vendor, _ = overrides('vendor_specs.json')
    measured, _ = overrides('measurements.json') if measurements is None else (measurements, {})
    fits, _ = overrides('fit_results.json')
    for source in (vendor, measured, fits):
        expressions.update({k: v for k, v in source.items() if k in expressions})
    if configuration == 'p1b':
        expressions.update({k: v[0] for k, v in p1b['P1B_OVERRIDES'].items()})
    values = {}
    pending = dict(expressions)
    for _ in range(len(pending) + 1):
        for name, expression in list(pending.items()):
            try:
                values[name] = evaluate(expression, values)
                del pending[name]
            except NameError:
                continue
        if not pending: break
    if pending: raise ValueError('Unresolvable parameters: ' + ', '.join(pending))
    return values


def masses():
    _, vendor = overrides('vendor_specs.json')
    _, measured = overrides('measurements.json')
    return {**vendor, **measured}


def cage_geometry(values):
    """Hub centre points (mm), edge index pairs and pole edges from the generator's own functions."""
    p1a = load_generator('build_p1a.py')
    points, edges, pole_edges, mounts = p1a['cage_graph'](values)
    return points, edges, pole_edges
