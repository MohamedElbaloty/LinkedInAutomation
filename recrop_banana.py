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
    target_img = Path("output_images/powering_ai_grid_banana_pro_clean.png")
    
    if state_img.exists():
        with Image.open(state_img) as im:
            # Clean crop: left=248, top=105, right=739, bottom=384
            box = (248, 105, 739, 384)
            cropped = im.crop(box)
            cropped.save(target_img)
            print("Pristine crop saved to:", target_img)
            
    caption = "🍌 **[تصميم Nano Banana Pro المعتمد على Google Flow - النسخة الدقيقة]**\nأكبر عقبة تواجه ثورة الذكاء الاصطناعي اليوم ليست خوارزميات النماذج، بل بنية شبكات الطاقة (Grid Architecture)!"
    with open(target_img, "rb") as f:
        await bot.send_photo(
            chat_id=chat_id,
            photo=f,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
        )
    print("Sent clean photo to Telegram!")
    
    with open(target_img, "rb") as f:
        await bot.send_document(
            chat_id=chat_id,
            document=f,
            caption="📁 [Master Quality Infographic - Nano Banana Pro 🍌]",
        )
    print("Sent clean document to Telegram!")

if __name__ == "__main__":
    asyncio.run(main())
