import io
import os
import locale
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

SIZE = (1080, 1080)

# Brand colors
BG_TOP = (26, 5, 51)       # #1a0533 dark purple
BG_BOTTOM = (10, 2, 30)    # #0a021e near-black
ACCENT_PURPLE = (124, 58, 237)   # #7c3aed
ACCENT_CYAN = (34, 211, 238)     # #22d3ee
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (180, 160, 220)

MONTH_NAMES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]
DAY_NAMES_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _make_canvas():
    img = Image.new('RGB', SIZE, color=BG_TOP)
    draw = ImageDraw.Draw(img)

    # Vertical gradient (simple: draw horizontal bands)
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (SIZE[0], y)], fill=(r, g, b))

    return img, draw


def _get_font(size, bold=False):
    # Try to load a system font; fall back to Pillow default
    candidates = [
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_gradient_bar(draw, y, height=4):
    """Draw a horizontal gradient accent bar."""
    for x in range(SIZE[0]):
        t = x / SIZE[0]
        r = int(ACCENT_PURPLE[0] + (ACCENT_CYAN[0] - ACCENT_PURPLE[0]) * t)
        g = int(ACCENT_PURPLE[1] + (ACCENT_CYAN[1] - ACCENT_PURPLE[1]) * t)
        b = int(ACCENT_PURPLE[2] + (ACCENT_CYAN[2] - ACCENT_PURPLE[2]) * t)
        draw.line([(x, y), (x, y + height - 1)], fill=(r, g, b))


def _centered_text(draw, y, text, font, color=TEXT_WHITE):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    x = (SIZE[0] - w) // 2
    draw.text((x, y), text, font=font, fill=color)
    return bbox[3] - bbox[1]  # return height


def _format_date_es(dt):
    day_name = DAY_NAMES_ES[dt.weekday()]
    month_name = MONTH_NAMES_ES[dt.month]
    return f"{day_name} {dt.day} de {month_name}, {dt.year}"


def _save_card(img, booking_id, filename):
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    path = f'share_cards/{booking_id}/{filename}'
    if default_storage.exists(path):
        default_storage.delete(path)
    saved_path = default_storage.save(path, ContentFile(buf.read()))
    return default_storage.url(saved_path)


def generate_confirmation_card(booking):
    """
    Generate a 1080x1080 confirmation card for a booking.
    Returns the media URL of the saved PNG.
    """
    img, draw = _make_canvas()

    # Top gradient bar
    _draw_gradient_bar(draw, 0, height=6)

    # Brand name
    font_brand = _get_font(52, bold=True)
    font_title = _get_font(46, bold=True)
    font_date = _get_font(58, bold=True)
    font_sub = _get_font(32)
    font_small = _get_font(28)

    y = 100
    _centered_text(draw, y, 'TERRAZA PINEDA', font_brand, color=TEXT_WHITE)

    y += 80
    _draw_gradient_bar(draw, y, height=2)

    y += 40
    _centered_text(draw, y, '¡Tengo mi evento reservado!', font_title, color=ACCENT_CYAN)

    # Emoji / star decoration
    y += 120
    _centered_text(draw, y, '🎉', _get_font(100), color=TEXT_WHITE)

    # Date
    y += 160
    date_str = _format_date_es(booking.start_datetime)
    _centered_text(draw, y, date_str, font_date, color=TEXT_WHITE)

    # Time
    y += 90
    time_str = f"{booking.start_datetime.strftime('%H:%M')} – {booking.end_datetime.strftime('%H:%M')} hrs"
    _centered_text(draw, y, time_str, font_sub, color=TEXT_MUTED)

    # Package name
    if booking.package:
        y += 80
        _centered_text(draw, y, booking.package.title, font_sub, color=ACCENT_CYAN)

    # Bottom gradient bar + tagline
    _draw_gradient_bar(draw, SIZE[1] - 90, height=4)
    y = SIZE[1] - 70
    _centered_text(draw, y, 'terrazapineda.com  •  @terrazapineda', font_small, color=TEXT_MUTED)

    return _save_card(img, str(booking.id), 'confirmation.png')


def generate_review_card(review, booking):
    """
    Generate a 1080x1080 share card after a user leaves a review.
    Returns the media URL of the saved PNG.
    """
    img, draw = _make_canvas()

    _draw_gradient_bar(draw, 0, height=6)

    font_brand = _get_font(52, bold=True)
    font_title = _get_font(48, bold=True)
    font_date = _get_font(44, bold=True)
    font_sub = _get_font(32)
    font_small = _get_font(28)
    font_stars = _get_font(80)

    y = 100
    _centered_text(draw, y, 'TERRAZA PINEDA', font_brand, color=TEXT_WHITE)

    y += 80
    _draw_gradient_bar(draw, y, height=2)

    y += 50
    _centered_text(draw, y, '¡Lo viví en Terraza Pineda!', font_title, color=ACCENT_CYAN)

    # Stars
    y += 110
    stars = '★' * review.rating + '☆' * (5 - review.rating)
    _centered_text(draw, y, stars, font_stars, color=(251, 191, 36))  # yellow

    # User first name
    y += 130
    name = review.user.first_name or review.user.email.split('@')[0]
    _centered_text(draw, y, f'— {name}', font_sub, color=TEXT_MUTED)

    # Date of event
    y += 80
    date_str = _format_date_es(booking.start_datetime)
    _centered_text(draw, y, date_str, font_date, color=TEXT_WHITE)

    # Short review text (truncated)
    if review.review:
        y += 90
        text = review.review[:80] + ('…' if len(review.review) > 80 else '')
        _centered_text(draw, y, f'"{text}"', font_sub, color=TEXT_MUTED)

    _draw_gradient_bar(draw, SIZE[1] - 90, height=4)
    y = SIZE[1] - 70
    _centered_text(draw, y, 'terrazapineda.com  •  @terrazapineda', font_small, color=TEXT_MUTED)

    return _save_card(img, str(booking.id), 'review.png')
