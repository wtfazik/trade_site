#!/usr/bin/env python3
"""Generate edited trading reel lessons from local PDFs.

The script is deterministic and API-free. It uses PDF text as evidence that a
concept appears in the local book library, then writes concise educational reel
cards from a curated concept bank. It intentionally avoids raw paragraph dumps.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "content" / "books"
DEEP_OUTPUT = ROOT / "content" / "lessons.generated.deep.json"
ACTIVE_OUTPUT = ROOT / "content" / "lessons.json"
MAX_FINAL_LESSONS = 60
MIN_TARGET_LESSONS = 25


CONCEPT_BANK = [
    {
        "title": "Read Price In Context",
        "topic": "price-action",
        "order": 10,
        "visual": "structure",
        "keywords": ["price action", "market", "chart", "context", "setup"],
        "short_text": "A single candle or level means more when it is read inside the larger market context. Start with the current structure before judging a setup.",
        "simple_explanation": "Do not treat one signal as the whole story. First ask whether price is trending, ranging, or shifting direction.",
        "example": "A bullish candle at support is more useful if the broader structure is also making higher lows. Educational content only. Not financial advice.",
        "image_query": "price action trading chart",
    },
    {
        "title": "Start With Higher Timeframes",
        "topic": "timeframes",
        "order": 11,
        "visual": "structure",
        "keywords": ["timeframe", "htf", "ltf", "higher timeframe", "lower timeframe"],
        "short_text": "Higher timeframes help define the main direction, while lower timeframes help refine entries. Mixing them without a plan can create conflicting signals.",
        "simple_explanation": "Use the bigger chart for the map and the smaller chart for timing. The smaller chart should not make you ignore the larger context.",
        "example": "A trader might mark a daily resistance zone, then wait on a 15-minute chart for rejection before considering a short idea.",
        "image_query": "multiple timeframe trading analysis",
    },
    {
        "title": "Trend Is A Sequence",
        "topic": "market-structure",
        "order": 20,
        "visual": "structure",
        "keywords": ["trend", "higher high", "higher low", "lower high", "lower low"],
        "short_text": "A trend is built from a sequence of highs and lows, not from one strong candle. Watch whether price keeps accepting higher or lower levels.",
        "simple_explanation": "An uptrend usually pushes to higher highs and holds higher lows. A downtrend usually creates lower highs and lower lows.",
        "example": "If price makes a higher high and then holds above the prior swing low, the uptrend structure remains healthier than a one-candle spike.",
        "image_query": "market structure higher highs higher lows",
    },
    {
        "title": "Structure Shift Matters",
        "topic": "market-structure",
        "order": 21,
        "visual": "structure",
        "keywords": ["choch", "change of character", "bos", "break of structure", "structure shift"],
        "short_text": "A structure shift happens when price breaks the rhythm that was controlling the move. It is a reason to reassess, not a signal to chase blindly.",
        "simple_explanation": "When a market stops making the same kind of swings, the previous plan may no longer fit.",
        "example": "If an uptrend breaks below the last meaningful higher low, a trader may pause long ideas until price rebuilds structure.",
        "image_query": "break of structure trading chart",
    },
    {
        "title": "Ranges Need Patience",
        "topic": "market-structure",
        "order": 22,
        "visual": "structure",
        "keywords": ["range", "consolidation", "premium", "discount", "accumulation"],
        "short_text": "Inside a range, price often rotates between areas instead of trending cleanly. The best lesson is patience: avoid forcing trend trades in a balanced market.",
        "simple_explanation": "A range is a market pause. Price can move both ways without giving a clear long-term direction.",
        "example": "If price keeps rejecting the same high and low, a trader may wait for a clean break and hold instead of entering in the middle.",
        "image_query": "trading range consolidation chart",
    },
    {
        "title": "Support Is An Area",
        "topic": "support-resistance",
        "order": 30,
        "visual": "support",
        "keywords": ["support", "floor", "demand", "bounce", "support level"],
        "short_text": "Support is better treated as an area where buyers previously reacted, not as a perfect line. Price can pierce the area before deciding.",
        "simple_explanation": "Think of support as a zone where buyers may care. It still needs confirmation from price behavior.",
        "example": "If price has bounced near a level several times, a trader may wait for rejection or a reclaim before considering the level useful.",
        "image_query": "support zone trading chart",
    },
    {
        "title": "Resistance Is Supply",
        "topic": "support-resistance",
        "order": 31,
        "visual": "support",
        "keywords": ["resistance", "supply", "ceiling", "rejection", "resistance level"],
        "short_text": "Resistance marks an area where sellers previously had enough strength to slow or reverse price. Clean rejection is more useful than a simple touch.",
        "simple_explanation": "Resistance is a zone where selling pressure may appear. Wait for price behavior, not just contact with the line.",
        "example": "If price taps resistance and closes back below it with weak follow-through, that may show buyers failed to accept higher prices.",
        "image_query": "resistance zone trading chart",
    },
    {
        "title": "Broken Levels Can Flip",
        "topic": "support-resistance",
        "order": 32,
        "visual": "support",
        "keywords": ["rbs", "sbr", "resistance becomes support", "support becomes resistance", "breaker"],
        "short_text": "A broken support can become resistance, and a broken resistance can become support. The retest shows whether the market accepts the new side of the level.",
        "simple_explanation": "When price crosses an important area, traders watch the next visit to see if the old level has changed roles.",
        "example": "After a breakout above resistance, a pullback that holds the old resistance as support can confirm stronger acceptance.",
        "image_query": "support resistance flip trading",
    },
    {
        "title": "Key Levels Need Reactions",
        "topic": "support-resistance",
        "order": 33,
        "visual": "support",
        "keywords": ["key level", "open close", "ocl", "level", "zone"],
        "short_text": "A key level only becomes useful when price reacts around it. Marking levels is preparation; reading the reaction is the decision point.",
        "simple_explanation": "A level on the chart is not a trade by itself. The behavior near it matters most.",
        "example": "A trader may mark a weekly level, then wait for a rejection wick, failed breakout, or strong close before making a plan.",
        "image_query": "key levels trading chart",
    },
    {
        "title": "Liquidity Sits Near Obvious Highs",
        "topic": "liquidity",
        "order": 40,
        "visual": "liquidity",
        "keywords": ["liquidity", "swing high", "external range liquidity", "erl", "highs"],
        "short_text": "Liquidity often builds above visible highs because many traders place stops or breakout orders there. Price may move there before making its real decision.",
        "simple_explanation": "Obvious highs attract orders. Markets often visit those areas because there is activity waiting there.",
        "example": "If price rallies above a prior high and then quickly falls back below it, the move may have collected liquidity instead of starting a trend.",
        "image_query": "liquidity above swing highs trading",
    },
    {
        "title": "Liquidity Sits Below Lows",
        "topic": "liquidity",
        "order": 41,
        "visual": "liquidity",
        "keywords": ["liquidity", "swing low", "sell stops", "lows", "irl"],
        "short_text": "Visible lows can attract sell stops and breakout sellers. A sweep below the low is not automatically bearish if price quickly reclaims the range.",
        "simple_explanation": "When everyone sees the same low, many orders can collect below it. Price can dip there and reverse.",
        "example": "A move below a range low that closes back inside the range can warn traders not to chase the breakdown.",
        "image_query": "liquidity below swing lows trading",
    },
    {
        "title": "Draw On Liquidity",
        "topic": "liquidity",
        "order": 42,
        "visual": "liquidity",
        "keywords": ["draw on liquidity", "dol", "target liquidity", "liquidity draw"],
        "short_text": "Draw on liquidity is the idea that price may be attracted toward a pool of orders. It helps traders think about where price is likely trying to reach.",
        "simple_explanation": "Instead of asking only where to enter, ask where the market may be trying to collect orders next.",
        "example": "If price is rising from a discount area, the next obvious swing high may become a liquidity objective rather than a random line.",
        "image_query": "draw on liquidity trading",
    },
    {
        "title": "A Sweep Needs Confirmation",
        "topic": "liquidity",
        "order": 43,
        "visual": "liquidity",
        "keywords": ["liquidity sweep", "sweep", "stop hunt", "reclaim", "raid"],
        "short_text": "A liquidity sweep becomes more meaningful when price rejects the swept area and reclaims structure. The sweep alone is only a warning sign.",
        "simple_explanation": "A sweep shows price took an obvious level. Confirmation comes from what price does after that.",
        "example": "If price breaks below a low, then quickly closes back above it and forms a higher low, traders may read that as stronger rejection.",
        "image_query": "liquidity sweep trading chart",
    },
    {
        "title": "Order Blocks Need Context",
        "topic": "liquidity",
        "order": 44,
        "visual": "liquidity",
        "keywords": ["order block", "ob", "engulfing", "mitigation", "breaker block"],
        "short_text": "An order block is more useful when it aligns with structure, liquidity, and a clear reaction. A rectangle alone is not enough evidence.",
        "simple_explanation": "Do not trade every marked block. Ask why that area matters in the current market story.",
        "example": "A bullish order block after a liquidity sweep and structure shift may be cleaner than a block in the middle of a noisy range.",
        "image_query": "order block trading chart",
    },
    {
        "title": "Candles Show Negotiation",
        "topic": "candlesticks",
        "order": 50,
        "visual": "candlestick",
        "keywords": ["candle", "candlestick", "open", "close", "wick"],
        "short_text": "A candle shows the negotiation between buyers and sellers during one period. The close tells you who held control at the end of that period.",
        "simple_explanation": "The wick shows where price traveled. The body and close show what price could keep.",
        "example": "A candle that pushes above resistance but closes below it can show buyers tried to break out but failed to hold control.",
        "image_query": "candlestick wick close trading",
    },
    {
        "title": "Wicks Show Rejection",
        "topic": "candlesticks",
        "order": 51,
        "visual": "candlestick",
        "keywords": ["wick", "rejection", "shadow", "pin", "doji"],
        "short_text": "Long wicks can show rejection, especially when they appear at important levels. They matter most when the close confirms the rejection.",
        "simple_explanation": "A wick means price visited an area but could not stay there. The close helps confirm whether the rejection was meaningful.",
        "example": "A long upper wick at resistance followed by a close below the level may show failed buying pressure.",
        "image_query": "candlestick rejection wick trading",
    },
    {
        "title": "Candle Range Tells A Story",
        "topic": "candlesticks",
        "order": 52,
        "visual": "candlestick",
        "keywords": ["candle range", "crt", "range theory", "candle high", "candle low"],
        "short_text": "The high and low of an important candle can become a short-term decision range. Breaks and closes around that range reveal pressure.",
        "simple_explanation": "Treat a meaningful candle like a mini battlefield. Its high and low show where buyers and sellers contested price.",
        "example": "If price sweeps a candle low and closes back inside the candle range, the move may show rejection rather than continuation.",
        "image_query": "candle range theory trading",
    },
    {
        "title": "Engulfing Needs Location",
        "topic": "candlesticks",
        "order": 53,
        "visual": "candlestick",
        "keywords": ["engulfing", "engulf", "reversal candle", "candle pattern"],
        "short_text": "An engulfing candle is stronger when it appears at a meaningful level or after a liquidity sweep. Without location, it can be noise.",
        "simple_explanation": "The pattern matters less than where it happens. A reversal candle in the middle of nowhere is weaker evidence.",
        "example": "A bullish engulfing candle after sweeping a prior low can be more useful than the same candle inside a choppy middle range.",
        "image_query": "engulfing candle trading setup",
    },
    {
        "title": "Breakouts Need Acceptance",
        "topic": "entries-exits",
        "order": 60,
        "visual": "breakout",
        "keywords": ["breakout", "break out", "close above", "close below", "acceptance"],
        "short_text": "A breakout is more reliable when price accepts beyond the level, not just when it briefly crosses it. The close and retest matter.",
        "simple_explanation": "Crossing a line is easy. Holding beyond the line is the real test.",
        "example": "If price breaks above resistance, closes above it, and later holds a retest, the breakout has better structure than a quick spike.",
        "image_query": "breakout retest trading chart",
    },
    {
        "title": "Fakeouts Trap Chasers",
        "topic": "entries-exits",
        "order": 61,
        "visual": "breakout",
        "keywords": ["fakeout", "false breakout", "trap", "failed breakout", "reversal"],
        "short_text": "A fakeout happens when price breaks a visible level but cannot hold beyond it. It often punishes traders who enter without confirmation.",
        "simple_explanation": "A fakeout is a failed breakout. The market looked strong, then quickly moved back into the old area.",
        "example": "If price breaks below support and closes back above it, short sellers who chased the break may be trapped.",
        "image_query": "false breakout fakeout trading",
    },
    {
        "title": "Confirmation Reduces Guessing",
        "topic": "entries-exits",
        "order": 62,
        "visual": "trend",
        "keywords": ["confirmation", "confirm", "valid", "setup", "entry"],
        "short_text": "Confirmation is evidence that price agrees with your idea. It can be a close, a retest, a structure shift, or rejection at a planned level.",
        "simple_explanation": "Confirmation does not guarantee success. It simply gives you a clearer reason than guessing.",
        "example": "Instead of buying the first touch of support, a trader may wait for a rejection candle and a higher low before planning risk.",
        "image_query": "trading confirmation entry setup",
    },
    {
        "title": "Retests Improve Timing",
        "topic": "entries-exits",
        "order": 63,
        "visual": "trend",
        "keywords": ["retest", "pullback", "return", "entry point", "mitigation"],
        "short_text": "A retest lets traders see whether a broken level still matters. It can improve timing because the market has already shown its first move.",
        "simple_explanation": "After price breaks a level, the retest asks: will this level now hold from the other side?",
        "example": "After resistance breaks, a pullback that respects the old resistance as support may offer a cleaner plan than chasing the first candle.",
        "image_query": "retest entry trading chart",
    },
    {
        "title": "Confluence Is Agreement",
        "topic": "entries-exits",
        "order": 64,
        "visual": "trend",
        "keywords": ["confluence", "combine", "align", "confirmation", "setup"],
        "short_text": "Confluence means multiple independent reasons point to the same area or idea. It should simplify a trade plan, not add clutter.",
        "simple_explanation": "Good confluence is agreement between useful signals. Too many indicators can create confusion instead of clarity.",
        "example": "A support zone, higher timeframe trend, and liquidity sweep can form cleaner confluence than five unrelated indicators.",
        "image_query": "trading confluence chart analysis",
    },
    {
        "title": "Entries Need Invalidation",
        "topic": "entries-exits",
        "order": 65,
        "visual": "risk",
        "keywords": ["entry", "exit", "invalidation", "stop loss", "risk"],
        "short_text": "A planned entry should include a clear invalidation point. If you cannot define where the idea is wrong, the setup is not ready.",
        "simple_explanation": "Before entering, know what would prove your idea incorrect. That point shapes the stop and position size.",
        "example": "If a long idea depends on a higher low holding, a break below that higher low may invalidate the setup.",
        "image_query": "trade invalidation stop loss",
    },
    {
        "title": "Stop Loss Is A Logic Point",
        "topic": "risk-management",
        "order": 70,
        "visual": "risk",
        "keywords": ["stop loss", "stop", "sl", "cut loss", "invalidation"],
        "short_text": "A stop loss should sit where the trade idea no longer makes sense, not where the loss merely feels comfortable.",
        "simple_explanation": "The stop is tied to the setup. It marks the point where your reason for entering is no longer valid.",
        "example": "For a long trade based on support holding, a stop may belong beyond the failed support area rather than randomly close to entry.",
        "image_query": "stop loss placement trading",
    },
    {
        "title": "Risk Comes Before Reward",
        "topic": "risk-management",
        "order": 71,
        "visual": "risk",
        "keywords": ["risk", "reward", "rr", "risk reward", "loss"],
        "short_text": "Before thinking about profit, define the amount you are willing to lose if the idea fails. Risk control keeps one trade from becoming too important.",
        "simple_explanation": "A good-looking setup can still fail. Decide the acceptable loss before entering.",
        "example": "If a trader risks 1% per idea, the position size must fit that risk even when the setup looks attractive.",
        "image_query": "risk reward trading plan",
    },
    {
        "title": "Position Size Controls Damage",
        "topic": "risk-management",
        "order": 72,
        "visual": "risk",
        "keywords": ["position size", "lot", "size", "risk per trade", "account"],
        "short_text": "Position size connects account risk to stop distance. A wider stop usually requires a smaller position if the risk amount stays fixed.",
        "simple_explanation": "You do not control the market, but you control how large the trade is relative to your plan.",
        "example": "If the planned risk is $50 and the stop is far from entry, the position must be reduced to keep the loss controlled.",
        "image_query": "position sizing trading calculator",
    },
    {
        "title": "Avoid Moving The Stop Emotionally",
        "topic": "risk-management",
        "order": 73,
        "visual": "risk",
        "keywords": ["stop", "emotion", "discipline", "risk", "fear"],
        "short_text": "Moving a stop because of fear usually changes the trade from a plan into a reaction. Adjust stops only when the market structure justifies it.",
        "simple_explanation": "If the stop was placed for a reason, do not move it just because the trade feels uncomfortable.",
        "example": "A trader may trail a stop after price creates a new higher low, but not simply because a candle moves against the position.",
        "image_query": "trading discipline stop loss",
    },
    {
        "title": "No Setup Needs Oversizing",
        "topic": "risk-management",
        "order": 74,
        "visual": "risk",
        "keywords": ["risk", "lot", "overtrade", "money management", "account"],
        "short_text": "Even a strong setup does not justify oversized risk. Consistency comes from repeating a process, not betting heavily on one idea.",
        "simple_explanation": "Confidence should not turn into oversized exposure. The next trade is never guaranteed.",
        "example": "A trader who normally risks 1% should be cautious about risking 5% just because several signals line up.",
        "image_query": "trading money management risk",
    },
    {
        "title": "Trading Psychology Is Process",
        "topic": "psychology",
        "order": 80,
        "visual": "psychology",
        "keywords": ["psychology", "discipline", "emotion", "fear", "greed"],
        "short_text": "Trading psychology is the ability to follow a defined process while emotions are active. A written plan reduces impulsive decisions.",
        "simple_explanation": "Fear and greed are normal. The goal is to avoid letting them rewrite your plan mid-trade.",
        "example": "After a losing trade, a written checklist can prevent revenge entries that were not part of the original plan.",
        "image_query": "trading psychology discipline",
    },
    {
        "title": "Patience Is A Trading Skill",
        "topic": "psychology",
        "order": 81,
        "visual": "psychology",
        "keywords": ["patience", "wait", "discipline", "setup", "plan"],
        "short_text": "Waiting for the planned area is part of the strategy. Entering early often creates worse risk and weaker confirmation.",
        "simple_explanation": "A trade is not better because it happens faster. It is better when it matches the plan.",
        "example": "If the plan requires a retest, entering before price returns to the level may turn a structured idea into a guess.",
        "image_query": "patient trader waiting setup",
    },
    {
        "title": "Losses Are Feedback",
        "topic": "psychology",
        "order": 82,
        "visual": "psychology",
        "keywords": ["loss", "journal", "review", "mistake", "discipline"],
        "short_text": "A losing trade is useful when it is reviewed honestly. The goal is to learn whether the loss came from the plan or from breaking the plan.",
        "simple_explanation": "Not every loss is a mistake. But every loss should teach you something about execution or market conditions.",
        "example": "A journal can separate a valid planned loss from an impulsive entry that should not have been taken.",
        "image_query": "trading journal review losses",
    },
    {
        "title": "Do Not Chase Missed Moves",
        "topic": "psychology",
        "order": 83,
        "visual": "psychology",
        "keywords": ["chase", "fomo", "emotion", "breakout", "entry"],
        "short_text": "Chasing a missed move usually means entering after risk has expanded. If the entry is gone, wait for a new setup.",
        "simple_explanation": "Missing a trade is not the same as losing money. Chasing can turn patience into unnecessary risk.",
        "example": "If price already moved far from the breakout level, a trader may wait for a retest instead of buying the top of the impulse.",
        "image_query": "fomo trading discipline",
    },
]


RU_LESSON_TEXT = {
    "Read Price In Context": {
        "hook": "Не смотри на сигнал отдельно — сначала прочитай контекст.",
        "short_text": "Одна свеча или один уровень имеют смысл только внутри общей картины рынка. Сначала определи структуру, а уже потом оценивай сетап.",
        "simple_explanation": "Не превращай один сигнал в всю историю. Сначала спроси себя: цена трендит, стоит в диапазоне или меняет направление?",
        "example": "Бычья свеча у поддержки выглядит сильнее, если общий рынок тоже формирует более высокие минимумы.",
    },
    "Start With Higher Timeframes": {
        "hook": "Большая картина часто важнее красивого входа.",
        "short_text": "Старшие таймфреймы помогают понять основное направление, а младшие — уточнить вход. Без плана разные таймфреймы легко начинают противоречить друг другу.",
        "simple_explanation": "Старший график — это карта. Младший график — это точка входа. Не позволяй младшему шуму отменять контекст старшего графика.",
        "example": "Трейдер может отметить дневную зону сопротивления, а затем на 15-минутном графике ждать признаки отскока или rejection.",
    },
    "Trend Is A Sequence": {
        "hook": "Тренд — это не одна сильная свеча, а последовательность.",
        "short_text": "Тренд строится из серии максимумов и минимумов, а не из одного импульса. Смотри, принимает ли цена всё более высокие или более низкие уровни.",
        "simple_explanation": "Восходящий тренд обычно делает higher highs и higher lows. Нисходящий — lower highs и lower lows.",
        "example": "Если цена обновила максимум и затем удержалась выше прошлого swing low, структура роста выглядит здоровее, чем простой резкий скачок.",
    },
    "Structure Shift Matters": {
        "hook": "Смена структуры — момент, где старый план может сломаться.",
        "short_text": "Смена структуры возникает, когда цена ломает ритм, который вёл движение. Это повод пересмотреть план, а не причина сразу входить вдогонку.",
        "simple_explanation": "Если рынок перестал делать привычные swing-точки, значит прежняя логика может больше не работать.",
        "example": "Если восходящий тренд пробивает последний важный higher low, трейдер может поставить long-идеи на паузу, пока структура не восстановится.",
    },
    "Ranges Need Patience": {
        "hook": "В диапазоне рынок часто наказывает нетерпение.",
        "short_text": "Внутри диапазона цена чаще вращается между границами, чем трендит чисто. Главный навык здесь — терпение и отказ от случайных входов в середине.",
        "simple_explanation": "Диапазон — это пауза рынка. Цена может ходить в обе стороны без ясного направления.",
        "example": "Если цена снова и снова отбивается от одной и той же верхней и нижней границы, разумнее дождаться чистого пробоя и удержания.",
    },
    "Support Is An Area": {
        "hook": "Поддержка — это зона решений, а не магическая линия.",
        "short_text": "Поддержку лучше рассматривать как область, где покупатели уже проявляли интерес. Цена может проколоть её перед тем, как показать настоящее решение.",
        "simple_explanation": "Думай о поддержке как о зоне, где покупатели могут защищать цену. Но ей всё равно нужно подтверждение поведением цены.",
        "example": "Если цена несколько раз отскакивала от зоны, трейдер может ждать rejection или возврата выше уровня, а не покупать первый касание.",
    },
    "Resistance Is Supply": {
        "hook": "Сопротивление важно только тогда, когда цена реагирует.",
        "short_text": "Сопротивление показывает область, где продавцы уже смогли замедлить или развернуть цену. Чистая реакция важнее простого касания уровня.",
        "simple_explanation": "Сопротивление — это зона возможного давления продавцов. Смотри на поведение цены, а не только на линию.",
        "example": "Если цена коснулась сопротивления и закрылась ниже без продолжения вверх, это может показать слабость покупателей.",
    },
    "Broken Levels Can Flip": {
        "hook": "Старый потолок часто становится новым полом.",
        "short_text": "Пробитая поддержка может стать сопротивлением, а пробитое сопротивление — поддержкой. Ретест показывает, принял ли рынок новую роль уровня.",
        "simple_explanation": "Когда цена проходит важную зону, трейдеры смотрят на следующий возврат: будет ли старый уровень работать с другой стороны?",
        "example": "После пробоя сопротивления откат, который удерживает этот уровень как поддержку, может подтвердить принятие цены выше.",
    },
    "Key Levels Need Reactions": {
        "hook": "Сам уровень — это подготовка. Решение даёт реакция.",
        "short_text": "Ключевой уровень полезен только тогда, когда цена показывает реакцию рядом с ним. Разметка уровня — это подготовка, чтение реакции — момент решения.",
        "simple_explanation": "Линия на графике сама по себе не является сделкой. Важно, что делает цена рядом с этой линией.",
        "example": "Трейдер может отметить недельный уровень и ждать wick rejection, failed breakout или сильное закрытие перед планом входа.",
    },
    "Liquidity Sits Near Obvious Highs": {
        "hook": "Очевидные максимумы часто притягивают ликвидность.",
        "short_text": "Ликвидность часто собирается выше заметных максимумов, потому что там стоят стопы и breakout-ордера. Цена может сходить туда перед настоящим решением.",
        "simple_explanation": "Когда все видят один и тот же максимум, вокруг него накапливаются ордера. Рынок часто посещает такие зоны.",
        "example": "Если цена вышла выше прошлого максимума и быстро вернулась ниже, движение могло собрать ликвидность, а не начать новый тренд.",
    },
    "Liquidity Sits Below Lows": {
        "hook": "Под очевидными минимумами часто лежат стопы.",
        "short_text": "Заметные минимумы могут притягивать sell stops и продавцов на пробой. Прокол ниже минимума не всегда означает настоящий breakdown.",
        "simple_explanation": "Если все видят один минимум, под ним часто собираются ордера. Цена может нырнуть туда и вернуться обратно.",
        "example": "Если цена пробила нижнюю границу диапазона и закрылась обратно внутри, это может быть предупреждением не шортить вдогонку.",
    },
    "Draw On Liquidity": {
        "hook": "Цена часто движется туда, где ждут ордера.",
        "short_text": "Draw on liquidity — это идея, что цена может тянуться к зоне скопления ордеров. Это помогает понять, куда рынок, возможно, пытается дойти.",
        "simple_explanation": "Спрашивай не только «где войти», но и «где рынок может собрать ордера дальше». Это меняет взгляд на график.",
        "example": "Если цена растёт из discount-зоны, следующий очевидный swing high может стать целью ликвидности, а не случайной линией.",
    },
    "A Sweep Needs Confirmation": {
        "hook": "Снятие ликвидности без подтверждения — только предупреждение.",
        "short_text": "Liquidity sweep становится значимее, когда цена отвергает пробитую область и возвращает структуру. Сам sweep — это ещё не готовый сигнал.",
        "simple_explanation": "Sweep показывает, что цена забрала очевидный уровень. Подтверждение приходит после: смогла ли цена вернуться и удержаться?",
        "example": "Если цена пробила минимум, быстро закрылась выше и сформировала higher low, это может показать сильное отвержение.",
    },
    "Order Blocks Need Context": {
        "hook": "Прямоугольник на графике не является сетапом сам по себе.",
        "short_text": "Order block полезнее, когда он совпадает со структурой, ликвидностью и понятной реакцией. Одна отмеченная зона не даёт достаточно доказательств.",
        "simple_explanation": "Не торгуй каждый блок. Сначала спроси, почему именно эта зона важна в текущей истории рынка.",
        "example": "Бычий order block после sweep и смены структуры может быть чище, чем блок посреди шумного диапазона.",
    },
    "Candles Show Negotiation": {
        "hook": "Свеча показывает борьбу, а закрытие — кто удержал контроль.",
        "short_text": "Свеча показывает переговоры между покупателями и продавцами за один период. Закрытие помогает понять, кто удержал контроль в конце.",
        "simple_explanation": "Тень показывает, куда цена ходила. Тело и закрытие показывают, что цена смогла удержать.",
        "example": "Если свеча вышла выше сопротивления, но закрылась ниже, покупатели пытались пробить уровень, но не удержали контроль.",
    },
    "Wicks Show Rejection": {
        "hook": "Длинная тень важна только там, где есть контекст.",
        "short_text": "Длинные тени могут показывать rejection, особенно у важных уровней. Но сильнее всего они работают, когда закрытие подтверждает отвержение.",
        "simple_explanation": "Тень означает, что цена посетила область, но не смогла там остаться. Закрытие показывает, было ли отвержение значимым.",
        "example": "Длинная верхняя тень у сопротивления и закрытие ниже уровня могут показать неудачную попытку покупателей.",
    },
    "Candle Range Tells A Story": {
        "hook": "Диапазон важной свечи может стать мини-картой рынка.",
        "short_text": "High и low важной свечи могут стать краткосрочным диапазоном решений. Пробои и закрытия вокруг него показывают давление сторон.",
        "simple_explanation": "Смотри на важную свечу как на маленькое поле боя. Её максимум и минимум показывают, где спорили покупатели и продавцы.",
        "example": "Если цена сняла low свечи и закрылась обратно внутри диапазона, это может быть rejection, а не продолжение движения.",
    },
    "Engulfing Needs Location": {
        "hook": "Паттерн без места на графике часто просто шум.",
        "short_text": "Engulfing-свеча сильнее, когда появляется у важного уровня или после снятия ликвидности. Без правильного места она может быть обычным шумом.",
        "simple_explanation": "Важен не только паттерн, но и место, где он появился. Reversal candle в середине хаоса слабее.",
        "example": "Бычий engulfing после sweep предыдущего минимума может быть полезнее, чем такой же паттерн в середине диапазона.",
    },
    "Breakouts Need Acceptance": {
        "hook": "Пробой — это не касание линии. Это принятие цены.",
        "short_text": "Breakout надёжнее, когда цена принимает область за уровнем, а не просто на секунду пересекает его. Закрытие и ретест имеют значение.",
        "simple_explanation": "Пересечь линию легко. Удержаться за ней — настоящий тест.",
        "example": "Если цена пробила сопротивление, закрылась выше и затем удержала ретест, пробой выглядит структурно сильнее, чем быстрый spike.",
    },
    "Fakeouts Trap Chasers": {
        "hook": "Этот момент часто отделяет пробой от ловушки.",
        "short_text": "Fakeout происходит, когда цена пробивает заметный уровень, но не может удержаться за ним. Он часто ловит тех, кто входит без подтверждения.",
        "simple_explanation": "Fakeout — это неудачный пробой. Рынок выглядел сильным, но быстро вернулся в старую область.",
        "example": "Если цена пробила поддержку и закрылась обратно выше неё, продавцы, вошедшие вдогонку, могут оказаться в ловушке.",
    },
    "Confirmation Reduces Guessing": {
        "hook": "Подтверждение не гарантирует результат, но убирает гадание.",
        "short_text": "Confirmation — это доказательство, что цена согласуется с твоей идеей. Это может быть закрытие, ретест, смена структуры или rejection у уровня.",
        "simple_explanation": "Подтверждение не делает сделку безопасной. Оно просто даёт более ясную причину, чем догадка.",
        "example": "Вместо покупки первого касания поддержки трейдер может дождаться rejection-свечи и higher low перед планированием риска.",
    },
    "Retests Improve Timing": {
        "hook": "Ретест показывает, действительно ли уровень изменил роль.",
        "short_text": "Ретест помогает увидеть, сохраняет ли пробитый уровень значение. Он улучшает тайминг, потому что рынок уже показал первое движение.",
        "simple_explanation": "После пробоя ретест задаёт вопрос: будет ли этот уровень держать цену с другой стороны?",
        "example": "После пробоя сопротивления откат, который уважает старое сопротивление как поддержку, может дать более чистый план, чем вход вдогонку.",
    },
    "Confluence Is Agreement": {
        "hook": "Confluence должен упрощать план, а не захламлять график.",
        "short_text": "Confluence означает, что несколько независимых причин указывают на одну идею или область. Хороший confluence делает план яснее.",
        "simple_explanation": "Это согласие полезных сигналов. Слишком много индикаторов часто создаёт не уверенность, а шум.",
        "example": "Зона поддержки, тренд старшего таймфрейма и liquidity sweep могут быть чище, чем пять несвязанных индикаторов.",
    },
    "Entries Need Invalidation": {
        "hook": "Если ты не знаешь, где идея ошибочна, вход не готов.",
        "short_text": "Планируемый вход должен иметь точку invalidation. Если нельзя определить, где идея становится неверной, сетап ещё не готов.",
        "simple_explanation": "Перед входом нужно знать, что докажет ошибку идеи. Эта точка формирует стоп и размер позиции.",
        "example": "Если long-идея зависит от удержания higher low, пробой ниже этого higher low может отменить сетап.",
    },
    "Stop Loss Is A Logic Point": {
        "hook": "Стоп должен стоять там, где ломается логика сделки.",
        "short_text": "Stop loss должен находиться там, где торговая идея больше не имеет смысла, а не там, где убыток просто кажется комфортным.",
        "simple_explanation": "Стоп связан с сетапом. Он отмечает точку, где причина входа перестаёт быть valid.",
        "example": "Если long строится на удержании поддержки, стоп может логично находиться за зоной провала поддержки, а не случайно близко к входу.",
    },
    "Risk Comes Before Reward": {
        "hook": "Сначала риск. Потенциальная прибыль — только потом.",
        "short_text": "Перед мыслью о прибыли нужно определить сумму, которую ты готов потерять, если идея не сработает. Контроль риска не даёт одной сделке стать слишком важной.",
        "simple_explanation": "Даже красивый сетап может не сработать. Реши допустимый убыток до входа.",
        "example": "Если трейдер рискует 1% на идею, размер позиции должен соответствовать этому риску даже при привлекательном сетапе.",
    },
    "Position Size Controls Damage": {
        "hook": "Размер позиции решает, насколько сильно ошибка ударит по счёту.",
        "short_text": "Position size связывает риск по счёту с расстоянием до стопа. Чем шире стоп, тем меньше обычно должна быть позиция при фиксированном риске.",
        "simple_explanation": "Ты не контролируешь рынок, но контролируешь размер сделки относительно своего плана.",
        "example": "Если плановый риск — 50 долларов, а стоп далеко от входа, позицию нужно уменьшить, чтобы сохранить контролируемый убыток.",
    },
    "Avoid Moving The Stop Emotionally": {
        "hook": "Эмоциональный перенос стопа превращает план в реакцию.",
        "short_text": "Перенос стопа из-за страха часто превращает сделку из плана в импульс. Меняй стоп только тогда, когда это оправдано структурой рынка.",
        "simple_explanation": "Если стоп был поставлен по причине, не двигай его только потому, что сделка стала неприятной эмоционально.",
        "example": "Трейдер может подтянуть стоп после нового higher low, но не просто потому, что одна свеча пошла против позиции.",
    },
    "No Setup Needs Oversizing": {
        "hook": "Даже сильный сетап не требует чрезмерного риска.",
        "short_text": "Даже хороший сетап не оправдывает слишком большой риск. Стабильность строится на повторении процесса, а не на ставке на одну идею.",
        "simple_explanation": "Уверенность не должна превращаться в завышенный объём. Следующая сделка никогда не известна заранее.",
        "example": "Если трейдер обычно рискует 1%, стоит осторожно относиться к идее рискнуть 5% только потому, что сигналы совпали.",
    },
    "Trading Psychology Is Process": {
        "hook": "Психология — это способность следовать процессу, когда эмоции уже включились.",
        "short_text": "Trading psychology — это умение соблюдать процесс, когда страх, жадность или спешка уже влияют на решения. Письменный план снижает импульсивность.",
        "simple_explanation": "Страх и жадность нормальны. Цель — не позволить им переписать план прямо во время сделки.",
        "example": "После убыточной сделки чеклист может остановить revenge entry, которого не было в исходном плане.",
    },
    "Patience Is A Trading Skill": {
        "hook": "Ожидание сетапа — это часть стратегии, а не бездействие.",
        "short_text": "Ожидание нужной зоны — часть торговой системы. Ранний вход часто ухудшает риск и даёт слабее подтверждение.",
        "simple_explanation": "Сделка не становится лучше только потому, что случилась быстрее. Она лучше, когда совпадает с планом.",
        "example": "Если план требует ретеста, вход до возврата цены к уровню может превратить структурную идею в догадку.",
    },
    "Losses Are Feedback": {
        "hook": "Убыток полезен, если он разобран честно.",
        "short_text": "Убыточная сделка становится полезной, когда её честно анализируют. Важно понять: убыток был частью плана или результатом нарушения плана.",
        "simple_explanation": "Не каждый убыток — ошибка. Но каждый убыток должен чему-то учить про исполнение или рыночные условия.",
        "example": "Журнал помогает отделить нормальный плановый убыток от импульсивного входа, которого не должно было быть.",
    },
    "Do Not Chase Missed Moves": {
        "hook": "Пропущенная сделка — не убыток. Погоня за ней может им стать.",
        "short_text": "Погоня за пропущенным движением часто означает вход после расширения риска. Если вход ушёл, лучше ждать новый сетап.",
        "simple_explanation": "Пропустить движение — не то же самое, что потерять деньги. FOMO часто превращает терпение в лишний риск.",
        "example": "Если цена уже далеко ушла от уровня пробоя, трейдер может ждать ретест вместо покупки вершины импульса.",
    },
}


def main() -> int:
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(BOOKS_DIR.glob("*.pdf"))
    if not pdfs:
        write_json(DEEP_OUTPUT, [])
        write_json(ACTIVE_OUTPUT, [])
        safe_print(f"No PDFs found in {relative(BOOKS_DIR)}.")
        safe_print("Add licensed PDFs locally, then run: python tools/deep_pdf_to_reels.py")
        return 0

    try:
        import fitz  # type: ignore
    except ImportError:
        safe_print("Install dependencies with: pip install -r requirements.txt")
        return 1

    corpus_parts = []
    processed = 0
    for pdf in pdfs:
        try:
            pages = extract_pages(fitz, pdf)
        except Exception as error:
            safe_print(f"Skipping {relative(pdf)}: {error}")
            continue
        cleaned = clean_text(remove_repeated_lines(pages))
        if cleaned:
            corpus_parts.append(cleaned)
            processed += 1

    corpus = "\n".join(corpus_parts).lower()
    candidates = build_candidates(corpus)
    final_lessons = dedupe_and_rank(candidates)[:MAX_FINAL_LESSONS]
    final_lessons = assign_ids(final_lessons)

    if len(final_lessons) < MIN_TARGET_LESSONS:
        safe_print(f"Warning: only {len(final_lessons)} high-confidence lessons were generated.")

    write_json(DEEP_OUTPUT, final_lessons)
    write_json(ACTIVE_OUTPUT, final_lessons)
    safe_print(f"PDF files found: {len(pdfs)}")
    safe_print(f"PDFs with extractable text: {processed}")
    safe_print(f"Raw candidate lessons found: {len(candidates)}")
    safe_print(f"Final lessons created: {len(final_lessons)}")
    safe_print(f"Wrote {relative(DEEP_OUTPUT)}")
    safe_print(f"Updated {relative(ACTIVE_OUTPUT)}")
    return 0


def extract_pages(fitz, pdf_path: Path) -> list[str]:
    pages = []
    with fitz.open(pdf_path) as document:
        for page in document:
            pages.append(page.get_text("text"))
    return pages


def remove_repeated_lines(pages: list[str]) -> str:
    line_counts: Counter[str] = Counter()
    page_lines = []
    for page in pages:
        lines = [normalize_line(line) for line in page.splitlines()]
        lines = [line for line in lines if line]
        page_lines.append(lines)
        line_counts.update(set(lines))

    repeated = {
        line
        for line, count in line_counts.items()
        if count >= 3 and (count / max(len(pages), 1) >= 0.35 or looks_like_page_marker(line))
    }

    cleaned_pages = []
    for lines in page_lines:
        kept = [line for line in lines if line not in repeated and not looks_like_page_marker(line)]
        cleaned_pages.append(" ".join(kept))
    return "\n".join(cleaned_pages)


def normalize_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", line).strip()


def looks_like_page_marker(line: str) -> bool:
    return bool(re.fullmatch(r"\d{1,4}|page\s+\d+(\s+of\s+\d+)?", line, re.I))


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"([a-z])([A-Z])", r"\1. \2", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^\w\s.,;:!?$%()'\"/+-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_candidates(corpus: str) -> list[dict[str, object]]:
    candidates = []
    for concept in CONCEPT_BANK:
        score = concept_score(corpus, concept["keywords"])
        if score <= 0:
            continue
        confidence = "high" if score >= 3 else "medium"
        candidates.append({
            "title": concept["title"],
            "topic": concept["topic"],
            "level": level_for_order(int(concept["order"])),
            "hook": localized_field(concept, "hook"),
            "short_text": localized_field(concept, "short_text"),
            "simple_explanation": localized_field(concept, "simple_explanation"),
            "example": localized_field(concept, "example"),
            "image_query": concept["image_query"],
            "media_query": media_query_for(concept),
            "visual": {"type": "market", "value": concept["visual"]},
            "source": "book-derived",
            "confidence": confidence,
            "_score": score,
            "_order": concept["order"],
        })
    return candidates


def localized_field(concept: dict[str, object], field: str) -> str:
    title = str(concept["title"])
    localized = RU_LESSON_TEXT.get(title, {})
    if field in localized:
        return localized[field]
    if field == "hook":
        return hook_for_topic(str(concept["topic"]))
    return str(concept.get(field, ""))


def hook_for_topic(topic: str) -> str:
    if "liquidity" in topic:
        return "Ликвидность часто прячется там, где все смотрят."
    if "risk" in topic:
        return "Сначала защити счёт, потом думай о результате."
    if "psychology" in topic:
        return "Главная ошибка часто происходит не на графике, а в решении."
    if "candle" in topic:
        return "Свеча важна только вместе с местом и контекстом."
    if "entries" in topic:
        return "Хороший вход начинается с понятной причины отмены идеи."
    return "Контекст превращает график из шума в структуру."


def level_for_order(order: int) -> str:
    if order < 60:
        return "beginner"
    if order < 75:
        return "intermediate"
    return "beginner"


def media_query_for(concept: dict[str, object]) -> str:
    topic = str(concept["topic"]).replace("-", " ")
    visual = str(concept["visual"])
    if visual == "liquidity":
        return "dark trading chart liquidity zones finance screen"
    if visual == "risk":
        return "risk management trading dashboard dark finance"
    if visual == "candlestick":
        return "candlestick chart trading screen dark"
    if visual == "psychology":
        return "focused trader dark trading desk"
    if visual == "breakout":
        return "stock market chart breakout dark trading screen"
    return f"{topic} trading chart dark finance dashboard"


def concept_score(corpus: str, keywords: list[str]) -> int:
    score = 0
    for keyword in keywords:
        pattern = re.escape(keyword.lower())
        if re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", corpus):
            score += 1
    return score


def dedupe_and_rank(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(candidates, key=lambda item: (item["_order"], -item["_score"], item["title"]))
    kept: list[dict[str, object]] = []
    for candidate in ranked:
        if violates_quality_rules(candidate):
            continue
        if any(is_near_duplicate(candidate, existing) for existing in kept):
            continue
        cleaned = {key: value for key, value in candidate.items() if not key.startswith("_")}
        kept.append(cleaned)
    return kept


def violates_quality_rules(lesson: dict[str, object]) -> bool:
    visible = " ".join(str(lesson.get(key, "")) for key in ["title", "short_text", "simple_explanation", "example"])
    if len(str(lesson.get("short_text", ""))) > 320:
        return True
    if re.search(r"guaranteed|always profitable|100%|api[_ -]?key|sk-|AIza|hf_|tgp_", visible, re.I):
        return True
    if re.search(r"\.pdf|content/books|page\s+\d+", visible, re.I):
        return True
    return False


def is_near_duplicate(a: dict[str, object], b: dict[str, object]) -> bool:
    if a["title"] != b["title"]:
        return False
    left = f"{a['title']} {a['topic']} {a['short_text']}".lower()
    right = f"{b['title']} {b['topic']} {b['short_text']}".lower()
    return SequenceMatcher(None, left, right).ratio() > 0.9


def assign_ids(lessons: list[dict[str, object]]) -> list[dict[str, object]]:
    assigned = []
    for index, lesson in enumerate(lessons, start=1):
        assigned.append({"id": f"book-reel-{index:03d}", **lesson})
    return assigned


def write_json(path: Path, data: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_print(message: object) -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="backslashreplace").decode(encoding))


if __name__ == "__main__":
    sys.exit(main())
