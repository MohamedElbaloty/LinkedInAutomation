"""
Interactive Telegram Bot for AI News LinkedIn Publisher.
Allows the user to browse top available AI news titles in Telegram,
choose one by tapping an inline button, and autonomously generates the Arabic post,
renders the Nano Banana Pro infographic on Google Flow, and publishes to LinkedIn.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

# Ensure Windows terminal supports UTF-8 cleanly
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from fetcher import Article, fetch_unread_articles, mark_as_posted
from ai_generator import create_ai_bundle
from linkedin_publisher import publish_to_linkedin, LINKEDIN_PROFILE_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger("interactive_bot")

# In-memory storage for current active articles presented to the user
active_articles_cache: Dict[str, Article] = {}


def build_news_menu(articles: List[Article]) -> tuple[str, InlineKeyboardMarkup]:
    """Builds a formatted message and inline buttons for the top articles."""
    global active_articles_cache
    active_articles_cache.clear()

    if not articles:
        text = (
            "🤖 **لا توجد أخبار جديدة غير مقروءة حالياً في الخلاصات.**\n"
            "اضغط على الزر أدناه لإعادة الفحص لاحقاً."
        )
        keyboard = [[InlineKeyboardButton("🔄 فحص وتحديث الأخبار", callback_data="refresh_news")]]
        return text, InlineKeyboardMarkup(keyboard)

    text_lines = [
        "👋 **أهلاً بك! إليك أحدث وأبرز أخبار الذكاء الاصطناعي المتاحة الآن:**\n",
        "👇 *اضغط على رقم الخبر الذي ترغب في صياغته وتوليد تصميمه ونشره:*",
    ]

    buttons = []
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for i, art in enumerate(articles[:5]):
        short_id = art.id[:10]
        active_articles_cache[short_id] = art
        emoji = emojis[i] if i < len(emojis) else f"{i+1}️⃣"
        
        # Display title in message body
        text_lines.append(f"\n{emoji} **[{art.source}]**\n{art.title}")
        
        # Add button
        btn_label = f"{emoji} نشر: {art.title[:45]}..."
        buttons.append([InlineKeyboardButton(btn_label, callback_data=f"publish_{short_id}")])

    buttons.append([InlineKeyboardButton("🔄 جلب وتحديث أخبار أخرى", callback_data="refresh_news")])
    return "\n".join(text_lines), InlineKeyboardMarkup(buttons)


async def send_menu(chat_id: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches articles and sends the interactive selection menu."""
    articles = fetch_unread_articles()
    text, markup = build_news_menu(articles)
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start or /news commands."""
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("🔎 جاري جلب أحدث الأخبار التقنية وتحليلها...")
    await send_menu(chat_id, context)


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline button clicks for selecting news or refreshing."""
    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = str(update.effective_chat.id)

    if data == "refresh_news":
        await query.edit_message_text("🔄 جاري تحديث الخلاصات وجلب أحدث الأخبار...")
        await send_menu(chat_id, context)
        return

    if data.startswith("publish_"):
        short_id = data.replace("publish_", "")
        article = active_articles_cache.get(short_id)

        if not article:
            await query.edit_message_text("⚠️ انتهت صلاحية هذه القائمة، يرجى طلب الأخبار مجدداً عبر /news")
            return

        # Confirm selection and start generation
        status_msg = await query.edit_message_text(
            f"🚀 **تم اختيار الخبر بنجاح:**\n"
            f"📌 *{article.title}*\n\n"
            f"⏳ **جاري العمل الآن:**\n"
            f"1. 🧠 صياغة منشور لينكد إن العربي وتحليل أبعاد الخبر عبر Gemini.\n"
            f"2. 🍌 توليد تصميم إنفوجرافيك تقني عبر Nano Banana Pro على Google Flow.\n"
            f"3. 🌐 إرسال النتيجة إلى تليجرام ونشرها على LinkedIn...\n\n"
            f"*(يرجى الانتظار دقيقة إلى دقيقتين...)*",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Run pipeline in a background thread to avoid blocking Telegram's event loop
        loop = asyncio.get_running_loop()

        def _execute_bundle():
            return create_ai_bundle(article)

        try:
            logger.info("Starting AI bundle creation for '%s'...", article.title)
            bundle = await loop.run_in_executor(None, _execute_bundle)
            post_text = bundle["post_text"]
            short_hook = bundle["short_hook"]
            image_path = Path(bundle["image_path"])

            # 1. Send photo preview to Telegram
            with open(image_path, "rb") as photo_stream:
                caption = (short_hook or post_text[:1000]).strip()
                if len(caption) > 1020:
                    caption = caption[:1017] + "..."
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_stream,
                    caption=caption,
                )

            # 2. Send complete post text to Telegram
            await context.bot.send_message(
                chat_id=chat_id,
                text=post_text,
                parse_mode=None,
            )

            # 3. Send uncompressed master quality document
            with open(image_path, "rb") as doc_stream:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=doc_stream,
                    caption="📁 [Master Quality Infographic - Nano Banana Pro 🍌]",
                )

            # 4. Attempt publishing to LinkedIn
            linkedin_published = False
            linkedin_msg = ""

            # Check if LinkedIn session exists
            if LINKEDIN_PROFILE_DIR.exists():
                try:
                    logger.info("Publishing selected article to LinkedIn...")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⏳ جاري نشر المنشور والتصميم على حسابك في LinkedIn الآن...",
                    )
                    
                    def _do_publish():
                        return publish_to_linkedin(post_text, image_path)

                    linkedin_published = await loop.run_in_executor(None, _do_publish)
                    if linkedin_published:
                        linkedin_msg = "🎉 **تم النشر بنجاح على حسابك في LinkedIn!**"
                        # Send confirmation screenshot if available
                        screenshot_path = Path("linkedin_published_success.png")
                        if screenshot_path.exists():
                            with open(screenshot_path, "rb") as ss:
                                await context.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=ss,
                                    caption="📸 تأكيد النشر المباشر من داخل صفحتك في LinkedIn",
                                )
                except Exception as lk_err:
                    logger.warning("LinkedIn publish failed or session not logged in: %s", str(lk_err))
                    linkedin_msg = (
                        f"⚠️ تعذر النشر المباشر على LinkedIn ({str(lk_err)[:80]}).\n"
                        "يرجى تشغيل `python login_linkedin.py` لمرة واحدة لتسجيل الدخول."
                    )
            else:
                linkedin_msg = (
                    "ℹ️ المنشور والتصميم جاهزان بالكامل ومرفقان أعلاه!\n"
                    "لتفعيل النشر المباشر التلقائي من زر تليجرام، شغّل أمر `python login_linkedin.py` لتسجيل الدخول مرة واحدة."
                )

            # 5. Mark as posted in SQLite
            mark_as_posted(
                article_id=article.id,
                title=article.title,
                published_at=article.published_at,
            )

            # Final success notice
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ **اكتملت العملية بنجاح!**\n\n{linkedin_msg}",
                parse_mode=ParseMode.MARKDOWN,
            )

            # Send menu again for next post
            await send_menu(chat_id, context)

        except Exception as err:
            logger.error("Error processing article '%s': %s", article.title, str(err), exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ حدث خطأ أثناء التوليد: {str(err)[:150]}\nيرجى المحاولة مجدداً عبر /news",
            )


async def main():
    """Starts the interactive Telegram bot application."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing in .env")

    logger.info("Initializing Interactive Telegram News Bot...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler(["start", "news", "menu"], start_command))
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    # Catch-all text messages trigger the menu
    async def any_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await start_command(update, context)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_text))

    logger.info("Bot is now polling! Send /start or /news in Telegram chat.")
    
    # Send initial welcome menu to target chat on launch
    if TELEGRAM_CHAT_ID:
        try:
            articles = fetch_unread_articles()
            text, markup = build_news_menu(articles)
            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"🚀 **تم تشغيل روبوت الأخبار التفاعلي!**\n\n{text}",
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info("Sent welcome news menu to chat %s.", TELEGRAM_CHAT_ID)
        except Exception as e:
            logger.warning("Could not send initial menu: %s", str(e))

    # Run polling
    await app.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interactive bot stopped.")
