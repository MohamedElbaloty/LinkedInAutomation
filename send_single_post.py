import asyncio
import os
import sys
from pathlib import Path
from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chat_id = TELEGRAM_CHAT_ID
    image_path = Path("output_images/powering_ai_grid_banana_pro_perfect.png")
    
    if not image_path.exists():
        print("Image not found, fallback to state image...")
        image_path = Path("flow_banana_generation_state.png")

    post_caption = (
        "⚡ **أزمة الذكاء الاصطناعي القادمة: مشكلة بنية طاقة وليست مجرد خوارزميات!**\n\n"
        "في حادثة كشفت هشاشة التوسع الحالي، أدى عطل كهربائي مفاجئ في فرجينيا إلى انقطاع أكثر من **3 جيجاوات** من أحمال مراكز بيانات الـ AI خلال ثوانٍ معدودة!\n\n"
        "🔬 **التحليل المعماري والهندسي:**\n"
        "1️⃣ **The Concentration Risk:** التكدس الشديد لمراكز البيانات في بقع جغرافية محددة يخلق نقطة فشل مركزية (Single Point of Failure) تهدد استقرار الشبكات الإقليمية.\n"
        "2️⃣ **Step Load Spikes:** أحمال تدريب الـ LLMs تختلف جذرياً عن الحوسبة السحابية التقليدية؛ فهي تتسبب بقفزات طاقة حادة ومفاجئة يصعب على محطات التوليد استيعابها.\n"
        "3️⃣ **The Architectural Shift:** الحل ليس مجرد بناء شرائح أسرع، بل إعادة هندسة منظومة الطاقة: الانتقال إلى الحوسبة الموزعة، والشبكات الذكية، وتوليد الطاقة الموضعي عبر مفاعلات SMR النووية المصغرة.\n\n"
        "💬 **برأيك، هل تصبح قدرة الوصول إلى مصادر طاقة مخصصة هي الميزة التنافسية الحقيقية لعمالقة الـ AI؟**\n\n"
        "#AI #DataCenters #SoftwareEngineering #Architecture #CloudComputing #Energy"
    )

    print(f"Caption length: {len(post_caption)} characters (Telegram photo limit is 1024).")
    
    with open(image_path, "rb") as photo_file:
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo_file,
                caption=post_caption,
                parse_mode=ParseMode.MARKDOWN,
            )
            print("Successfully sent unified photo + text post to Telegram!")
        except Exception as e:
            print(f"Markdown parsing failed ({e}), trying plain text caption...")
            photo_file.seek(0)
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo_file,
                caption=post_caption,
                parse_mode=None,
            )
            print("Successfully sent unified post with plain text to Telegram!")

if __name__ == "__main__":
    asyncio.run(main())
