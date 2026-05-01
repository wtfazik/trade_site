import express from "express";
import cors from "cors";

const app = express();
const PORT = Number(process.env.PORT || 3000);
const WARNING = "Образовательный контент. Не финансовый совет.";
const MARKET_CANDLE_LIMIT = 80;
const MARKET_TIMEOUT_MS = 7000;

app.use(express.json({ limit: "128kb" }));
app.use(cors({ origin: isAllowedOrigin, credentials: false }));

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "trading-reels-api" });
});

app.get("/api/media-status", (_req, res) => {
  res.json({
    ok: true,
    pexelsConfigured: Boolean(process.env.PEXELS_API_KEY),
    pixabayConfigured: Boolean(process.env.PIXABAY_API_KEY),
    mode: "metadata-only",
  });
});

app.post("/api/explain", async (req, res) => {
  const lesson = normalizeLessonInput(req.body || {});
  const fallback = fallbackResponse(lesson);
  const prompt = buildPrompt(lesson);

  if (process.env.GEMINI_API_KEY) {
    const gemini = await callGemini(process.env.GEMINI_API_KEY, prompt).catch(() => null);
    if (gemini) return res.json({ ...parseAiText(gemini, fallback), provider: "gemini" });
  }

  if (process.env.OPENROUTER_API_KEY) {
    const openrouter = await callOpenRouter(process.env.OPENROUTER_API_KEY, prompt).catch(() => null);
    if (openrouter) return res.json({ ...parseAiText(openrouter, fallback), provider: "openrouter" });
  }

  return res.json({ ...fallback, provider: "fallback" });
});

app.post("/api/market-candles", async (req, res) => {
  const input = normalizeMarketInput(req.body || {});
  const prefer = input.provider;

  if ((prefer === "auto" || prefer === "twelvedata") && process.env.TWELVE_DATA_API_KEY) {
    const candles = await fetchTwelveDataCandles(process.env.TWELVE_DATA_API_KEY, input).catch(() => []);
    if (candles.length) return res.json({ provider: "twelvedata", symbol: input.symbol, interval: input.interval, candles, fallback: false });
  }

  if ((prefer === "auto" || prefer === "alphavantage") && process.env.ALPHA_VANTAGE_API_KEY) {
    const candles = await fetchAlphaVantageCandles(process.env.ALPHA_VANTAGE_API_KEY, input).catch(() => []);
    if (candles.length) return res.json({ provider: "alphavantage", symbol: input.symbol, interval: input.interval, candles, fallback: false });
  }

  return res.json(marketFallback(input));
});

app.use((_req, res) => {
  res.status(404).json({ error: "Not found" });
});

app.listen(PORT, () => {
  console.log(`trading-reels-api listening on ${PORT}`);
});

function isAllowedOrigin(origin, callback) {
  if (!origin) return callback(null, true);
  try {
    const hostname = new URL(origin).hostname;
    const allowed = hostname === "localhost" || hostname === "127.0.0.1" || hostname.endsWith(".vercel.app");
    return callback(null, allowed || process.env.CORS_ALLOW_ALL === "true");
  } catch {
    return callback(null, false);
  }
}

function normalizeMarketInput(body) {
  const provider = cleanText(body.provider).toLowerCase();
  return {
    symbol: normalizeSymbol(body.symbol),
    interval: normalizeInterval(body.interval),
    provider: ["auto", "twelvedata", "alphavantage"].includes(provider) ? provider : "auto",
  };
}

function normalizeSymbol(value) {
  const symbol = cleanText(value).toUpperCase().replace("-", "/") || "EUR/USD";
  return ["BTC/USD", "ETH/USD", "EUR/USD", "XAU/USD", "SPY"].includes(symbol) ? symbol : "EUR/USD";
}

function normalizeInterval(value) {
  const interval = cleanText(value).toLowerCase() || "1h";
  return ["5min", "15min", "30min", "1h", "4h", "1day"].includes(interval) ? interval : "1h";
}

async function fetchTwelveDataCandles(apiKey, input) {
  const params = new URLSearchParams({
    symbol: input.symbol,
    interval: twelveInterval(input.interval),
    outputsize: String(MARKET_CANDLE_LIMIT),
    apikey: apiKey,
  });
  const response = await fetchWithTimeout(`https://api.twelvedata.com/time_series?${params}`);
  if (!response.ok) return [];
  const data = await response.json();
  if (data?.status === "error" || !Array.isArray(data?.values)) return [];
  return data.values
    .map((item) => normalizeCandle(Date.parse(item.datetime) / 1000, item.open, item.high, item.low, item.close))
    .filter(Boolean)
    .reverse();
}

async function fetchAlphaVantageCandles(apiKey, input) {
  const url = alphaVantageUrl(apiKey, input);
  if (!url) return [];
  const response = await fetchWithTimeout(url);
  if (!response.ok) return [];
  const data = await response.json();
  if (data?.Note || data?.Information || data?.Error || data?.["Error Message"]) return [];
  const key = Object.keys(data).find((name) => name.includes("Time Series"));
  const series = key ? data[key] : null;
  if (!series || typeof series !== "object") return [];
  return Object.entries(series)
    .slice(0, MARKET_CANDLE_LIMIT)
    .map(([time, item]) => normalizeCandle(Date.parse(time) / 1000, item["1. open"], item["2. high"], item["3. low"], item["4. close"]))
    .filter(Boolean)
    .reverse();
}

function alphaVantageUrl(apiKey, input) {
  const interval = alphaInterval(input.interval);
  const params = new URLSearchParams({ apikey: apiKey, outputsize: "compact" });
  if (input.symbol === "SPY") {
    params.set("function", input.interval === "1day" ? "TIME_SERIES_DAILY" : "TIME_SERIES_INTRADAY");
    params.set("symbol", "SPY");
    if (input.interval !== "1day") params.set("interval", interval);
    return `https://www.alphavantage.co/query?${params}`;
  }
  const [from, to] = input.symbol.split("/");
  params.set("from_symbol", from);
  params.set("to_symbol", to);
  if (input.interval === "1day") {
    params.set("function", from === "BTC" || from === "ETH" ? "DIGITAL_CURRENCY_DAILY" : "FX_DAILY");
    if (from === "BTC" || from === "ETH") params.set("market", to);
  } else {
    params.set("function", from === "BTC" || from === "ETH" ? "CRYPTO_INTRADAY" : "FX_INTRADAY");
    params.set("interval", interval);
  }
  return `https://www.alphavantage.co/query?${params}`;
}

function normalizeCandle(time, open, high, low, close) {
  const candle = { time: Number(time), open: Number(open), high: Number(high), low: Number(low), close: Number(close) };
  return Object.values(candle).every(Number.isFinite) ? candle : null;
}

function twelveInterval(interval) {
  return { "5min": "5min", "15min": "15min", "30min": "30min", "1h": "1h", "4h": "4h", "1day": "1day" }[interval] || "1h";
}

function alphaInterval(interval) {
  return { "5min": "5min", "15min": "15min", "30min": "30min", "1h": "60min", "4h": "60min" }[interval] || "60min";
}

async function fetchWithTimeout(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), MARKET_TIMEOUT_MS);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

function marketFallback(input = {}) {
  return { provider: "demo", symbol: input.symbol || "EUR/USD", interval: input.interval || "1h", candles: [], fallback: true };
}

function normalizeLessonInput(body) {
  const legacy = body.lesson || {};
  return {
    lesson_id: cleanText(body.lesson_id || legacy.id || "lesson"),
    title: cleanText(body.title || legacy.title || "Trading insight"),
    topic: cleanText(body.topic || legacy.topic || "trading"),
    short_text: cleanText(body.short_text || legacy.short_text || legacy.simple_explanation || "Разбери торговую идею в контексте графика."),
    mode: cleanText(body.mode || "simple") === "example" ? "example" : "simple",
  };
}

function buildPrompt(lesson) {
  return `Ты объясняешь трейдинг новичку на русском языке. Название урока оставь на английском: "${lesson.title}".

Тема: ${lesson.topic}
Короткий текст урока: ${lesson.short_text}
Режим: ${lesson.mode}

Ответь строго как JSON без markdown:
{
  "summary": "1 короткое резюме на русском",
  "simple": "Что это значит, почему важно, как новичку понять. 3-5 коротких предложений.",
  "example": "Практический пример без обещаний прибыли. 2-4 предложения.",
  "warning": "Образовательный контент. Не финансовый совет."
}

Не обещай прибыль. Не давай торговый сигнал. Не используй слова гарантированно, 100%, всегда прибыльно.`;
}

async function callGemini(apiKey, prompt) {
  const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.35, maxOutputTokens: 650, responseMimeType: "application/json" },
    }),
  });
  if (!response.ok) return null;
  const data = await response.json();
  return data?.candidates?.[0]?.content?.parts?.[0]?.text || null;
}

async function callOpenRouter(apiKey, prompt) {
  const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${apiKey}`,
      "HTTP-Referer": "https://trading-reels-ai.local",
      "X-Title": "Trading Reels AI",
    },
    body: JSON.stringify({
      model: "openai/gpt-4o-mini",
      temperature: 0.35,
      max_tokens: 650,
      messages: [
        { role: "system", content: "Ты аккуратный русскоязычный редактор трейдинг-образования. Отвечай только JSON." },
        { role: "user", content: prompt },
      ],
    }),
  });
  if (!response.ok) return null;
  const data = await response.json();
  return data?.choices?.[0]?.message?.content || null;
}

function parseAiText(text, fallback) {
  try {
    const parsed = JSON.parse(stripCodeFence(text));
    return {
      summary: cleanText(parsed.summary || fallback.summary, 900),
      simple: cleanText(parsed.simple || fallback.simple, 1400),
      example: cleanText(parsed.example || fallback.example, 1200),
      warning: WARNING,
    };
  } catch {
    return { ...fallback, simple: cleanText(text, 1400) || fallback.simple };
  }
}

function fallbackResponse(lesson) {
  return {
    summary: `${lesson.title}: ${lesson.short_text}`,
    simple: `Идея урока: ${lesson.short_text} Смотри на это как на часть контекста графика, а не как на готовый сигнал для сделки.`,
    example: "Например, если цена подходит к важному уровню, сначала оцени структуру, реакцию свечей и риск. Только после этого можно строить учебный план наблюдения.",
    warning: WARNING,
  };
}

function stripCodeFence(value) {
  return String(value).replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```$/i, "").trim();
}

function cleanText(value, limit = 900) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}
