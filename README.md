# Trading Reels AI

Trading Reels AI is a lightweight, scroll-first trading education app. It turns the user's local licensed trading books into short Reels-style lessons, then uses optional AI and media helpers around that source content.

The MVP stays simple:

- Static frontend in `frontend/`.
- Book-derived JSON lessons in `content/`.
- Local-only PDFs in `content/books/`.
- Optional media metadata from Pexels/Pixabay in `content/media.json`.
- Cloudflare Worker placeholder in `worker/`.

## Project Structure

```text
trade_site/
  frontend/
    index.html
    style.css
    app.js
    data/
      lessons.json
      media.json
      credits.json
      book_images/
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

`content/lessons.json` is the source lesson file. `frontend/data/lessons.json` is the deployment-ready runtime copy used by Cloudflare Pages.

## Prepare Pages Data

Generate the static runtime bundle for Cloudflare Pages:

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

## Worker Placeholder

The Worker exposes:

- `GET /health`
- `POST /api/explain`
- `POST /api/market-candles`
- `GET /api/media-status`

Future secrets belong in Cloudflare Secrets:

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

Market candles are optional and always go through the Worker. The frontend never calls Alpha Vantage or Twelve Data directly and never stores API keys.

Add market-data secrets in Cloudflare:

```bash
cd worker
wrangler secret put ALPHA_VANTAGE_API_KEY
wrangler secret put TWELVE_DATA_API_KEY
wrangler deploy
```

Connect the frontend to the Worker before `frontend/app.js` loads:

```html
<script>
window.TRADING_REELS_API_BASE = "https://your-worker.workers.dev";
</script>
```

The chart modal defaults to the educational/book chart. If `Market` is selected, the frontend calls `POST /api/market-candles`. The Worker tries Twelve Data first, then Alpha Vantage, then returns a safe demo fallback. Without a Worker or API keys, the app stays on educational demo charts.

For local testing, run the static frontend and Worker separately. On `localhost`, the frontend automatically tries `http://localhost:8787` when `TRADING_REELS_API_BASE` is not set.

Terminal 1:

```bash
python -m http.server 8080
```

Terminal 2:

```bash
cd worker
wrangler dev
```

For local Worker secrets, use Wrangler secrets or a local `.dev.vars` file that is ignored by Git:

```text
ALPHA_VANTAGE_API_KEY=your_key
TWELVE_DATA_API_KEY=your_key
```

Then open:

```text
http://localhost:8080/frontend/
```

## Publish Frontend to Cloudflare Pages

Cloudflare Pages settings:

```text
Framework preset: None
Build command: empty
Build output directory: frontend
Production branch: main
```

The deployed static frontend uses `frontend/data/` at runtime. It works without a Worker by using local lesson data, local/book images, CSS visuals, local explanation fallback, and demo educational charts.

AI explanations and market-data candles require the optional Worker.

## Optional Worker Deploy

Set secrets with Wrangler. Do not put real keys in frontend files, docs, JSON, or `wrangler.toml`.

```bash
cd worker
wrangler secret put GEMINI_API_KEY
wrangler secret put OPENROUTER_API_KEY
wrangler secret put ALPHA_VANTAGE_API_KEY
wrangler secret put TWELVE_DATA_API_KEY
wrangler deploy
```

If you deploy the Worker, configure the frontend API base before `frontend/app.js` loads:

```html
<script>
window.TRADING_REELS_API_BASE = "https://your-worker.your-subdomain.workers.dev";
</script>
```

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
node --check worker/src/index.js
git status --short
```
