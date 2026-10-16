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

function generateRandomClientIp(): string {
  const o1 = Math.floor(Math.random() * 140) + 40;
  const o2 = Math.floor(Math.random() * 250) + 1;
  const o3 = Math.floor(Math.random() * 250) + 1;
  const o4 = Math.floor(Math.random() * 250) + 1;
  return `${o1}.${o2}.${o3}.${o4}`;
}

/**
 * Fetch video or photo slideshow metadata without watermarks.
 * Uses a resilient multi-provider strategy:
 * 1. TikWM with dynamic client IP header (bypasses shared Cloudflare 10,000/day limit)
 * 2. SSSTik.io as automatic zero-rate-limit fallback
 */
export async function getTikTokMediaInfo(url: string): Promise<TikTokMediaInfo> {
  let tikwmError: Error | null = null;

  // 1. Try TikWM with dynamic IP
  for (const endpoint of TIKWM_ENDPOINTS) {
    try {
      const clientIp = generateRandomClientIp();
      const body = new URLSearchParams({ url, hd: "1" });
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: {
          "User-Agent": DEFAULT_USER_AGENT,
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json, text/javascript, */*; q=0.01",
          Referer: "https://www.tikwm.com/",
          "X-Forwarded-For": clientIp,
          "Client-IP": clientIp,
          "X-Real-IP": clientIp,
        },
        body: body.toString(),
      });

      if (resp.ok) {
        const json: any = await resp.json();
        if (json.code === 0 && json.data) {
          return parseTikWmResponse(json.data);
        }
        console.warn(`TikWM endpoint ${endpoint} code ${json.code}: ${json.msg}`);
        tikwmError = new Error(json.msg || "TikWM error");
      }
    } catch (err: any) {
      console.warn(`TikWM endpoint ${endpoint} failed:`, err.message);
      tikwmError = err;
    }
  }

  // 2. Automatic Fallback: SSSTik.io
  try {
    console.log("TikWM limit or error reached. Falling back to SSSTik.io...");
    return await getSSSTikMediaInfo(url);
  } catch (ssstikErr: any) {
    console.error("SSSTik fallback also failed:", ssstikErr.message);
  }

  throw (
    tikwmError ||
    new Error(
      "Не удалось получить видео. Возможно, публикация удалена или скрыта настройками приватности."
    )
  );
}

function parseTikWmResponse(data: any): TikTokMediaInfo {
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
}

/**
 * Fallback extractor using SSSTik.io
 */
async function getSSSTikMediaInfo(url: string): Promise<TikTokMediaInfo> {
  const pageResp = await fetch("https://ssstik.io/en", {
    headers: {
      "User-Agent": DEFAULT_USER_AGENT,
      Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
  });

  if (!pageResp.ok) {
    throw new Error(`SSSTik init error: HTTP ${pageResp.status}`);
  }

  const pageHtml = await pageResp.text();
  const ttMatch = pageHtml.match(/s_tt\s*=\s*['"]([^'"]+)['"]/);
  if (!ttMatch) {
    throw new Error("Не удалось получить токен проверки SSSTik");
  }

  const postResp = await fetch("https://ssstik.io/abc?url=dl", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      Origin: "https://ssstik.io",
      Referer: "https://ssstik.io/en",
      "User-Agent": DEFAULT_USER_AGENT,
    },
    body: new URLSearchParams({
      id: url,
      locale: "en",
      tt: ttMatch[1],
    }).toString(),
  });

  if (!postResp.ok) {
    throw new Error(`SSSTik download error: HTTP ${postResp.status}`);
  }

  const resHtml = await postResp.text();

  const titleMatch = resHtml.match(/<p class=["']maintext["']>([^<]*)<\/p>/);
  const title = titleMatch ? titleMatch[1].trim() : "";

  const authorMatch = resHtml.match(/<h2>([^<]*)<\/h2>/);
  const authorNickname = authorMatch ? authorMatch[1].trim() : undefined;

  // Check for images (photo slideshow)
  const images: string[] = [];
  const splideMatches = [
    ...resHtml.matchAll(/class=["']splide__slide["'][^>]*>[\s\S]*?href=["']([^"']+)["']/g),
  ];
  for (const m of splideMatches) {
    if (m[1]) images.push(m[1]);
  }

  // Audio track
  const musicMatch = resHtml.match(
    /href=["']([^"']+)["'][^>]*class=["'][^"']*music[^"']*["']/
  );
  const musicUrl = musicMatch ? musicMatch[1] : undefined;

  if (images.length > 0) {
    return {
      id: "ssstik_photos",
      title,
      type: "photos",
      images,
      author: { nickname: authorNickname },
      music: musicUrl
        ? { url: musicUrl, title: "Оригинальный звук", author: authorNickname }
        : undefined,
    };
  }

  // Video without watermark
  const videoMatch = resHtml.match(
    /href=["']([^"']+)["'][^>]*class=["'][^"']*without_watermark[^"']*["']/
  );

  if (!videoMatch || !videoMatch[1]) {
    throw new Error("Не удалось найти ссылку на видео без водяного знака");
  }

  return {
    id: "ssstik_video",
    title,
    type: "video",
    videoUrl: videoMatch[1],
    author: { nickname: authorNickname },
    music: musicUrl
      ? { url: musicUrl, title: "Оригинальный звук", author: authorNickname }
      : undefined,
  };
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
      Referer: url.includes("tikcdn.io") ? "https://ssstik.io/" : "https://www.tiktok.com/",
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
