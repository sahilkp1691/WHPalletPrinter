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
    pattern = _decomposed_pattern(payload)
    oa, oA = ord("a") - 1, ord("A") - 1

    segments: list[tuple[str, int]] = []
    for ch in pattern:
        oc = ord(ch)
        if ch in ascii_lowercase:
            segments.append(("space", (oc - oa) * bar_width))
        elif ch in ascii_uppercase:
            segments.append(("bar", (oc - oA) * bar_width))

    quiet = 10
    total_w = quiet * 2 + sum(width for _, width in segments)
    img = Image.new("RGB", (max(total_w, 1), height + 10), "white")
    draw = ImageDraw.Draw(img)

    x = quiet
    for kind, width in segments:
        if kind == "bar" and width > 0:
            draw.rectangle([x, 5, x + width - 1, height + 4], fill="black")
        x += width

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_barcode_base64(payload: str) -> str:
    return base64.b64encode(render_barcode_png(payload)).decode("ascii")
