import { Bot, InputFile, InputMediaBuilder } from "grammy";
import { extractTikTokUrls, fetchMediaBytes, getTikTokMediaInfo } from "./tiktok";

export function createBot(token: string) {
  const bot = new Bot(token);

  // Command /start
  bot.command("start", async (ctx) => {
    const text =
      "👋 <b>Привет! Я бот для скачивания контента из TikTok без водяных знаков.</b>\n\n" +
      "✨ <b>Что я умею:</b>\n" +
      "• 📹 Скачивать видео в максимальном HD-качестве без вотермарок\n" +
      "• 🖼 Скачивать публикации из фото (слайдшоу / карусели картинок)\n" +
      "• 🎵 Отправлять оригинальную аудиодорожку из видео и фото-постов\n\n" +
      "📥 <b>Как мной пользоваться:</b>\n" +
      "Просто отправь мне ссылку на любое видео или фото-пост из TikTok (например, из приложения TikTok или из браузера) — " +
      "и я мгновенно пришлю тебе медиафайл в наилучшем качестве!\n\n" +
      "<i>Поддерживаются как стандартные ссылки, так и короткие (vm.tiktok.com / vt.tiktok.com).</i>";

    await ctx.reply(text, { parse_mode: "HTML" });
  });

  // Command /help
  bot.command("help", async (ctx) => {
    const text =
      "ℹ️ <b>Как скачать видео или фото из TikTok:</b>\n\n" +
      "1. Откройте TikTok и найдите желаемое видео или фото-пост.\n" +
      "2. Нажмите кнопку <b>«Поделиться»</b> (стрелочка) ➔ <b>«Копировать ссылку»</b>.\n" +
      "3. Отправьте скопированную ссылку в этот чат.\n" +
      "4. Подождите несколько секунд — бот скачает контент и пришлет вам файл без водяных знаков!\n\n" +
      "📌 <b>Поддерживаемые форматы ссылок:</b>\n" +
      "• <code>https://vm.tiktok.com/...</code>\n" +
      "• <code>https://vt.tiktok.com/...</code>\n" +
      "• <code>https://www.tiktok.com/@пользователь/video/...</code>\n" +
      "• <code>https://www.tiktok.com/@пользователь/photo/...</code>";

    await ctx.reply(text, { parse_mode: "HTML" });
  });

  // Handle incoming text or captions
  bot.on(["message:text", "message:caption"], async (ctx) => {
    const text = ctx.message.text || ctx.message.caption || "";
    const urls = extractTikTokUrls(text);

    if (urls.length === 0) {
      if (ctx.chat.type === "private" && !text.startsWith("/")) {
        await ctx.reply(
          "🤔 Пожалуйста, отправьте корректную ссылку на видео или фото из TikTok.\n\n" +
            "Пример: <code>https://vm.tiktok.com/...</code> или <code>https://www.tiktok.com/@user/video/...</code>",
          { parse_mode: "HTML" }
        );
      }
      return;
    }

    const me = await ctx.api.getMe();
    const botUser = me.username;
    const caption = botUser
      ? `✨ Скачано с помощью <a href="https://t.me/${botUser}">@${botUser}</a>`
      : "✨ Скачано с помощью бота";

    for (const url of urls) {
      await processUrl(ctx, url, caption);
    }
  });

  return bot;
}

async function processUrl(ctx: any, url: string, caption: string) {
  const statusMsg = await ctx.reply("⏳ <b>Получаю информацию о публикации...</b>", {
    parse_mode: "HTML",
  });

  try {
    await ctx.replyWithChatAction("typing");
    const mediaInfo = await getTikTokMediaInfo(url);

    if (mediaInfo.type === "photos") {
      const images = mediaInfo.images || [];
      if (images.length === 0) {
        throw new Error("В публикации не найдены изображения.");
      }

      await ctx.api
        .editMessageText(
          ctx.chat.id,
          statusMsg.message_id,
          `⏳ <b>Скачиваю фото (${images.length} шт.)...</b>`,
          { parse_mode: "HTML" }
        )
        .catch(() => {});

      await ctx.replyWithChatAction("upload_photo");

      // Download bytes in parallel
      const imageBytesList = await Promise.all(images.map((imgUrl) => fetchMediaBytes(imgUrl)));

      if (imageBytesList.length === 1) {
        await ctx.replyWithPhoto(new InputFile(imageBytesList[0], "photo.jpg"), {
          caption,
          parse_mode: "HTML",
        });
      } else {
        // Chunk into groups of 10
        const chunkSize = 10;
        for (let i = 0; i < imageBytesList.length; i += chunkSize) {
          const chunk = imageBytesList.slice(i, i + chunkSize);
          const media = chunk.map((bytes, idx) =>
            InputMediaBuilder.photo(new InputFile(bytes, `photo_${i + idx}.jpg`), {
              ...(i === 0 && idx === 0 ? { caption, parse_mode: "HTML" } : {}),
            })
          );
          await ctx.replyWithMediaGroup(media);
        }
      }

      // If audio is available, send audio
      if (mediaInfo.music?.url) {
        try {
          const audioBytes = await fetchMediaBytes(mediaInfo.music.url);
          await ctx.replyWithChatAction("upload_voice");
          await ctx.replyWithAudio(new InputFile(audioBytes, "audio.mp3"), {
            caption,
            parse_mode: "HTML",
            title: mediaInfo.music.title || "Оригинальный звук",
            performer: mediaInfo.music.author || "TikTok",
          });
        } catch (audioErr) {
          console.warn("Could not download audio for slideshow:", audioErr);
        }
      }
    } else {
      // Video
      const videoUrl = mediaInfo.videoUrl;
      if (!videoUrl) {
        throw new Error("Не найдена ссылка на скачивание видео без водяных знаков.");
      }

      await ctx.api
        .editMessageText(
          ctx.chat.id,
          statusMsg.message_id,
          "⏳ <b>Скачиваю видео в HD без вотермарок...</b>",
          { parse_mode: "HTML" }
        )
        .catch(() => {});

      await ctx.replyWithChatAction("upload_video");

      let videoBytes: Uint8Array;
      try {
        videoBytes = await fetchMediaBytes(videoUrl);
      } catch (err) {
        if (mediaInfo.videoUrlSd && mediaInfo.videoUrlSd !== videoUrl) {
          videoBytes = await fetchMediaBytes(mediaInfo.videoUrlSd);
        } else {
          throw err;
        }
      }

      await ctx.replyWithVideo(new InputFile(videoBytes, "video.mp4"), {
        caption,
        parse_mode: "HTML",
        supports_streaming: true,
        duration: mediaInfo.duration,
      });
    }

    // Delete status message
    await ctx.api.deleteMessage(ctx.chat.id, statusMsg.message_id).catch(() => {});
  } catch (err: any) {
    console.error("Error processing TikTok:", err);
    await ctx.api
      .editMessageText(
        ctx.chat.id,
        statusMsg.message_id,
        `❌ <b>Ошибка:</b> ${err.message || "Не удалось загрузить видео."}`,
        { parse_mode: "HTML" }
      )
      .catch(() => {});
  }
}
