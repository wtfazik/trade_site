# Trading Reels API

Express API for the Trading Reels AI MVP on Render.

## Local Run

```bash
npm install
npm start
```

Health check:

```text
http://localhost:3000/health
```

## Endpoints

- `GET /health`
- `POST /api/explain`
- `POST /api/market-candles`
- `GET /api/media-status`

## Environment Variables

Set these in Render environment variables. Do not commit real values.

```text
GEMINI_API_KEY
OPENROUTER_API_KEY
ALPHA_VANTAGE_API_KEY
TWELVE_DATA_API_KEY
PEXELS_API_KEY
PIXABAY_API_KEY
```

Optional for a fully open MVP CORS policy:

```text
CORS_ALLOW_ALL=true
```

By default, CORS allows localhost and Vercel preview/production domains.
