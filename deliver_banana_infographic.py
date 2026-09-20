import asyncio
import os
import sys
from pathlib import Path
from PIL import Image

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chat_id = TELEGRAM_CHAT_ID
    
    state_img = Path("flow_banana_generation_state.png")
    target_img = Path("output_images/powering_ai_grid_banana_pro.png")
    
    if state_img.exists():
        with Image.open(state_img) as im:
            # Crop the top-left tile: "POWERING AI IS A GRID ARCHITECTURE PROBLEM"
            # In 1280x720 canvas: left=248, top=105, right=740, bottom=490
            box = (248, 105, 739, 489)
            cropped = im.crop(box)
            cropped.save(target_img)
            print("Cropped pristine Nano Banana Pro infographic saved to:", target_img)
            
    # Send to Telegram
    caption = "🍌 **[تصميم Nano Banana Pro المعتمد على Google Flow]**\nأكبر عقبة تواجه ثورة الذكاء الاصطناعي اليوم ليست خوارزميات النماذج، بل بنية شبكات الطاقة (Grid Architecture)!"
    with open(target_img, "rb") as f:
        await bot.send_photo(
            chat_id=chat_id,
            photo=f,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
        )
    print("Sent photo to Telegram!")
    
    # Send uncompressed document
    with open(target_img, "rb") as f:
        await bot.send_document(
            chat_id=chat_id,
            document=f,
            caption="📁 [Master Quality Infographic - Nano Banana Pro 🍌]",
        )
    print("Sent uncompressed document to Telegram!")

if __name__ == "__main__":
    asyncio.run(main())
