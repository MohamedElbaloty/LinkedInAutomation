"""
Telegram Bot delivery module for ai_news_agent.
Uses python-telegram-bot to dispatch generated technical visual assets and
LinkedIn post text to Telegram channels or private chats, handling caption character limits cleanly.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Union

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

# Telegram API constants
MAX_CAPTION_LENGTH = 1024
MAX_MESSAGE_LENGTH = 4096


class TelegramPublisher:
    """Handles publishing images and long-form posts to Telegram."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[Union[str, int]] = None):
        self.bot_token = (bot_token or TELEGRAM_BOT_TOKEN).strip()
        self.chat_id = str(chat_id or TELEGRAM_CHAT_ID).strip()

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is missing. Please set it in your environment or .env file.")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is missing. Please set it in your environment or .env file.")

        self.bot = Bot(token=self.bot_token)

    async def _send_text_safely(self, text: str) -> None:
        """
        Sends text to Telegram, attempting Markdown first, with graceful fallback to plain text
        if Telegram parsing errors occur. Handles messages exceeding 4096 characters by chunking.
        """
        # Chunk text if necessary
        chunks = [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]

        for chunk in chunks:
            try:
                # Attempt to send with standard Markdown
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=False,
                )
            except BadRequest as e:
                logger.warning("Markdown parsing failed (%s), falling back to raw plain text.", str(e))
                # Fallback to plain text if Markdown format is invalid
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=chunk,
                    parse_mode=None,
                    disable_web_page_preview=False,
                )

    async def send_bundle_async(
        self,
        image_path: Union[str, Path],
        post_text: str,
        short_hook: Optional[str] = None,
    ) -> None:
        """
        Asynchronously sends the image and text bundle to Telegram.

        Caption limit handling:
        - If post_text is within Telegram's 1024 caption limit, sends photo with post_text as caption.
        - If post_text exceeds 1024 characters, sends photo with the short_hook as caption,
          followed immediately by the full post_text in a subsequent connected message.
        """
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image file does not exist at path: {image_file}")

        logger.info("Sending news bundle to Telegram chat %s...", self.chat_id)

        try:
            with open(image_file, "rb") as photo_stream:
                if len(post_text) <= MAX_CAPTION_LENGTH:
                    # Post fits within single photo caption
                    try:
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo_stream,
                            caption=post_text,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except BadRequest:
                        # Fallback without parse_mode
                        photo_stream.seek(0)
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo_stream,
                            caption=post_text,
                            parse_mode=None,
                        )
                    logger.info("Sent photo with full caption successfully.")
                else:
                    # Post exceeds 1024 characters
                    # 1. Send photo with short hook as caption
                    caption = (short_hook or post_text[:MAX_CAPTION_LENGTH - 3] + "...").strip()
                    if len(caption) > MAX_CAPTION_LENGTH:
                        caption = caption[:MAX_CAPTION_LENGTH - 3] + "..."

                    try:
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo_stream,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except BadRequest:
                        photo_stream.seek(0)
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo_stream,
                            caption=caption,
                            parse_mode=None,
                        )

                    # 2. Immediately send the complete full post text
                    await self._send_text_safely(post_text)
                    logger.info("Sent photo followed by full post message successfully.")

                # 3. Also send uncompressed master file as Document to bypass Telegram compression
                try:
                    with open(image_file, "rb") as doc_stream:
                        await self.bot.send_document(
                            chat_id=self.chat_id,
                            document=doc_stream,
                            caption="📁 [Master Quality File - 100% Uncompressed Nano Banana Pro 🍌]",
                        )
                    logger.info("Sent uncompressed master image document successfully.")
                except Exception as doc_err:
                    logger.warning("Failed to send uncompressed document: %s", str(doc_err))

        except TelegramError as te:
            logger.error("Telegram API error occurred: %s", str(te), exc_info=True)
            raise

    def send_bundle(
        self,
        image_path: Union[str, Path],
        post_text: str,
        short_hook: Optional[str] = None,
    ) -> None:
        """Synchronous wrapper for send_bundle_async."""
        asyncio.run(self.send_bundle_async(image_path=image_path, post_text=post_text, short_hook=short_hook))
