#!/usr/bin/env python3
"""Generate a small deterministic chart config manifest for deployment checks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "data" / "chart_configs.json"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    configs = {
        "default": "educational",
        "symbols": ["EUR/USD", "BTC/USD", "ETH/USD", "XAU/USD", "SPY"],
        "intervals": ["5min", "15min", "30min", "1h", "4h", "1day"],
        "fallback": "demo-chart",
    }
    OUTPUT.write_text(json.dumps(configs, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
