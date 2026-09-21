"""
Branding & Watermark module for LinkedIn AI Publisher.
Stamps a professional frosted-glass author badge with the user's circular avatar,
official LinkedIn icon, and name onto generated infographic images.
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
    Applies an ultra-sleek, executive LinkedIn author branding pill badge
    to the bottom-right of the generated technical infographic.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        logger.warning("Image path does not exist for branding: %s", image_path)
        return image_path

    av_path = avatar_path or DEFAULT_AVATAR_PATH

    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        scale = max(0.75, width / 1280.0)

        # Proportional badge dimensions
        badge_height = int(68 * scale)
        avatar_size = int(52 * scale)
        icon_size = int(28 * scale)
        pad = int(10 * scale)

        # Modern typography
        try:
            name_font = ImageFont.truetype("arialbd.ttf", int(18 * scale))
            tag_font = ImageFont.truetype("arial.ttf", int(12 * scale))
        except Exception:
            try:
                name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(18 * scale))
                tag_font = ImageFont.truetype("DejaVuSans.ttf", int(12 * scale))
            except Exception:
                name_font = ImageFont.load_default()
                tag_font = ImageFont.load_default()

        # Calculate exact bounding boxes
        dummy = ImageDraw.Draw(img)
        name_bbox = dummy.textbbox((0, 0), author_name, font=name_font)
        name_w = name_bbox[2] - name_bbox[0]
        tag_bbox = dummy.textbbox((0, 0), tagline, font=tag_font)
        tag_w = tag_bbox[2] - tag_bbox[0]
        text_w = max(name_w, tag_w)

        badge_width = avatar_size + icon_size + text_w + (pad * 5)
        margin_x = int(25 * scale)
        margin_y = int(25 * scale)
        bx = width - badge_width - margin_x
        by = height - badge_height - margin_y

        # Badge Overlay Layer
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)

        # Frosted glass card background
        bg_box = (bx, by, bx + badge_width, by + badge_height)
        draw_ov.rounded_rectangle(
            bg_box,
            radius=int(badge_height // 2),
            fill=(10, 15, 29, 235),
            outline=(0, 242, 254, 190),
            width=int(max(1, 2 * scale)),
        )

        # 1. Circular Author Avatar
        if av_path.exists():
            av_raw = Image.open(av_path)
            av_crop = ImageOps.fit(av_raw, (avatar_size, avatar_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            av_rgba = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
            av_rgba.paste(av_crop.convert("RGBA"), (0, 0), mask)
            
            # Glowing border ring around avatar
            ImageDraw.Draw(av_rgba).ellipse(
                (1, 1, avatar_size - 2, avatar_size - 2),
                outline=(0, 242, 254, 255),
                width=int(max(1, 2 * scale)),
            )
            av_x = bx + pad
            av_y = by + (badge_height - avatar_size) // 2
            overlay.paste(av_rgba, (av_x, av_y), av_rgba)

        # 2. Official LinkedIn Icon
        icon = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
        draw_icon = ImageDraw.Draw(icon)
        draw_icon.rounded_rectangle(
            (0, 0, icon_size, icon_size),
            radius=max(2, icon_size // 5),
            fill=(10, 102, 194, 255),
        )
        try:
            in_font = ImageFont.truetype("arialbd.ttf", int(icon_size * 0.65))
        except Exception:
            in_font = ImageFont.load_default()
        ibox = draw_icon.textbbox((0, 0), "in", font=in_font)
        iw, ih = ibox[2] - ibox[0], ibox[3] - ibox[1]
        draw_icon.text(
            ((icon_size - iw) // 2, (icon_size - ih) // 2 - int(icon_size * 0.08)),
            "in",
            fill=(255, 255, 255, 255),
            font=in_font,
        )

        icon_x = bx + pad + avatar_size + pad
        icon_y = by + (badge_height - icon_size) // 2
        overlay.paste(icon, (icon_x, icon_y), icon)

        # 3. Typography (Author Name & Handle)
        text_x = icon_x + icon_size + int(8 * scale)
        name_y = by + int(12 * scale)
        tag_y = name_y + int(22 * scale)

        draw_ov.text((text_x, name_y), author_name, fill=(255, 255, 255, 255), font=name_font)
        draw_ov.text((text_x, tag_y), tagline, fill=(0, 242, 254, 255), font=tag_font)

        # Alpha Composite & Save
        final_img = Image.alpha_composite(img, overlay).convert("RGB")
        final_img.save(image_path, format="JPEG", quality=95)
        logger.info("Successfully stamped Mohamed Elbaloty branding badge on %s", image_path)

    except Exception as e:
        logger.error("Failed to stamp author branding onto %s: %s", image_path, e)

    return image_path
