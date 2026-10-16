import html
import re
from typing import Optional

# Pattern to find TikTok links in any text
TIKTOK_URL_REGEX = re.compile(
    r"https?://(?:[a-zA-Z0-9_\-]+\.)?tiktok\.com/[^\s]+",
    re.IGNORECASE,
)

TRAILING_PUNCTUATION = ".,!?:;)>'\"”’»"


def extract_tiktok_urls(text: Optional[str]) -> list[str]:
    """
    Extract all TikTok URLs from a string.
    Strips trailing punctuation and returns unique URLs preserving order.
    """
    if not text:
        return []

    found = TIKTOK_URL_REGEX.findall(text)
    cleaned_urls = []
    seen = set()

    for url in found:
        clean = url.rstrip(TRAILING_PUNCTUATION)
        if clean and clean not in seen:
            seen.add(clean)
            cleaned_urls.append(clean)

    return cleaned_urls


def format_bot_caption(bot_username: Optional[str] = None) -> str:
    """
    Format a Telegram HTML caption referencing the bot instead of the original video title/author.
    """
    if bot_username:
        clean_user = bot_username.lstrip("@")
        return f"✨ Скачано с помощью <a href=\"https://t.me/{clean_user}\">@{clean_user}</a>"
    return "✨ Скачано с помощью бота"


def format_caption(
    title: Optional[str] = None,
    author_nickname: Optional[str] = None,
    author_username: Optional[str] = None,
    max_length: int = 1024,
) -> str:
    """
    Format a Telegram HTML caption for TikTok media.
    Safely escapes HTML and fits within Telegram's max caption length.
    """
    parts: list[str] = []

    if title and title.strip():
        parts.append(html.escape(title.strip()))

    author_tokens: list[str] = []
    if author_nickname and author_nickname.strip():
        author_tokens.append(html.escape(author_nickname.strip()))
    if author_username and author_username.strip():
        clean_user = author_username.strip().lstrip("@")
        author_tokens.append(f"(@{html.escape(clean_user)})")

    if author_tokens:
        parts.append(f"👤 <b>Автор:</b> {' '.join(author_tokens)}")

    caption = "\n\n".join(parts) if parts else ""

    if len(caption) > max_length:
        caption = caption[: max_length - 3].rstrip() + "..."

    return caption


def format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string (KB/MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    return f"{size_bytes / (1024 * 1024):.2f} МБ"
