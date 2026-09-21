"""
Branding & Watermark module for LinkedIn AI Publisher.
Stamps an ultra-high-definition, executive LinkedIn author badge with the user's circular avatar,
official LinkedIn icon, and name onto generated infographic images using 3x supersampling anti-aliasing.
"""

import logging
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_AVATAR_PATH = BASE_DIR / "assets" / "author_avatar.jpg"


def stamp_author_branding(
    image_path: Path,
    author_name: str = "Mohamed Elbaloty",
    tagline: str = "linkedin.com/in/MohamedElbaloty",
    avatar_path: Optional[Path] = None,
) -> Path:
    """
    Applies an ultra-crisp, high-definition author branding badge
    to the bottom-right of the generated technical infographic.
    Uses 3x Supersampling (SS=3) with Lanczos downsampling and full 4:4:4 chroma (subsampling=0)
    to eliminate all pixelation, blur, or compression artifacts.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        logger.warning("Image path does not exist for branding: %s", image_path)
        return image_path

    av_path = avatar_path or DEFAULT_AVATAR_PATH

    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size

        # Dynamic scale based on infographic resolution (calibrated for 1280x720 and 1408x768)
        base_scale = max(0.9, min(1.8, width / 1280.0))
        SS = 3  # 3x Supersampling factor for vector-sharp anti-aliasing

        # 1x Target Dimensions
        badge_h_1x = int(82 * base_scale)
        avatar_d_1x = int(62 * base_scale)
        icon_sz_1x = int(32 * base_scale)
        pad_1x = int(12 * base_scale)
        name_pt_1x = int(20 * base_scale)
        tag_pt_1x = int(13 * base_scale)

        # 3x High-Resolution Rendering Dimensions
        badge_h = badge_h_1x * SS
        avatar_d = avatar_d_1x * SS
        icon_sz = icon_sz_1x * SS
        pad = pad_1x * SS
        name_pt = name_pt_1x * SS
        tag_pt = tag_pt_1x * SS

        # Cross-platform font discovery (Windows & Linux / Railway)
        font_candidates_bold = [
            "segoeuib.ttf",
            "arialbd.ttf",
            "DejaVuSans-Bold.ttf",
            "LiberationSans-Bold.ttf",
        ]
        font_candidates_reg = [
            "segoeui.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf",
        ]

        name_font = None
        for fc in font_candidates_bold:
            try:
                name_font = ImageFont.truetype(fc, name_pt)
                break
            except Exception:
                continue
        if not name_font:
            name_font = ImageFont.load_default()

        tag_font = None
        for fc in font_candidates_reg:
            try:
                tag_font = ImageFont.truetype(fc, tag_pt)
                break
            except Exception:
                continue
        if not tag_font:
            tag_font = ImageFont.load_default()

        # Calculate exact text widths at 3x
        dummy_img = Image.new("RGBA", (10, 10))
        dummy_draw = ImageDraw.Draw(dummy_img)
        name_bbox = dummy_draw.textbbox((0, 0), author_name, font=name_font)
        tag_bbox = dummy_draw.textbbox((0, 0), tagline, font=tag_font)

        name_w = name_bbox[2] - name_bbox[0]
        tag_w = tag_bbox[2] - tag_bbox[0]
        text_w = max(name_w, tag_w)

        badge_w = pad + avatar_d + pad + icon_sz + int(10 * SS) + text_w + (pad * 2)
        badge_w_1x = badge_w // SS

        # Render 3x High-Definition Badge
        badge_canvas = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(badge_canvas)

        # 1. Frosted Slate Pill Card with Glowing Cyan Border
        b_draw.rounded_rectangle(
            (0, 0, badge_w - 1, badge_h - 1),
            radius=badge_h // 2,
            fill=(11, 17, 33, 245),
            outline=(0, 242, 254, 210),
            width=int(2.5 * SS),
        )

        # 2. Ultra-Sharp Circular Avatar
        if av_path.exists():
            av_raw = Image.open(av_path)
            av_crop = ImageOps.fit(av_raw, (avatar_d, avatar_d), Image.Resampling.LANCZOS)

            mask = Image.new("L", (avatar_d, avatar_d), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, avatar_d - 1, avatar_d - 1), fill=255)

            av_rgba = Image.new("RGBA", (avatar_d, avatar_d), (0, 0, 0, 0))
            av_rgba.paste(av_crop.convert("RGBA"), (0, 0), mask)

            # Smooth Glowing Cyan Ring
            ring_offset = int(1.5 * SS)
            ImageDraw.Draw(av_rgba).ellipse(
                (ring_offset, ring_offset, avatar_d - ring_offset - 1, avatar_d - ring_offset - 1),
                outline=(0, 242, 254, 255),
                width=int(2.5 * SS),
            )

            av_x = pad
            av_y = (badge_h - avatar_d) // 2
            badge_canvas.paste(av_rgba, (av_x, av_y), av_rgba)

        # 3. Official LinkedIn Icon
        icon = Image.new("RGBA", (icon_sz, icon_sz), (0, 0, 0, 0))
        icon_draw = ImageDraw.Draw(icon)
        icon_draw.rounded_rectangle(
            (0, 0, icon_sz - 1, icon_sz - 1),
            radius=int(icon_sz * 0.22),
            fill=(10, 102, 194, 255),
        )

        in_font = None
        for fc in font_candidates_bold:
            try:
                in_font = ImageFont.truetype(fc, int(icon_sz * 0.65))
                break
            except Exception:
                continue
        if not in_font:
            in_font = ImageFont.load_default()

        ibox = icon_draw.textbbox((0, 0), "in", font=in_font)
        iw, ih = ibox[2] - ibox[0], ibox[3] - ibox[1]
        icon_draw.text(
            ((icon_sz - iw) // 2, (icon_sz - ih) // 2 - int(icon_sz * 0.08)),
            "in",
            fill=(255, 255, 255, 255),
            font=in_font,
        )

        icon_x = pad + avatar_d + pad
        icon_y = (badge_h - icon_sz) // 2
        badge_canvas.paste(icon, (icon_x, icon_y), icon)

        # 4. Bold Typography & Legible Cyan Handle
        text_x = icon_x + icon_sz + int(10 * SS)
        name_y = (badge_h // 2) - int(24 * SS)
        tag_y = (badge_h // 2) + int(4 * SS)

        b_draw.text((text_x, name_y), author_name, fill=(255, 255, 255, 255), font=name_font)
        b_draw.text((text_x, tag_y), tagline, fill=(0, 242, 254, 255), font=tag_font)

        # Downscale 3x badge to 1x using high-order Lanczos anti-aliasing
        badge_1x = badge_canvas.resize((badge_w_1x, badge_h_1x), Image.Resampling.LANCZOS)

        # Position badge at bottom-right with proportional margins
        margin_x = int(28 * base_scale)
        margin_y = int(28 * base_scale)
        pos_x = width - badge_w_1x - margin_x
        pos_y = height - badge_h_1x - margin_y

        # Alpha Composite onto Infographic
        img.paste(badge_1x, (pos_x, pos_y), badge_1x)

        # Save with Maximum Quality (98) and Full 4:4:4 Chroma Subsampling (subsampling=0)
        final_img = img.convert("RGB")
        final_img.save(image_path, format="JPEG", quality=98, subsampling=0)
        logger.info("Successfully stamped Ultra-HD author branding on %s", image_path)

    except Exception as e:
        logger.error("Failed to stamp author branding onto %s: %s", image_path, e, exc_info=True)

    return image_path
