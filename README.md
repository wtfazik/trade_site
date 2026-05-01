# Trading Reels AI

Trading Reels AI is a lightweight, scroll-first trading education app. It turns the user's local licensed trading books into short Reels-style lessons, then uses optional AI and media helpers around that source content.

The MVP stays simple:

- Static frontend in `frontend/`.
- Book-derived JSON lessons in `content/`.
- Local-only PDFs in `content/books/`.
- Optional media metadata from Pexels/Pixabay in `content/media.json`.
- Render-ready Express API in `backend/`.
- Cloudflare Worker alternative in `worker/`.

## Project Structure

```text
trade_site/
  frontend/
    index.html
    style.css
    app.js
    config.example.js
    data/
      lessons.json
      media.json
      credits.json
      book_images/
  backend/
    package.json
    server.js
    README.md
  content/
    books/.gitkeep
    extracted/.gitkeep
    credits.json
    media.json
    lessons.json
    lessons.generated.json
    lessons.generated.deep.json
    lessons.sample.json
  tools/
    deep_pdf_to_reels.py
    extract_book_images.py
    fetch_media.py
    match_images_to_lessons.py
    optimize_book_images.py
    pdf_to_lessons.py
    prepare_pages_data.py
    generate_chart_configs.py
    review_lessons.py
  worker/
    src/index.js
    wrangler.toml
  README.md
  AGENTS.md
  requirements.txt
```

## Local Test

Run from the repo root:

```bash
python -m http.server 8080
```

Open:

```text
http://localhost:8080/frontend/
```

## Add Books Locally

Put your licensed PDF books in:

```text
content/books/
```

Books are local-only. Do not commit PDFs, ZIPs, uploads, extracted text, or secrets.

## Generate Deep Lessons

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate curated book-derived reels:

```bash
python tools/deep_pdf_to_reels.py
```

This writes:

```text
content/lessons.generated.deep.json
content/lessons.json
```

`content/lessons.json` is the source lesson file. `frontend/data/lessons.json` is the deployment-ready runtime copy used by Vercel.

## Prepare Frontend Data

Generate the static runtime bundle for Vercel:

```bash
python tools/prepare_pages_data.py
python tools/generate_chart_configs.py
```

This writes safe frontend runtime data to:

```text
frontend/data/lessons.json
frontend/data/media.json
frontend/data/credits.json
frontend/data/book_images/
```

Only book images referenced by active lessons are copied into `frontend/data/book_images/`.

## Fetch Media

Media fetching is optional. API keys must come from environment variables only. Never put keys in frontend code, JSON files, docs, `wrangler.toml`, or commits.

PowerShell:

```powershell
$env:PEXELS_API_KEY="your_key"
$env:PIXABAY_API_KEY="your_key"
python tools/fetch_media.py
```

Bash:

```bash
PEXELS_API_KEY="your_key" PIXABAY_API_KEY="your_key" python tools/fetch_media.py
```

If keys are missing, the script writes a safe empty fallback:

```json
[]
```

Media metadata is stored in:

```text
content/media.json
```

The app falls back to local CSS market visuals when media is missing.

## Extract Book Images

Extract embedded chart-like images from local PDFs:

```bash
python tools/extract_book_images.py
python tools/optimize_book_images.py
python tools/match_images_to_lessons.py
```

Images are written to:

```text
content/extracted/book_images/
```

Safe metadata is written to:

```text
content/extracted/book_images.json
```

The frontend visual priority is:

1. `lesson.book_media` from extracted book images
2. `content/media.json` Pexels/Pixabay metadata
3. CSS/SVG trading visuals

Extracted image files are ignored by Git by default.

## Review Lessons

Run quality checks for lesson language, missing fields, forbidden secret-like strings, and oversized cards:

```bash
python tools/review_lessons.py
```

## Render Backend

The primary backend for this deployment plan is the Express API in `backend/`.

Local API test:

```bash
cd backend
npm install
npm start
```

Endpoints:

- `GET /health`
- `POST /api/explain`
- `POST /api/market-candles`
- `GET /api/media-status`

Secrets belong in Render environment variables only:

```text
GEMINI_API_KEY
OPENROUTER_API_KEY
ALPHA_VANTAGE_API_KEY
TWELVE_DATA_API_KEY
PEXELS_API_KEY
PIXABAY_API_KEY
```

The backend uses Gemini first, OpenRouter second, and a safe Russian fallback when AI keys are missing or provider calls fail. Market candles use Twelve Data first, Alpha Vantage second, and demo fallback when market keys or providers fail.

## Worker Alternative

The Worker exposes:

- `GET /health`
- `POST /api/explain`
- `POST /api/market-candles`
- `GET /api/media-status`

The Cloudflare Worker remains in the repo as an alternative backend, but it is not the current deployment target.

Worker secrets belong in Cloudflare Secrets:

```bash
cd worker
wrangler secret put GEMINI_API_KEY
wrangler secret put OPENROUTER_API_KEY
wrangler secret put PEXELS_API_KEY
wrangler secret put PIXABAY_API_KEY
wrangler secret put ALPHA_VANTAGE_API_KEY
wrangler secret put TWELVE_DATA_API_KEY
```

Deploy the Worker later with:

```bash
cd worker
wrangler deploy
```

Connect the static frontend to a deployed Worker by defining the API base before `frontend/app.js` loads:

```html
<script>
window.TRADING_REELS_API_BASE = "https://your-worker.your-subdomain.workers.dev";
</script>
```

If `TRADING_REELS_API_BASE` is not set, the frontend uses local Russian fallback explanations.

## Optional Market Data

Market candles are optional and always go through the backend API. The frontend never calls Alpha Vantage or Twelve Data directly and never stores API keys.

Add market-data secrets in Render:

```text
ALPHA_VANTAGE_API_KEY
TWELVE_DATA_API_KEY
```

Connect the frontend to the Render API by editing the public API base in `frontend/config.js`, or by injecting the same assignment before `frontend/app.js` loads:

```html
<script>
window.TRADING_REELS_API_BASE = "https://your-render-service.onrender.com";
</script>
```

The chart modal defaults to the educational/book chart. If `Market` is selected, the frontend calls `POST /api/market-candles`. The backend tries Twelve Data first, then Alpha Vantage, then returns a safe demo fallback. Without a backend or API keys, the app stays on educational demo charts.

For local testing, run the static frontend and backend separately. On `localhost`, the frontend automatically tries `http://localhost:8787` when `TRADING_REELS_API_BASE` is not set. To use the Express backend locally, set `frontend/config.js` to `http://localhost:3000`.

Terminal 1:

```bash
python -m http.server 8080
```

Terminal 2:

```bash
cd backend
npm install
npm start
```

Optional local frontend API config in `frontend/config.js`:

```text
window.TRADING_REELS_API_BASE = "http://localhost:3000";
```

Then open:

```text
http://localhost:8080/frontend/
```

## Deploy Frontend to Vercel

Vercel settings:

```text
Framework preset: Other
Root Directory: .
Build Command: empty
Output Directory: frontend
Install Command: empty
Production branch: main
```

`vercel.json` keeps `/` mapped to `frontend/index.html` when Vercel serves the static output. Vercel deploys automatically from GitHub after push.

The deployed static frontend uses `frontend/data/` at runtime. It works without the Render backend by using local lesson data, selected book images, CSS visuals, local explanation fallback, and demo educational charts.

AI explanations and market-data candles require the optional Render backend.

## Deploy Backend to Render

Render Web Service settings:

```text
Root Directory: backend
Runtime: Node
Build Command: npm install
Start Command: npm start
```

Render environment variables:

```text
GEMINI_API_KEY
OPENROUTER_API_KEY
ALPHA_VANTAGE_API_KEY
TWELVE_DATA_API_KEY
PEXELS_API_KEY
PIXABAY_API_KEY
```

After Render deploys, copy the backend URL and connect the frontend API base in `frontend/config.js`, or inject this snippet before `app.js`:

```html
<script>
window.TRADING_REELS_API_BASE = "https://your-render-service.onrender.com";
</script>
```

Never put API keys in frontend config. The value above is only a public API base URL.

## Important

Never commit:

- API keys
- `.env`
- `.env.*`
- `.dev.vars`
- PDFs
- ZIPs
- `content/books/*`
- `content/extracted/*`
- `content/extracted/book_images/*`
- raw private book files
- `content/uploads/*`

Be careful with:

- `content/lessons.generated.deep.json`
- `content/lessons.json`
- `content/media.json`
- `content/extracted/book_images.json`

They may contain book-derived educational content or external asset URLs. Review them before committing.

## Pre-Commit Checks

```bash
python -m json.tool content/lessons.json
python -m json.tool frontend/data/lessons.json
python -m json.tool frontend/data/media.json
python -m json.tool frontend/data/credits.json
python -m json.tool content/credits.json
python -m json.tool content/media.json
python -m py_compile tools/deep_pdf_to_reels.py
python -m py_compile tools/fetch_media.py
python -m py_compile tools/extract_book_images.py
python -m py_compile tools/match_images_to_lessons.py
python -m py_compile tools/optimize_book_images.py
python -m py_compile tools/review_lessons.py
python -m py_compile tools/prepare_pages_data.py
python -m py_compile tools/generate_chart_configs.py
python tools/review_lessons.py
node --check frontend/app.js
node --check backend/server.js
node --check worker/src/index.js
cd backend
npm install
npm run start-check
git status --short
```
