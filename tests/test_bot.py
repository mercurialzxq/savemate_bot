import pytest
from bot.services import TikTokItemType, TikTokService
from bot.utils import extract_tiktok_urls, format_caption, format_size


def test_extract_tiktok_urls():
    text = (
        "Смотри какое видео https://www.tiktok.com/@user/video/1234567890123456789! "
        "И еще вот это https://vm.tiktok.com/ZM8abcDEF/, а также "
        "https://vt.tiktok.com/ZS8abcDEF/."
    )
    urls = extract_tiktok_urls(text)
    assert len(urls) == 3
    assert urls[0] == "https://www.tiktok.com/@user/video/1234567890123456789"
    assert urls[1] == "https://vm.tiktok.com/ZM8abcDEF/"
    assert urls[2] == "https://vt.tiktok.com/ZS8abcDEF/"


def test_extract_tiktok_urls_empty():
    assert extract_tiktok_urls("") == []
    assert extract_tiktok_urls(None) == []
    assert extract_tiktok_urls("Привет, как дела? Нет ссылок тут.") == []


def test_format_caption():
    cap = format_caption(
        title="Тестовое видео <script>",
        author_nickname="Иван & Марья",
        author_username="ivan_marya",
    )
    assert "&lt;script&gt;" in cap
    assert "Иван &amp; Марья" in cap
    assert "(@ivan_marya)" in cap
    assert "👤 <b>Автор:</b>" in cap


def test_format_caption_truncate():
    long_title = "A" * 1500
    cap = format_caption(title=long_title, max_length=100)
    assert len(cap) <= 100
    assert cap.endswith("...")


def test_format_size():
    assert format_size(500) == "500 Б"
    assert format_size(2048) == "2.0 КБ"
    assert format_size(10 * 1024 * 1024) == "10.00 МБ"


def test_service_parse_video():
    service = TikTokService()
    raw = {
        "id": "7106594312292453678",
        "title": "Cool TikTok Video",
        "duration": 15,
        "play": "/video/media/play/abc",
        "hdplay": "https://cdn.tiktok.com/hd.mp4",
        "hd_size": 15000000,
        "author": {
            "nickname": "BestCreator",
            "unique_id": "best_creator",
        },
        "music": "/audio/music.mp3",
        "music_info": {
            "title": "Hit Song",
            "author": "Singer",
        },
    }
    info = service._parse_response(raw)
    assert info.id == "7106594312292453678"
    assert info.media_type == TikTokItemType.VIDEO
    assert info.video_url == "https://cdn.tiktok.com/hd.mp4"
    assert info.video_url_sd == "https://www.tikwm.com/video/media/play/abc"
    assert info.author.nickname == "BestCreator"
    assert info.music.url == "https://www.tikwm.com/audio/music.mp3"


def test_service_parse_photos():
    service = TikTokService()
    raw = {
        "id": "7200000000000000000",
        "title": "Photo Carousel",
        "images": [
            "https://cdn.tiktok.com/img1.jpg",
            "/images/img2.jpg",
        ],
        "author": {
            "nickname": "Photographer",
            "unique_id": "photo_guy",
        },
    }
    info = service._parse_response(raw)
    assert info.id == "7200000000000000000"
    assert info.media_type == TikTokItemType.PHOTOS
    assert len(info.images) == 2
    assert info.images[0] == "https://cdn.tiktok.com/img1.jpg"
    assert info.images[1] == "https://www.tikwm.com/images/img2.jpg"
