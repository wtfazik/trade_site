# AGENTS.md

Instructions for future Codex/OpenCode work on Trading Reels AI.

## Product Direction

- Keep the project lightweight unless the user explicitly asks for a heavier framework.
- Main content comes from the user's licensed books.
- AI is an explanation helper, not the primary content source.
- Maintain a premium, calm, professional trading education feel.
- Prioritize polished mobile and desktop UX.

## Security

- Do not expose secrets in frontend code.
- Do not commit API keys, `.env` files, PDFs, ZIPs, uploaded books, or extracted book content.
- Use Cloudflare Secrets for future `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `PEXELS_API_KEY`, and `PIXABAY_API_KEY`.
- Never add real keys to `wrangler.toml`, JavaScript source, JSON content, docs, tests, or examples.

## Architecture

- Frontend MVP stays in `frontend/index.html`, `frontend/style.css`, and `frontend/app.js`.
- Active public lesson content is `content/lessons.json`.
- Sample lesson content is `content/lessons.sample.json`.
- Generated drafts go to `content/lessons.generated.json`.
- Worker placeholder stays in `worker/src/index.js` with config in `worker/wrangler.toml`.
- Python tools stay in `tools/` with dependencies in `requirements.txt`.

## UI Rules

- No dead buttons. Every visible button must work or be hidden.
- Preserve scroll-snap reel behavior.
- Keep text readable and spacing responsive.
- Do not add random neon overload or generic AI-template sections.
- Use CSS gradients and local visuals until external media is explicitly integrated.

## Code Rules

- Prefer small, readable changes.
- Avoid introducing build steps for the MVP unless requested.
- Keep browser code dependency-free.
- Keep Worker responses safe and educational.
- Keep generated lesson text conservative and deterministic.
- Add comments only where they clarify non-obvious behavior or future secret-safe integration points.
