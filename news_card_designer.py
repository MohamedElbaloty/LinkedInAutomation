"""
Executive News Card Designer for LinkedIn & Telegram.
Creates high-contrast, editorial-grade branded news cards across 5 radically distinct visual paradigms:
1. 'executive_broadsheet': Financial Times / Wall Street Journal light ivory luxury newspaper.
2. 'bold_statement_hero': Apple / Swiss minimalist typography hero with massive impact.
3. 'cyber_radar_cockpit': Palantir / Terminal DeepTech radar with telemetry metrics & HUD grid.
4. 'magazine_asymmetric_cover': Wired / Fast Company modern asymmetric color block.
5. 'split_left' / 'split_right' / 'hero_top': Bloomberg / Forbes Middle East glassmorphic cards.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

from config import BASE_DIR

logger = logging.getLogger(__name__)

FONTS_DIR = BASE_DIR / "assets" / "fonts"
AVATAR_PATH = BASE_DIR / "assets" / "author_avatar.jpg"
NOTO_FONT_PATH = FONTS_DIR / "NotoSansArabic.ttf"
AMIRI_FONT_PATH = FONTS_DIR / "Amiri-Bold.ttf"

# 8 Curated Color Palettes for High Engagement
THEMES = {
    "fintech_emerald": {
        "name": "FinTech Emerald",
        "primary": (16, 185, 129),       # Emerald
        "primary_light": (52, 211, 153), # Mint
        "accent": (245, 158, 11),        # Amber Gold
        "glow": (16, 185, 129, 45),
        "secondary_glow": (6, 182, 212, 35),
    },
    "saudi_gold": {
        "name": "Saudi Royal Gold",
        "primary": (217, 119, 6),        # Warm Gold
        "primary_light": (251, 191, 36),
        "accent": (16, 185, 129),        # Green
        "glow": (217, 119, 6, 45),
        "secondary_glow": (16, 185, 129, 35),
    },
    "ai_cyan": {
        "name": "Cyber AI Cyan",
        "primary": (6, 182, 212),        # Electric Cyan
        "primary_light": (103, 232, 249),
        "accent": (168, 85, 247),        # Purple
        "glow": (6, 182, 212, 45),
        "secondary_glow": (99, 102, 241, 35),
    },
    "proptech_amber": {
        "name": "PropTech Bronze Amber",
        "primary": (245, 158, 11),       # Amber / Gold
        "primary_light": (252, 211, 77),
        "accent": (16, 185, 129),        # Emerald
        "glow": (245, 158, 11, 45),
        "secondary_glow": (234, 88, 12, 35),
    },
    "deeptech_purple": {
        "name": "DeepTech Violet",
        "primary": (139, 92, 246),       # Violet
        "primary_light": (196, 181, 253),
        "accent": (6, 182, 212),         # Cyan
        "glow": (139, 92, 246, 45),
        "secondary_glow": (236, 72, 153, 30),
    },
    "bloomberg_orange": {
        "name": "Bloomberg Executive Orange",
        "primary": (234, 88, 12),        # Tangerine
        "primary_light": (253, 186, 116),
        "accent": (56, 189, 248),        # Sky Blue
        "glow": (234, 88, 12, 40),
        "secondary_glow": (56, 189, 248, 30),
    },
    "crimson_pulse": {
        "name": "Crimson Ruby",
        "primary": (225, 29, 72),        # Ruby Red
        "primary_light": (253, 164, 175),
        "accent": (245, 158, 11),        # Amber
        "glow": (225, 29, 72, 40),
        "secondary_glow": (245, 158, 11, 30),
    },
    "midnight_sapphire": {
        "name": "Midnight Sapphire",
        "primary": (37, 99, 235),        # Royal Sapphire
        "primary_light": (147, 197, 253),
        "accent": (52, 211, 153),        # Mint
        "glow": (37, 99, 235, 45),
        "secondary_glow": (52, 211, 153, 30),
    },
}

LAYOUT_ARCHETYPES = [
    "executive_broadsheet",      # Paradigm 1: Luxury Broadsheet Newspaper (FT / WSJ Ivory)
    "bold_statement_hero",      # Paradigm 2: Bold Typography Hero (Apple / Swiss Matte)
    "cyber_radar_cockpit",      # Paradigm 3: DeepTech Radar & HUD (Palantir / Terminal)
    "magazine_asymmetric_cover",# Paradigm 4: Modern Two-Tone Color Block (Wired / Fast Company)
    "split_left",               # Paradigm 5A: Classic Glass Split (Left Stat)
    "split_right",              # Paradigm 5B: Classic Glass Split (Right Stat)
    "hero_top",                 # Paradigm 5C: Classic Glass Banner Top
]

VISUAL_PARADIGMS = LAYOUT_ARCHETYPES


def shape_arabic(text: str) -> str:
    """Correctly shapes and reorders Arabic text for PIL rendering without breaking English words."""
    if not text:
        return ""
    # Strip emojis that cause box glyphs in standard text fonts
    cleaned = "".join(ch for ch in str(text) if ord(ch) < 0x1F000 and ch not in "⚡📌🚀🇸🇦🇦🇪🏢🤖🏦💡♦►")
    reshaped = arabic_reshaper.reshape(cleaned.strip())
    return get_display(reshaped)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> List[str]:
    """Wraps text so no line exceeds max_width."""
    if not text:
        return []
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        shaped = shape_arabic(test_line)
        bbox = draw.textbbox((0, 0), shaped, font=font)
        if bbox[2] - bbox[0] <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _get_font(size: int, font_type: str = "noto") -> ImageFont.FreeTypeFont:
    """Loads appropriate font with fallbacks."""
    if font_type == "amiri" and AMIRI_FONT_PATH.exists():
        font_path = AMIRI_FONT_PATH
    elif NOTO_FONT_PATH.exists():
        font_path = NOTO_FONT_PATH
    elif AMIRI_FONT_PATH.exists():
        font_path = AMIRI_FONT_PATH
    else:
        for sys_path in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/tahoma.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            if os.path.exists(sys_path):
                font_path = Path(sys_path)
                break
        else:
            return ImageFont.load_default()

    try:
        return ImageFont.truetype(str(font_path), size)
    except Exception as e:
        logger.warning("Could not load font from %s (%s). Using default.", font_path, e)
        return ImageFont.load_default()


def _fit_metric_font(draw: ImageDraw.Draw, text: str, max_w: int, base_size: int = 44) -> ImageFont.FreeTypeFont:
    """Dynamically scales down the metric font so long numbers never overflow the stat box."""
    font = _get_font(base_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    if text_w > max_w:
        scale = max_w / max(text_w, 1)
        new_size = max(24, int(base_size * scale * 0.95))
        font = _get_font(new_size)
    return font


def create_blended_canvas(
    width: int,
    height: int,
    theme: dict,
    background_image_path: Optional[Path] = None,
    dim_factor: float = 0.36,
) -> Image.Image:
    """
    Creates a luxurious blended mesh gradient canvas with multi-stop harmonic color bleeds.
    If background_image_path is provided, smoothly composites it behind a luxury dark wash.
    """
    primary = theme.get("primary", (6, 182, 212))
    primary_light = theme.get("primary_light", (103, 232, 249))
    accent = theme.get("accent", (168, 85, 247))

    if background_image_path and Path(background_image_path).exists():
        try:
            bg_raw = Image.open(background_image_path).convert("RGB")
            bg_resized = bg_raw.resize((width, height), Image.Resampling.LANCZOS)
            # Luxury dark tint overlay so text has 100% executive contrast
            tint = Image.new("RGBA", (width, height), (10, 15, 26, int(255 * (1 - dim_factor))))
            bg_rgba = bg_resized.convert("RGBA")
            blended = Image.alpha_composite(bg_rgba, tint).convert("RGB")
            return blended
        except Exception as e:
            logger.debug("Failed to composite background visual: %s", e)

    # Multi-stop subtle diagonal base gradient
    base = Image.new("RGB", (width, height))
    draw_base = ImageDraw.Draw(base)
    for y in range(height):
        t = y / height
        r = int(10 * (1 - t) + 15 * t)
        g = int(14 * (1 - t) + 23 * t)
        b = int(26 * (1 - t) + 40 * t)
        draw_base.line([(0, y), (width, y)], fill=(r, g, b))

    # Ambient light glow layer with Gaussian blur (Mesh Gradient)
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    # 3 Harmonious ambient glowing orbs blending seamlessly
    # Top-Right: Primary color glow
    glow_draw.ellipse([width - 480, -160, width + 260, 460], fill=(primary[0], primary[1], primary[2], 75))
    # Bottom-Left: Accent color glow
    glow_draw.ellipse([-180, height - 380, 440, height + 220], fill=(accent[0], accent[1], accent[2], 65))
    # Top-Center: Primary light soft highlight
    glow_draw.ellipse([width // 3 - 220, -220, width // 3 + 420, 260], fill=(primary_light[0], primary_light[1], primary_light[2], 40))

    glow = glow.filter(ImageFilter.GaussianBlur(110))
    base = base.convert("RGBA")
    return Image.alpha_composite(base, glow).convert("RGB")



# ---------------------------------------------------------------------------
# PARADIGM 1: Financial Times / WSJ Light Ivory Luxury Broadsheet Newspaper
# ---------------------------------------------------------------------------
def _render_executive_broadsheet(
    width: int,
    height: int,
    headline_line1: str,
    headline_line2: str,
    metric_value: str,
    metric_label: str,
    metric_sub: str,
    category_badge: str,
    event_badge: str,
    bullet_points: List[str],
    sector_tags: List[str],
    source_name: str,
    primary: tuple,
    target_path: Path,
) -> Path:
    # 1. Warm Luxury Ivory/Parchment Paper Canvas
    img = Image.new("RGB", (width, height), (247, 245, 240))
    draw = ImageDraw.Draw(img)

    # 2. Classic Newspaper Masthead
    draw.line([(50, 30), (width - 50, 30)], fill=(30, 41, 59), width=2)
    draw.line([(50, 35), (width - 50, 35)], fill=(30, 41, 59), width=1)

    mast_font = _get_font(18)
    head_font = _get_font(38, font_type="amiri")
    sub_font = _get_font(20)
    role_font = _get_font(16)
    name_font = _get_font(21)

    # Masthead text
    m_left = shape_arabic(event_badge or "إحاطة اقتصادية حصرية • SPECIAL DISPATCH")
    draw.text((55, 42), m_left, font=mast_font, fill=primary)

    m_right = shape_arabic(category_badge or "التقنية والأسواق المالية | FINANCIAL DISPATCH")
    m_r_bbox = draw.textbbox((0, 0), m_right, font=mast_font)
    draw.text((width - 55 - (m_r_bbox[2] - m_r_bbox[0]), 42), m_right, font=mast_font, fill=(51, 65, 85))

    draw.line([(50, 72), (width - 50, 72)], fill=(30, 41, 59), width=1)

    # 3. Two-Column Editorial Layout
    # Left Column: Financial Stat Box (Parchment Card with Double Inset Border)
    stat_x = 55
    stat_y = 95
    stat_w = 340
    stat_h = 340

    draw.rounded_rectangle([stat_x, stat_y, stat_x + stat_w, stat_y + stat_h], radius=6, fill=(255, 255, 255), outline=(203, 213, 225), width=1)
    draw.rounded_rectangle([stat_x + 8, stat_y + 8, stat_x + stat_w - 8, stat_y + stat_h - 8], radius=4, fill=(255, 255, 255), outline=primary, width=2)

    val_lbl = shape_arabic(metric_label or "القيمة التقديرية / المؤشر")
    draw.text((stat_x + 25, stat_y + 25), val_lbl, font=mast_font, fill=(71, 85, 105))

    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    m_font = _fit_metric_font(draw, display_metric, stat_w - 50, base_size=46)
    draw.text((stat_x + 25, stat_y + 85), display_metric, font=m_font, fill=(15, 23, 42))

    sub_tag = shape_arabic(metric_sub or "مؤشر السوق والنمو")
    draw.text((stat_x + 25, stat_y + 180), sub_tag, font=sub_font, fill=primary)

    draw.line([(stat_x + 25, stat_y + 240), (stat_x + stat_w - 25, stat_y + 240)], fill=(226, 232, 240), width=1)
    sec_lbl = shape_arabic("تقرير تنفيذي معتمد • FINANCIAL TIMES STYLE")
    draw.text((stat_x + 25, stat_y + 265), sec_lbl, font=role_font, fill=(100, 116, 139))

    # Right Column: Big Journalistic Headline + 3 Column Bullets
    right_x = 430
    right_w = width - right_x - 55

    full_headline = f"{headline_line1.strip()} {headline_line2.strip()}".strip()
    headline_lines = wrap_text(full_headline, head_font, right_w, draw)
    curr_y = 95
    for h_line in headline_lines[:3]:
        draw.text((right_x, curr_y), shape_arabic(h_line), font=head_font, fill=(15, 23, 42))
        curr_y += 56

    draw.line([(right_x, curr_y + 12), (width - 55, curr_y + 12)], fill=(203, 213, 225), width=1)

    start_y = curr_y + 26
    for bp in bullet_points[:3]:
        cleaned_bp = bp.lstrip("•- ")
        bp_lines = wrap_text(f"♦  {cleaned_bp}", sub_font, right_w, draw)
        for bp_l in bp_lines[:1]:
            draw.text((right_x, start_y), shape_arabic(bp_l), font=sub_font, fill=(30, 41, 59))
            start_y += 44

    # Tags
    tx = right_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=role_font)
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, 545, tx + tw + 20, 580], radius=4, fill=(241, 245, 249), outline=(203, 213, 225), width=1)
        draw.text((tx + 10, 552), t_text, font=role_font, fill=(51, 65, 85))
        tx += tw + 28

    # 4. Newspaper Footer
    draw.line([(50, 615), (width - 50, 615)], fill=(30, 41, 59), width=1)

    if AVATAR_PATH.exists():
        try:
            av = Image.open(AVATAR_PATH).convert("RGBA").resize((60, 60), Image.Resampling.LANCZOS)
            mask = Image.new("L", (60, 60), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 60, 60], fill=255)
            draw.ellipse([50, 635, 110, 695], fill=(203, 213, 225))
            img.paste(av, (50, 635), mask)
        except Exception:
            pass

    auth_name = "Mohamed Elbaloty"
    draw.text((125, 638), auth_name, font=name_font, fill=(15, 23, 42))
    auth_title = "CTO @ Sahalat"
    draw.text((125, 665), auth_title, font=role_font, fill=(100, 116, 139))

    if source_name:
        src_text = shape_arabic(f"المصدر المعتمد: {source_name}")
        src_bbox = draw.textbbox((0, 0), src_text, font=role_font)
        src_w = src_bbox[2] - src_bbox[0]
        draw.text((width - 55 - src_w, 652), src_text, font=role_font, fill=(71, 85, 105))

    img.save(target_path, quality=98)
    return target_path


# ---------------------------------------------------------------------------
# PARADIGM 2: Apple / Swiss Minimalist Bold Typographic Statement Hero
# ---------------------------------------------------------------------------
def _render_bold_statement_hero(
    width: int,
    height: int,
    headline_line1: str,
    headline_line2: str,
    metric_value: str,
    metric_label: str,
    metric_sub: str,
    category_badge: str,
    event_badge: str,
    bullet_points: List[str],
    sector_tags: List[str],
    source_name: str,
    theme: dict,
    target_path: Path,
    background_image_path: Optional[Path] = None,
) -> Path:
    primary = theme.get("primary", (6, 182, 212))
    primary_light = theme.get("primary_light", (103, 232, 249))
    accent = theme.get("accent", (168, 85, 247))

    # 1. Luxurious Blended Mesh Canvas
    img = create_blended_canvas(width, height, theme, background_image_path=background_image_path, dim_factor=0.36)
    draw = ImageDraw.Draw(img)

    # 2. Glowing top accent border line
    for x in range(width):
        ratio = x / width
        r = int(primary[0] * (1 - ratio) + accent[0] * ratio)
        g = int(primary[1] * (1 - ratio) + accent[1] * ratio)
        b = int(primary[2] * (1 - ratio) + accent[2] * ratio)
        draw.line([(x, 0), (x, 3)], fill=(r, g, b))

    # Fonts
    badge_font = _get_font(18)
    hero_title_font = _get_font(42)
    sub_font = _get_font(22)
    role_font = _get_font(16)
    name_font = _get_font(22)

    # 3. Top Category Capsule (Floating frosted pill)
    top_badge = shape_arabic(f"{category_badge or 'التقنية والريادة'}  •  {event_badge or 'تحديث استراتيجي'}")
    draw.rounded_rectangle([70, 45, 70 + 460, 85], radius=20, fill=(16, 24, 40), outline=(255, 255, 255, 35), width=1)
    draw.ellipse([85, 60, 95, 70], fill=primary_light)
    draw.text((105, 52), top_badge, font=badge_font, fill=primary_light)

    # 4. Commanding Center Headline
    full_headline = f"{headline_line1.strip()} {headline_line2.strip()}".strip()
    headline_lines = wrap_text(full_headline, hero_title_font, width - 140, draw)
    curr_y = 120
    for h_line in headline_lines[:2]:
        draw.text((70, curr_y), shape_arabic(h_line), font=hero_title_font, fill=(255, 255, 255))
        curr_y += 62

    # Glowing thin horizontal underline
    draw.line([(70, curr_y + 15), (width - 70, curr_y + 15)], fill=(45, 60, 85), width=1)

    # 5. Middle Split: Frosted Hero Metric Card + 2 Clean Bullet Points
    stat_x = 70
    stat_y = curr_y + 35
    stat_w = 380
    stat_h = 240

    # Frosted stat box
    draw.rounded_rectangle([stat_x, stat_y, stat_x + stat_w, stat_y + stat_h], radius=16, fill=(14, 22, 38), outline=primary, width=2)
    draw.rounded_rectangle([stat_x + 20, stat_y + 14, stat_x + 60, stat_y + 18], radius=2, fill=primary_light)
    draw.text((stat_x + 22, stat_y + 30), shape_arabic(metric_label or "المؤشر القياسي"), font=role_font, fill=(148, 163, 184))

    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    m_font = _fit_metric_font(draw, display_metric, stat_w - 44, base_size=54)
    draw.text((stat_x + 22, stat_y + 75), display_metric, font=m_font, fill=(255, 255, 255))

    draw.text((stat_x + 22, stat_y + 165), shape_arabic(metric_sub or "السوق السعودي والخليجي"), font=sub_font, fill=primary_light)
    draw.line([(stat_x + 22, stat_y + 205), (stat_x + stat_w - 22, stat_y + 205)], fill=(35, 50, 75), width=1)

    # Right: 2 Key Takeaways (Swiss Minimalist)
    right_x = stat_x + stat_w + 45
    right_w = width - right_x - 70
    bp_y = stat_y + 20
    for bp in bullet_points[:2]:
        cleaned_bp = bp.lstrip("•- ")
        draw.ellipse([right_x, bp_y + 8, right_x + 8, bp_y + 16], fill=primary_light)
        bp_lines = wrap_text(cleaned_bp, sub_font, right_w - 24, draw)
        for bp_l in bp_lines[:1]:
            draw.text((right_x + 20, bp_y), shape_arabic(bp_l), font=sub_font, fill=(226, 232, 240))
            bp_y += 56

    # Tags
    tx = right_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=role_font)
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, stat_y + stat_h - 45, tx + tw + 22, stat_y + stat_h - 12], radius=6, fill=(18, 28, 48), outline=(45, 68, 105), width=1)
        draw.text((tx + 11, stat_y + stat_h - 40), t_text, font=role_font, fill=(148, 163, 184))
        tx += tw + 28

    # 6. Floating Signature Bar (Capsule)
    draw.rounded_rectangle([70, height - 90, width - 70, height - 25], radius=14, fill=(16, 24, 40), outline=(255, 255, 255, 30), width=1)

    if AVATAR_PATH.exists():
        try:
            av = Image.open(AVATAR_PATH).convert("RGBA").resize((48, 48), Image.Resampling.LANCZOS)
            mask = Image.new("L", (48, 48), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 48, 48], fill=255)
            draw.ellipse([85, height - 81, 85 + 48, height - 81 + 48], fill=primary)
            img.paste(av, (85, height - 81), mask)
        except Exception:
            pass

    auth_name = "Mohamed Elbaloty"
    draw.text((148, height - 76), auth_name, font=name_font, fill=(255, 255, 255))
    auth_title = "•  CTO @ Sahalat"
    auth_w = draw.textbbox((0, 0), auth_name, font=name_font)[2] - draw.textbbox((0, 0), auth_name, font=name_font)[0]
    draw.text((148 + auth_w + 12, height - 72), auth_title, font=role_font, fill=(148, 163, 184))

    if source_name:
        src_text = shape_arabic(f"المصدر المعتمد: {source_name}")
        src_bbox = draw.textbbox((0, 0), src_text, font=role_font)
        src_w = src_bbox[2] - src_bbox[0]
        draw.text((width - 95 - src_w, height - 65), src_text, font=role_font, fill=(148, 163, 184))

    img.save(target_path, quality=98)
    return target_path


# ---------------------------------------------------------------------------
# PARADIGM 3: Palantir / Terminal DeepTech Radar with Telemetry Metrics
# ---------------------------------------------------------------------------
def _render_cyber_radar_cockpit(
    width: int,
    height: int,
    headline_line1: str,
    headline_line2: str,
    metric_value: str,
    metric_label: str,
    metric_sub: str,
    category_badge: str,
    event_badge: str,
    bullet_points: List[str],
    sector_tags: List[str],
    source_name: str,
    theme: dict,
    target_path: Path,
    background_image_path: Optional[Path] = None,
) -> Path:
    primary = theme.get("primary", (6, 182, 212))
    primary_light = theme.get("primary_light", (103, 232, 249))
    accent = theme.get("accent", (168, 85, 247))

    # 1. Blended Mesh Canvas
    img = create_blended_canvas(width, height, theme, background_image_path=background_image_path, dim_factor=0.32)
    draw = ImageDraw.Draw(img)

    # 2. Subtle Tech Grid Lines
    grid_color = (20, 30, 50, 40)
    for gx in range(0, width, 60):
        draw.line([(gx, 0), (gx, height)], fill=(20, 32, 52), width=1)
    for gy in range(0, height, 60):
        draw.line([(0, gy), (width, gy)], fill=(20, 32, 52), width=1)

    # 3. Corner HUD Brackets
    hud_c = primary
    bracket_len = 30
    draw.line([(45, 45), (45 + bracket_len, 45)], fill=hud_c, width=2)
    draw.line([(45, 45), (45, 45 + bracket_len)], fill=hud_c, width=2)
    draw.line([(width - 45, 45), (width - 45 - bracket_len, 45)], fill=hud_c, width=2)
    draw.line([(width - 45, 45), (width - 45, 45 + bracket_len)], fill=hud_c, width=2)
    draw.line([(45, height - 45), (45 + bracket_len, height - 45)], fill=hud_c, width=2)
    draw.line([(45, height - 45), (45, height - 45 - bracket_len)], fill=hud_c, width=2)
    draw.line([(width - 45, height - 45), (width - 45 - bracket_len, height - 45)], fill=hud_c, width=2)
    draw.line([(width - 45, height - 45), (width - 45, height - 45 - bracket_len)], fill=hud_c, width=2)

    # Fonts
    tag_font = _get_font(17)
    title_font = _get_font(36)
    sub_font = _get_font(21)
    role_font = _get_font(16)
    name_font = _get_font(22)

    # 4. Top Telemetry Status Header
    draw.rounded_rectangle([70, 42, 280, 78], radius=6, fill=(14, 22, 36), outline=(30, 50, 80), width=1)
    draw.ellipse([85, 56, 93, 64], fill=(239, 68, 68))  # Red flashing live dot
    draw.text((105, 48), "LIVE INTEL // TELEMETRY", font=tag_font, fill=primary_light)

    cat_text = shape_arabic(category_badge or "ذكاء اصطناعي وبنية تحتية | DEEPTECH")
    cat_bbox = draw.textbbox((0, 0), cat_text, font=tag_font)
    draw.text((width - 70 - (cat_bbox[2] - cat_bbox[0]), 48), cat_text, font=tag_font, fill=accent)

    # 5. Left Column: Telemetry Gauge Card
    stat_x = 70
    stat_y = 105
    stat_w = 340
    stat_h = 475

    draw.rounded_rectangle([stat_x, stat_y, stat_x + stat_w, stat_y + stat_h], radius=10, fill=(11, 18, 30), outline=primary, width=2)

    # Tech chip inside card
    draw.text((stat_x + 20, stat_y + 20), shape_arabic(event_badge or "مؤشر النمو والتقييم"), font=tag_font, fill=(148, 163, 184))
    draw.text((stat_x + 20, stat_y + 55), shape_arabic(metric_label or "القيمة المحققة"), font=role_font, fill=primary_light)

    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    m_font = _fit_metric_font(draw, display_metric, stat_w - 40, base_size=46)
    draw.text((stat_x + 20, stat_y + 95), display_metric, font=m_font, fill=(255, 255, 255))

    # Simulated visual benchmark bar
    draw.text((stat_x + 20, stat_y + 185), "CAPACITY / EXPANSION INDEX", font=role_font, fill=(100, 116, 139))
    draw.rounded_rectangle([stat_x + 20, stat_y + 215, stat_x + stat_w - 20, stat_y + 230], radius=4, fill=(18, 28, 46))
    draw.rounded_rectangle([stat_x + 20, stat_y + 215, stat_x + int((stat_w - 40) * 0.82), stat_y + 230], radius=4, fill=primary)

    draw.line([(stat_x + 20, stat_y + 265), (stat_x + stat_w - 20, stat_y + 265)], fill=(30, 48, 75), width=1)
    draw.text((stat_x + 20, stat_y + 285), shape_arabic(metric_sub or "نطاق التأثير الإقليمي"), font=sub_font, fill=(203, 213, 225))

    draw.text((stat_x + 20, stat_y + 360), "STATUS: VERIFIED // SAMA & GCC", font=role_font, fill=primary_light)
    draw.text((stat_x + 20, stat_y + 400), "SYS.LATENCY: OPTIMAL", font=role_font, fill=(100, 116, 139))

    # 6. Right Column: Command Terminal
    right_x = 445
    right_w = width - right_x - 70

    # Headline with glowing left bar
    draw.line([(right_x, 105), (right_x, 210)], fill=primary, width=4)

    full_headline = f"{headline_line1.strip()} {headline_line2.strip()}".strip()
    headline_lines = wrap_text(full_headline, title_font, right_w - 20, draw)
    curr_y = 105
    for h_line in headline_lines[:2]:
        draw.text((right_x + 18, curr_y), shape_arabic(h_line), font=title_font, fill=(255, 255, 255))
        curr_y += 54

    draw.line([(right_x, 235), (width - 70, 235)], fill=(30, 48, 75), width=1)

    # Bullet Points with technical arrows ►
    bp_y = 260
    for bp in bullet_points[:3]:
        cleaned_bp = bp.lstrip("•- ")
        bp_lines = wrap_text(f"►  {cleaned_bp}", sub_font, right_w, draw)
        for bp_l in bp_lines[:1]:
            draw.text((right_x, bp_y), shape_arabic(bp_l), font=sub_font, fill=(203, 213, 225))
            bp_y += 48

    # Tags
    tx = right_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=role_font)
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, 455, tx + tw + 24, 490], radius=4, fill=(15, 25, 42), outline=(35, 55, 85), width=1)
        draw.text((tx + 12, 462), t_text, font=role_font, fill=(148, 163, 184))
        tx += tw + 30

    # 7. Author Telemetry ID Footer
    if AVATAR_PATH.exists():
        try:
            av = Image.open(AVATAR_PATH).convert("RGBA").resize((60, 60), Image.Resampling.LANCZOS)
            mask = Image.new("L", (60, 60), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 60, 60], fill=255)
            draw.ellipse([right_x - 3, height - 90 - 3, right_x + 60 + 3, height - 90 + 60 + 3], fill=primary)
            img.paste(av, (right_x, height - 90), mask)
        except Exception:
            pass

    auth_name = "Mohamed Elbaloty"
    draw.text((right_x + 75, height - 85), auth_name, font=name_font, fill=(255, 255, 255))
    auth_title = "CTO @ Sahalat  //  TECH EXECUTIVE"
    draw.text((right_x + 75, height - 58), auth_title, font=role_font, fill=primary_light)

    if source_name:
        src_text = shape_arabic(f"المصدر المعتمد: {source_name}")
        src_bbox = draw.textbbox((0, 0), src_text, font=role_font)
        src_w = src_bbox[2] - src_bbox[0]
        draw.text((width - 70 - src_w, height - 70), src_text, font=role_font, fill=(100, 116, 139))

    img.save(target_path, quality=98)
    return target_path


# ---------------------------------------------------------------------------
# PARADIGM 4: Wired / Fast Company Asymmetric Vibrant Color Block
# ---------------------------------------------------------------------------
def _render_magazine_asymmetric_cover(
    width: int,
    height: int,
    headline_line1: str,
    headline_line2: str,
    metric_value: str,
    metric_label: str,
    metric_sub: str,
    category_badge: str,
    event_badge: str,
    bullet_points: List[str],
    sector_tags: List[str],
    source_name: str,
    theme: dict,
    target_path: Path,
    background_image_path: Optional[Path] = None,
) -> Path:
    primary = theme.get("primary", (16, 185, 129))
    primary_light = theme.get("primary_light", (52, 211, 153))

    # 1. Base Blended Mesh Canvas for the right side
    img = create_blended_canvas(width, height, theme, background_image_path=background_image_path, dim_factor=0.35)
    draw = ImageDraw.Draw(img)

    # 2. Asymmetric Gradient Block (Left 38% of screen) - Rich vertical blended gradient
    block_w = 460
    for y in range(height):
        t = y / height
        r = int(primary[0] * (1 - t * 0.65) + 10 * (t * 0.65))
        g = int(primary[1] * (1 - t * 0.65) + 18 * (t * 0.65))
        b = int(primary[2] * (1 - t * 0.65) + 32 * (t * 0.65))
        draw.line([(0, y), (block_w, y)], fill=(r, g, b))

    # Sleek frosted divider line
    draw.line([(block_w, 0), (block_w, height)], fill=(255, 255, 255, 70), width=2)

    # Fonts
    tag_font = _get_font(18)
    title_font = _get_font(38)
    sub_font = _get_font(21)
    role_font = _get_font(16)
    name_font = _get_font(22)

    # 3. Inside the Vibrant Color Block
    # Category badge capsule
    draw.rounded_rectangle([45, 45, block_w - 45, 90], radius=10, fill=(10, 20, 32), outline=(255, 255, 255, 40), width=1)
    draw.text((65, 54), shape_arabic(category_badge or "التقنية والابتكار | TECH"), font=tag_font, fill=primary_light)

    # Giant Metric Value in stark white
    draw.text((45, 175), shape_arabic(metric_label or "قيمة الإنجاز"), font=tag_font, fill=(209, 250, 229))

    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    m_font = _fit_metric_font(draw, display_metric, block_w - 90, base_size=56)
    draw.text((45, 220), display_metric, font=m_font, fill=(255, 255, 255))

    draw.text((45, 330), shape_arabic(metric_sub or "السوق الخليجي"), font=sub_font, fill=(240, 253, 250))

    # Event badge pill at bottom of color block
    draw.rounded_rectangle([45, 520, block_w - 45, 570], radius=10, fill=(255, 255, 255))
    draw.text((65, 532), shape_arabic(event_badge or "تطور استراتيجي بارز"), font=tag_font, fill=(15, 20, 30))

    # 4. Right Side (Dark High-Contrast Section: 62%)
    right_x = block_w + 60
    right_w = width - right_x - 60

    full_headline = f"{headline_line1.strip()} {headline_line2.strip()}".strip()
    headline_lines = wrap_text(full_headline, title_font, right_w, draw)
    curr_y = 65
    for h_line in headline_lines[:3]:
        draw.text((right_x, curr_y), shape_arabic(h_line), font=title_font, fill=(255, 255, 255))
        curr_y += 56

    draw.line([(right_x, curr_y + 15), (width - 60, curr_y + 15)], fill=(40, 56, 80), width=1)

    # Bullet Points
    bp_y = curr_y + 35
    for bp in bullet_points[:3]:
        cleaned_bp = bp.lstrip("•- ")
        draw.ellipse([right_x, bp_y + 8, right_x + 8, bp_y + 16], fill=primary_light)
        bp_lines = wrap_text(cleaned_bp, sub_font, right_w - 24, draw)
        for bp_l in bp_lines[:1]:
            draw.text((right_x + 20, bp_y), shape_arabic(bp_l), font=sub_font, fill=(226, 232, 240))
            bp_y += 46

    # Tags
    tx = right_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=role_font)
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, 495, tx + tw + 22, 530], radius=6, fill=(18, 28, 48), outline=(45, 68, 105), width=1)
        draw.text((tx + 11, 503), t_text, font=role_font, fill=(148, 163, 184))
        tx += tw + 28

    # 5. Author Branding Bar
    draw.line([(right_x, 575), (width - 60, 575)], fill=(35, 48, 70), width=1)

    if AVATAR_PATH.exists():
        try:
            av = Image.open(AVATAR_PATH).convert("RGBA").resize((60, 60), Image.Resampling.LANCZOS)
            mask = Image.new("L", (60, 60), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 60, 60], fill=255)
            draw.ellipse([right_x - 2, 595 - 2, right_x + 60 + 2, 595 + 60 + 2], fill=primary_light)
            img.paste(av, (right_x, 595), mask)
        except Exception:
            pass

    auth_name = "Mohamed Elbaloty"
    draw.text((right_x + 75, 600), auth_name, font=name_font, fill=(255, 255, 255))
    auth_title = "CTO @ Sahalat"
    draw.text((right_x + 75, 628), auth_title, font=role_font, fill=(148, 163, 184))

    if source_name:
        src_text = shape_arabic(f"المصدر المعتمد: {source_name}")
        src_bbox = draw.textbbox((0, 0), src_text, font=role_font)
        src_w = src_bbox[2] - src_bbox[0]
        draw.text((width - 60 - src_w, 620), src_text, font=role_font, fill=(148, 163, 184))

    img.save(target_path, quality=98)
    return target_path



# ---------------------------------------------------------------------------
# PARADIGM 5: Classic Refined Glassmorphic Card (Existing Split Left/Right/Top)
# ---------------------------------------------------------------------------
def _render_layout_split_left(
    draw: ImageDraw.Draw,
    width: int,
    headline_lines: List[str],
    metric_value: str,
    metric_label: str,
    metric_sub: str,
    bullet_points: List[str],
    sector_tags: List[str],
    primary: tuple,
    primary_light: tuple,
    fonts: dict,
):
    stat_x = 85
    stat_y = 135
    stat_w = 330
    stat_h = 295
    draw.rounded_rectangle([stat_x, stat_y, stat_x + stat_w, stat_y + stat_h], radius=12, fill=(12, 18, 30), outline=primary, width=2)
    
    draw.ellipse([stat_x + 20, stat_y + 24, stat_x + 30, stat_y + 34], fill=primary_light)
    val_lbl = shape_arabic(metric_label or "القيمة التقديرية / المؤشر")
    draw.text((stat_x + 38, stat_y + 19), val_lbl, font=fonts["metric_lbl"], fill=(148, 163, 184))

    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    metric_font = _fit_metric_font(draw, display_metric, stat_w - 40, base_size=44)
    draw.text((stat_x + 20, stat_y + 75), display_metric, font=metric_font, fill=(255, 255, 255))
    
    sub_tag = shape_arabic(metric_sub or "مؤشر السوق والنمو")
    draw.text((stat_x + 20, stat_y + 165), sub_tag, font=fonts["metric_lbl"], fill=primary_light)

    draw.line([(stat_x + 20, stat_y + 225), (stat_x + stat_w - 20, stat_y + 225)], fill=(30, 45, 65), width=1)
    exec_lbl = shape_arabic("تحليل استراتيجي تنفيذي • MARKET INSIGHT")
    draw.text((stat_x + 20, stat_y + 245), exec_lbl, font=fonts["role"], fill=(148, 163, 184))

    right_x = 450
    right_w = width - right_x - 85

    curr_y = 135
    for h_line in headline_lines[:2]:
        draw.text((right_x, curr_y), shape_arabic(h_line), font=fonts["title"], fill=(255, 255, 255))
        curr_y += 54

    div_y = max(curr_y + 12, 255)
    draw.line([(right_x, div_y), (width - 85, div_y)], fill=(45, 60, 85), width=1)

    start_y = div_y + 18
    for bp in bullet_points[:3]:
        cleaned_bp = bp.lstrip("•- ")
        bp_lines = wrap_text(f"• {cleaned_bp}", fonts["sub"], right_w, draw)
        for bp_l in bp_lines[:1]:
            draw.text((right_x, start_y), shape_arabic(bp_l), font=fonts["sub"], fill=(203, 213, 225))
            start_y += 42

    tx = right_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=fonts["role"])
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, 480, tx + tw + 24, 515], radius=6, fill=(22, 33, 50), outline=(45, 65, 95), width=1)
        draw.text((tx + 12, 488), t_text, font=fonts["role"], fill=(148, 163, 184))
        tx += tw + 32


def _render_layout_split_right(
    draw: ImageDraw.Draw,
    width: int,
    headline_lines: List[str],
    metric_value: str,
    metric_label: str,
    metric_sub: str,
    bullet_points: List[str],
    sector_tags: List[str],
    primary: tuple,
    primary_light: tuple,
    fonts: dict,
):
    stat_w = 330
    stat_h = 295
    stat_x = width - 85 - stat_w
    stat_y = 135

    draw.rounded_rectangle([stat_x, stat_y, stat_x + stat_w, stat_y + stat_h], radius=12, fill=(12, 18, 30), outline=primary, width=2)
    draw.ellipse([stat_x + 20, stat_y + 24, stat_x + 30, stat_y + 34], fill=primary_light)
    val_lbl = shape_arabic(metric_label or "القيمة التقديرية / المؤشر")
    draw.text((stat_x + 38, stat_y + 19), val_lbl, font=fonts["metric_lbl"], fill=(148, 163, 184))

    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    metric_font = _fit_metric_font(draw, display_metric, stat_w - 40, base_size=44)
    draw.text((stat_x + 20, stat_y + 75), display_metric, font=metric_font, fill=(255, 255, 255))
    
    sub_tag = shape_arabic(metric_sub or "مؤشر السوق والنمو")
    draw.text((stat_x + 20, stat_y + 165), sub_tag, font=fonts["metric_lbl"], fill=primary_light)

    draw.line([(stat_x + 20, stat_y + 225), (stat_x + stat_w - 20, stat_y + 225)], fill=(30, 45, 65), width=1)
    exec_lbl = shape_arabic("تحليل استراتيجي تنفيذي • MARKET INSIGHT")
    draw.text((stat_x + 20, stat_y + 245), exec_lbl, font=fonts["role"], fill=(148, 163, 184))

    left_x = 85
    left_w = stat_x - left_x - 40

    curr_y = 135
    for h_line in headline_lines[:2]:
        draw.text((left_x, curr_y), shape_arabic(h_line), font=fonts["title"], fill=(255, 255, 255))
        curr_y += 54

    div_y = max(curr_y + 12, 255)
    draw.line([(left_x, div_y), (left_x + left_w, div_y)], fill=(45, 60, 85), width=1)

    start_y = div_y + 18
    for bp in bullet_points[:3]:
        cleaned_bp = bp.lstrip("•- ")
        bp_lines = wrap_text(f"• {cleaned_bp}", fonts["sub"], left_w, draw)
        for bp_l in bp_lines[:1]:
            draw.text((left_x, start_y), shape_arabic(bp_l), font=fonts["sub"], fill=(203, 213, 225))
            start_y += 42

    tx = left_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=fonts["role"])
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, 480, tx + tw + 24, 515], radius=6, fill=(22, 33, 50), outline=(45, 65, 95), width=1)
        draw.text((tx + 12, 488), t_text, font=fonts["role"], fill=(148, 163, 184))
        tx += tw + 32


def _render_layout_hero_top(
    draw: ImageDraw.Draw,
    width: int,
    headline_lines: List[str],
    metric_value: str,
    metric_label: str,
    metric_sub: str,
    bullet_points: List[str],
    sector_tags: List[str],
    primary: tuple,
    primary_light: tuple,
    fonts: dict,
):
    head_x = 85
    curr_y = 125
    for h_line in headline_lines[:2]:
        draw.text((head_x, curr_y), shape_arabic(h_line), font=fonts["title"], fill=(255, 255, 255))
        curr_y += 50

    div_y = max(curr_y + 12, 235)
    draw.line([(85, div_y), (width - 85, div_y)], fill=(45, 60, 85), width=1)

    stat_x = 85
    stat_y = div_y + 18
    stat_w = 340
    stat_h = 245
    draw.rounded_rectangle([stat_x, stat_y, stat_x + stat_w, stat_y + stat_h], radius=12, fill=(12, 18, 30), outline=primary, width=2)
    
    draw.ellipse([stat_x + 20, stat_y + 22, stat_x + 30, stat_y + 32], fill=primary_light)
    val_lbl = shape_arabic(metric_label or "المؤشر القيادي")
    draw.text((stat_x + 38, stat_y + 17), val_lbl, font=fonts["metric_lbl"], fill=(148, 163, 184))

    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    metric_font = _fit_metric_font(draw, display_metric, stat_w - 40, base_size=44)
    draw.text((stat_x + 20, stat_y + 60), display_metric, font=metric_font, fill=(255, 255, 255))

    sub_tag = shape_arabic(metric_sub or "مؤشر النمو والتوسع")
    draw.text((stat_x + 20, stat_y + 140), sub_tag, font=fonts["metric_lbl"], fill=primary_light)

    draw.line([(stat_x + 20, stat_y + 190), (stat_x + stat_w - 20, stat_y + 190)], fill=(30, 45, 65), width=1)
    exec_lbl = shape_arabic("تحليل استراتيجي تنفيذي • INSIGHT")
    draw.text((stat_x + 20, stat_y + 205), exec_lbl, font=fonts["role"], fill=(148, 163, 184))

    right_x = 460
    right_w = width - right_x - 85
    start_y = div_y + 18

    for bp in bullet_points[:3]:
        cleaned_bp = bp.lstrip("•- ")
        bp_lines = wrap_text(f"• {cleaned_bp}", fonts["sub"], right_w, draw)
        for bp_l in bp_lines[:1]:
            draw.text((right_x, start_y), shape_arabic(bp_l), font=fonts["sub"], fill=(203, 213, 225))
            start_y += 44

    tx = right_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=fonts["role"])
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, 480, tx + tw + 24, 515], radius=6, fill=(22, 33, 50), outline=(45, 65, 95), width=1)
        draw.text((tx + 12, 488), t_text, font=fonts["role"], fill=(148, 163, 184))
        tx += tw + 32


# ---------------------------------------------------------------------------
# MAIN DISPATCHER FUNCTION
# ---------------------------------------------------------------------------
def render_editorial_news_card(
    headline_line1: str,
    headline_line2: str = "",
    metric_value: str = "99.9%",
    metric_label: str = "مؤشر النمو",
    metric_sub: str = "",
    category_badge: str = "FINTECH & PROPTECH",
    event_badge: str = "DEVELOPMENT BREAKTHROUGH",
    bullet_points: Optional[List[str]] = None,
    sector_tags: Optional[List[str]] = None,
    source_name: str = "",
    theme_name: str = "auto",
    layout_archetype: str = "auto",
    target_path: Optional[Path] = None,
    background_image_path: Optional[Path] = None,
) -> Path:
    """
    Renders a pristine 16:9 (1280x720) executive news card.
    Dynamically alternates between 5 distinct design paradigms and 8 color themes.
    Employs blended mesh gradients and translucent frosted glass styling.
    """
    if bullet_points is None:
        bullet_points = []
    if sector_tags is None:
        sector_tags = ["#FinTech", "#PropTech", "#Saudi_Arabia"]
    width, height = 1280, 720
    if target_path is None:
        target_path = BASE_DIR / "scratch" / "news_card_output.jpg"
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Auto-resolve Layout Archetype if not explicitly set
    if not layout_archetype or layout_archetype == "auto" or layout_archetype not in LAYOUT_ARCHETYPES:
        idx = abs(hash(headline_line1 + (source_name or ""))) % len(LAYOUT_ARCHETYPES)
        layout_archetype = LAYOUT_ARCHETYPES[idx]

    # Auto-resolve Theme if not explicitly set or not recognized
    if not theme_name or theme_name == "auto" or theme_name not in THEMES:
        combined = (headline_line1 + " " + (category_badge or "")).lower()
        if any(k in combined for k in ["عقار", "عقاري", "أراضي", "proptech"]):
            theme_name = "proptech_amber"
        elif any(k in combined for k in ["سعودي", "المملكة", "الرياض", "saudi", "رؤية"]):
            theme_name = "saudi_gold"
        elif any(k in combined for k in ["ذكاء", "نموذج", "حوسبة", "ai", "llm", "agent"]):
            theme_name = "ai_cyan"
        elif any(k in combined for k in ["تمويل", "فنتك", "بنك", "مدفوعات", "fintech", "pay"]):
            theme_name = "fintech_emerald" if abs(hash(headline_line1)) % 2 == 0 else "bloomberg_orange"
        else:
            all_keys = list(THEMES.keys())
            theme_name = all_keys[abs(hash(headline_line1)) % len(all_keys)]

    theme = THEMES.get(theme_name, THEMES["fintech_emerald"])
    primary = theme["primary"]
    primary_light = theme["primary_light"]
    accent = theme["accent"]

    # --- Dispatch to Specific Radical Paradigms ---
    if layout_archetype == "executive_broadsheet":
        return _render_executive_broadsheet(
            width=width,
            height=height,
            headline_line1=headline_line1,
            headline_line2=headline_line2,
            metric_value=metric_value,
            metric_label=metric_label,
            metric_sub=metric_sub,
            category_badge=category_badge,
            event_badge=event_badge,
            bullet_points=bullet_points,
            sector_tags=sector_tags,
            source_name=source_name,
            primary=primary,
            target_path=target_path,
        )

    if layout_archetype == "bold_statement_hero":
        return _render_bold_statement_hero(
            width=width,
            height=height,
            headline_line1=headline_line1,
            headline_line2=headline_line2,
            metric_value=metric_value,
            metric_label=metric_label,
            metric_sub=metric_sub,
            category_badge=category_badge,
            event_badge=event_badge,
            bullet_points=bullet_points,
            sector_tags=sector_tags,
            source_name=source_name,
            theme=theme,
            target_path=target_path,
            background_image_path=background_image_path,
        )

    if layout_archetype == "cyber_radar_cockpit":
        return _render_cyber_radar_cockpit(
            width=width,
            height=height,
            headline_line1=headline_line1,
            headline_line2=headline_line2,
            metric_value=metric_value,
            metric_label=metric_label,
            metric_sub=metric_sub,
            category_badge=category_badge,
            event_badge=event_badge,
            bullet_points=bullet_points,
            sector_tags=sector_tags,
            source_name=source_name,
            theme=theme,
            target_path=target_path,
            background_image_path=background_image_path,
        )

    if layout_archetype == "magazine_asymmetric_cover":
        return _render_magazine_asymmetric_cover(
            width=width,
            height=height,
            headline_line1=headline_line1,
            headline_line2=headline_line2,
            metric_value=metric_value,
            metric_label=metric_label,
            metric_sub=metric_sub,
            category_badge=category_badge,
            event_badge=event_badge,
            bullet_points=bullet_points,
            sector_tags=sector_tags,
            source_name=source_name,
            theme=theme,
            target_path=target_path,
            background_image_path=background_image_path,
        )

    # --- Paradigm 5: Classic Glassmorphic Split Designs on Blended Canvas ---
    img = create_blended_canvas(width, height, theme, background_image_path=background_image_path, dim_factor=0.38)
    draw = ImageDraw.Draw(img)

    # Top delicate glowing accent line
    for x in range(width):
        ratio = x / width
        r = int(primary[0] * (1 - ratio) + accent[0] * ratio)
        g = int(primary[1] * (1 - ratio) + accent[1] * ratio)
        b = int(primary[2] * (1 - ratio) + accent[2] * ratio)
        draw.line([(x, 0), (x, 3)], fill=(r, g, b))

    fonts = {
        "title": _get_font(36),
        "sub": _get_font(21),
        "tag": _get_font(18),
        "metric_num": _get_font(44),
        "metric_lbl": _get_font(19),
        "name": _get_font(22),
        "role": _get_font(16),
    }

    # Top Header Floating Pills
    cat_text = shape_arabic(category_badge or "التقنية المالية والتمويل | FINTECH")
    cat_bbox = draw.textbbox((0, 0), cat_text, font=fonts["tag"])
    cat_w = cat_bbox[2] - cat_bbox[0]
    cat_x = width - 70 - cat_w
    draw.rounded_rectangle([cat_x - 18, 40, width - 52, 78], radius=18, fill=(16, 24, 40), outline=(255, 255, 255, 35), width=1)
    draw.ellipse([width - 68, 55, width - 60, 63], fill=primary_light)
    draw.text((cat_x - 8, 46), cat_text, font=fonts["tag"], fill=(255, 255, 255))

    event_text = shape_arabic(event_badge or "تطور تقني جديد • MARKET UPDATE")
    event_bbox = draw.textbbox((0, 0), event_text, font=fonts["tag"])
    event_w = event_bbox[2] - event_bbox[0]
    draw.rounded_rectangle([52, 40, 52 + event_w + 40, 78], radius=18, fill=(16, 24, 40), outline=(255, 255, 255, 35), width=1)
    draw.ellipse([66, 55, 74, 63], fill=accent)
    draw.text((84, 46), event_text, font=fonts["tag"], fill=accent)

    # Frosted Glass Main Card Panel (Translucent RGBA with refined border)
    panel_w = width - 104
    panel_h = 455
    panel = Image.new("RGBA", (panel_w, panel_h), (11, 17, 30, 190))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle([0, 0, panel_w, panel_h], radius=18, outline=(255, 255, 255, 38), width=1)
    panel_draw.rounded_rectangle([1, 1, panel_w - 1, panel_h - 1], radius=17, outline=(primary[0], primary[1], primary[2], 25), width=1)
    img.paste(panel, (52, 102), panel)

    draw = ImageDraw.Draw(img)

    full_headline = f"{headline_line1.strip()} {headline_line2.strip()}".strip()
    max_head_w = width - 450 - 85 if layout_archetype == "split_left" else (745 if layout_archetype == "split_right" else 1110)
    headline_lines = wrap_text(full_headline, fonts["title"], max_head_w, draw)

    if layout_archetype == "split_right":
        _render_layout_split_right(
            draw=draw,
            width=width,
            headline_lines=headline_lines,
            metric_value=metric_value,
            metric_label=metric_label,
            metric_sub=metric_sub,
            bullet_points=bullet_points,
            sector_tags=sector_tags,
            primary=primary,
            primary_light=primary_light,
            fonts=fonts,
        )
    elif layout_archetype == "hero_top":
        _render_layout_hero_top(
            draw=draw,
            width=width,
            headline_lines=headline_lines,
            metric_value=metric_value,
            metric_label=metric_label,
            metric_sub=metric_sub,
            bullet_points=bullet_points,
            sector_tags=sector_tags,
            primary=primary,
            primary_light=primary_light,
            fonts=fonts,
        )
    else:  # split_left
        _render_layout_split_left(
            draw=draw,
            width=width,
            headline_lines=headline_lines,
            metric_value=metric_value,
            metric_label=metric_label,
            metric_sub=metric_sub,
            bullet_points=bullet_points,
            sector_tags=sector_tags,
            primary=primary,
            primary_light=primary_light,
            fonts=fonts,
        )

    # Bottom Footer Bar (Author Branding + Verified Checkmark + Source)
    if AVATAR_PATH.exists():
        try:
            av = Image.open(AVATAR_PATH).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
            mask = Image.new("L", (64, 64), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 64, 64], fill=255)
            draw.ellipse([52 - 2, height - 88 - 2, 52 + 64 + 2, height - 88 + 64 + 2], fill=primary)
            img.paste(av, (52, height - 88), mask)
        except Exception as e:
            logger.debug("Could not paste avatar: %s", e)

    auth_name = "Mohamed Elbaloty"
    draw.text((130, height - 85), auth_name, font=fonts["name"], fill=(255, 255, 255))
    auth_title = "•  CTO @ Sahalat"
    auth_w = draw.textbbox((0, 0), auth_name, font=fonts["name"])[2] - draw.textbbox((0, 0), auth_name, font=fonts["name"])[0]
    draw.text((130 + auth_w + 12, height - 80), auth_title, font=fonts["role"], fill=(148, 163, 184))

    if source_name:
        src_text = shape_arabic(f"المصدر المعتمد: {source_name}")
        src_bbox = draw.textbbox((0, 0), src_text, font=fonts["role"])
        src_w = src_bbox[2] - src_bbox[0]
        draw.text((width - 70 - src_w, height - 70), src_text, font=fonts["role"], fill=(148, 163, 184))

    img.save(target_path, quality=98)
    logger.info("Executive news card created successfully (Paradigm: %s, Theme: %s) at %s", layout_archetype, theme_name, target_path)
    return target_path


# Public Aliases
create_executive_news_card = render_editorial_news_card

