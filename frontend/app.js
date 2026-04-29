const feed = document.querySelector("#top");
const loadingState = document.querySelector("#loadingState");
const template = document.querySelector("#reelTemplate");
const progressRail = document.querySelector("#progressRail");
const sheet = document.querySelector("#bottomSheet");
const sheetBackdrop = document.querySelector("#sheetBackdrop");
const sheetTitle = document.querySelector("#sheetTitle");
const sheetKicker = document.querySelector("#sheetKicker");
const sheetBody = document.querySelector("#sheetBody");
const closeSheetButton = document.querySelector("#closeSheet");
const creditsButton = document.querySelector("#creditsButton");
const savedButton = document.querySelector("#savedButton");
const savedCount = document.querySelector("#savedCount");

const LESSONS_URL = "../content/lessons.json";
const SAMPLE_LESSONS_URL = "../content/lessons.sample.json";
const CREDITS_URL = "../content/credits.json";
const SAVED_KEY = "trading-reels-ai:saved-lessons";
const MAX_CARD_TEXT = 260;
const visualClasses = {
  support: "visual-support",
  candlestick: "visual-candle",
  trend: "visual-trend",
  liquidity: "visual-structure",
  risk: "visual-risk",
  stop: "visual-risk",
  structure: "visual-structure",
  breakout: "visual-candle",
  psychology: "visual-support",
  sizing: "visual-risk",
};

let lessons = [];
let credits = null;
let activeIndex = 0;
let reelObserver = null;

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

async function loadJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Unable to load ${url}`);
  }
  return response.json();
}

async function init() {
  setSavedLessons(getSavedLessons());

  try {
    const [loadedLessons, creditData] = await Promise.all([
      loadLessonsWithFallback(),
      loadJson(CREDITS_URL).catch(() => null),
    ]);
    lessons = loadedLessons;
    credits = creditData;
    renderLessons();
  } catch (error) {
    renderLoadError(error);
  }
}

async function loadLessonsWithFallback() {
  try {
    return normalizeLessons(await loadJson(LESSONS_URL));
  } catch (primaryError) {
    console.warn("Falling back to sample lessons:", primaryError);
  }

  try {
    return normalizeLessons(await loadJson(SAMPLE_LESSONS_URL));
  } catch (sampleError) {
    throw new Error("Could not load active or sample lessons. Start a local server and check content JSON files.");
  }
}

function normalizeLessons(data) {
  const list = Array.isArray(data) ? data : data?.lessons;
  if (!Array.isArray(list)) {
    throw new Error("Lesson file must contain an array of lessons.");
  }

  const normalized = list
    .map((lesson, index) => ({
      id: cleanString(lesson?.id) || `lesson-${String(index + 1).padStart(3, "0")}`,
      title: cleanString(lesson?.title) || "Trading Insight",
      topic: cleanString(lesson?.topic) || "lesson",
      short_text: cleanString(lesson?.short_text),
      simple_explanation: cleanString(lesson?.simple_explanation),
      example: cleanString(lesson?.example),
      image_query: cleanString(lesson?.image_query),
      visual: lesson?.visual && typeof lesson.visual === "object" ? lesson.visual : { type: "gradient", value: "support" },
      source: cleanString(lesson?.source) || "unknown",
    }))
    .filter((lesson) => lesson.short_text || lesson.simple_explanation || lesson.example);

  if (!normalized.length) {
    throw new Error("No usable lessons found in the lesson file.");
  }

  return normalized;
}

function cleanString(value) {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

function renderLoadError(error) {
  feed.replaceChildren(createStateCard({
    kicker: "Content unavailable",
    title: "Lessons could not load.",
    message: `${error.message} Run python -m http.server 8080 from the repo root, then open http://localhost:8080/frontend/.`,
  }));
  progressRail.replaceChildren();
}

function createStateCard({ kicker, title, message }) {
  const section = document.createElement("section");
  section.className = "loading-state";

  const card = document.createElement("div");
  card.className = "loader-card";

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
    const visualKey = lesson.visual?.value || lesson.visual?.type || "support";
    reel.id = safeDomId(lesson.id);
    reel.dataset.index = String(index);
    reel.classList.add(visualClasses[visualKey] || "visual-support");
    reel.querySelector(".topic-pill").textContent = formatTopic(lesson.topic);
    reel.querySelector(".lesson-count").textContent = `${index + 1} / ${lessons.length}`;
    reel.querySelector(".lesson-title").textContent = lesson.title;
    reel.querySelector(".lesson-text").textContent = truncateText(lesson.short_text, MAX_CARD_TEXT);

    const explainButton = reel.querySelector(".explain-button");
    const exampleButton = reel.querySelector(".example-button");
    const saveButton = reel.querySelector(".save-button");

    explainButton.addEventListener("click", () => showExplanation(lesson));
    exampleButton.addEventListener("click", () => openSheet("Example", lesson.title, lesson.example));
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

function formatTopic(topic) {
  return String(topic || "lesson").replaceAll("-", " ");
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
  if (saved.has(lessonId)) {
    saved.delete(lessonId);
  } else {
    saved.add(lessonId);
  }
  setSavedLessons(saved);
  updateSaveButton(button, saved.has(lessonId));
}

async function showExplanation(lesson) {
  openSheet("Explain simpler", lesson.title, lesson.simple_explanation, true);

  // Future Worker call: POST /api/explain can use Cloudflare Secrets named
  // GEMINI_API_KEY or OPENROUTER_API_KEY. Never put those keys in this file.
  const aiResult = await requestWorkerExplanation(lesson).catch(() => null);
  if (aiResult?.simple) {
    openSheet("Explain simpler", lesson.title, aiResult.simple, true, aiResult.warning);
  }
}

async function requestWorkerExplanation(lesson) {
  const workerUrl = window.TRADING_REELS_WORKER_URL;
  if (!workerUrl) return null;

  const response = await fetch(`${workerUrl.replace(/\/$/, "")}/api/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lesson }),
  });

  if (!response.ok) return null;
  return response.json();
}

function openSheet(kicker, title, content, includeWarning = false, warning) {
  sheetKicker.textContent = kicker;
  sheetTitle.textContent = title;
  sheetBody.replaceChildren();

  const paragraph = document.createElement("p");
  paragraph.textContent = content || "This lesson needs more source material before it can be explained clearly.";
  sheetBody.appendChild(paragraph);

  if (includeWarning || warning) {
    const warningNode = document.createElement("p");
    warningNode.className = "warning";
    warningNode.textContent = warning || "Educational content only. Not financial advice.";
    sheetBody.appendChild(warningNode);
  }

  sheet.hidden = false;
  sheetBackdrop.hidden = false;
  closeSheetButton.focus();
}

function closeSheet() {
  sheet.hidden = true;
  sheetBackdrop.hidden = true;
}

function observeActiveReel() {
  reelObserver?.disconnect();
  reelObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActiveIndex(Number(visible.target.dataset.index));
    },
    { root: feed, threshold: [0.55, 0.75] }
  );

  document.querySelectorAll(".reel").forEach((reel) => reelObserver.observe(reel));
}

function setActiveIndex(index) {
  activeIndex = Math.max(0, Math.min(index, lessons.length - 1));
  [...progressRail.children].forEach((button, buttonIndex) => {
    button.classList.toggle("active", buttonIndex === activeIndex);
  });
}

function scrollToIndex(index) {
  const targetIndex = Math.max(0, Math.min(index, lessons.length - 1));
  const reel = document.querySelector(`.reel[data-index="${targetIndex}"]`);
  reel?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showSavedPanel() {
  const saved = getSavedLessons();
  const savedLessons = lessons.filter((lesson) => saved.has(lesson.id));
  const content = savedLessons.length
    ? savedLessons.map((lesson) => `${lesson.title}: ${lesson.short_text}`).join("\n\n")
    : "No saved lessons yet. Tap Save on any reel to build a study list.";
  openSheet("Saved lessons", `${savedLessons.length} saved`, content);
}

function showCreditsPanel() {
  const sources = credits?.sources?.length
    ? credits.sources.map((source) => `${source.name}: ${source.note}`).join("\n\n")
    : "MVP visuals are generated with local CSS gradients. Future Pexels/Pixabay media credits will be stored in content/credits.json.";
  openSheet("Credits", "Media and Sources", sources);
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeSheet();
  if (event.key === "ArrowDown") {
    event.preventDefault();
    scrollToIndex(activeIndex + 1);
  }
  if (event.key === "ArrowUp") {
    event.preventDefault();
    scrollToIndex(activeIndex - 1);
  }
});

closeSheetButton.addEventListener("click", closeSheet);
sheetBackdrop.addEventListener("click", closeSheet);
savedButton.addEventListener("click", showSavedPanel);
creditsButton.addEventListener("click", showCreditsPanel);

init();
