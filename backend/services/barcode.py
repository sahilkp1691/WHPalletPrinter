import base64
import io

import barcode
from barcode.writer import ImageWriter


def build_scan_payload(art_num: str, qty: int) -> str:
    return f"{art_num.strip()}\r{qty}"


def render_barcode_png(payload: str) -> bytes:
    code = barcode.get("code128", payload, writer=ImageWriter())
    buf = io.BytesIO()
    code.write(buf, options={"write_text": False, "module_height": 12.0, "module_width": 0.3})
    return buf.getvalue()


def render_barcode_base64(payload: str) -> str:
    return base64.b64encode(render_barcode_png(payload)).decode("ascii")
