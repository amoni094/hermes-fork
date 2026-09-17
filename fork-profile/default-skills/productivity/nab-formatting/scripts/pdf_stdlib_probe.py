#!/usr/bin/env python3
"""Stdlib-only PDF probe: extract embedded fonts + RGB colors from a PDF.

Use when poppler (pdffonts/pdftotext), pymupdf/fitz, mutool, gs are unavailable
or blocked. No pip install needed — only zlib/re/struct from the stdlib.

Usage:
    python3 pdf_stdlib_probe.py FILE.pdf [FILE2.pdf ...]

Prints, per file: embedded font names, all device-RGB colors used (as hex),
and the reddish subset (handy for brand-color verification).
Also: pass --image to dump the first embedded RGB image to <file>.png
(minimal hand-rolled PNG, no imaging library) so you can view it with vision.
"""
import sys, zlib, re, struct, collections


def iter_streams(data):
    for m in re.finditer(rb'stream\r?\n', data):
        s = m.end()
        e = data.find(b'endstream', s)
        if e < 0:
            continue
        try:
            yield zlib.decompress(data[s:e])
        except Exception:
            continue


def probe(path):
    data = open(path, 'rb').read()
    fonts = set()
    colors = collections.Counter()
    for c in iter_streams(data):
        for bf in re.findall(rb'/BaseFont\s*/([A-Za-z0-9+\-,.]+)', c):
            fonts.add(bf.decode())
        for cm in re.finditer(rb'([0-9.]+) ([0-9.]+) ([0-9.]+) (rg|RG)\b', c):
            r, g, b = (float(cm.group(i)) for i in (1, 2, 3))
            colors[(round(r * 255), round(g * 255), round(b * 255))] += 1
    print("=" * 60)
    print(path)
    print("Fonts:", sorted(fonts) or "NONE (may be non-flate or subset-stripped)")
    print("Colors (device RGB), most used:")
    for (r, g, b), n in colors.most_common(20):
        print("   #%02X%02X%02X  (%d)" % (r, g, b, n))
    reds = [(c, n) for c, n in colors.items() if c[0] > 120 and c[0]-c[1] > 50 and c[0]-c[2] > 50]
    if reds:
        print("Reddish:")
        for (r, g, b), n in sorted(reds, key=lambda x: -x[1]):
            print("   #%02X%02X%02X  (%d)" % (r, g, b, n))


def dump_image(path):
    """Dump the first embedded RGB image (/Width N ... FlateDecode) to <path>.png."""
    data = open(path, 'rb').read()
    m = re.search(rb'/Width\s+(\d+)', data)
    if not m:
        print("no /Width found"); return
    w = int(m.group(1))
    hm = re.search(rb'/Height\s+(\d+)', data[m.start():m.start()+400])
    if not hm:
        print("no /Height near /Width"); return
    h = int(hm.group(1))
    s = data.find(b'stream', m.start()) + 6
    if data[s:s+2] in (b'\r\n', b'\n\r'):
        s += 2
    elif data[s:s+1] in (b'\n', b'\r'):
        s += 1
    e = data.find(b'endstream', s)
    img = zlib.decompress(data[s:e])
    if len(img) != w * h * 3:
        print("stream size %d != W*H*3 (%d); not 8-bit RGB, skipping" % (len(img), w*h*3)); return

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += img[y*stride:(y+1)*stride]
    out = path.rsplit('.', 1)[0] + ".png"
    with open(out, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(raw), 6)))
        f.write(chunk(b'IEND', b''))
    print("wrote", out, "(%dx%d)" % (w, h))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_image = '--image' in sys.argv
    if not args:
        print(__doc__); sys.exit(1)
    for p in args:
        probe(p)
        if do_image:
            dump_image(p)
