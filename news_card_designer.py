"""
Executive News Card Designer for LinkedIn & Telegram.
Creates high-contrast, editorial-grade branded news cards (Bloomberg / Forbes Middle East style)
with crisp typography, formatted Arabic shaping, key metrics, and executive author signature.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

from config import BASE_DIR

logger = logging.getLogger(__name__)

FONTS_DIR = BASE_DIR / "assets" / "fonts"
AVATAR_PATH = BASE_DIR / "assets" / "author_avatar.jpg"
NOTO_FONT_PATH = FONTS_DIR / "NotoSansArabic.ttf"
AMIRI_FONT_PATH = FONTS_DIR / "Amiri-Bold.ttf"

# Color Palettes by Theme
THEMES = {
    "fintech_emerald": {
        "primary": (16, 185, 129),      # Emerald
        "primary_light": (52, 211, 153), # Mint
        "accent": (245, 158, 11),       # Amber Gold
        "glow": (16, 185, 129, 45),
        "secondary_glow": (6, 182, 212, 35),
    },
    "ai_cyan": {
        "primary": (6, 182, 212),       # Cyan
        "primary_light": (103, 232, 249),
        "accent": (168, 85, 247),       # Purple
        "glow": (6, 182, 212, 45),
        "secondary_glow": (99, 102, 241, 35),
    },
    "proptech_amber": {
        "primary": (245, 158, 11),      # Amber / Gold
        "primary_light": (252, 211, 77),
        "accent": (16, 185, 129),       # Emerald
        "glow": (245, 158, 11, 45),
        "secondary_glow": (234, 88, 12, 35),
    },
    "saudi_gold": {
        "primary": (217, 119, 6),       # Warm Gold
        "primary_light": (251, 191, 36),
        "accent": (16, 185, 129),       # Green
        "glow": (217, 119, 6, 45),
        "secondary_glow": (16, 185, 129, 35),
    },
    "deeptech_purple": {
        "primary": (139, 92, 246),      # Violet
        "primary_light": (196, 181, 253),
        "accent": (6, 182, 212),        # Cyan
        "glow": (139, 92, 246, 45),
        "secondary_glow": (236, 72, 153, 30),
    },
}


def shape_arabic(text: str) -> str:
    """Correctly shapes and reorders Arabic text for PIL rendering without breaking English words."""
    if not text:
        return ""
    # Strip emojis that cause box glyphs in standard text fonts
    cleaned = "".join(ch for ch in str(text) if ord(ch) < 0x1F000 and ch not in "⚡📌🚀🇸🇦🇦🇪🏢🤖🏦💡")
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


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Loads appropriate Noto Sans Arabic or fallback system font."""
    font_path = NOTO_FONT_PATH if NOTO_FONT_PATH.exists() else AMIRI_FONT_PATH
    if not font_path.exists():
        # Fallback to system fonts
        for sys_path in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/tahoma.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            if os.path.exists(sys_path):
                font_path = Path(sys_path)
                break

    try:
        return ImageFont.truetype(str(font_path), size)
    except Exception as e:
        logger.warning("Could not load font from %s (%s). Using default.", font_path, e)
        return ImageFont.load_default()


def render_editorial_news_card(
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
    theme_name: str = "fintech_emerald",
    target_path: Optional[Path] = None,
) -> Path:
    """
    Renders a pristine 16:9 (1280x720) executive news card.
    """
    width, height = 1280, 720
    theme = THEMES.get(theme_name, THEMES["fintech_emerald"])
    primary = theme["primary"]
    primary_light = theme["primary_light"]
    accent = theme["accent"]

    # 1. Base Deep Luxury Slate Canvas
    img = Image.new("RGB", (width, height), (11, 15, 25))

    # 2. Ambient Gradient Glows (Soft studio lighting)
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([850, -150, 1400, 350], fill=theme["glow"])
    glow_draw.ellipse([-100, 420, 550, 950], fill=theme["secondary_glow"])
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    img.paste(glow, (0, 0), glow)

    # 3. Top Accent Line (Gradient)
    draw = ImageDraw.Draw(img)
    for x in range(width):
        ratio = x / width
        r = int(primary[0] * (1 - ratio) + accent[0] * ratio)
        g = int(primary[1] * (1 - ratio) + accent[1] * ratio)
        b = int(primary[2] * (1 - ratio) + accent[2] * ratio)
        draw.line([(x, 0), (x, 4)], fill=(r, g, b))

    # 4. Fonts
    title_font = _get_font(36)
    sub_font = _get_font(21)
    tag_font = _get_font(18)
    metric_num_font = _get_font(44)
    metric_lbl_font = _get_font(19)
    name_font = _get_font(22)
    role_font = _get_font(16)

    # 5. Top Header Badges
    # Category Tag (Right side)
    cat_text = shape_arabic(category_badge or "التقنية المالية والتمويل | FINTECH")
    cat_bbox = draw.textbbox((0, 0), cat_text, font=tag_font)
    cat_w = cat_bbox[2] - cat_bbox[0]
    cat_x = width - 70 - cat_w
    draw.rounded_rectangle([cat_x - 18, 40, width - 52, 78], radius=8, fill=(15, 28, 42), outline=primary, width=1)
    draw.ellipse([width - 68, 55, width - 60, 63], fill=primary_light)
    draw.text((cat_x - 8, 46), cat_text, font=tag_font, fill=primary_light)

    # Event Type / Breaking (Left side)
    event_text = shape_arabic(event_badge or "تطور تقني جديد • MARKET UPDATE")
    event_bbox = draw.textbbox((0, 0), event_text, font=tag_font)
    event_w = event_bbox[2] - event_bbox[0]
    draw.rounded_rectangle([52, 40, 52 + event_w + 40, 78], radius=8, fill=(28, 24, 14), outline=accent, width=1)
    draw.ellipse([66, 55, 74, 63], fill=accent)
    draw.text((84, 46), event_text, font=tag_font, fill=accent)

    # 6. Main Card Panel (Glassmorphism Container)
    panel = Image.new("RGBA", (width - 104, 450), (17, 24, 39, 215))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle([0, 0, width - 104, 450], radius=16, outline=(38, 50, 75), width=1)
    img.paste(panel, (52, 105), panel)

    draw = ImageDraw.Draw(img)

    # 7. Left Column: Big Metric Box
    stat_x = 85
    stat_y = 135
    stat_w = 330
    stat_h = 220
    draw.rounded_rectangle([stat_x, stat_y, stat_x + stat_w, stat_y + stat_h], radius=12, fill=(12, 18, 30), outline=primary, width=2)
    
    # Glowing Indicator inside stat box
    draw.ellipse([stat_x + 20, stat_y + 24, stat_x + 30, stat_y + 34], fill=primary_light)
    val_lbl = shape_arabic(metric_label or "القيمة التقديرية / المؤشر")
    draw.text((stat_x + 38, stat_y + 19), val_lbl, font=metric_lbl_font, fill=(148, 163, 184))

    # Metric Number / Stat
    display_metric = metric_value.strip() if metric_value else "LEADERSHIP"
    draw.text((stat_x + 20, stat_y + 65), display_metric, font=metric_num_font, fill=(255, 255, 255))
    
    # Sub tag
    sub_tag = shape_arabic(metric_sub or "مؤشر السوق والنمو")
    draw.text((stat_x + 20, stat_y + 150), sub_tag, font=metric_lbl_font, fill=primary_light)

    # Secondary Info Box below Stat Box
    draw.rounded_rectangle([stat_x, stat_y + stat_h + 20, stat_x + stat_w, stat_y + stat_h + 65], radius=8, fill=(18, 28, 44), outline=(40, 60, 85), width=1)
    lead_lbl = shape_arabic(f"المصدر: {source_name}" if source_name else "تحليل قطاعي تنفيذي")
    draw.text((stat_x + 15, stat_y + stat_h + 30), lead_lbl, font=role_font, fill=(203, 213, 225))

    # 8. Right Column: Headline & Editorial Bullet Points
    right_x = 450
    right_w = width - right_x - 85

    # Headline wrapping
    full_headline = f"{headline_line1.strip()} {headline_line2.strip()}".strip()
    headline_lines = wrap_text(full_headline, title_font, right_w, draw)
    
    curr_y = 135
    for h_line in headline_lines[:2]:
        draw.text((right_x, curr_y), shape_arabic(h_line), font=title_font, fill=(255, 255, 255))
        curr_y += 54

    # Elegant divider line
    div_y = max(curr_y + 12, 255)
    draw.line([(right_x, div_y), (width - 85, div_y)], fill=(45, 60, 85), width=1)

    # Bullet Points (Structured Key Takeaways)
    start_y = div_y + 18
    for bp in bullet_points[:3]:
        cleaned_bp = bp.lstrip("•- ")
        bp_lines = wrap_text(f"• {cleaned_bp}", sub_font, right_w, draw)
        for bp_l in bp_lines[:1]:  # 1 line per bullet to keep spacing pristine
            draw.text((right_x, start_y), shape_arabic(bp_l), font=sub_font, fill=(203, 213, 225))
            start_y += 42

    # Strategic Tags at bottom of right column
    tx = right_x
    for tag in sector_tags[:3]:
        t_text = shape_arabic(tag)
        tb = draw.textbbox((0, 0), t_text, font=role_font)
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([tx, 480, tx + tw + 24, 515], radius=6, fill=(22, 33, 50), outline=(45, 65, 95), width=1)
        draw.text((tx + 12, 488), t_text, font=role_font, fill=(148, 163, 184))
        tx += tw + 32

    # 9. Bottom Footer Bar (Author Branding + Verified Checkmark + Source)
    if AVATAR_PATH.exists():
        try:
            av = Image.open(AVATAR_PATH).convert("RGBA").resize((68, 68), Image.Resampling.LANCZOS)
            mask = Image.new("L", (68, 68), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 68, 68], fill=255)
            
            # Glowing border ring
            draw.ellipse([52 - 3, height - 90 - 3, 52 + 68 + 3, height - 90 + 68 + 3], fill=primary)
            img.paste(av, (52, height - 90), mask)
        except Exception as e:
            logger.debug("Could not paste avatar: %s", e)

    # Author Name & Verified Badge
    auth_name = "Mohamed Elbaloty"
    draw.text((135, height - 85), auth_name, font=name_font, fill=(255, 255, 255))
    
    auth_title = "CTO @ Sahalat"
    draw.text((135, height - 58), auth_title, font=role_font, fill=(148, 163, 184))

    # Source Attribution (Right bottom)
    if source_name:
        src_text = shape_arabic(f"المصدر المعتمد: {source_name}")
        src_bbox = draw.textbbox((0, 0), src_text, font=role_font)
        src_w = src_bbox[2] - src_bbox[0]
        draw.text((width - 70 - src_w, height - 70), src_text, font=role_font, fill=(100, 116, 139))

    if target_path is None:
        target_path = BASE_DIR / "scratch" / "news_card_output.jpg"
    
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(target_path, quality=98)
    logger.info("Executive news card created successfully at %s", target_path)
    return target_path
