import base64
import io
from string import ascii_lowercase, ascii_uppercase

from PIL import Image, ImageDraw
from reportlab.graphics.barcode.code128 import Code128


def build_scan_payload(art_num: str, qty: int) -> str:
    return f"{art_num.strip()}\r{qty}"


def _decomposed_pattern(payload: str) -> str:
    bc = Code128(payload)
    bc.validate()
    bc.encode()
    return bc.decompose()


def render_barcode_png(payload: str, bar_width: int = 2, height: int = 48) -> bytes:
    """Render a Code 128 PNG with integer module widths (required for reliable scanning)."""
    pattern = _decomposed_pattern(payload)
    oa, oA = ord("a") - 1, ord("A") - 1
    module = max(2, int(bar_width))

    segments: list[tuple[str, int]] = []
    for ch in pattern:
        oc = ord(ch)
        if ch in ascii_lowercase:
            segments.append(("space", (oc - oa) * module))
        elif ch in ascii_uppercase:
            segments.append(("bar", (oc - oA) * module))

    # ISO/IEC 15417: quiet zone >= 10x module width on each side.
    quiet = module * 10
    pad_y = max(4, module)
    total_w = quiet * 2 + sum(width for _, width in segments)
    img = Image.new("RGB", (max(total_w, 1), height + pad_y * 2), "white")
    draw = ImageDraw.Draw(img)

    x = quiet
    for kind, width in segments:
        if kind == "bar" and width > 0:
            draw.rectangle([x, pad_y, x + width - 1, height + pad_y - 1], fill="black")
        x += width

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_barcode_for_print(
    payload: str,
    max_width_pt: float,
    bar_height_pt: float,
    dpi: int = 300,
) -> tuple[bytes, float, float]:
    """Pick the widest integer module width that fits; return PNG bytes and size in pt."""
    max_w_px = int(max_width_pt / 72 * dpi)
    bar_h_px = max(32, int(bar_height_pt / 72 * dpi))

    png: bytes | None = None
    w_px = h_px = 0
    for module in range(6, 1, -1):
        candidate = render_barcode_png(payload, bar_width=module, height=bar_h_px)
        img = Image.open(io.BytesIO(candidate))
        w_px, h_px = img.size
        if w_px <= max_w_px:
            png = candidate
            break

    if png is None:
        png = render_barcode_png(payload, bar_width=2, height=bar_h_px)
        img = Image.open(io.BytesIO(png))
        w_px, h_px = img.size

    w_pt = w_px / dpi * 72
    h_pt = h_px / dpi * 72
    return png, w_pt, h_pt


def render_barcode_base64(payload: str) -> str:
    return base64.b64encode(render_barcode_png(payload)).decode("ascii")
