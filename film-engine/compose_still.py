"""ANATOMICA film engine - plate compositor + brand mark.

Composites per-system render plates (produced by plates.py) into a
finished still using a named layer recipe, and stamps the NIGHTWARE
LABZ mark: all caps, letter-spaced, bottom right, clean white, no
effects. The same mark pass is applied to every film frame.

  python3 compose_still.py --plates plates_dir --recipe surgery \
      --out still.png [--prefix main_]

Recipes are ordered layer lists of (plate group, opacity). The drape
plate, when present, is always composited last so the surgical drape
covers the pelvis over every anatomy layer.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

RECIPES = {
    # the surgical field: heart and lungs over ghost muscle/skin,
    # vascular tree threaded through
    'surgery': [('skin', 0.10), ('muscle', 0.25), ('lung', 0.55),
                ('heart', 1.0), ('vessels', 0.9)],
    # full-body layered analysis view
    'fullbody': [('skin', 0.14), ('lung', 0.9), ('organliver', 0.9),
                 ('muscle', 0.42), ('bone', 0.85), ('vessels', 1.0),
                 ('heart', 1.0), ('nerve', 1.0), ('brain', 1.0)],
    # intact patient (intake / post-op)
    'intact': [('skin', 1.0)],
    # skeletal (x-ray) view
    'xray': [('skin', 0.05), ('bone', 1.0)],
}

FONT_CANDIDATES = (
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
)


def load_plate(plates_dir, prefix, group):
    path = os.path.join(plates_dir, f'{prefix}{group}.png')
    if not os.path.exists(path):
        return None
    return Image.open(path).convert('RGBA')


def composite(plates_dir, prefix, recipe):
    img = load_plate(plates_dir, prefix, 'base')
    if img is None:
        raise SystemExit('base plate missing')
    for group, alpha in RECIPES[recipe]:
        plate = load_plate(plates_dir, prefix, group)
        if plate is None:
            continue
        plate.putalpha(plate.getchannel('A').point(
            lambda v, a=alpha: int(v * a)))
        img.alpha_composite(plate)
    drape = load_plate(plates_dir, prefix, 'drapeonly')
    if drape is not None:
        img.alpha_composite(drape)
    return img.convert('RGB')


def stamp_mark(img, text='NIGHTWARE LABZ'):
    """Clean all-caps brand mark, bottom right. Metrics scale with
    frame width; reference metrics are the approved 1280x720 ones:
    25 px font, 6 px letter spacing, 40 px right / 44 px bottom."""
    W, H = img.size
    k = W / 1280.0
    font = None
    for cand in FONT_CANDIDATES:
        if os.path.exists(cand):
            font = ImageFont.truetype(cand, int(25 * k))
            break
    if font is None:
        raise SystemExit('no sans font available for the mark')
    d = ImageDraw.Draw(img, 'RGBA')
    spacing = 6 * k
    widths = []
    for ch in text:
        b = d.textbbox((0, 0), ch, font=font)
        widths.append(b[2] - b[0])
    total = sum(widths) + spacing * (len(text) - 1)
    x = W - 40 * k - total
    y = H - 44 * k
    for ch, wch in zip(text, widths):
        d.text((x, y), ch, font=font, fill=(235, 240, 245, 220))
        x += wch + spacing
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plates', required=True)
    ap.add_argument('--recipe', default='surgery', choices=RECIPES)
    ap.add_argument('--prefix', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--no-mark', action='store_true')
    args = ap.parse_args()
    img = composite(args.plates, args.prefix, args.recipe)
    if not args.no_mark:
        img = stamp_mark(img)
    img.save(args.out)
    print('STILL', args.out, img.size)


if __name__ == '__main__':
    main()
