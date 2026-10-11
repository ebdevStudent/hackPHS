"""AprilTag kit: register tags in the roster, print them at an exact size, and test detection.

    ball-demo tags wizard                         # guided: name, role, size -> roster + printable PDF
    ball-demo tags add person "Rahul" --size-cm 12
    ball-demo tags add pad "Landing pad" --size-cm 16
    ball-demo tags list
    ball-demo tags print --output tags.pdf        # every roster tag, exact size, with a scale check bar
    ball-demo tags detect --url http://<pi>:8090/snapshot.jpg

The roster is the server-owned JSON file that `serve --roster` reads (default
~/.config/ball-drone/roster.json, or $BALL_ROSTER_FILE). Size = the black square's outer edge.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np

from .roster import LandingSite, Person, Roster, load_roster
from .tag_target import FAMILY, MAX_TAG_ID, TagScanner, describe

DEFAULT_ROSTER = Path(os.environ.get('BALL_ROSTER_FILE') or Path.home() / '.config' / 'ball-drone' / 'roster.json')
PAGES = {'letter': (8.5, 11.0), 'a4': (8.27, 11.69), 'tabloid': (11.0, 17.0)}
DPI = 300


# --- roster -------------------------------------------------------------------------------------

def load_or_new(path):
    path = Path(path)
    return load_roster(path) if path.exists() else Roster()


def save(roster, path):
    """Validate the whole roster, then write it atomically."""
    path = Path(path)
    roster = Roster.model_validate(roster.model_dump())
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(roster.model_dump_json(indent=2) + '\n')
    os.replace(temp, path)
    return path


def used_ids(roster):
    return {p.tag_id for p in roster.people} | {s.tag_id for s in roster.landing_sites}


def next_free_id(roster):
    used = used_ids(roster)
    return next(i for i in range(MAX_TAG_ID + 1) if i not in used)


def slug(name, existing):
    base = ''.join(c if c.isalnum() or c in '_.-' else '-' for c in name.strip().lower()).strip('-') or 'tag'
    candidate, n = base[:70], 2
    while candidate in existing:
        candidate, n = f'{base[:66]}-{n}', n + 1
    return candidate


def add(roster, role, name, size_m, tag_id=None, pad_width_m=None, pad_length_m=None):
    """Return (new roster, entry). Picks the next free tag ID when none is given."""
    name = name.strip()
    if not name:
        raise ValueError('Name must not be empty')
    tag_id = next_free_id(roster) if tag_id is None else int(tag_id)
    if not 0 <= tag_id <= MAX_TAG_ID:
        raise ValueError(f'Tag ID must be 0–{MAX_TAG_ID}')
    if tag_id in used_ids(roster):
        raise ValueError(f'Tag ID {tag_id} is already in the roster')
    if not .01 <= size_m <= 2:
        raise ValueError('Tag size must be between 1 cm and 2 m')
    data = roster.model_dump()
    if role == 'person':
        entry = Person(person_id=slug(name, {p.person_id for p in roster.people}), display_name=name,
                       tag_family=FAMILY, tag_id=tag_id, tag_size_m=size_m)
        data['people'].append(entry.model_dump())
    elif role == 'pad':
        width = pad_width_m or max(.3, size_m * 2)
        entry = LandingSite(site_id=slug(name, {s.site_id for s in roster.landing_sites}), display_name=name,
                            tag_family=FAMILY, tag_id=tag_id, tag_size_m=size_m,
                            width_m=width, length_m=pad_length_m or width)
        data['landing_sites'].append(entry.model_dump())
    else:
        raise ValueError("Role must be 'person' or 'pad'")
    return Roster.model_validate(data), entry


def remove(roster, tag_id):
    data = roster.model_dump()
    before = len(data['people']) + len(data['landing_sites'])
    data['people'] = [p for p in data['people'] if p['tag_id'] != tag_id]
    data['landing_sites'] = [s for s in data['landing_sites'] if s['tag_id'] != tag_id]
    if len(data['people']) + len(data['landing_sites']) == before:
        raise ValueError(f'Tag ID {tag_id} is not in the roster')
    return Roster.model_validate(data)


def entries(roster):
    rows = [('person', p.tag_id, p.display_name, p.tag_size_m, p.enabled) for p in roster.people]
    rows += [('pad', s.tag_id, s.display_name, s.tag_size_m, s.enabled) for s in roster.landing_sites]
    return sorted(rows, key=lambda r: r[1])


# --- printing ------------------------------------------------------------------------------------

def tag_image(tag_id, pixels):
    """Black-square tag of exactly `pixels` px (outer black edge), no quiet zone."""
    import cv2
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    return cv2.aruco.generateImageMarker(dictionary, int(tag_id), int(pixels), borderBits=1)


def _font(size):
    from PIL import ImageFont
    for name in ('DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'Arial.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def render_pages(items, page='letter', dpi=DPI):
    """items: [(tag_id, size_m, caption)] -> list of PIL pages, tags at exact physical size."""
    from PIL import Image, ImageDraw
    width_in, height_in = PAGES[page]
    page_w, page_h = int(width_in * dpi), int(height_in * dpi)
    margin, gap, caption_h = int(.3 * dpi), int(.25 * dpi), int(.45 * dpi)
    pages, page_img, draw, x, y, row_h = [], None, None, 0, 0, 0

    def new_page():
        img = Image.new('L', (page_w, page_h), 255)
        d = ImageDraw.Draw(img)
        bar = int(round(5 / 2.54 * dpi))   # 5 cm scale-check bar
        top = page_h - margin + int(.05 * dpi)
        d.rectangle([margin, top, margin + bar, top + int(.06 * dpi)], fill=0)
        d.text((margin + bar + int(.15 * dpi), top - int(.05 * dpi)),
               'This bar must measure exactly 5.0 cm. If not, reprint at 100% / "Actual size".',
               fill=0, font=_font(int(.13 * dpi)))
        return img, d

    for tag_id, size_m, caption in items:
        side = int(round(size_m / .0254 * dpi))
        quiet = max(int(side / 8), int(.1 * dpi))   # white border the detector needs
        cell_w, cell_h = side + 2 * quiet, side + 2 * quiet + caption_h
        usable_w, usable_h = page_w - 2 * margin, page_h - 2 * margin - int(.25 * dpi)
        if cell_w > usable_w or cell_h > usable_h:
            raise ValueError(f'Tag {tag_id} at {size_m * 100:.1f} cm does not fit on a {page} page')
        bottom = page_h - margin - int(.25 * dpi)
        if page_img is None:
            page_img, draw = new_page()
            x, y, row_h = margin, margin, 0
        if x + cell_w > page_w - margin:          # wrap to the next row
            x, y, row_h = margin, y + row_h + gap, 0
        if y + cell_h > bottom:                   # next page
            pages.append(page_img)
            page_img, draw = new_page()
            x, y, row_h = margin, margin, 0
        draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=200)   # cut line
        page_img.paste(Image.fromarray(tag_image(tag_id, side)), (x + quiet, y + quiet))
        draw.text((x + quiet, y + quiet + side + int(.08 * dpi)),
                  f'ID {tag_id} · {caption}', fill=0, font=_font(int(.14 * dpi)))
        draw.text((x + quiet, y + quiet + side + int(.26 * dpi)),
                  f'{FAMILY} · black square = {size_m * 100:.1f} cm', fill=90, font=_font(int(.11 * dpi)))
        x += cell_w + gap
        row_h = max(row_h, cell_h)
    if page_img is not None:
        pages.append(page_img)
    return pages


def write_pdf(pages, output, dpi=DPI):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == '.pdf':
        pages[0].save(output, save_all=True, append_images=pages[1:], resolution=dpi)
        return [output]
    paths = []
    for i, page in enumerate(pages, 1):
        path = output.with_name(f'{output.stem}-{i}{output.suffix or ".png"}')
        page.save(path, dpi=(dpi, dpi))
        paths.append(path)
    return paths


def roster_items(roster, ids=None):
    rows = entries(roster)
    if ids:
        rows = [r for r in rows if r[1] in ids]
    return [(tag_id, size, f"{name} ({'landing pad' if role == 'pad' else 'person'})")
            for role, tag_id, name, size, _ in rows]


# --- detection test ------------------------------------------------------------------------------

def read_image(path=None, url=None, camera=None):
    import cv2
    if url:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = np.frombuffer(response.read(), np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    elif path:
        image = cv2.imread(str(path))
    else:
        capture = cv2.VideoCapture(camera if not str(camera).isdigit() else int(camera))
        for _ in range(10):
            ok, image = capture.read()
        capture.release()
        image = image if ok else None
    if image is None:
        raise ValueError('Could not read an image from the given source')
    return image


def detect_report(image, roster, size_m=.10, hfov_deg=160, width=640, height=480):
    """Resize like the live pipeline, then list every tag with roster identity and range estimate."""
    import cv2
    from .config import Settings
    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    settings = Settings(width=width, height=height, tag_size_m=size_m, camera_hfov_deg=hfov_deg)
    tags = [describe(i, c, settings, roster, width, height) for i, c in TagScanner().scan(image)]
    return image, sorted(tags, key=lambda t: t['id'])


# --- command line ----------------------------------------------------------------------------------

def add_arguments(parser):
    parser.add_argument('--roster', default=str(DEFAULT_ROSTER), help=f'Roster JSON (default {DEFAULT_ROSTER})')
    sub = parser.add_subparsers(dest='tags_command', required=True)
    sub.add_parser('wizard', help='Guided: add tags and make a printable PDF')
    a = sub.add_parser('add', help='Register a tag (next free ID unless --id)')
    a.add_argument('role', choices=['person', 'pad'])
    a.add_argument('name')
    a.add_argument('--size-cm', type=float, required=True, help='Printed black-square edge, measured')
    a.add_argument('--id', type=int)
    a.add_argument('--pad-size-cm', type=float, help='Landing pad footprint edge (default 2x tag, min 30 cm)')
    r = sub.add_parser('remove', help='Remove a tag from the roster')
    r.add_argument('id', type=int)
    sub.add_parser('list', help='Show the roster')
    p = sub.add_parser('print', help='Printable PDF/PNG of roster tags (or --ids)')
    p.add_argument('--output', default='runs/apriltags.pdf')
    p.add_argument('--ids', type=int, nargs='+', help='Only these roster IDs')
    p.add_argument('--blank', type=int, nargs='+', help='Print these IDs without registering them')
    p.add_argument('--size-cm', type=float, default=10, help='Size for --blank tags')
    p.add_argument('--page', choices=sorted(PAGES), default='letter')
    d = sub.add_parser('detect', help='List tags visible in an image, URL snapshot or camera')
    src = d.add_mutually_exclusive_group(required=True)
    src.add_argument('--image')
    src.add_argument('--url', help='e.g. http://172.16.240.48:8090/snapshot.jpg (Pi FPV streamer)')
    src.add_argument('--camera')
    d.add_argument('--annotate', help='Write an outlined copy of the image here')
    d.add_argument('--hfov', type=float, default=160)


def ask(prompt, default=None, cast=str):
    while True:
        raw = input(f'{prompt}' + (f' [{default}]' if default is not None else '') + ': ').strip()
        if not raw and default is not None:
            return default
        try:
            return cast(raw)
        except ValueError:
            print('  Please try again.')


def wizard(path, out=print):
    roster = load_or_new(path)
    out(f'Roster: {path}  ({len(roster.people)} people, {len(roster.landing_sites)} landing pads)')
    added = []
    while True:
        role = ask('Add a tag: [f]ollow target (person), [l]anding pad, or [d]one', 'd').lower()[:1]
        if role == 'd':
            break
        if role not in ('f', 'l'):
            continue
        role = 'person' if role == 'f' else 'pad'
        name = ask('Name shown on screen', 'Landing pad' if role == 'pad' else None)
        size_cm = ask('Printed size in cm (black square edge; bigger = seen from farther)', 16.0 if role == 'pad' else 12.0, float)
        try:
            roster, entry = add(roster, role, name, size_cm / 100)
        except ValueError as error:
            out(f'  Not added: {error}')
            continue
        save(roster, path)
        added.append(entry.tag_id)
        out(f'  Added tag {entry.tag_id} for {name} ({size_cm:g} cm).')
    if added:
        output = Path('runs') / 'apriltags.pdf'
        files = write_pdf(render_pages(roster_items(roster, added)), output)
        out(f'Printable tags: {files[0].resolve()}')
        out('Print at 100% ("Actual size"), check the 5 cm bar, glue flat on stiff card.')
        out('Then on the Pi: reload tags in the monitor (Operator → Reload tags) or restart the service.')
    return roster


def run(args, out=print):
    path = Path(args.roster)
    command = args.tags_command
    if command == 'wizard':
        wizard(path, out)
    elif command == 'add':
        roster, entry = add(load_or_new(path), args.role, args.name, args.size_cm / 100, args.id,
                            args.pad_size_cm / 100 if args.pad_size_cm else None)
        save(roster, path)
        out(f'Added tag {entry.tag_id} ({args.role}: {args.name}, {args.size_cm:g} cm) to {path}')
    elif command == 'remove':
        save(remove(load_or_new(path), args.id), path)
        out(f'Removed tag {args.id} from {path}')
    elif command == 'list':
        rows = entries(load_or_new(path))
        out(f'{path}: {len(rows)} tags')
        for role, tag_id, name, size, enabled in rows:
            out(f'  {tag_id:>3}  {role:<6}  {size * 100:5.1f} cm  {name}' + ('' if enabled else '  (disabled)'))
    elif command == 'print':
        items = roster_items(load_or_new(path), args.ids) if not args.blank else []
        items += [(i, args.size_cm / 100, 'unregistered') for i in (args.blank or [])]
        if not items:
            raise ValueError('Nothing to print: add tags first (ball-demo tags add …) or use --blank IDS')
        files = write_pdf(render_pages(items, args.page), args.output)
        out('Wrote ' + ', '.join(str(f.resolve()) for f in files))
        out('Print at 100% / "Actual size" and check the 5 cm bar on each page.')
    elif command == 'detect':
        import cv2
        image, tags = detect_report(read_image(args.image, args.url, args.camera), load_or_new(path), hfov_deg=args.hfov)
        if not tags:
            out('No AprilTags (tag36h11) found. Tags need a white border, flat card, and to fill ~25+ px.')
        for t in tags:
            who = (f"{'landing pad' if t['role'] == 'landing' else 'person'}: {t['name']}" if t['registered']
                   else 'NOT in roster')
            out(f"  tag {t['id']:>3}  {who:<28} {t['side_px']:6.1f} px  ~{t['range_m']} m  at ({t['x']:.0f},{t['y']:.0f})")
        if args.annotate:
            from .tag_target import draw_overlay
            draw_overlay(image, {'tags_seen': tags, 'target_id': None, 'stage': 'DETECT',
                                 'cue': f'{len(tags)} tag(s)'})
            cv2.imwrite(args.annotate, image)
            out(f'Annotated image: {Path(args.annotate).resolve()}')
    return 0


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog='ball-demo tags', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ValueError as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2
