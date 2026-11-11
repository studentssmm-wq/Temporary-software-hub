"""Self-contained QR ticket; no missing template or placeholder URL."""
import io
from PIL import Image, ImageDraw, ImageFont
import qrcode

def create_personalized_ticket(order_id, event_title, seat_str=None):
    qr = qrcode.make(f"NULP-{order_id}").convert("RGB")
    image = Image.new("RGB", (1000, 560), "white")
    draw = ImageDraw.Draw(image)
    font = None
    for candidate in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(candidate, 25)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    draw.text((35, 40), "NULP | Student ticket", fill="black", font=font)
    draw.text((35, 110), str(event_title)[:45], fill="black", font=font)
    draw.text((35, 180), f"NULP-{order_id}", fill="black", font=font)
    if seat_str:
        draw.text((35, 250), str(seat_str)[:45], fill="black", font=font)
    image.paste(qr.resize((340,340),resample=Image.Resampling.NEAREST), (620,120))
    result = io.BytesIO()
    image.save(result, format="PNG")
    result.seek(0)
    return result
