import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.types import FSInputFile, InputMediaPhoto, Message

from bot.config import config
from bot.services import (
    TikTokError,
    TikTokItemType,
    TikTokNotFoundError,
    TikTokService,
    TikTokSizeLimitError,
)
from bot.utils import extract_tiktok_urls, format_caption

logger = logging.getLogger(__name__)

router = Router(name="tiktok_router")
tiktok_service = TikTokService(timeout_seconds=config.download_timeout)


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Handle text messages and detect TikTok URLs."""
    urls = extract_tiktok_urls(message.text)

    # If no URL in text, check caption
    if not urls and message.caption:
        urls = extract_tiktok_urls(message.caption)

    # If still no URL found:
    if not urls:
        # If in private chat and not a command, give a polite hint
        if message.chat.type == ChatType.PRIVATE and not message.text.startswith("/"):
            await message.reply(
                "🤔 Пожалуйста, отправьте корректную ссылку на видео или фото из TikTok.\n\n"
                "Пример: <code>https://vm.tiktok.com/...</code> или <code>https://www.tiktok.com/@user/video/...</code>",
                parse_mode="HTML",
            )
        return

    # Process all detected TikTok URLs (usually just 1)
    for url in urls:
        await process_tiktok_url(message, url)


async def process_tiktok_url(message: Message, url: str) -> None:
    """Download and send TikTok content (video or photo slideshow)."""
    status_msg = await message.reply("⏳ <b>Получаю информацию о публикации...</b>", parse_mode="HTML")
    temp_dir = config.temp_dir / f"tt_{uuid.uuid4().hex[:12]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = config.max_file_size_mb * 1024 * 1024

    try:
        # Send typing action
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        # Fetch media info
        media_info = await tiktok_service.get_media_info(url)

        author_nick = media_info.author.nickname if media_info.author else None
        author_user = media_info.author.username if media_info.author else None
        caption = format_caption(
            title=media_info.title,
            author_nickname=author_nick,
            author_username=author_user,
        )

        if media_info.media_type == TikTokItemType.PHOTOS:
            await handle_photos(
                message=message,
                status_msg=status_msg,
                media_info=media_info,
                caption=caption,
                temp_dir=temp_dir,
            )
        else:
            await handle_video(
                message=message,
                status_msg=status_msg,
                media_info=media_info,
                caption=caption,
                temp_dir=temp_dir,
                max_bytes=max_bytes,
            )

        # Delete status message on success
        try:
            await status_msg.delete()
        except Exception:
            pass

    except TikTokNotFoundError as err:
        logger.info("Not found error for %s: %s", url, err)
        try:
            await status_msg.edit_text(f"❌ <b>Ошибка:</b> {err}", parse_mode="HTML")
        except Exception:
            pass

    except TikTokSizeLimitError as err:
        logger.warning("Size limit error for %s: %s", url, err)
        text = (
            f"⚠️ {err}\n\n"
            "Telegram ограничивает размер файлов для ботов до 50 МБ."
        )
        if media_info and media_info.video_url:
            text += f"\n\nВы можете скачать видео напрямую: <a href='{media_info.video_url}'>Скачать видео</a>"
        try:
            await status_msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            pass

    except TikTokError as err:
        logger.error("TikTok error for %s: %s", url, err)
        try:
            await status_msg.edit_text(
                f"❌ <b>Не удалось скачать:</b> {err}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    except Exception as err:
        logger.exception("Unexpected error processing TikTok URL %s: %s", url, err)
        try:
            await status_msg.edit_text(
                "❌ <b>Произошла ошибка при обработке публикации.</b>\n"
                "Пожалуйста, попробуйте еще раз позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    finally:
        # Clean up temporary files
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as cleanup_err:
            logger.warning("Error cleaning temp directory %s: %s", temp_dir, cleanup_err)


async def handle_video(
    message: Message,
    status_msg: Message,
    media_info,
    caption: str,
    temp_dir: Path,
    max_bytes: int,
) -> None:
    """Download and send video."""
    video_url = media_info.video_url
    if not video_url:
        raise TikTokError("Не найдена ссылка на скачивание видео без водяных знаков.")

    try:
        await status_msg.edit_text("⏳ <b>Скачиваю видео в HD без вотермарок...</b>", parse_mode="HTML")
    except Exception:
        pass

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO)

    video_path = temp_dir / "video.mp4"

    try:
        await tiktok_service.download_file(video_url, video_path, max_bytes=max_bytes)
    except TikTokSizeLimitError:
        # If HD exceeded limit, try standard quality if available
        if media_info.video_url_sd and media_info.video_url_sd != video_url:
            logger.info("HD video too large, trying SD version...")
            try:
                await status_msg.edit_text("⏳ <b>HD версия больше 50 МБ, скачиваю в стандартном качестве...</b>", parse_mode="HTML")
            except Exception:
                pass
            await tiktok_service.download_file(media_info.video_url_sd, video_path, max_bytes=max_bytes)
        else:
            raise

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO)

    await message.reply_video(
        video=FSInputFile(video_path),
        caption=caption or None,
        duration=media_info.duration or None,
        supports_streaming=True,
        parse_mode="HTML",
    )


async def handle_photos(
    message: Message,
    status_msg: Message,
    media_info,
    caption: str,
    temp_dir: Path,
) -> None:
    """Download and send photo slideshow / album."""
    images = media_info.images
    if not images:
        raise TikTokError("В публикации отсутствуют изображения для скачивания.")

    photo_count = len(images)
    try:
        await status_msg.edit_text(
            f"⏳ <b>Скачиваю фото-публикацию ({photo_count} фото)...</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)

    images_dir = temp_dir / "images"
    image_paths = await tiktok_service.download_images(images, images_dir)

    if not image_paths:
        raise TikTokError("Не удалось сохранить изображения публикации.")

    # If only 1 photo:
    if len(image_paths) == 1:
        await message.reply_photo(
            photo=FSInputFile(image_paths[0]),
            caption=caption or None,
            parse_mode="HTML",
        )
    else:
        # Split into chunks of 10 (Telegram media group limit)
        chunk_size = 10
        for i in range(0, len(image_paths), chunk_size):
            chunk = image_paths[i : i + chunk_size]
            media_group: list[InputMediaPhoto] = []

            for idx, path in enumerate(chunk):
                # Put caption on the very first item of the album
                if i == 0 and idx == 0:
                    media_group.append(
                        InputMediaPhoto(
                            media=FSInputFile(path),
                            caption=caption or None,
                            parse_mode="HTML",
                        )
                    )
                else:
                    media_group.append(InputMediaPhoto(media=FSInputFile(path)))

            await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
            await message.reply_media_group(media=media_group)
            if i + chunk_size < len(image_paths):
                await asyncio.sleep(0.5)

    # If publication has background music, send it as well!
    if media_info.music and media_info.music.url:
        try:
            music_path = temp_dir / "audio.mp3"
            await tiktok_service.download_file(media_info.music.url, music_path)
            await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE)

            await message.reply_audio(
                audio=FSInputFile(music_path),
                title=media_info.music.title or "Оригинальный звук",
                performer=media_info.music.author or "TikTok",
            )
        except Exception as audio_err:
            logger.warning("Could not download/send audio for slideshow: %s", audio_err)
