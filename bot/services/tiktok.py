import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

TIKWM_ENDPOINTS = [
    "https://www.tikwm.com/api/",
    "https://tikwm.com/api/",
]


class TikTokItemType(str, Enum):
    VIDEO = "video"
    PHOTOS = "photos"


class TikTokError(Exception):
    """Base exception for TikTok service errors."""
    pass


class TikTokNotFoundError(TikTokError):
    """Video or post was not found, is private, or deleted."""
    pass


class TikTokSizeLimitError(TikTokError):
    """File exceeds allowed size limit."""
    pass


@dataclass
class TikTokAuthor:
    nickname: Optional[str] = None
    username: Optional[str] = None
    avatar: Optional[str] = None


@dataclass
class TikTokMusic:
    url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None


@dataclass
class TikTokMediaInfo:
    id: str
    title: str
    media_type: TikTokItemType
    author: Optional[TikTokAuthor] = None
    music: Optional[TikTokMusic] = None
    video_url: Optional[str] = None
    video_url_sd: Optional[str] = None
    video_size: Optional[int] = None
    images: list[str] = field(default_factory=list)
    duration: int = 0
    cover_url: Optional[str] = None


def make_absolute_url(url: Optional[str]) -> Optional[str]:
    """Ensure URL is absolute."""
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"https://www.tikwm.com{url}"
    return url


class TikTokService:
    """Service to fetch and download TikTok videos and photo slideshows without watermarks."""

    def __init__(self, timeout_seconds: int = 60):
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://www.tikwm.com/",
        }

    async def get_media_info(self, tiktok_url: str) -> TikTokMediaInfo:
        """
        Query TikTok metadata via TikWM API.
        Returns parsed TikTokMediaInfo with HD/SD video links or photo slideshow URLs.
        """
        async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
            last_error = None

            for endpoint in TIKWM_ENDPOINTS:
                try:
                    payload = {"url": tiktok_url, "hd": 1}
                    async with session.post(endpoint, data=payload) as resp:
                        if resp.status != 200:
                            logger.warning("Endpoint %s returned HTTP %s", endpoint, resp.status)
                            continue

                        result = await resp.json(content_type=None)
                        code = result.get("code")
                        msg = result.get("msg", "")

                        if code != 0:
                            logger.info("TikWM returned non-zero code %s: %s", code, msg)
                            if "failed" in msg.lower() or "not found" in msg.lower():
                                raise TikTokNotFoundError(
                                    "Не удалось найти видео или публикацию. "
                                    "Проверьте правильность ссылки, возможно, публикация удалена или скрыта настройками приватности."
                                )
                            raise TikTokError(f"Ошибка получения данных: {msg or 'неизвестная ошибка'}")

                        data = result.get("data")
                        if not data:
                            raise TikTokError("Пустой ответ от сервера TikTok API.")

                        return self._parse_response(data)

                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    logger.warning("Network error on %s: %s", endpoint, err)
                    last_error = err
                    continue

            if last_error:
                raise TikTokError("Сервис скачивания временно недоступен. Попробуйте снова через минуту.")
            raise TikTokError("Не удалось получить информацию о публикации.")

    def _parse_response(self, data: dict) -> TikTokMediaInfo:
        """Parse the raw response dictionary into TikTokMediaInfo."""
        post_id = str(data.get("id") or "")
        title = (data.get("title") or "").strip()
        duration = int(data.get("duration") or 0)
        cover_url = make_absolute_url(data.get("cover") or data.get("origin_cover"))

        # Author details
        author_data = data.get("author") or {}
        author = TikTokAuthor(
            nickname=author_data.get("nickname"),
            username=author_data.get("unique_id"),
            avatar=make_absolute_url(author_data.get("avatar")),
        )

        # Music details
        music_url = make_absolute_url(data.get("music"))
        music_info = data.get("music_info") or {}
        music = None
        if music_url:
            music = TikTokMusic(
                url=music_url,
                title=music_info.get("title") or "Оригинальный звук",
                author=music_info.get("author") or author.nickname or "TikTok",
            )

        # Check for photo slideshow
        raw_images = data.get("images")
        if raw_images and isinstance(raw_images, list) and len(raw_images) > 0:
            cleaned_images = [make_absolute_url(img) for img in raw_images if img]
            return TikTokMediaInfo(
                id=post_id,
                title=title,
                media_type=TikTokItemType.PHOTOS,
                author=author,
                music=music,
                images=cleaned_images,
                cover_url=cover_url,
            )

        # Video post (HD preferred, fallback to standard play)
        hd_play = make_absolute_url(data.get("hdplay"))
        sd_play = make_absolute_url(data.get("play"))
        best_url = hd_play or sd_play
        video_size = data.get("hd_size") if hd_play else data.get("size")

        return TikTokMediaInfo(
            id=post_id,
            title=title,
            media_type=TikTokItemType.VIDEO,
            author=author,
            music=music,
            video_url=best_url,
            video_url_sd=sd_play,
            video_size=video_size,
            duration=duration,
            cover_url=cover_url,
        )

    async def download_file(
        self,
        url: str,
        dest_path: Path,
        max_bytes: Optional[int] = None,
    ) -> int:
        """
        Download a file from url to dest_path in chunks.
        Raises TikTokSizeLimitError if max_bytes is exceeded.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        downloaded = 0

        async with aiohttp.ClientSession(headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=self.timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise TikTokError(f"Ошибка загрузки файла с сервера TikTok (HTTP {resp.status})")

                content_len = resp.headers.get("Content-Length")
                if content_len and max_bytes and int(content_len) > max_bytes:
                    raise TikTokSizeLimitError(
                        f"Размер файла ({int(content_len) // (1024 * 1024)} МБ) превышает лимит {max_bytes // (1024 * 1024)} МБ."
                    )

                with open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        downloaded += len(chunk)
                        if max_bytes and downloaded > max_bytes:
                            raise TikTokSizeLimitError(
                                f"Размер файла превысил допустимый лимит {max_bytes // (1024 * 1024)} МБ."
                            )
                        f.write(chunk)

        return downloaded

    async def download_images(
        self,
        image_urls: list[str],
        output_dir: Path,
    ) -> list[Path]:
        """Download all images concurrently with a concurrency limit."""
        output_dir.mkdir(parents=True, exist_ok=True)
        semaphore = asyncio.Semaphore(5)

        async def _download_one(index: int, img_url: str) -> Path:
            async with semaphore:
                file_path = output_dir / f"image_{index:03d}.jpg"
                await self.download_file(img_url, file_path)
                return file_path

        tasks = [_download_one(i, url) for i, url in enumerate(image_urls)]
        return await asyncio.gather(*tasks)
