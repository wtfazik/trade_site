const feed = document.querySelector("#top");
const template = document.querySelector("#reelTemplate");
const progressRail = document.querySelector("#progressRail");
const sheet = document.querySelector("#bottomSheet");
const sheetBackdrop = document.querySelector("#sheetBackdrop");
const sheetTitle = document.querySelector("#sheetTitle");
const sheetKicker = document.querySelector("#sheetKicker");
const sheetBody = document.querySelector("#sheetBody");
const closeSheetButton = document.querySelector("#closeSheet");
const pathButton = document.querySelector("#pathButton");
const creditsButton = document.querySelector("#creditsButton");
const savedButton = document.querySelector("#savedButton");
const savedCount = document.querySelector("#savedCount");
const scrollHint = document.querySelector(".scroll-hint");
const sessionModule = document.querySelector("#sessionModule");
const sessionTitle = document.querySelector("#sessionTitle");
const mobileProgressFill = document.querySelector("#mobileProgressFill");
const chartBackdrop = document.querySelector("#chartBackdrop");
const chartModal = document.querySelector("#chartModal");
const chartModalImage = document.querySelector("#chartModalImage");
const chartTitle = document.querySelector("#chartTitle");
const closeChartButton = document.querySelector("#closeChart");
const educationalChartButton = document.querySelector("#educationalChart");
const marketChartButton = document.querySelector("#marketChart");
const chartStatus = document.querySelector("#chartStatus");
const marketCanvas = document.querySelector("#marketCanvas");
const zoomOutChartButton = document.querySelector("#zoomOutChart");
const resetChartButton = document.querySelector("#resetChart");
const zoomInChartButton = document.querySelector("#zoomInChart");
const viewedProgress = document.querySelector("#viewedProgress");
const aiStatus = document.querySelector("#aiStatus");
const toast = document.querySelector("#toast");

const LESSON_URLS = ["./data/lessons.json", "../content/lessons.json", "../content/lessons.sample.json"];
const CREDIT_URLS = ["./data/credits.json", "../content/credits.json"];
const MEDIA_URLS = ["./data/media.json", "../content/media.json"];
let API_BASE = "";
const SAVED_KEY = "trading-reels-ai:saved-lessons";
const VIEWED_KEY = "trading-reels-ai:viewed-lessons";
const MAX_CARD_TEXT = 260;
const MAX_KEY_IDEA = 115;
const VIEWED_AFTER_MS = 2400;
const TOAST_MS = 1800;

const visualClasses = {
  support: "visual-support",
  resistance: "visual-support",
  liquidity: "visual-liquidity",
  risk: "visual-risk",
  stop: "visual-risk",
  psychology: "visual-psychology",
  candlestick: "visual-candlestick",
  candlesticks: "visual-candlestick",
  candle: "visual-candlestick",
  structure: "visual-structure",
  trend: "visual-trend",
  breakout: "visual-breakout",
  sizing: "visual-risk",
};

const moduleOrder = ["Basics", "Structure", "Levels", "Liquidity", "Candles", "Entries", "Risk", "Psychology"];

let lessons = [];
let credits = null;
let mediaByLesson = new Map();
let activeIndex = 0;
let reelObserver = null;
let viewedTimer = null;
let chartScale = 1;
let toastTimer = null;
let currentChart = null;

function localDevApiBase() {
  return ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://localhost:8787" : "";
}

function loadOptionalRuntimeConfig() {
  if (window.TRADING_REELS_API_BASE) return Promise.resolve();
  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = "./config.js";
    script.async = false;
    script.onload = () => resolve();
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
}

function getSavedLessons() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function setSavedLessons(saved) {
  localStorage.setItem(SAVED_KEY, JSON.stringify([...saved]));
  savedCount.textContent = String(saved.size);
}

function getViewedLessons() {
  try {
    return new Set(JSON.parse(localStorage.getItem(VIEWED_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function setViewedLessons(viewed) {
  localStorage.setItem(VIEWED_KEY, JSON.stringify([...viewed]));
  updateViewedProgress(viewed);
}

async function loadJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`Unable to load ${url}`);
  return response.json();
}

async function init() {
  await loadOptionalRuntimeConfig();
  API_BASE = window.TRADING_REELS_API_BASE || localDevApiBase();
  setSavedLessons(getSavedLessons());
  updateViewedProgress(getViewedLessons());
  aiStatus.textContent = API_BASE ? "AI online" : "Local mode";
  try {
    const [loadedLessons, creditData, mediaData] = await Promise.all([
      loadLessonsWithFallback(),
      loadFirstJson(CREDIT_URLS, null),
      loadFirstJson(MEDIA_URLS, []),
    ]);
    lessons = loadedLessons;
    credits = creditData;
    mediaByLesson = indexMedia(mediaData);
    renderLessons();
  } catch (error) {
    renderLoadError(error);
  }
}

async function loadLessonsWithFallback() {
  return normalizeLessons(await loadFirstJson(LESSON_URLS, []));
}

async function loadFirstJson(urls, fallback) {
  let lastError = null;
  for (const url of urls) {
    try {
      return await loadJson(url);
    } catch (error) {
      lastError = error;
    }
  }
  if (fallback !== undefined) return fallback;
  throw lastError || new Error("Unable to load runtime data.");
}

function normalizeLessons(data) {
  const list = Array.isArray(data) ? data : data?.lessons;
  if (!Array.isArray(list)) throw new Error("Lesson file must contain an array of lessons.");
  const normalized = list
    .map((lesson, index) => ({
      id: cleanString(lesson?.id) || `lesson-${String(index + 1).padStart(3, "0")}`,
      title: cleanString(lesson?.title) || "Trading Insight",
      topic: cleanString(lesson?.topic) || "lesson",
      level: cleanString(lesson?.level) || "beginner",
      hook: cleanString(lesson?.hook),
      short_text: cleanString(lesson?.short_text),
      simple_explanation: cleanString(lesson?.simple_explanation),
      example: cleanString(lesson?.example),
      image_query: cleanString(lesson?.image_query),
      media_query: cleanString(lesson?.media_query),
      book_media: normalizeBookMedia(lesson?.book_media),
      visual: lesson?.visual && typeof lesson.visual === "object" ? lesson.visual : { type: "market", value: "structure" },
      source: cleanString(lesson?.source) || "book-derived",
      confidence: cleanString(lesson?.confidence) || "medium",
    }))
    .filter((lesson) => lesson.short_text || lesson.simple_explanation || lesson.example);
  if (!normalized.length) throw new Error("No usable lessons found in the lesson file.");
  return normalized;
}

function indexMedia(data) {
  const map = new Map();
  if (!Array.isArray(data)) return map;
  data.forEach((item) => {
    if (item?.lesson_id) map.set(String(item.lesson_id), item);
  });
  return map;
}

function normalizeBookMedia(media) {
  if (!media || typeof media !== "object" || !media.url) return null;
  return {
    type: cleanString(media.type) || "image",
    url: cleanString(media.url),
    thumbnail: cleanString(media.thumbnail),
    source: cleanString(media.source) || "book-extracted",
  };
}

function cleanString(value) {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

function renderLoadError(error) {
  feed.replaceChildren(createStateCard({
    kicker: "Content unavailable",
    title: "Lessons could not load.",
    message: `${error.message}. Run python -m http.server 8080 from the repo root, then open http://localhost:8080/frontend/.`,
  }));
  progressRail.replaceChildren();
}

function createStateCard({ kicker, title, message }) {
  const section = document.createElement("section");
  section.className = "loading-state";
  const card = document.createElement("div");
  card.className = "terminal-card";
  const eyebrow = document.createElement("span");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = kicker;
  const heading = document.createElement("h1");
  heading.textContent = title;
  const paragraph = document.createElement("p");
  paragraph.textContent = message;
  card.append(eyebrow, heading, paragraph);
  section.appendChild(card);
  return section;
}

function renderLessons() {
  const saved = getSavedLessons();
  setSavedLessons(saved);
  feed.replaceChildren();
  progressRail.replaceChildren();

  lessons.forEach((lesson, index) => {
    const reel = template.content.firstElementChild.cloneNode(true);
    const viewed = getViewedLessons();
    const visualKey = lesson.visual?.value || lesson.topic || "structure";
    reel.id = safeDomId(lesson.id);
    reel.dataset.index = String(index);
    reel.classList.add(visualClasses[visualKey] || visualClasses[topicVisual(lesson.topic)] || "visual-structure");
    reel.classList.toggle("is-viewed", viewed.has(lesson.id));

    reel.querySelector(".topic-pill").textContent = formatTopic(lesson.topic);
    reel.querySelector(".level-pill").textContent = lesson.level;
    reel.querySelector(".lesson-count").textContent = `${index + 1} / ${lessons.length}`;
    reel.querySelector(".lesson-hook").textContent = lesson.hook || fallbackHook(lesson.topic);
    reel.querySelector(".lesson-title").textContent = lesson.title;
    reel.querySelector(".lesson-subtitle").textContent = lesson.hook || fallbackHook(lesson.topic);
    reel.querySelector(".key-idea strong").textContent = truncateText(lesson.simple_explanation || lesson.short_text, MAX_KEY_IDEA);
    reel.querySelector(".lesson-text").textContent = truncateText(lesson.short_text, MAX_CARD_TEXT);
    applyMarketStrip(reel, lesson);

    applyBookBackground(reel, lesson);
    applyMedia(reel, lesson.book_media ? null : mediaByLesson.get(lesson.id));

    const explainButton = reel.querySelector(".explain-button");
    const exampleButton = reel.querySelector(".example-button");
    const checklistButton = reel.querySelector(".checklist-button");
    const saveButton = reel.querySelector(".save-button");
    explainButton.addEventListener("click", () => showExplanation(lesson));
    exampleButton.addEventListener("click", () => openSheet("Example", lesson.title, lesson.example, true));
    checklistButton.addEventListener("click", () => showChecklist(lesson));
    updateSaveButton(saveButton, saved.has(lesson.id));
    saveButton.addEventListener("click", () => toggleSaved(lesson.id, saveButton));

    feed.appendChild(reel);

    const railButton = document.createElement("button");
    railButton.type = "button";
    railButton.setAttribute("aria-label", `Go to ${lesson.title}`);
    railButton.addEventListener("click", () => scrollToIndex(index));
    progressRail.appendChild(railButton);
  });

  observeActiveReel();
  setActiveIndex(0);
}

function applyMedia(reel, media) {
  if (!media?.url) return;
  const imageLayer = reel.querySelector(".media-layer");
  const videoLayer = reel.querySelector(".media-video");
  if (media.type === "video") {
    videoLayer.src = media.url;
    if (media.poster) videoLayer.poster = media.poster;
    videoLayer.hidden = false;
  } else {
    const url = String(media.url).replaceAll('"', "%22");
    imageLayer.style.backgroundImage = `url("${url}")`;
    imageLayer.dataset.source = media.source || "media";
    preloadImage(url, () => {
      imageLayer.style.backgroundImage = "";
      delete imageLayer.dataset.source;
    });
  }
}

function applyMarketStrip(reel, lesson) {
  const items = reel.querySelectorAll(".market-strip span");
  const checks = miniChecksForTopic(lesson.topic);
  items.forEach((item, index) => {
    const check = checks[index];
    item.dataset.label = check.label;
    item.dataset.state = check.state;
  });
}

function miniChecksForTopic(topic) {
  if (topic.includes("risk")) return [
    { label: "Risk", state: "Defined" },
    { label: "Stop", state: "Logic" },
    { label: "Size", state: "Controlled" },
  ];
  if (topic.includes("psychology")) return [
    { label: "Plan", state: "Written" },
    { label: "Emotion", state: "Checked" },
    { label: "Action", state: "Wait" },
  ];
  if (topic.includes("liquidity")) return [
    { label: "Stops", state: "Located" },
    { label: "Sweep", state: "Check" },
    { label: "Return", state: "Confirm" },
  ];
  if (topic.includes("candle")) return [
    { label: "Location", state: "Check" },
    { label: "Close", state: "Confirm" },
    { label: "Context", state: "Needed" },
  ];
  return [
    { label: "HTF Context", state: "Check" },
    { label: "Key Level", state: "Found" },
    { label: "Confirmation", state: "Pending" },
  ];
}

function applyBookBackground(section, lesson) {
  const bookImage = lesson.book_media?.url || null;
  const bookThumb = lesson.book_media?.thumbnail || bookImage;
  const normalizedUrl = normalizeAssetUrl(bookImage);
  const normalizedThumb = normalizeAssetUrl(bookThumb);
  const source = lesson.book_media?.source || "book_media";
  if (isDevHost()) console.log("[media]", lesson.id, normalizedUrl, source);

  const overlay = document.createElement("div");
  overlay.className = "reel-overlay";
  section.appendChild(overlay);

  if (!normalizedUrl) return;

  const mediaLayer = section.querySelector(".book-media-layer");
  const mediaImage = section.querySelector(".book-media-image");
  const ghostLayer = section.querySelector(".book-ghost-layer");
  const ghostImage = section.querySelector(".book-ghost-image");
  const badge = section.querySelector(".book-media-badge");
  const preview = section.querySelector(".book-preview");
  const previewImage = preview?.querySelector("img");

  if (!mediaLayer || !mediaImage) return;

  mediaImage.dataset.src = normalizedThumb || normalizedUrl;
  mediaImage.dataset.fullSrc = normalizedUrl;
  if (ghostImage) {
    ghostImage.dataset.src = normalizedThumb || normalizedUrl;
    ghostImage.dataset.fullSrc = normalizedUrl;
  }
  if (previewImage) {
    previewImage.dataset.src = normalizedThumb || normalizedUrl;
    previewImage.dataset.fullSrc = normalizedUrl;
  }
  mediaLayer.hidden = false;
  if (ghostLayer) ghostLayer.hidden = false;
  if (preview) preview.hidden = false;
  preview?.addEventListener("click", () => openChartModal(normalizedUrl, lesson.title, lesson));

  mediaImage.addEventListener("load", () => {
    section.classList.add("has-book-media");
    if (isDevHost()) {
      if (badge) badge.hidden = false;
      console.log("[media:loaded]", lesson.id, normalizedUrl);
    }
  });

  mediaImage.addEventListener("error", () => {
    if (mediaImage.dataset.fullSrc && mediaImage.src !== new URL(mediaImage.dataset.fullSrc, window.location.href).href) {
      mediaImage.src = mediaImage.dataset.fullSrc;
      if (ghostImage) ghostImage.src = ghostImage.dataset.fullSrc || mediaImage.dataset.fullSrc;
      if (previewImage) previewImage.src = previewImage.dataset.fullSrc || mediaImage.dataset.fullSrc;
      return;
    }
    section.classList.remove("has-book-media");
    mediaLayer.hidden = true;
    if (ghostLayer) ghostLayer.hidden = true;
    if (preview) preview.hidden = true;
    if (badge) badge.hidden = true;
    mediaImage.removeAttribute("src");
    ghostImage?.removeAttribute("src");
    previewImage?.removeAttribute("src");
    if (isDevHost()) console.warn("[media:error]", lesson.id, normalizedUrl);
  });
}

function normalizeAssetUrl(url) {
  return url ? String(url).replace("../", "/") : null;
}

function openChartModal(imageUrl, title, lesson) {
  currentChart = { imageUrl, title, lesson };
  chartTitle.textContent = title || "Extracted chart";
  chartModalImage.src = imageUrl;
  chartScale = 1;
  updateChartScale();
  setChartMode("educational");
  updateChartStatus("Demo chart");
  if (!API_BASE) {
    marketChartButton.disabled = true;
    marketChartButton.title = "Market data requires API connection";
  } else {
    marketChartButton.disabled = false;
    marketChartButton.title = "";
  }
  chartBackdrop.hidden = false;
  chartModal.hidden = false;
  closeChartButton.focus();
}

function closeChartModal() {
  chartModal.hidden = true;
  chartBackdrop.hidden = true;
  chartModalImage.removeAttribute("src");
  marketCanvas.hidden = true;
  currentChart = null;
}

function updateChartScale() {
  chartModalImage.style.width = `${chartScale * 100}%`;
}

function zoomChart(delta) {
  chartScale = Math.max(0.75, Math.min(3, Number((chartScale + delta).toFixed(2))));
  updateChartScale();
}

function setChartMode(mode) {
  const isMarket = mode === "market";
  educationalChartButton.classList.toggle("active", !isMarket);
  marketChartButton.classList.toggle("active", isMarket);
  chartModalImage.hidden = isMarket;
  marketCanvas.hidden = !isMarket;
  zoomOutChartButton.disabled = isMarket;
  resetChartButton.disabled = isMarket;
  zoomInChartButton.disabled = isMarket;
}

function updateChartStatus(text) {
  chartStatus.textContent = text;
}

function showEducationalChart() {
  if (!currentChart) return;
  setChartMode("educational");
  chartModalImage.src = currentChart.imageUrl;
  updateChartStatus("Demo chart");
}

async function showMarketChart() {
  if (!API_BASE) {
    showEducationalChart();
    updateChartStatus("Market data requires API connection");
    return;
  }
  setChartMode("market");
  updateChartStatus("Loading market data...");
  drawLoadingChart();
  const symbol = symbolForLesson(currentChart?.lesson);
  const result = await requestMarketCandles(symbol, "1h").catch(() => null);
  if (!result || result.fallback || !Array.isArray(result.candles) || !result.candles.length) {
    showEducationalChart();
    updateChartStatus("Demo chart");
    return;
  }
  setChartMode("market");
  drawCandles(result.candles);
  updateChartStatus(`Market data · ${marketProviderLabel(result.provider)}`);
}

async function requestMarketCandles(symbol, interval) {
  const response = await fetch(`${API_BASE.replace(/\/$/, "")}/api/market-candles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, interval, provider: "auto" }),
  });
  return response.ok ? response.json() : null;
}

function symbolForLesson(lesson) {
  const topic = lesson?.topic || "";
  if (topic.includes("risk") || topic.includes("psychology")) return "SPY";
  if (topic.includes("liquidity")) return "EUR/USD";
  if (topic.includes("candle")) return "BTC/USD";
  return "EUR/USD";
}

function marketProviderLabel(provider) {
  if (provider === "twelvedata") return "Twelve Data";
  if (provider === "alphavantage") return "Alpha Vantage";
  return "Demo chart";
}

function drawLoadingChart() {
  const ctx = marketCanvas.getContext("2d");
  ctx.clearRect(0, 0, marketCanvas.width, marketCanvas.height);
  ctx.fillStyle = "#081019";
  ctx.fillRect(0, 0, marketCanvas.width, marketCanvas.height);
  ctx.fillStyle = "#93a1b3";
  ctx.font = "700 24px Inter, sans-serif";
  ctx.fillText("Loading market candles...", 42, 70);
}

function drawCandles(candles) {
  const ctx = marketCanvas.getContext("2d");
  const width = marketCanvas.width;
  const height = marketCanvas.height;
  const pad = { left: 54, right: 28, top: 34, bottom: 46 };
  const highs = candles.map((candle) => candle.high);
  const lows = candles.map((candle) => candle.low);
  const max = Math.max(...highs);
  const min = Math.min(...lows);
  const range = max - min || 1;
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const step = plotWidth / Math.max(candles.length, 1);
  const bodyWidth = Math.max(4, Math.min(12, step * 0.58));

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#070c13";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 6; i += 1) {
    const y = pad.top + (plotHeight / 5) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
  }

  candles.forEach((candle, index) => {
    const x = pad.left + index * step + step / 2;
    const yHigh = priceToY(candle.high, min, range, pad.top, plotHeight);
    const yLow = priceToY(candle.low, min, range, pad.top, plotHeight);
    const yOpen = priceToY(candle.open, min, range, pad.top, plotHeight);
    const yClose = priceToY(candle.close, min, range, pad.top, plotHeight);
    const up = candle.close >= candle.open;
    ctx.strokeStyle = up ? "#7ee0a4" : "#ff8c8c";
    ctx.fillStyle = up ? "rgba(126,224,164,0.86)" : "rgba(255,140,140,0.86)";
    ctx.beginPath();
    ctx.moveTo(x, yHigh);
    ctx.lineTo(x, yLow);
    ctx.stroke();
    ctx.fillRect(x - bodyWidth / 2, Math.min(yOpen, yClose), bodyWidth, Math.max(2, Math.abs(yClose - yOpen)));
  });

  ctx.fillStyle = "#93a1b3";
  ctx.font = "700 18px Inter, sans-serif";
  ctx.fillText(currentChart?.title || "Market candles", pad.left, 26);
  ctx.font = "600 14px Inter, sans-serif";
  ctx.fillText(max.toFixed(4), width - 105, pad.top + 4);
  ctx.fillText(min.toFixed(4), width - 105, height - pad.bottom);
}

function priceToY(price, min, range, top, height) {
  return top + (1 - (price - min) / range) * height;
}

function isDevHost() {
  return ["localhost", "127.0.0.1", ""].includes(window.location.hostname);
}

function preloadImage(url, onError) {
  const image = new Image();
  image.onerror = onError;
  image.src = url;
}

function formatTopic(topic) {
  return String(topic || "lesson").replaceAll("-", " ");
}

function topicVisual(topic) {
  if (topic.includes("liquidity")) return "liquidity";
  if (topic.includes("risk")) return "risk";
  if (topic.includes("psychology")) return "psychology";
  if (topic.includes("candle")) return "candlestick";
  if (topic.includes("support")) return "support";
  if (topic.includes("entries")) return "breakout";
  return "structure";
}

function fallbackHook(topic) {
  if (topic.includes("liquidity")) return "Ликвидность часто находится там, где её видят все.";
  if (topic.includes("risk")) return "Сильный трейд начинается с контроля риска.";
  if (topic.includes("psychology")) return "Решение важнее эмоции в моменте.";
  if (topic.includes("candle")) return "Свеча без контекста легко вводит в заблуждение.";
  if (topic.includes("entries")) return "Вход должен иметь причину и точку отмены.";
  return "Сначала структура, потом сигнал.";
}

function safeDomId(value) {
  return String(value || "lesson").replace(/[^a-zA-Z0-9_-]/g, "-");
}

function truncateText(value, limit) {
  const text = cleanString(value);
  if (text.length <= limit) return text;
  return `${text.slice(0, limit).trim().replace(/[,.!?;:]?$/, "")}...`;
}

function updateSaveButton(button, isSaved) {
  button.classList.toggle("saved", isSaved);
  button.textContent = isSaved ? "Saved" : "Save";
  button.setAttribute("aria-pressed", String(isSaved));
}

function toggleSaved(lessonId, button) {
  const saved = getSavedLessons();
  const willSave = !saved.has(lessonId);
  willSave ? saved.add(lessonId) : saved.delete(lessonId);
  setSavedLessons(saved);
  updateSaveButton(button, saved.has(lessonId));
  showToast(willSave ? "Added to study deck" : "Removed from saved");
}

async function showExplanation(lesson) {
  openSheet("Explain", lesson.title, "Готовлю объяснение...", false);
  if (!API_BASE) {
    openStructuredExplanation(lesson, {
      simple: lesson.simple_explanation,
      example: lesson.example,
      warning: "Local explanation · Образовательный контент. Не финансовый совет.",
    });
    return;
  }

  const aiResult = await requestWorkerExplanation(lesson, "simple").catch(() => null);
  if (aiResult?.simple) {
    openStructuredExplanation(lesson, {
      simple: aiResult.simple,
      example: aiResult.example || lesson.example,
      warning: `${providerLabel(aiResult.provider)} · ${aiResult.warning || "Образовательный контент. Не финансовый совет."}`,
    });
  } else {
    openStructuredExplanation(lesson, {
      simple: lesson.simple_explanation,
      example: lesson.example,
      warning: "Local fallback · Образовательный контент. Не финансовый совет.",
    });
  }
}

function openStructuredExplanation(lesson, result) {
  sheetKicker.textContent = "Explain";
  sheetTitle.textContent = lesson.title;
  sheetBody.replaceChildren();
  appendInfoBlock("Simple", result.simple || lesson.simple_explanation);
  appendInfoBlock("Example", result.example || lesson.example);
  appendInfoBlock("Checklist", checklistForTopic(lesson.topic).map((item) => `□ ${item}`).join("\n"));
  appendParagraph(sheetBody, result.warning || "Образовательный контент. Не финансовый совет.", "warning");
  sheet.hidden = false;
  sheetBackdrop.hidden = false;
  focusSheetClose();
}

function appendInfoBlock(title, text) {
  const block = document.createElement("div");
  block.className = "info-block";
  const heading = document.createElement("strong");
  heading.textContent = title;
  const paragraph = document.createElement("p");
  paragraph.textContent = text || "Недостаточно исходного материала для понятного объяснения.";
  block.append(heading, paragraph);
  sheetBody.appendChild(block);
}

function providerLabel(provider) {
  if (provider === "gemini") return "AI: Gemini";
  if (provider === "openrouter") return "AI: OpenRouter";
  if (provider === "fallback") return "Fallback";
  return "AI";
}

async function requestWorkerExplanation(lesson, mode) {
  if (!API_BASE) return null;
  const response = await fetch(`${API_BASE.replace(/\/$/, "")}/api/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lesson_id: lesson.id,
      title: lesson.title,
      topic: lesson.topic,
      short_text: lesson.short_text,
      mode,
    }),
  });
  return response.ok ? response.json() : null;
}

function openSheet(kicker, title, content, includeWarning = false, warning) {
  sheetKicker.textContent = kicker;
  sheetTitle.textContent = title;
  sheetBody.replaceChildren();
  appendParagraph(sheetBody, content || "This lesson needs more source material before it can be explained clearly.");
  if (includeWarning || warning) appendParagraph(sheetBody, warning || "Educational content only. Not financial advice.", "warning");
  sheet.hidden = false;
  sheetBackdrop.hidden = false;
  closeSheetButton.focus();
}

function showChecklist(lesson) {
  const lines = checklistForTopic(lesson.topic).map((item) => `□ ${item}`).join("\n");
  openSheet("Practice checklist", lesson.title, lines, true, "Перед входом проверь контекст, отмену идеи и риск. Это не торговый сигнал.");
}

function checklistForTopic(topic) {
  if (topic.includes("liquidity")) return ["Где очевидные стопы большинства участников?", "Был ли sweep или только ожидание sweep?", "Цена вернулась обратно за уровень?", "Риск заранее ограничен?"];
  if (topic.includes("risk")) return ["Размер позиции соответствует стопу?", "Потеря по сделке приемлема?", "Нет ли усреднения без плана?", "После убытка не нужно отыгрываться?"];
  if (topic.includes("psychology")) return ["Решение принято по плану, а не по эмоции?", "Нет FOMO после резкого движения?", "Сделка не нарушает дневной лимит?", "Можно спокойно принять стоп?"];
  if (topic.includes("candle")) return ["Свеча находится в важном контексте?", "Есть подтверждение, а не только форма свечи?", "Где ближайшая ликвидность?", "Риск заранее ограничен?"];
  return ["Контекст старшего таймфрейма понятен?", "Есть уровень или структура, вокруг которой строится идея?", "Понятна точка отмены сценария?", "Риск заранее ограничен?"];
}

function appendParagraph(parent, text, className) {
  const paragraph = document.createElement("p");
  if (className) paragraph.className = className;
  paragraph.textContent = text;
  parent.appendChild(paragraph);
}

function showToast(message) {
  if (!toast) return;
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  toast.classList.add("is-visible");
  toastTimer = setTimeout(() => {
    toast.classList.remove("is-visible");
    toast.hidden = true;
  }, TOAST_MS);
}

function closeSheet() {
  sheet.hidden = true;
  sheetBackdrop.hidden = true;
}

function focusSheetClose() {
  closeSheetButton.focus();
}

function observeActiveReel() {
  reelObserver?.disconnect();
  reelObserver = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) setActiveIndex(Number(visible.target.dataset.index));
  }, { root: feed, threshold: [0.55, 0.75] });
  document.querySelectorAll(".reel").forEach((reel) => reelObserver.observe(reel));
}

function setActiveIndex(index) {
  activeIndex = Math.max(0, Math.min(index, lessons.length - 1));
  [...progressRail.children].forEach((button, buttonIndex) => button.classList.toggle("active", buttonIndex === activeIndex));
  document.querySelectorAll(".reel").forEach((reel) => reel.classList.toggle("is-active", Number(reel.dataset.index) === activeIndex));
  if (activeIndex > 0) scrollHint?.classList.add("is-hidden");
  updateSessionMeta();
  loadMediaAroundActive();
  scheduleViewedMark();
  document.querySelectorAll(".media-video").forEach((video) => video.pause());
  const activeVideo = document.querySelector(`.reel[data-index="${activeIndex}"] .media-video:not([hidden])`);
  activeVideo?.play?.().catch(() => {});
}

function loadMediaAroundActive() {
  document.querySelectorAll(".reel").forEach((reel) => {
    const index = Number(reel.dataset.index);
    const shouldLoad = Math.abs(index - activeIndex) <= 1;
    reel.querySelectorAll("img[data-src]").forEach((image) => {
      if (shouldLoad && !image.getAttribute("src")) image.src = image.dataset.src;
      if (!shouldLoad && image.getAttribute("src")) image.removeAttribute("src");
    });
  });
}

function scheduleViewedMark() {
  clearTimeout(viewedTimer);
  viewedTimer = setTimeout(() => {
    const lesson = lessons[activeIndex];
    if (!lesson) return;
    const viewed = getViewedLessons();
    viewed.add(lesson.id);
    setViewedLessons(viewed);
    document.querySelector(`.reel[data-index="${activeIndex}"]`)?.classList.add("is-viewed");
  }, VIEWED_AFTER_MS);
}

function updateViewedProgress(viewed = getViewedLessons()) {
  if (!viewedProgress) return;
  const total = lessons.length || 0;
  const viewedInDeck = lessons.filter((lesson) => viewed.has(lesson.id)).length;
  viewedProgress.textContent = total ? `${viewedInDeck}/${total} viewed` : `${viewed.size} viewed`;
}

function updateSessionMeta() {
  const lesson = lessons[activeIndex];
  if (!lesson) return;
  const moduleName = moduleForTopic(lesson.topic);
  const moduleIndex = Math.max(0, moduleOrder.indexOf(moduleName)) + 1;
  sessionModule.textContent = `Module ${String(moduleIndex).padStart(2, "0")}`;
  sessionTitle.textContent = moduleName;
  if (mobileProgressFill) mobileProgressFill.style.width = `${((activeIndex + 1) / lessons.length) * 100}%`;
  updateViewedProgress();
}

function moduleForTopic(topic) {
  if (topic.includes("structure") || topic.includes("timeframe")) return "Structure";
  if (topic.includes("support")) return "Levels";
  if (topic.includes("liquidity")) return "Liquidity";
  if (topic.includes("candle")) return "Candles";
  if (topic.includes("entries")) return "Entries";
  if (topic.includes("risk")) return "Risk";
  if (topic.includes("psychology")) return "Psychology";
  return "Basics";
}

function scrollToIndex(index) {
  const targetIndex = Math.max(0, Math.min(index, lessons.length - 1));
  document.querySelector(`.reel[data-index="${targetIndex}"]`)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showSavedPanel() {
  const saved = getSavedLessons();
  const savedLessons = lessons.filter((lesson) => saved.has(lesson.id));
  if (!savedLessons.length) return openSheet("Saved lessons", "0 saved", "No saved lessons yet. Tap Save on any reel to build a study list.");
  sheetKicker.textContent = "Saved lessons";
  sheetTitle.textContent = `${savedLessons.length} saved`;
  sheetBody.replaceChildren();
  savedLessons.forEach((lesson) => appendSavedItem(lesson));
  sheet.hidden = false;
  sheetBackdrop.hidden = false;
  focusSheetClose();
}

function appendSavedItem(lesson) {
  const item = document.createElement("div");
  item.className = "saved-item";
  const meta = document.createElement("span");
  meta.textContent = formatTopic(lesson.topic);
  const title = document.createElement("strong");
  title.textContent = lesson.title;
  const text = document.createElement("p");
  text.textContent = truncateText(lesson.short_text, 150);
  const actions = document.createElement("div");
  actions.className = "saved-actions";
  const go = document.createElement("button");
  go.type = "button";
  go.textContent = "Open";
  go.addEventListener("click", () => {
    closeSheet();
    scrollToIndex(lessons.findIndex((itemLesson) => itemLesson.id === lesson.id));
  });
  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "Remove";
  remove.addEventListener("click", () => {
    const saved = getSavedLessons();
    saved.delete(lesson.id);
    setSavedLessons(saved);
    document.querySelectorAll(".save-button").forEach((button) => {
      const reel = button.closest(".reel");
      const reelLesson = lessons[Number(reel?.dataset.index || 0)];
      if (reelLesson?.id === lesson.id) updateSaveButton(button, false);
    });
    item.remove();
    if (!saved.size) showSavedPanel();
  });
  actions.append(go, remove);
  item.append(meta, title, text, actions);
  sheetBody.appendChild(item);
}

function showPathPanel() {
  sheetKicker.textContent = "Learning path";
  sheetTitle.textContent = "Modules";
  sheetBody.replaceChildren();
  moduleOrder.forEach((moduleName) => {
    const moduleLessons = lessons.filter((lesson) => moduleForTopic(lesson.topic) === moduleName);
    if (!moduleLessons.length) return;
    const item = document.createElement("button");
    item.type = "button";
    item.className = "path-item";
    const firstIndex = lessons.findIndex((lesson) => moduleForTopic(lesson.topic) === moduleName);
    item.addEventListener("click", () => {
      closeSheet();
      scrollToIndex(firstIndex);
    });
    const title = document.createElement("strong");
    title.textContent = moduleName;
    const count = document.createElement("span");
    const viewed = getViewedLessons();
    const viewedCount = moduleLessons.filter((lesson) => viewed.has(lesson.id)).length;
    count.textContent = `${viewedCount}/${moduleLessons.length} viewed`;
    const progress = document.createElement("small");
    progress.className = "path-progress";
    progress.style.setProperty("--path-progress", `${(viewedCount / moduleLessons.length) * 100}%`);
    item.append(title, count);
    item.appendChild(progress);
    sheetBody.appendChild(item);
  });
  sheet.hidden = false;
  sheetBackdrop.hidden = false;
  focusSheetClose();
}

function showCreditsPanel() {
  sheetKicker.textContent = "Credits";
  sheetTitle.textContent = "Sources and Media";
  sheetBody.replaceChildren();
  if (credits?.policy) appendParagraph(sheetBody, credits.policy);
  (credits?.sources || []).forEach((source) => appendCreditItem(source.name, source.note, source.type, source.url));
  const mediaItems = [...mediaByLesson.values()];
  if (mediaItems.length) appendParagraph(sheetBody, "Media assets used in the current lesson deck:", "warning");
  mediaItems.forEach((item) => appendCreditItem(`${item.lesson_id} - ${item.source}`, `${item.author || "Unknown author"} - ${item.license || "License not listed"}`, item.query || item.type, item.source_url));
  if (!mediaItems.length) appendParagraph(sheetBody, "No external media is active. Reels are using local CSS market visuals.", "warning");
  sheet.hidden = false;
  sheetBackdrop.hidden = false;
  focusSheetClose();
}

function appendCreditItem(title, note, meta, url) {
  const item = document.createElement("div");
  item.className = "credit-item";
  const strong = document.createElement("strong");
  strong.textContent = title || "Credit";
  const small = document.createElement("small");
  small.textContent = [meta, note].filter(Boolean).join(" - ");
  item.append(strong, small);
  if (url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Source link";
    item.appendChild(link);
  }
  sheetBody.appendChild(item);
}

document.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (["input", "textarea", "select"].includes(document.activeElement?.tagName?.toLowerCase())) return;
  if (event.key === "Escape") {
    closeSheet();
    closeChartModal();
    return;
  }
  if (!sheet.hidden || !chartModal.hidden) return;
  if (event.key === "ArrowDown") { event.preventDefault(); scrollToIndex(activeIndex + 1); }
  if (event.key === "ArrowUp") { event.preventDefault(); scrollToIndex(activeIndex - 1); }
  if (key === "s") document.querySelector(`.reel[data-index="${activeIndex}"] .save-button`)?.click();
  if (key === "e") document.querySelector(`.reel[data-index="${activeIndex}"] .example-button`)?.click();
  if (key === "x") document.querySelector(`.reel[data-index="${activeIndex}"] .explain-button`)?.click();
  if (key === "c") document.querySelector(`.reel[data-index="${activeIndex}"] .checklist-button`)?.click();
});

feed.addEventListener("click", (event) => {
  if (event.target.closest("button, a, input, textarea, select")) return;
  if (window.matchMedia("(min-width: 761px)").matches) return;
  const x = event.clientX / window.innerWidth;
  if (x > 0.68) scrollToIndex(activeIndex + 1);
  if (x < 0.32) scrollToIndex(activeIndex - 1);
});

closeSheetButton.addEventListener("click", closeSheet);
sheetBackdrop.addEventListener("click", closeSheet);
closeChartButton.addEventListener("click", closeChartModal);
educationalChartButton.addEventListener("click", showEducationalChart);
marketChartButton.addEventListener("click", showMarketChart);
zoomOutChartButton.addEventListener("click", () => zoomChart(-0.25));
resetChartButton.addEventListener("click", () => { chartScale = 1; updateChartScale(); });
zoomInChartButton.addEventListener("click", () => zoomChart(0.25));
chartBackdrop.addEventListener("click", closeChartModal);
pathButton.addEventListener("click", showPathPanel);
savedButton.addEventListener("click", showSavedPanel);
creditsButton.addEventListener("click", showCreditsPanel);

init();
