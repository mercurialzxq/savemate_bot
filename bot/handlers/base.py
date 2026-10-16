from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="base_router")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Handle /start command with a warm welcome and usage instructions."""
    text = (
        "👋 <b>Привет! Я бот для скачивания контента из TikTok без водяных знаков.</b>\n\n"
        "✨ <b>Что я умею:</b>\n"
        "• 📹 Скачивать видео в максимальном HD-качестве без вотермарок\n"
        "• 🖼 Скачивать публикации из фото (слайдшоу / карусели картинок)\n"
        "• 🎵 Отправлять оригинальную аудиодорожку из видео и фото-постов\n\n"
        "📥 <b>Как мной пользоваться:</b>\n"
        "Просто отправь мне ссылку на любое видео или фото-пост из TikTok (например, из приложения TikTok или из браузера) — "
        "и я мгновенно пришлю тебе медиафайл в наилучшем качестве!\n\n"
        "<i>Поддерживаются как стандартные ссылки, так и короткие (vm.tiktok.com / vt.tiktok.com).</i>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command."""
    text = (
        "ℹ️ <b>Как скачать видео или фото из TikTok:</b>\n\n"
        "1. Откройте TikTok и найдите желаемое видео или фото-пост.\n"
        "2. Нажмите кнопку <b>«Поделиться»</b> (стрелочка) ➔ <b>«Копировать ссылку»</b>.\n"
        "3. Отправьте скопированную ссылку в этот чат.\n"
        "4. Подождите несколько секунд — бот скачает контент и пришлет вам файл без водяных знаков!\n\n"
        "📌 <b>Поддерживаемые форматы ссылок:</b>\n"
        "• <code>https://vm.tiktok.com/...</code>\n"
        "• <code>https://vt.tiktok.com/...</code>\n"
        "• <code>https://www.tiktok.com/@пользователь/video/...</code>\n"
        "• <code>https://www.tiktok.com/@пользователь/photo/...</code>\n\n"
        "Если у вас возникли вопросы или видео не скачивается, убедитесь, что аккаунт автора или видео не являются приватными."
    )
    await message.answer(text, parse_mode="HTML")
