import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.handlers import base_router, tiktok_router

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    try:
        config.validate_token()
    except ValueError as err:
        logger.error("Configuration error: %s", err)
        sys.exit(1)

    # Ensure temporary directory exists
    config.temp_dir.mkdir(parents=True, exist_ok=True)

    bot = Bot(
        token=config.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register routers
    dp.include_router(base_router)
    dp.include_router(tiktok_router)

    logger.info("Bot starting...")

    try:
        # Delete pending webhook updates to prevent spamming old messages on startup
        await bot.delete_webhook(drop_pending_updates=True)
        bot_user = await bot.get_me()
        logger.info("Bot @%s successfully authenticated and polling!", bot_user.username)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot session closed. Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
