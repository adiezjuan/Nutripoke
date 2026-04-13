# core/presentation/pokemon_image_generator.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# Utilidades básicas
# ============================================================

def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) != 6:
        return (120, 120, 120)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _blend(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _lighten(c: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return _blend(c, (255, 255, 255), t)


def _darken(c: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return _blend(c, (0, 0, 0), t)


def _try_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass

    return ImageFont.load_default()


# ============================================================
# Paletas por dominio
# ============================================================

TYPE_COLORS = {
    "Lípidos": "#f59e0b",
    "Glucosa": "#06b6d4",
    "Inflamación": "#ef4444",
    "Hígado": "#84cc16",
    "Riñón": "#3b82f6",
    "Hematología": "#dc2626",
    "Nutricional": "#10b981",
    "Hormonal": "#8b5cf6",
    "Estrés oxidativo": "#f97316",
    "Metabólico": "#64748b",
}

DOMAIN_ICON_FALLBACK = {
    "Lípidos": "L",
    "Glucosa": "G",
    "Inflamación": "I",
    "Hígado": "H",
    "Riñón": "R",
    "Hematología": "He",
    "Nutricional": "N",
    "Hormonal": "Ho",
    "Estrés oxidativo": "Ox",
    "Metabólico": "M",
}


def _pick_palette(types_: List[str]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    if not types_:
        base1 = _hex_to_rgb("#334155")
        base2 = _hex_to_rgb("#94a3b8")
        accent = _hex_to_rgb("#22d3ee")
        return base1, base2, accent

    base1 = _hex_to_rgb(TYPE_COLORS.get(types_[0], "#334155"))
    base2 = _hex_to_rgb(TYPE_COLORS.get(types_[1], "#94a3b8")) if len(types_) > 1 else _hex_to_rgb("#cbd5e1")
    accent = _lighten(_blend(base1, base2, 0.5), 0.18)
    return base1, base2, accent


# ============================================================
# Dibujo base
# ============================================================

def _draw_vertical_gradient(img: Image.Image, c_top, c_bottom) -> None:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / max(1, h - 1)
        color = _blend(c_top, c_bottom, t)
        draw.line([(0, y), (w, y)], fill=color)


def _draw_radial_glow(base: Image.Image, center: Tuple[int, int], radius: int, color: Tuple[int, int, int], alpha_scale: int = 24) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cx, cy = center

    layers = 14
    for i in range(layers, 0, -1):
        t = i / layers
        r = int(radius * (0.45 + t * 1.05))
        alpha = int(alpha_scale * i)
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=(color[0], color[1], color[2], alpha),
        )

    overlay = overlay.filter(ImageFilter.GaussianBlur(12))
    base.alpha_composite(overlay)


def _draw_noise_stars(base: Image.Image, color: Tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(base, "RGBA")
    w, h = base.size

    for i in range(36):
        x = 80 + (i * 83) % (w - 160)
        y = 90 + (i * 137) % 680
        r = 2 + (i % 3)
        alpha = 70 + (i * 13) % 90
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(color[0], color[1], color[2], alpha))


def _draw_rounded_panel(draw: ImageDraw.ImageDraw, box, radius: int, fill, outline=None, width: int = 1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _draw_premium_frame(base: Image.Image, card_box, color1, color2, accent) -> None:
    draw = ImageDraw.Draw(base, "RGBA")
    x1, y1, x2, y2 = card_box

    # sombra externa
    for i in range(14):
        alpha = 20 - min(18, i)
        draw.rounded_rectangle(
            (x1 - 8 - i, y1 - 8 - i, x2 + 8 + i, y2 + 8 + i),
            radius=44 + i,
            outline=(0, 0, 0, max(0, alpha * 6)),
            width=2,
        )

    # marco exterior
    _draw_rounded_panel(
        draw,
        card_box,
        radius=42,
        fill=(8, 12, 26, 230),
        outline=_lighten(accent, 0.18) + (220,),
        width=4,
    )

    # filete interior
    inset = 14
    _draw_rounded_panel(
        draw,
        (x1 + inset, y1 + inset, x2 - inset, y2 - inset),
        radius=32,
        fill=(5, 10, 24, 120),
        outline=(255, 255, 255, 70),
        width=2,
    )

    # línea superior premium
    top_h = 10
    draw.rounded_rectangle(
        (x1 + 30, y1 + 26, x2 - 30, y1 + 26 + top_h),
        radius=6,
        fill=_lighten(color1, 0.2) + (180,),
    )
    draw.rounded_rectangle(
        (x1 + 30, y1 + 26, x1 + 240, y1 + 26 + top_h),
        radius=6,
        fill=_lighten(color2, 0.25) + (220,),
    )


# ============================================================
# Tipografías y texto
# ============================================================

def _draw_type_badge(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, fill_rgb: Tuple[int, int, int]) -> int:
    x, y = xy
    font = _try_font(26, bold=True)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad_x = 18
    pad_y = 10
    w = tw + pad_x * 2
    h = th + pad_y * 2

    draw.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=20,
        fill=fill_rgb,
        outline=(255, 255, 255),
        width=2,
    )
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=(255, 255, 255))
    return w


def _draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, box: Tuple[int, int, int, int], font, fill=(255, 255, 255), line_spacing: int = 8) -> None:
    x1, y1, x2, y2 = box
    max_width = x2 - x1
    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else current + " " + word
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    y = y1
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        if y + h > y2:
            break
        draw.text((x1, y), line, font=font, fill=fill)
        y += h + line_spacing


# ============================================================
# Rasgos de criatura según dominios
# ============================================================

def _draw_lipidos_feature(draw, cx, cy, body_color, accent):
    # placas/escamas doradas laterales
    for i in range(4):
        ox = 180 + i * 18
        oy = -60 + i * 42
        draw.polygon(
            [(cx - ox, cy + oy), (cx - ox - 52, cy + oy - 34), (cx - ox - 28, cy + oy + 48)],
            fill=_lighten(accent, 0.05),
        )
        draw.polygon(
            [(cx + ox, cy + oy), (cx + ox + 52, cy + oy - 34), (cx + ox + 28, cy + oy + 48)],
            fill=_lighten(accent, 0.05),
        )


def _draw_glucosa_feature(draw, cx, cy, accent):
    # picos/energía angular
    draw.polygon([(cx - 120, cy - 280), (cx - 210, cy - 110), (cx - 70, cy - 160)], fill=accent)
    draw.polygon([(cx + 120, cy - 280), (cx + 210, cy - 110), (cx + 70, cy - 160)], fill=accent)


def _draw_inflamacion_feature(draw, cx, cy, accent):
    # llama/crestas
    fire = _lighten(accent, 0.12)
    draw.polygon([(cx, cy - 340), (cx - 60, cy - 230), (cx - 10, cy - 240), (cx - 75, cy - 130), (cx + 10, cy - 190), (cx + 55, cy - 110), (cx + 48, cy - 235)], fill=fire)


def _draw_higado_feature(draw, cx, cy, accent):
    # hojas/aletas redondeadas
    fill = _lighten(accent, 0.12)
    draw.ellipse((cx - 260, cy - 80, cx - 110, cy + 80), fill=fill)
    draw.ellipse((cx + 110, cy - 80, cx + 260, cy + 80), fill=fill)


def _draw_rinon_feature(draw, cx, cy, accent):
    fill = _lighten(accent, 0.1)
    draw.ellipse((cx - 260, cy + 80, cx - 120, cy + 260), fill=fill)
    draw.ellipse((cx + 120, cy + 80, cx + 260, cy + 260), fill=fill)


def _draw_hormonal_feature(draw, cx, cy, accent):
    fill = _lighten(accent, 0.08)
    # anillos orbitando
    draw.ellipse((cx - 220, cy - 120, cx + 220, cy + 120), outline=fill, width=6)
    draw.ellipse((cx - 170, cy - 160, cx + 170, cy + 160), outline=fill, width=4)


def _draw_oxidativo_feature(draw, cx, cy, accent):
    fill = _lighten(accent, 0.15)
    for i in range(8):
        ox = -220 + i * 60
        draw.line((cx + ox, cy + 40, cx + ox + 30, cy - 40), fill=fill, width=5)


def _draw_domain_features(draw, types_: List[str], cx: int, cy: int, body_color, accent):
    type_set = set(types_)

    if "Lípidos" in type_set:
        _draw_lipidos_feature(draw, cx, cy, body_color, accent)
    if "Glucosa" in type_set:
        _draw_glucosa_feature(draw, cx, cy, accent)
    if "Inflamación" in type_set:
        _draw_inflamacion_feature(draw, cx, cy, accent)
    if "Hígado" in type_set:
        _draw_higado_feature(draw, cx, cy, accent)
    if "Riñón" in type_set:
        _draw_rinon_feature(draw, cx, cy, accent)
    if "Hormonal" in type_set:
        _draw_hormonal_feature(draw, cx, cy, accent)
    if "Estrés oxidativo" in type_set:
        _draw_oxidativo_feature(draw, cx, cy, accent)


# ============================================================
# Cuerpo principal orgánico
# ============================================================

def _draw_creature(base: Image.Image, types_: List[str], color1, color2, accent) -> None:
    draw = ImageDraw.Draw(base, "RGBA")
    w, h = base.size
    cx = w // 2
    cy = 565

    body = _blend(color1, color2, 0.45)
    body_light = _lighten(body, 0.18)
    body_dark = _darken(body, 0.25)

    # aura fuerte
    _draw_radial_glow(base, (cx, cy + 20), 250, accent, alpha_scale=26)
    _draw_radial_glow(base, (cx, cy - 50), 170, _lighten(accent, 0.12), alpha_scale=18)

    draw = ImageDraw.Draw(base, "RGBA")

    # sombra
    draw.ellipse((cx - 185, cy + 270, cx + 185, cy + 340), fill=(0, 0, 0, 120))

    # rasgos de dominios
    _draw_domain_features(draw, types_, cx, cy, body, accent)

    # cola / base
    draw.ellipse((cx - 110, cy + 150, cx + 110, cy + 300), fill=body_dark)

    # torso orgánico
    draw.ellipse((cx - 180, cy - 30, cx + 180, cy + 290), fill=body, outline=(255, 255, 255, 130), width=4)

    # hombros/volumen
    draw.ellipse((cx - 210, cy + 30, cx - 30, cy + 205), fill=_lighten(body, 0.08))
    draw.ellipse((cx + 30, cy + 30, cx + 210, cy + 205), fill=_lighten(body, 0.08))

    # cabeza
    draw.ellipse((cx - 125, cy - 175, cx + 125, cy + 35), fill=body_light, outline=(255, 255, 255, 150), width=4)

    # mejillas laterales suaves
    draw.ellipse((cx - 165, cy - 60, cx - 80, cy + 50), fill=_lighten(body, 0.1))
    draw.ellipse((cx + 80, cy - 60, cx + 165, cy + 50), fill=_lighten(body, 0.1))

    # vientre/núcleo
    draw.ellipse((cx - 68, cy + 70, cx + 68, cy + 205), fill=(255, 255, 255, 165), outline=(255, 255, 255, 210), width=3)
    draw.ellipse((cx - 30, cy + 105, cx + 30, cy + 165), fill=(255, 255, 255, 235))

    # ojos
    eye_y1 = cy - 95
    eye_y2 = cy - 28
    draw.ellipse((cx - 68, eye_y1, cx - 8, eye_y2), fill=(255, 255, 255))
    draw.ellipse((cx + 8, eye_y1, cx + 68, eye_y2), fill=(255, 255, 255))
    draw.ellipse((cx - 49, cy - 77, cx - 22, cy - 43), fill=(15, 23, 42))
    draw.ellipse((cx + 22, cy - 77, cx + 49, cy - 43), fill=(15, 23, 42))

    # brillo ojos
    draw.ellipse((cx - 43, cy - 72, cx - 34, cy - 62), fill=(255, 255, 255))
    draw.ellipse((cx + 28, cy - 72, cx + 37, cy - 62), fill=(255, 255, 255))

    # línea de boca mínima
    draw.arc((cx - 32, cy - 25, cx + 32, cy + 20), start=18, end=162, fill=(255, 255, 255, 120), width=3)


# ============================================================
# Stats y paneles inferiores
# ============================================================

def _draw_stat_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, label: str, value: int, accent) -> int:
    label_font = _try_font(23, bold=True)
    value_font = _try_font(21, bold=False)

    draw.text((x, y), label, font=label_font, fill=(255, 255, 255))
    draw.text((x + w - 48, y), f"{value}", font=value_font, fill=(255, 255, 255))

    bar_y = y + 34
    bar_h = 14
    draw.rounded_rectangle((x, bar_y, x + w, bar_y + bar_h), radius=9, fill=(255, 255, 255, 55))
    fill_w = int(max(0, min(100, value)) / 100 * w)
    draw.rounded_rectangle((x, bar_y, x + fill_w, bar_y + bar_h), radius=9, fill=accent + (255,))
    return 62


def _draw_domain_band(draw: ImageDraw.ImageDraw, dominant_domains: List[Dict[str, Any]], box, accent):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=24, fill=(5, 10, 24, 160), outline=(255, 255, 255, 60), width=2)

    title_font = _try_font(22, bold=True)
    small_font = _try_font(18, bold=False)
    draw.text((x1 + 22, y1 + 14), "DOMINIOS", font=title_font, fill=(255, 255, 255))

    if not dominant_domains:
        draw.text((x1 + 22, y1 + 52), "Sin dominios dominantes", font=small_font, fill=(220, 230, 245))
        return

    slots = min(4, len(dominant_domains))
    if slots <= 0:
        return

    usable_w = (x2 - x1) - 44
    step = usable_w / slots
    cy = y1 + 88

    for i, item in enumerate(dominant_domains[:4]):
        label = str(item.get("domain_label", "Metabólico"))
        score = float(item.get("score", 0.0) or 0.0)

        circle_x = int(x1 + 22 + step * i + step / 2)
        circle_r = 26

        circle_color = _hex_to_rgb(TYPE_COLORS.get(label, "#64748b"))
        fill = _lighten(circle_color, 0.05)
        draw.ellipse(
            (circle_x - circle_r, cy - circle_r, circle_x + circle_r, cy + circle_r),
            fill=fill,
            outline=(255, 255, 255),
            width=2,
        )

        txt = DOMAIN_ICON_FALLBACK.get(label, label[:2].upper())
        txt_font = _try_font(16, bold=True)
        tb = draw.textbbox((0, 0), txt, font=txt_font)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]
        draw.text((circle_x - tw / 2, cy - th / 2 - 1), txt, font=txt_font, fill=(255, 255, 255))

        label_font = _try_font(16, bold=True)
        score_font = _try_font(15, bold=False)

        lb = draw.textbbox((0, 0), label, font=label_font)
        lw = lb[2] - lb[0]
        draw.text((circle_x - lw / 2, cy + 38), label, font=label_font, fill=(240, 245, 255))

        score_text = f"{score:.1f}"
        sb = draw.textbbox((0, 0), score_text, font=score_font)
        sw = sb[2] - sb[0]
        draw.text((circle_x - sw / 2, cy + 60), score_text, font=score_font, fill=_lighten(accent, 0.18))


# ============================================================
# Generador principal
# ============================================================

def generate_pokemon_card_image(
    pokemon_card: Dict[str, Any],
    output_path: str = "outputs/pokemon_final.png",
) -> str:
    output = Path(output_path)
    _ensure_dir(output)

    name = str(pokemon_card.get("name", "Metamon"))
    subtitle = str(pokemon_card.get("subtitle", "Avatar metabólico actual"))
    types_ = list(pokemon_card.get("types", []) or ["Metabólico"])
    rarity = str(pokemon_card.get("rarity", "Raro"))
    threat_level = str(pokemon_card.get("threat_level", "Medio"))
    moves = list(pokemon_card.get("moves", []) or [])
    stats = dict(pokemon_card.get("stats", {}) or {})
    summary = str(pokemon_card.get("clinical_summary", ""))
    dominant_domains = list(pokemon_card.get("dominant_domains", []) or [])

    width, height = 1200, 1680
    color1, color2, accent = _pick_palette(types_)

    base = Image.new("RGBA", (width, height), (10, 14, 28, 255))
    _draw_vertical_gradient(base, _darken(color1, 0.68), _darken(color2, 0.52))
    _draw_noise_stars(base, _lighten(accent, 0.28))

    draw = ImageDraw.Draw(base, "RGBA")

    card_box = (42, 42, width - 42, height - 42)
    _draw_premium_frame(base, card_box, color1, color2, accent)

    draw = ImageDraw.Draw(base, "RGBA")

    # banda superior de color
    draw.rounded_rectangle((74, 78, width - 74, 96), radius=8, fill=_lighten(color1, 0.14) + (210,))
    draw.rounded_rectangle((74, 78, 290, 96), radius=8, fill=_lighten(color2, 0.15) + (220,))

    # cabecera
    title_font = _try_font(66, bold=True)
    sub_font = _try_font(30, bold=False)
    meta_font = _try_font(26, bold=True)
    small_font = _try_font(22, bold=False)
    section_font = _try_font(28, bold=True)

    draw.text((82, 118), name, font=title_font, fill=(255, 255, 255))
    draw.text((84, 194), subtitle, font=sub_font, fill=(232, 241, 255))

    # tipos
    bx = 82
    by = 246
    for t in types_[:2]:
        badge_color = _hex_to_rgb(TYPE_COLORS.get(t, "#64748b"))
        used_w = _draw_type_badge(draw, (bx, by), t, badge_color)
        bx += used_w + 14

    draw.text((82, 316), f"Rareza: {rarity}", font=meta_font, fill=(255, 255, 255))
    draw.text((82, 352), f"Nivel: {threat_level}", font=meta_font, fill=(255, 255, 255))

    # criatura principal
    _draw_creature(base, types_, color1, color2, accent)

    draw = ImageDraw.Draw(base, "RGBA")

    # división elegante
    divider_y = 930
    draw.rounded_rectangle((86, divider_y, width - 86, divider_y + 6), radius=4, fill=(255, 255, 255, 80))

    # panel stats
    stats_box = (82, 965, 500, 1435)
    _draw_rounded_panel(draw, stats_box, radius=28, fill=(0, 0, 0, 86), outline=(255, 255, 255, 60), width=2)
    draw.text((stats_box[0] + 24, stats_box[1] + 18), "STATS", font=section_font, fill=(255, 255, 255))

    y = stats_box[1] + 66
    stat_items = list(stats.items())[:6]
    if not stat_items:
        stat_items = [("equilibrio", 55), ("adaptación", 48)]

    for label, value in stat_items:
        label_clean = str(label).replace("_", " ").title()
        y += _draw_stat_bar(draw, stats_box[0] + 24, y, 330, label_clean, int(value), accent)

    # panel habilidades + interpretación
    info_box = (530, 965, width - 82, 1435)
    _draw_rounded_panel(draw, info_box, radius=28, fill=(0, 0, 0, 86), outline=(255, 255, 255, 60), width=2)

    draw.text((info_box[0] + 24, info_box[1] + 18), "HABILIDADES", font=section_font, fill=(255, 255, 255))

    my = info_box[1] + 64
    bullet_font = _try_font(23, bold=False)
    for move in moves[:4]:
        draw.text((info_box[0] + 30, my), f"• {move}", font=bullet_font, fill=(255, 255, 255))
        my += 40

    sep_y = my + 10
    draw.rounded_rectangle((info_box[0] + 24, sep_y, info_box[2] - 24, sep_y + 4), radius=3, fill=(255, 255, 255, 55))

    draw.text((info_box[0] + 24, sep_y + 18), "INTERPRETACIÓN", font=section_font, fill=(255, 255, 255))
    _draw_wrapped_text(
        draw,
        summary or "Sin resumen clínico disponible.",
        (info_box[0] + 24, sep_y + 62, info_box[2] - 24, info_box[3] - 24),
        font=small_font,
        fill=(240, 246, 255),
        line_spacing=9,
    )

    # mini banda de dominios debajo
    band_box = (82, 1468, width - 82, 1608)
    _draw_domain_band(draw, dominant_domains, band_box, accent)

    base = base.convert("RGB")
    base.save(output, quality=95)
    return str(output)