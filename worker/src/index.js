const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: JSON_HEADERS });
    }

    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "trading-reels-ai-worker" });
    }

    if (request.method === "POST" && url.pathname === "/api/explain") {
      return handleExplain(request, env);
    }

    return json({ error: "Not found" }, 404);
  },
};

async function handleExplain(request, env) {
  let body = {};
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON body" }, 400);
  }

  const lesson = body.lesson || {};
  const title = cleanText(lesson.title || "Trading insight");
  const shortText = cleanText(lesson.short_text || "This lesson needs source content before AI expansion.");
  const localSimple = cleanText(lesson.simple_explanation || shortText);
  const localExample = cleanText(lesson.example || "Review the source lesson and wait for confirmation before acting on any idea.");

  // TODO: Use env.GEMINI_API_KEY for Gemini through Cloudflare Secrets.
  // TODO: Use env.OPENROUTER_API_KEY for OpenRouter through Cloudflare Secrets.
  // Keep keys out of frontend code, source files, and committed config.
  // TODO: Use env.PEXELS_API_KEY and env.PIXABAY_API_KEY for safe background searches.

  return json({
    summary: `${title}: ${shortText}`,
    simple: localSimple,
    example: localExample,
    warning: "Educational content only. Not financial advice.",
  });
}

function cleanText(value) {
  return String(value).replace(/\s+/g, " ").trim().slice(0, 900);
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: JSON_HEADERS,
  });
}
