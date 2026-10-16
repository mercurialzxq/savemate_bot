export interface TikTokAuthor {
  nickname?: string;
  username?: string;
  avatar?: string;
}

export interface TikTokMusic {
  url?: string;
  title?: string;
  author?: string;
}

export interface TikTokMediaInfo {
  id: string;
  title: string;
  type: "video" | "photos";
  videoUrl?: string;
  videoUrlSd?: string;
  videoSize?: number;
  images?: string[];
  duration?: number;
  author?: TikTokAuthor;
  music?: TikTokMusic;
}

const TIKTOK_URL_REGEX = /https?:\/\/(?:[a-zA-Z0-9_\-]+\.)?tiktok\.com\/[^\s]+/gi;
const TRAILING_PUNCTUATION = /[.,!?:;)>'"`”’»]+$/;

const DEFAULT_USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const TIKWM_ENDPOINTS = [
  "https://www.tikwm.com/api/",
  "https://tikwm.com/api/",
];

/**
 * Extract clean TikTok URLs from input text.
 */
export function extractTikTokUrls(text?: string): string[] {
  if (!text) return [];
  const matches = text.match(TIKTOK_URL_REGEX);
  if (!matches) return [];

  const cleaned = matches.map((u) => u.replace(TRAILING_PUNCTUATION, "").trim());
  return Array.from(new Set(cleaned.filter(Boolean)));
}

function makeAbsoluteUrl(url?: string): string | undefined {
  if (!url) return undefined;
  const trimmed = url.trim();
  if (trimmed.startsWith("//")) return `https:${trimmed}`;
  if (trimmed.startsWith("/")) return `https://www.tikwm.com${trimmed}`;
  return trimmed;
}

/**
 * Fetch video or photo slideshow metadata without watermarks from TikWM API.
 */
export async function getTikTokMediaInfo(url: string): Promise<TikTokMediaInfo> {
  let lastError: Error | null = null;

  for (const endpoint of TIKWM_ENDPOINTS) {
    try {
      const body = new URLSearchParams({ url, hd: "1" });
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: {
          "User-Agent": DEFAULT_USER_AGENT,
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json, text/javascript, */*; q=0.01",
          Referer: "https://www.tikwm.com/",
        },
        body: body.toString(),
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status} from TikWM`);
      }

      const json: any = await resp.json();
      if (json.code !== 0) {
        const msg = json.msg || "Unknown error";
        if (msg.toLowerCase().includes("failed") || msg.toLowerCase().includes("not found")) {
          throw new Error("Публикация не найдена. Возможно, видео удалено или является приватным.");
        }
        throw new Error(`Ошибка TikTok API: ${msg}`);
      }

      const data = json.data;
      if (!data) {
        throw new Error("Пустые данные в ответе API");
      }

      const postId = String(data.id || "");
      const title = (data.title || "").trim();
      const duration = Number(data.duration || 0);

      const authorData = data.author || {};
      const author: TikTokAuthor = {
        nickname: authorData.nickname,
        username: authorData.unique_id,
        avatar: makeAbsoluteUrl(authorData.avatar),
      };

      const musicUrl = makeAbsoluteUrl(data.music);
      const musicInfo = data.music_info || {};
      const music: TikTokMusic | undefined = musicUrl
        ? {
            url: musicUrl,
            title: musicInfo.title || "Оригинальный звук",
            author: musicInfo.author || author.nickname || "TikTok",
          }
        : undefined;

      // Check if photo slideshow
      if (Array.isArray(data.images) && data.images.length > 0) {
        const images = data.images
          .map((img: string) => makeAbsoluteUrl(img))
          .filter(Boolean) as string[];

        return {
          id: postId,
          title,
          type: "photos",
          images,
          duration,
          author,
          music,
        };
      }

      // Video post
      const hdPlay = makeAbsoluteUrl(data.hdplay);
      const sdPlay = makeAbsoluteUrl(data.play);
      const videoUrl = hdPlay || sdPlay;

      return {
        id: postId,
        title,
        type: "video",
        videoUrl,
        videoUrlSd: sdPlay,
        videoSize: hdPlay ? data.hd_size : data.size,
        duration,
        author,
        music,
      };
    } catch (err: any) {
      lastError = err;
    }
  }

  throw lastError || new Error("Не удалось получить информацию о публикации");
}

/**
 * Fetch a binary file as Uint8Array with size check.
 */
export async function fetchMediaBytes(
  url: string,
  maxBytes: number = 50 * 1024 * 1024
): Promise<Uint8Array> {
  const resp = await fetch(url, {
    headers: {
      "User-Agent": DEFAULT_USER_AGENT,
      Referer: "https://www.tiktok.com/",
    },
  });

  if (!resp.ok) {
    throw new Error(`Ошибка скачивания файла (HTTP ${resp.status})`);
  }

  const contentLength = resp.headers.get("content-length");
  if (contentLength && parseInt(contentLength, 10) > maxBytes) {
    throw new Error(
      `Размер файла (${Math.round(parseInt(contentLength, 10) / (1024 * 1024))} МБ) превышает лимит Telegram в 50 МБ.`
    );
  }

  const buffer = await resp.arrayBuffer();
  if (buffer.byteLength > maxBytes) {
    throw new Error(
      `Размер файла (${Math.round(buffer.byteLength / (1024 * 1024))} МБ) превышает лимит Telegram в 50 МБ.`
    );
  }

  return new Uint8Array(buffer);
}

