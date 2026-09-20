import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from fetcher import get_latest_unread_article, mark_as_posted
from ai_generator import create_ai_bundle

async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chat_id = TELEGRAM_CHAT_ID
    
    print("Fetching latest high-impact AI architecture article...")
    article = get_latest_unread_article()
    if not article:
        print("No unread articles found!")
        return

    print(f"Processing article: '{article.title}' from {article.source}...")
    
    # 1. Generate AI bundle (copy, hook, Banana Pro infographic prompt, and Flow generation)
    loop = asyncio.get_running_loop()
    bundle = await loop.run_in_executor(None, create_ai_bundle, article)
    
    post_text = bundle["post_text"]
    short_hook = bundle["short_hook"]
    image_prompt = bundle["image_prompt"]
    image_path = Path(bundle["image_path"])
    
    print("AI Bundle created successfully!")
    print(f"Image path: {image_path} (size: {image_path.stat().st_size if image_path.exists() else 0} bytes)")
    
    # 2. Deliver to Telegram
    # A) Send Photo with short hook caption
    if image_path.exists():
        with open(image_path, "rb") as photo_stream:
            caption = f"🍌 **[Nano Banana Pro Infographic]**\n{short_hook}"
            if len(caption) > 1020:
                caption = caption[:1017] + "..."
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo_stream,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
        print("Sent infographic photo to Telegram!")

    # B) Send complete LinkedIn post text
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=post_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as me:
        print(f"Markdown send failed ({me}), sending as raw text...")
        await bot.send_message(
            chat_id=chat_id,
            text=post_text,
            parse_mode=None,
        )
    print("Sent post text to Telegram!")

    # C) Send the exact Nano Banana Pro Infographic Prompt
    prompt_msg = (
        "🎨 **[البرومبت الأصلي المعتمد لـ Nano Banana Pro على Google Flow]**:\n\n"
        f"```text\n{image_prompt}\n```"
    )
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=prompt_msg,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        await bot.send_message(
            chat_id=chat_id,
            text=prompt_msg,
            parse_mode=None,
        )
    print("Sent Banana Pro prompt to Telegram!")

    # D) Send uncompressed original document
    if image_path.exists():
        with open(image_path, "rb") as doc_stream:
            await bot.send_document(
                chat_id=chat_id,
                document=doc_stream,
                caption="📁 [Master Quality Infographic - Nano Banana Pro 🍌]",
            )
        print("Sent uncompressed document to Telegram!")

    # 3. Mark article as posted in SQLite
    mark_as_posted(article.id, article.title, article.published_at)
    print("Marked article as posted in SQLite database!")
    print("DONE! Check Telegram.")

if __name__ == "__main__":
    asyncio.run(main())
