# pokemon_image_generator.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) != 6:
        return (120, 120, 120)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _blend(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


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


def _pick_palette(types_: List[str]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    if not types_:
        return _hex_to_rgb("#334155"), _hex_to_rgb("#94a3b8")

    c1 = _hex_to_rgb(TYPE_COLORS.get(types_[0], "#334155"))
    c2 = _hex_to_rgb(TYPE_COLORS.get(types_[1], "#94a3b8")) if len(types_) > 1 else _hex_to_rgb("#cbd5e1")
    return c1, c2


def _try_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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


def _draw_gradient_background(draw: ImageDraw.ImageDraw, width: int, height: int, c1, c2) -> None:
    for y in range(height):
        t = y / max(1, height - 1)
        color = _blend(c1, c2, t)
        draw.line([(0, y), (width, y)], fill=color)


def _draw_glow_circle(base: Image.Image, center: Tuple[int, int], radius: int, color: Tuple[int, int, int], layers: int = 8) -> None:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    cx, cy = center
    for i in range(layers, 0, -1):
        alpha = int(18 * i)
        r = radius + i * 18
        glow_draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=(color[0], color[1], color[2], alpha),
        )

    base.alpha_composite(glow)


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

    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=fill_rgb, outline=(255, 255, 255), width=2)
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=(255, 255, 255))
    return w


def _draw_stat_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, label: str, value: int) -> int:
    label_font = _try_font(24, bold=True)
    value_font = _try_font(22, bold=False)

    draw.text((x, y), label, font=label_font, fill=(255, 255, 255))
    draw.text((x + w - 55, y), f"{value}", font=value_font, fill=(255, 255, 255))

    bar_y = y + 34
    bar_h = 16
    draw.rounded_rectangle((x, bar_y, x + w, bar_y + bar_h), radius=8, fill=(255, 255, 255, 70))
    fill_w = int(max(0, min(100, value)) / 100 * w)
    draw.rounded_rectangle((x, bar_y, x + fill_w, bar_y + bar_h), radius=8, fill=(255, 255, 255))

    return 64


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


def generate_pokemon_card_image(
    pokemon_card: Dict[str, Any],
    output_path: str = "outputs/pokemon_final.png",
) -> str:
    """
    Crea una imagen placeholder bonita estilo carta/avatar metabólico.
    Devuelve la ruta del archivo generado.
    """
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

    width, height = 1100, 1500
    c1, c2 = _pick_palette(types_)

    base = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(base, "RGBA")

    _draw_gradient_background(draw, width, height, c1, c2)

    # Panel principal
    margin = 42
    draw.rounded_rectangle(
        (margin, margin, width - margin, height - margin),
        radius=40,
        fill=(10, 15, 25, 110),
        outline=(255, 255, 255, 90),
        width=3,
    )

    # Glow central
    aura_color = _blend(c1, (255, 255, 255), 0.25)
    _draw_glow_circle(base, (width // 2, 520), 170, aura_color, layers=10)
    draw = ImageDraw.Draw(base, "RGBA")

    # Silueta del "pokémon"
    body_color = _blend(c1, c2, 0.35)
    shadow_color = (0, 0, 0, 90)

    # sombra
    draw.ellipse((350, 760, 750, 860), fill=shadow_color)

    # cuerpo
    draw.ellipse((350, 320, 750, 820), fill=body_color, outline=(255, 255, 255, 110), width=4)
    draw.ellipse((430, 220, 670, 470), fill=_blend(body_color, (255, 255, 255), 0.15), outline=(255, 255, 255, 100), width=4)

    # cuernos/alas energéticas
    draw.polygon([(450, 290), (330, 180), (410, 390)], fill=_blend(c1, (255, 255, 255), 0.2))
    draw.polygon([(650, 290), (770, 180), (690, 390)], fill=_blend(c2, (255, 255, 255), 0.2))

    # ojos
    draw.ellipse((485, 325, 535, 375), fill=(255, 255, 255))
    draw.ellipse((565, 325, 615, 375), fill=(255, 255, 255))
    draw.ellipse((500, 340, 525, 365), fill=(30, 41, 59))
    draw.ellipse((580, 340, 605, 365), fill=(30, 41, 59))

    # núcleo/metabolismo
    draw.ellipse((485, 520, 615, 650), fill=(255, 255, 255, 170), outline=(255, 255, 255), width=4)
    draw.ellipse((515, 550, 585, 620), fill=(255, 255, 255, 210))

    # título
    title_font = _try_font(64, bold=True)
    meta_font = _try_font(28, bold=False)
    small_bold = _try_font(24, bold=True)
    small_font = _try_font(22, bold=False)

    draw.text((72, 72), name, font=title_font, fill=(255, 255, 255))
    draw.text((74, 146), subtitle, font=meta_font, fill=(240, 248, 255))

    # badges
    bx = 72
    by = 198
    for t in types_[:2]:
        badge_color = _hex_to_rgb(TYPE_COLORS.get(t, "#64748b"))
        used_w = _draw_type_badge(draw, (bx, by), t, badge_color)
        bx += used_w + 14

    # rareza / nivel
    draw.text((72, 264), f"Rareza: {rarity}", font=small_bold, fill=(255, 255, 255))
    draw.text((72, 298), f"Nivel: {threat_level}", font=small_bold, fill=(255, 255, 255))

    # stats box
    stats_x1, stats_y1, stats_x2, stats_y2 = 72, 930, 520, 1400
    draw.rounded_rectangle((stats_x1, stats_y1, stats_x2, stats_y2), radius=28, fill=(0, 0, 0, 80), outline=(255, 255, 255, 60), width=2)
    draw.text((stats_x1 + 24, stats_y1 + 20), "STATS", font=small_bold, fill=(255, 255, 255))

    y = stats_y1 + 70
    for label, value in list(stats.items())[:6]:
        label_clean = label.replace("_", " ").title()
        y += _draw_stat_bar(draw, stats_x1 + 24, y, 370, label_clean, int(value))

    # moves / summary
    info_x1, info_y1, info_x2, info_y2 = 560, 930, 1028, 1400
    draw.rounded_rectangle((info_x1, info_y1, info_x2, info_y2), radius=28, fill=(0, 0, 0, 80), outline=(255, 255, 255, 60), width=2)

    draw.text((info_x1 + 24, info_y1 + 20), "HABILIDADES", font=small_bold, fill=(255, 255, 255))

    my = info_y1 + 66
    for move in moves[:4]:
        draw.text((info_x1 + 30, my), f"• {move}", font=small_font, fill=(255, 255, 255))
        my += 38

    draw.text((info_x1 + 24, my + 20), "INTERPRETACIÓN", font=small_bold, fill=(255, 255, 255))
    _draw_wrapped_text(
        draw,
        summary or "Sin resumen clínico disponible.",
        (info_x1 + 24, my + 58, info_x2 - 24, info_y2 - 24),
        font=small_font,
        fill=(245, 248, 255),
        line_spacing=8,
    )

    base = base.convert("RGB")
    base.save(output, quality=95)
    return str(output)