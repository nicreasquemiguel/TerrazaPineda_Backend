import io
import os
import re
import random
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

SIZE = (1080, 1080)

# Brand colors
BG_TOP    = (26, 5, 51)          # #1a0533
BG_BOTTOM = (10, 2, 30)          # #0a021e
ACCENT_PURPLE = (124, 58, 237)   # #7c3aed
ACCENT_CYAN   = (34, 211, 238)   # #22d3ee
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (180, 160, 220)
TEXT_YELLOW = (251, 191, 36)

MONTH_NAMES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]
DAY_NAMES_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

# ── Quote pools ──────────────────────────────────────────────────────────────

QUOTES_FUN = [
    "Ya se armó la carnita asada en Terraza Pineda.",
    "Apartado y confirmado. ¡Nos vemos en la alberca!",
    "Ya tenemos fecha para la pachanga.",
    "La fiesta ya tiene casa: Terraza Pineda.",
    "El ambiente ya está asegurado.",
    "Se viene un fiestón de aquellos.",
    "La cuenta regresiva comenzó.",
    "¡Ya cayó el apartado! Ahora sí, que empiece la emoción.",
    "La carne, las cheves y la música ya tienen lugar.",
    "Prepárense porque se va a poner bueno.",
    "Ya quedó apartada la mejor terraza.",
    "¡No hagan planes ese día!",
    "La reunión del año ya tiene fecha.",
    "La albercada ya está confirmada.",
    "Aquí se arma el despapaye.",
    "Que no falte nadie, ya está todo listo.",
    "Va a estar más buena la fiesta que la carne asada.",
    "El pretexto perfecto para reunirnos ya está listo.",
    "Aquí empieza una noche inolvidable.",
    "Ya se armó el plan, solo faltas tú.",
    "La fiesta del año ya tiene sede.",
    "La mejor decisión fue reservar Terraza Pineda.",
    "Nos vemos entre música, alberca y buena compañía.",
    "¡Que se escuche hasta la otra cuadra!",
    "Aquí no se viene a trabajar... se viene a disfrutar.",
    "Todo listo para crear recuerdos inolvidables.",
    "Una fecha, una terraza y muchas historias por contar.",
    "Lo mejor está por comenzar. ¡Nos vemos en Terraza Pineda!",
    "Ya se armó el cotorreo.",
    "Se viene el pachangón.",
    "Ahora sí, ¡a echar relajo!",
    "Que empiece la fiesta y se olviden las penas.",
    "¡A darle que es mole de olla!",
    "Va a estar con madre.",
    "Se va a poner hasta el gorro.",
    "Nomás falta que lleguen todos.",
    "Ya quedó el convivio.",
    "Puro ambiente del bueno.",
]

QUOTES_ELEGANT = [
    "Los mejores recuerdos comienzan aquí.",
    "Nuestro gran día ya tiene lugar.",
    "Celebrando los momentos que importan.",
    "Un día especial merece un lugar especial.",
    "El escenario perfecto para una historia inolvidable.",
    "Aquí comienza uno de los capítulos más bonitos.",
    "Cada detalle, pensado para que sea perfecto.",
    "Un momento que se quedará en el corazón para siempre.",
]

ALL_QUOTES = QUOTES_FUN + QUOTES_ELEGANT

QUOTES_REVIEW = [
    "Lo viví y lo volvería a vivir.",
    "Así se hacen las fiestas. Así se hace en Terraza Pineda.",
    "Una experiencia que no se olvida.",
    "El lugar, la gente, la vibra... perfectos.",
    "Terraza Pineda no defrauda. ¡Volvemos pronto!",
    "Así quedó el recuerdo. Así quedó en el corazón.",
    "La fiesta del año. Punto.",
    "Ya saben dónde se arma la pachanga. ¡Aquí!",
    "De esas noches que se cuentan toda la vida.",
    "Lo que pasa en Terraza Pineda... se recuerda siempre.",
    "Gracias por hacerlo tan especial.",
    "El mejor lugar para celebrar los momentos que importan.",
    "Aquí creamos recuerdos que duran para siempre.",
    "Una celebración perfecta merece el lugar perfecto.",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002500-\U00002BEF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F926-\U0001F937"
    "\U00010000-\U0010FFFF"
    "♀-♂"
    "☀-⭕"
    "‍⏏⏩⌚️〰"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text):
    return _EMOJI_RE.sub('', text).strip()


def _make_canvas():
    img = Image.new('RGB', SIZE, color=BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (SIZE[0], y)], fill=(r, g, b))
    return img, draw


def _get_font(size, bold=False):
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
    for x in range(SIZE[0]):
        t = x / SIZE[0]
        r = int(ACCENT_PURPLE[0] + (ACCENT_CYAN[0] - ACCENT_PURPLE[0]) * t)
        g = int(ACCENT_PURPLE[1] + (ACCENT_CYAN[1] - ACCENT_PURPLE[1]) * t)
        b = int(ACCENT_PURPLE[2] + (ACCENT_CYAN[2] - ACCENT_PURPLE[2]) * t)
        draw.line([(x, y), (x, y + height - 1)], fill=(r, g, b))


def _wrap_text(draw, text, font, max_width):
    """Word-wrap text to fit within max_width px. Returns list of lines."""
    words = text.split()
    lines, current = [], []
    for word in words:
        test = ' '.join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(' '.join(current))
            current = [word]
    if current:
        lines.append(' '.join(current))
    return lines


def _draw_wrapped_centered(draw, y, text, font, color, max_width, line_gap=16):
    """Draw centered wrapped text. Returns y below the last line."""
    lines = _wrap_text(draw, text, font, max_width)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lh = bbox[3] - bbox[1]
        lw = bbox[2] - bbox[0]
        draw.text(((SIZE[0] - lw) // 2, y), line, font=font, fill=color)
        y += lh + line_gap
    return y


def _centered_text(draw, y, text, font, color=TEXT_WHITE):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE[0] - w) // 2, y), text, font=font, fill=color)
    return bbox[3] - bbox[1]


def _format_date_es(dt):
    return f"{DAY_NAMES_ES[dt.weekday()]} {dt.day} de {MONTH_NAMES_ES[dt.month]}, {dt.year}"


def _save_card(img, booking_id, filename):
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    path = f'share_cards/{booking_id}/{filename}'
    if default_storage.exists(path):
        default_storage.delete(path)
    saved = default_storage.save(path, ContentFile(buf.read()))
    return default_storage.url(saved)


# ── Card generators ──────────────────────────────────────────────────────────

def generate_confirmation_card(booking):
    """
    1080×1080 confirmation card with a random quote as the hero element.
    Returns the media URL of the saved PNG.
    """
    raw_quote = random.choice(ALL_QUOTES)
    quote_text = _strip_emoji(raw_quote)

    img, draw = _make_canvas()

    # ── Subtle radial glow in the center ─────────────────────────────────────
    glow = Image.new('RGB', SIZE, (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(300, 0, -1):
        alpha = int(30 * (1 - r / 300))
        gd.ellipse(
            [SIZE[0] // 2 - r, SIZE[1] // 2 - r, SIZE[0] // 2 + r, SIZE[1] // 2 + r],
            fill=(124 + alpha, 58, 237)
        )
    img = Image.blend(img, glow, alpha=0.25)
    draw = ImageDraw.Draw(img)

    # ── Top gradient bar ──────────────────────────────────────────────────────
    _draw_gradient_bar(draw, 0, height=8)

    # ── Brand header ──────────────────────────────────────────────────────────
    font_brand  = _get_font(48, bold=True)
    font_sub    = _get_font(26)
    font_quote  = _get_font(62, bold=True)
    font_detail = _get_font(40, bold=True)
    font_time   = _get_font(30)
    font_pkg    = _get_font(28)
    font_foot   = _get_font(26)

    y = 70
    _centered_text(draw, y, 'TERRAZA PINEDA', font_brand, color=TEXT_WHITE)
    y += 58
    _centered_text(draw, y, 'terrazapineda.com', font_sub, color=TEXT_MUTED)

    y += 50
    _draw_gradient_bar(draw, y, height=2)

    # ── Quote hero ────────────────────────────────────────────────────────────
    # Dynamically size font so quote always fits in ~3 lines max
    max_w = 940
    for fsize in (62, 54, 46, 40, 34):
        fq = _get_font(fsize, bold=True)
        lines = _wrap_text(draw, quote_text, fq, max_w)
        if len(lines) <= 3:
            font_quote = fq
            break

    # Measure total quote block height to center it in the hero zone (y_start..y_end)
    hero_top = y + 70
    hero_bottom = 730
    lines = _wrap_text(draw, quote_text, font_quote, max_w)
    bbox_sample = draw.textbbox((0, 0), 'Ag', font=font_quote)
    line_h = bbox_sample[3] - bbox_sample[1]
    gap = 18
    block_h = len(lines) * (line_h + gap)
    quote_y = hero_top + max(0, (hero_bottom - hero_top - block_h) // 2)

    # Draw subtle large quotation mark behind text
    font_bigquote = _get_font(220, bold=True)
    qq_bbox = draw.textbbox((0, 0), '"', font=font_bigquote)
    qw = qq_bbox[2] - qq_bbox[0]
    draw.text(
        ((SIZE[0] - qw) // 2, quote_y - 80),
        '"',
        font=font_bigquote,
        fill=(80, 40, 140),
    )

    quote_y = _draw_wrapped_centered(
        draw, quote_y, quote_text, font_quote, TEXT_WHITE, max_w, line_gap=gap
    )

    # ── Divider ───────────────────────────────────────────────────────────────
    div_y = max(quote_y + 40, 750)
    _draw_gradient_bar(draw, div_y, height=2)

    # ── Event details ─────────────────────────────────────────────────────────
    y = div_y + 44
    date_str = _format_date_es(booking.start_datetime)
    _centered_text(draw, y, date_str, font_detail, color=TEXT_WHITE)

    y += 58
    time_str = f"{booking.start_datetime.strftime('%H:%M')} – {booking.end_datetime.strftime('%H:%M')} hrs"
    _centered_text(draw, y, time_str, font_time, color=TEXT_MUTED)

    if booking.package:
        y += 46
        _centered_text(draw, y, booking.package.title, font_pkg, color=ACCENT_CYAN)

    # ── Footer ────────────────────────────────────────────────────────────────
    _draw_gradient_bar(draw, SIZE[1] - 80, height=6)
    _centered_text(draw, SIZE[1] - 58, 'terrazapineda.com  •  @terrazapineda', font_foot, color=TEXT_MUTED)

    return _save_card(img, str(booking.id), 'confirmation.png')


def generate_review_card(review, booking):
    """
    1080×1080 review card with a random post-event quote.
    Returns the media URL of the saved PNG.
    """
    raw_quote = random.choice(QUOTES_REVIEW)
    quote_text = _strip_emoji(raw_quote)

    img, draw = _make_canvas()

    # Glow
    glow = Image.new('RGB', SIZE, (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(280, 0, -1):
        alpha = int(25 * (1 - r / 280))
        gd.ellipse(
            [SIZE[0] // 2 - r, SIZE[1] // 2 - r, SIZE[0] // 2 + r, SIZE[1] // 2 + r],
            fill=(34 + alpha, 211, 238)
        )
    img = Image.blend(img, glow, alpha=0.2)
    draw = ImageDraw.Draw(img)

    _draw_gradient_bar(draw, 0, height=8)

    font_brand  = _get_font(48, bold=True)
    font_sub    = _get_font(26)
    font_stars  = _get_font(72)
    font_quote  = _get_font(54, bold=True)
    font_name   = _get_font(32)
    font_detail = _get_font(38, bold=True)
    font_foot   = _get_font(26)

    y = 70
    _centered_text(draw, y, 'TERRAZA PINEDA', font_brand, color=TEXT_WHITE)
    y += 58
    _centered_text(draw, y, 'terrazapineda.com', font_sub, color=TEXT_MUTED)
    y += 50
    _draw_gradient_bar(draw, y, height=2)

    # Stars
    y += 60
    stars = '★' * review.rating + '☆' * (5 - review.rating)
    _centered_text(draw, y, stars, font_stars, color=TEXT_YELLOW)

    # Quote
    y += 110
    max_w = 900
    for fsize in (54, 46, 40, 34):
        fq = _get_font(fsize, bold=True)
        lines = _wrap_text(draw, quote_text, fq, max_w)
        if len(lines) <= 3:
            font_quote = fq
            break

    y = _draw_wrapped_centered(draw, y, quote_text, font_quote, TEXT_WHITE, max_w, line_gap=16)

    # Name
    y += 40
    name = review.user.first_name or review.user.email.split('@')[0]
    _centered_text(draw, y, f'— {name}', font_name, color=TEXT_MUTED)

    # Divider
    y += 70
    _draw_gradient_bar(draw, y, height=2)

    # Date
    y += 44
    _centered_text(draw, y, _format_date_es(booking.start_datetime), font_detail, color=TEXT_WHITE)

    # Short review snippet
    if review.review:
        y += 60
        snippet = review.review[:72] + ('…' if len(review.review) > 72 else '')
        font_snippet = _get_font(28)
        _draw_wrapped_centered(draw, y, f'"{snippet}"', font_snippet, TEXT_MUTED, 900, line_gap=10)

    _draw_gradient_bar(draw, SIZE[1] - 80, height=6)
    _centered_text(draw, SIZE[1] - 58, 'terrazapineda.com  •  @terrazapineda', font_foot, color=TEXT_MUTED)

    return _save_card(img, str(booking.id), 'review.png')
