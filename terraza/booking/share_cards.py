import io
import os
import re
import random
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

SIZE = (1080, 1080)

BG_TOP    = (18, 4, 42)          # deep purple-black
BG_BOTTOM = (6, 1, 20)           # near-black
ACCENT_PURPLE = (124, 58, 237)   # #7c3aed
ACCENT_CYAN   = (34, 211, 238)   # #22d3ee
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (170, 145, 210)
TEXT_YELLOW = (251, 191, 36)

MONTH_NAMES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]
DAY_NAMES_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

# ── Quotes ───────────────────────────────────────────────────────────────────

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
    "Va a estar con madre.",
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

# ── Logo ─────────────────────────────────────────────────────────────────────

_LOGO_SVG = os.path.join(os.path.dirname(__file__), 'logo_white.svg')
_logo_cache = None


def _get_logo(target_h=130):
    """Return logo as RGBA PIL Image, scaled to target_h pixels tall. Cached."""
    global _logo_cache
    if _logo_cache is not None:
        ratio = target_h / _logo_cache.height
        w = int(_logo_cache.width * ratio)
        return _logo_cache.resize((w, target_h), Image.LANCZOS)

    # Try cairosvg (best quality)
    try:
        import cairosvg
        # SVG aspect ratio: 1066 wide × 1196 tall
        target_w = int(target_h * 1066 / 1196)
        png_bytes = cairosvg.svg2png(
            url=_LOGO_SVG,
            output_width=target_w * 4,   # render 4× for crispness then resize
            output_height=target_h * 4,
        )
        big = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
        _logo_cache = big.resize((target_w, target_h), Image.LANCZOS)
        return _logo_cache
    except Exception:
        pass

    # Fallback: try svglib
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        drawing = svg2rlg(_LOGO_SVG)
        if drawing:
            buf = io.BytesIO()
            renderPM.drawToFile(drawing, buf, fmt='PNG')
            buf.seek(0)
            img = Image.open(buf).convert('RGBA')
            ratio = target_h / img.height
            w = int(img.width * ratio)
            _logo_cache = img.resize((w, target_h), Image.LANCZOS)
            return _logo_cache
    except Exception:
        pass

    return None  # will fall back to text


# ── Canvas helpers ────────────────────────────────────────────────────────────

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


_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U0001F926-\U0001F937"
    "\U00010000-\U0010FFFF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text):
    return _EMOJI_RE.sub('', text).strip()


def _save_card(img, booking_id, filename):
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    path = f'share_cards/{booking_id}/{filename}'
    if default_storage.exists(path):
        default_storage.delete(path)
    saved = default_storage.save(path, ContentFile(buf.read()))
    return default_storage.url(saved)


# ── Subtle noise texture overlay ──────────────────────────────────────────────

def _add_texture(img):
    """Add a very subtle grain/noise over the background for depth."""
    import random as rnd
    texture = Image.new('RGBA', SIZE, (0, 0, 0, 0))
    td = ImageDraw.Draw(texture)
    for _ in range(6000):
        x = rnd.randint(0, SIZE[0] - 1)
        y = rnd.randint(0, SIZE[1] - 1)
        v = rnd.randint(180, 255)
        a = rnd.randint(4, 14)
        td.point((x, y), fill=(v, v, v, a))
    base = img.convert('RGBA')
    base = Image.alpha_composite(base, texture)
    return base.convert('RGB')


# ── Card generators ───────────────────────────────────────────────────────────

def generate_confirmation_card(booking):
    """
    1080×1080 confirmation card:  logo → gradient bar → quote → gradient bar → date → footer.
    Returns the media URL of the saved PNG.
    """
    raw_quote = random.choice(ALL_QUOTES)
    quote_text = _strip_emoji(raw_quote)

    img, draw = _make_canvas()
    img = _add_texture(img)
    draw = ImageDraw.Draw(img)

    # ── Top bar ───────────────────────────────────────────────────────────────
    _draw_gradient_bar(draw, 0, height=8)

    # ── Logo or fallback text ─────────────────────────────────────────────────
    LOGO_H = 130
    logo = _get_logo(LOGO_H)
    y = 60

    if logo:
        lx = (SIZE[0] - logo.width) // 2
        # Paste with alpha channel as mask
        img.paste(logo, (lx, y), logo)
        y += LOGO_H + 30
    else:
        font_brand = _get_font(52, bold=True)
        _centered_text(draw, y, 'TERRAZA PINEDA', font_brand, color=TEXT_WHITE)
        y += 75

    draw = ImageDraw.Draw(img)  # re-get draw after paste

    # ── Divider ───────────────────────────────────────────────────────────────
    _draw_gradient_bar(draw, y, height=2)
    y += 50

    # ── Quote hero ────────────────────────────────────────────────────────────
    max_w = 920
    font_quote = _get_font(62, bold=True)
    for fsize in (62, 54, 46, 40, 34):
        fq = _get_font(fsize, bold=True)
        if len(_wrap_text(draw, quote_text, fq, max_w)) <= 3:
            font_quote = fq
            break

    # Center the quote block vertically in the hero zone
    hero_bottom = 780
    lines = _wrap_text(draw, quote_text, font_quote, max_w)
    lh = draw.textbbox((0, 0), 'Ag', font=font_quote)[3]
    gap = 20
    block_h = len(lines) * (lh + gap)
    quote_y = y + max(0, (hero_bottom - y - block_h) // 2)

    quote_y = _draw_wrapped_centered(draw, quote_y, quote_text, font_quote, TEXT_WHITE, max_w, line_gap=gap)

    # ── Divider before date ───────────────────────────────────────────────────
    div_y = max(quote_y + 50, 800)
    _draw_gradient_bar(draw, div_y, height=2)

    # ── Date ─────────────────────────────────────────────────────────────────
    font_date = _get_font(46, bold=True)
    date_y = div_y + 52
    _centered_text(draw, date_y, _format_date_es(booking.start_datetime), font_date, color=TEXT_WHITE)

    # ── Footer ────────────────────────────────────────────────────────────────
    _draw_gradient_bar(draw, SIZE[1] - 78, height=6)
    font_foot = _get_font(26)
    _centered_text(draw, SIZE[1] - 54, 'terrazapineda.com  •  @terrazapineda', font_foot, color=TEXT_MUTED)

    return _save_card(img, str(booking.id), 'confirmation.png')


def generate_review_card(review, booking):
    """
    1080×1080 review card after leaving a review.
    Returns the media URL of the saved PNG.
    """
    raw_quote = random.choice(QUOTES_REVIEW)
    quote_text = _strip_emoji(raw_quote)

    img, draw = _make_canvas()
    img = _add_texture(img)
    draw = ImageDraw.Draw(img)

    _draw_gradient_bar(draw, 0, height=8)

    LOGO_H = 110
    logo = _get_logo(LOGO_H)
    y = 60

    if logo:
        lx = (SIZE[0] - logo.width) // 2
        img.paste(logo, (lx, y), logo)
        y += LOGO_H + 30
    else:
        font_brand = _get_font(52, bold=True)
        _centered_text(draw, y, 'TERRAZA PINEDA', font_brand, color=TEXT_WHITE)
        y += 75

    draw = ImageDraw.Draw(img)

    _draw_gradient_bar(draw, y, height=2)

    # Stars
    y += 50
    font_stars = _get_font(72)
    stars = '★' * review.rating + '☆' * (5 - review.rating)
    _centered_text(draw, y, stars, font_stars, color=TEXT_YELLOW)
    y += 100

    # Quote
    max_w = 900
    font_quote = _get_font(54, bold=True)
    for fsize in (54, 46, 40, 34):
        fq = _get_font(fsize, bold=True)
        if len(_wrap_text(draw, quote_text, fq, max_w)) <= 3:
            font_quote = fq
            break

    y = _draw_wrapped_centered(draw, y, quote_text, font_quote, TEXT_WHITE, max_w, line_gap=18)

    # Name
    y += 36
    name = review.user.first_name or review.user.email.split('@')[0]
    font_name = _get_font(30)
    _centered_text(draw, y, f'— {name}', font_name, color=TEXT_MUTED)

    # Divider + date
    y += 70
    _draw_gradient_bar(draw, y, height=2)
    y += 48
    font_date = _get_font(42, bold=True)
    _centered_text(draw, y, _format_date_es(booking.start_datetime), font_date, color=TEXT_WHITE)

    # Short review snippet
    if review.review:
        y += 64
        snippet = review.review[:72] + ('…' if len(review.review) > 72 else '')
        font_snippet = _get_font(28)
        _draw_wrapped_centered(draw, y, f'"{snippet}"', font_snippet, TEXT_MUTED, 900, line_gap=10)

    _draw_gradient_bar(draw, SIZE[1] - 78, height=6)
    font_foot = _get_font(26)
    _centered_text(draw, SIZE[1] - 54, 'terrazapineda.com  •  @terrazapineda', font_foot, color=TEXT_MUTED)

    return _save_card(img, str(booking.id), 'review.png')
