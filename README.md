# 📥 SaveMate TikTok Downloader Bot

Современный и быстрый Telegram-бот для скачивания видео и фото-публикаций (каруселей/слайдшоу) из **TikTok** в максимальном качестве без водяных знаков.

Поддерживает работу как на **Cloudflare Workers (100% бесплатно, без сервера)**, так и локально/на VPS через **Python (aiogram 3)** или **Docker**.

---

## 🚀 Возможности

- 🎬 **Видео без вотермарок**: в максимальном доступном HD-качестве.
- 🖼 **Фото-публикации**: скачивание всех картинок из слайдшоу аккуратным альбомом (`MediaGroup`).
- 🎵 **Аудиодорожки**: автоматическое извлечение оригинального звука / музыки из публикации.
- 🏷 **Подпись бота**: к каждому отправленному медиафайлу добавляется кликабельная ссылка на вашего бота.
- ⚡️ **Cloudflare Workers Ready**: работает в бессерверном режиме на границе сети Cloudflare (Edge Network) с мгновенным откликом по всему миру.
- 🆓 **100% бесплатно**: до 100 000 запросов в день на бесплатном тарифе Cloudflare.

---

## ☁️ Развёртывание на Cloudflare Workers (Рекомендуется)

Бот работает на Cloudflare Workers без необходимости арендовать VPS или держать включённым ПК.

### Шаг 1. Войдите в Cloudflare
В терминале внутри папки проекта выполните:
```bash
npx wrangler login
```
*Откроется браузер, где нужно нажать кнопку «Allow» для авторизации.*

### Шаг 2. Установите токен бота
Добавьте ваш Telegram Bot Token в защищенное хранилище секретов Cloudflare:
```bash
npx wrangler secret put BOT_TOKEN
```
*Вставьте токен бота (например, `8870810480:AAEuR955jBJHDzOzp9zkzdCH6NXbeuS9rHM`) и нажмите Enter.*

### Шаг 3. Задеплойте Worker
```bash
npm run deploy
```
В выводе команды появится ваш адрес, например:
`https://savemate-bot.ваш-аккаунт.workers.dev`

### Шаг 4. Активируйте Webhook
Просто откройте в браузере ссылку:
```
https://savemate-bot.ваш-аккаунт.workers.dev/set-webhook
```
Бот мгновенно свяжется с Telegram и пришлёт подтверждение:
```json
{
  "message": "Webhook setup attempt finished",
  "telegram_response": {
    "ok": true,
    "result": true,
    "description": "Webhook was set"
  }
}
```
**Готово!** Бот теперь работает 24/7 в облаке Cloudflare абсолютно бесплатно.

---

## 💻 Локальная разработка и тестирование Worker

Для запуска локального сервера Cloudflare Workers:
```bash
npm run dev
```
Сервер запустится на `http://localhost:8787`.

---

## 🐍 Альтернатива: Запуск через Python (aiogram 3) или Docker

Если вы предпочитаете запускать бота на обычном сервере или VPS:

### Запуск через Docker Compose:
```bash
cp .env.example .env
# Укажите BOT_TOKEN в .env
docker compose up -d --build
```

### Локальный запуск на Python:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # укажите токен
python main.py
```

---

## 📋 Форматы ссылок

Бот принимает любые ссылки:
- `https://www.tiktok.com/@username/video/1234567890123456789`
- `https://www.tiktok.com/@username/photo/1234567890123456789`
- `https://vm.tiktok.com/ZMxxxxxx/`
- `https://vt.tiktok.com/ZSxxxxxx/`
- Ссылки, отправленные прямо внутри обычного текста.

---

## 📂 Структура проекта

```
savemate_bot/
├── src/
│   ├── index.ts        # Cloudflare Workers Fetch & Webhook обработчик
│   ├── bot.ts          # Логика Telegram-бота (grammY)
│   └── tiktok.ts       # Загрузчик TikTok (видео HD, фото, аудио)
├── bot/                # Python-версия бота (aiogram 3)
├── wrangler.jsonc      # Конфигурация Cloudflare Worker
├── package.json        # Node.js зависимости и скрипты
├── tsconfig.json       # Конфигурация TypeScript
├── Dockerfile          # Docker-образ для Python-версии
├── docker-compose.yml  # Docker Compose
└── main.py             # Точка входа для Python
```

---

## 📄 Лицензия

MIT License.
