import { webhookCallback } from "grammy";
import { createBot } from "./bot";

export interface Env {
  BOT_TOKEN: string;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (!env.BOT_TOKEN) {
      return new Response(
        "BOT_TOKEN secret is not set in Cloudflare Workers! Please set it with `npx wrangler secret put BOT_TOKEN` or in the Cloudflare Dashboard.",
        { status: 500 }
      );
    }

    // Health check root
    if (url.pathname === "/" && request.method === "GET") {
      return new Response(
        JSON.stringify(
          {
            status: "online",
            bot: "SaveMate TikTok Downloader",
            platform: "Cloudflare Workers",
            endpoints: {
              set_webhook: `${url.origin}/set-webhook`,
              get_webhook_info: `${url.origin}/get-webhook-info`,
              webhook: `${url.origin}/webhook`,
            },
          },
          null,
          2
        ),
        { headers: { "Content-Type": "application/json; charset=utf-8" } }
      );
    }

    // Automatic 1-click webhook registration endpoint
    if (url.pathname === "/set-webhook" && request.method === "GET") {
      const webhookUrl = `${url.origin}/webhook`;
      const res = await fetch(
        `https://api.telegram.org/bot${env.BOT_TOKEN}/setWebhook?url=${encodeURIComponent(webhookUrl)}&drop_pending_updates=true`
      );
      const data = await res.json();
      return new Response(
        JSON.stringify(
          {
            message: "Webhook setup attempt finished",
            target_webhook_url: webhookUrl,
            telegram_response: data,
          },
          null,
          2
        ),
        { headers: { "Content-Type": "application/json; charset=utf-8" } }
      );
    }

    // Check webhook info
    if (url.pathname === "/get-webhook-info" && request.method === "GET") {
      const res = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/getWebhookInfo`);
      const data = await res.json();
      return new Response(JSON.stringify(data, null, 2), {
        headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    }

    // Telegram webhook handler
    if (url.pathname === "/webhook" && request.method === "POST") {
      const bot = createBot(env.BOT_TOKEN);
      return webhookCallback(bot, "cloudflare-mod")(request);
    }

    return new Response("Not Found", { status: 404 });
  },
};
