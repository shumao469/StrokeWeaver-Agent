"""In-memory JSON, HTML, ZIP and generated slice rendering; no file readers."""

import html
import io
import json
import struct
import zipfile
import zlib


def to_json(report):
    return json.dumps(report, sort_keys=True, indent=2, allow_nan=False)


def to_html(report):
    encoded = html.escape(to_json(report))
    task = html.escape(str(report.get("task", "Generated research report")))
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>StrokeWeaver Agent — generated audit</title><style>body{{font:15px system-ui;max-width:1100px;margin:48px auto;padding:0 24px;background:#08111f;color:#edf3fa}}h1{{letter-spacing:-.04em}}.scope{{padding:18px;border:1px solid #2dd4bf;border-radius:12px}}pre{{background:#111e30;border-radius:12px;padding:24px;overflow:auto;white-space:pre-wrap}}small{{color:#a8b6ca}}</style>
<h1>StrokeWeaver Agent</h1><h2>{task}</h2><p class="scope">Generated inputs only. No patient execution, model inference or clinical validation. TACTIC is the internal controller, not an additional imaging model.</p><pre>{encoded}</pre><small>Audit hashes bind generated report content; they are not a clinical safety certificate.</small></html>"""


def export_zip(report):
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("generated_audit.json", to_json(report))
        archive.writestr("generated_audit.html", to_html(report))
    return target.getvalue()


def slice_png(mask, shape, z=0, scale=32):
    """Actual fixed generated binary voxels, not MRI or neural model output."""
    if len(shape) != 3 or any(type(n) is not int or not 1 <= n <= 16 for n in shape):
        raise ValueError("Bounded generated 3D shape required")
    if len(mask) != shape[0] * shape[1] * shape[2] or any(type(v) is not int or v not in (0, 1) for v in mask):
        raise ValueError("Generated binary voxels required")
    if type(z) is not int or not 0 <= z < shape[2] or type(scale) is not int or not 1 <= scale <= 64:
        raise ValueError("Bounded generated display coordinates required")
    width, height = shape[0] * scale, shape[1] * scale
    pixels = bytearray()
    for row in range(height):
        pixels.append(0)
        y = row // scale
        for column in range(width):
            x = column // scale
            value = mask[(x * shape[1] + y) * shape[2] + z]
            color = (45, 212, 191) if value else (17, 30, 48)
            if row % scale == 0 or column % scale == 0:
                color = (38, 59, 81)
            pixels.extend(color)

    def chunk(name, content):
        return struct.pack(">I", len(content)) + name + content + struct.pack(">I", zlib.crc32(name + content) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(pixels))) + chunk(b"IEND", b"")
