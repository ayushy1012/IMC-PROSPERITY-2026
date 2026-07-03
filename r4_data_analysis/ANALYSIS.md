# Round 4 Data Analysis

## Coherence check: PASSED

The round 4 historical data is **byte-identical** to the round 3 data for the overlapping days, confirming this is one continuous dataset, not a regenerated process:

| File | Identical to | Status |
|---|---|---|
| `prices_round_4_day_1.csv` | `prices_round_3_day_1.csv` | ✓ md5 match |
| `prices_round_4_day_2.csv` | `prices_round_3_day_2.csv` | ✓ md5 match |
| `prices_round_4_day_3.csv` | (round 3 live day, where the bot lost 85k) | ✓ exact match — verified by joining on (day, timestamp, product) and getting max abs diff = 0 |

The round 4 historical window has shifted forward by 1 day:
- Round 3 day 0 (TTE=8d) — DROPPED (now too old to matter)
- Round 4 day 1 = Round 3 day 1 (TTE=7d)
- Round 4 day 2 = Round 3 day 2 (TTE=6d)
- Round 4 day 3 = the live round 3 day (TTE=5d) — now historical

For round 4's live day, TTE will go 4d → 3d.

## Statistical coherence: identical process

Per-day stats over all 4 days:

| Day | Open | Close | Mean | σ_step | Lag-1 autocorr | Net move |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 5250 | 5244 | 5246.5 | 0.00021 | −0.151 | −6 |
| 1 | 5245 | 5266 | 5248.4 | 0.00022 | −0.169 | +20 |
| 2 | 5268 | 5296 | 5255.4 | 0.00022 | −0.155 | +28 |
| 3 | 5296 | 5232 | 5239.2 | 0.00022 | −0.156 | **−64** |

Per-step volatility: identical to 5 decimal places. Mean reversion strength: identical. Same data-generating process throughout. The round 3 live day was perfectly normal in every statistical sense — only its **starting level** was extreme.

## Updated reference statistics for round 4

| Quantity | Old (3-day) | New (4-day) |
|---|---:|---:|
| V mean | 5247.0 | **5247.4** |
| V std | 14.4 | **17.1** (wider — day 3 hit a new low) |
| V range | [5198, 5300] | [5191.5, 5300] |
| H mean | 9990.8 | **9993.7** |
| H std | 31.9 | **32.6** |

Use `μ_V = 5247.4, σ_V = 17.1` as your reference for any z-score-based logic in round 4.

## Cycle structure now has 5 fully-identified pivots

10 pivots identified in the smoothed series, forming 9 half-cycles:

```
Day 0.35: PEAK   V=5258.8
Day 0.56: TROUGH V=5238.1   ← 0.21d, 20.7 V drop
Day 0.83: PEAK   V=5257.0   ← 0.27d, 18.9 V rally
Day 1.00: TROUGH V=5243.6   ← 0.17d, 13.4 V drop  (straddles day boundary!)
Day 1.21: PEAK   V=5255.3   ← 0.21d, 11.7 V rally
Day 1.61: TROUGH V=5232.9   ← 0.40d, 22.4 V drop
Day 2.25: PEAK   V=5269.9   ← 0.64d, 37.0 V rally
Day 2.50: TROUGH V=5236.5   ← 0.25d, 33.4 V drop
Day 2.98: PEAK   V=5272.4   ← 0.48d, 35.9 V rally  (this is the trap that killed the bot)
Day 3.52: TROUGH V=5213.9   ← 0.54d, 58.5 V drop
```

Average half-cycle: **0.35 days** (range 0.17 to 0.64), amplitude **28 V** (std ~14). Rallies (T→P) are slightly slower than crashes (P→T), and slightly smaller in amplitude. **Cycles routinely straddle day boundaries** (day 1.00 trough is the clearest example) — this is exactly why a calendar-based FSM fails.

## Voucher time-value chain across days

| K \ Day | 0 | 1 | 2 | 3 | 4 (extrapolated) |
|---|---:|---:|---:|---:|---:|
| 5000 | 6.75 | 4.87 | 3.15 | 2.46 | **2.17** |
| 5100 | 21.6 | 16.6 | 11.9 | 11.1 | **9.81** |
| 5200 | 51.0 | 46.7 | 38.7 | 38.6 | **34.04** |
| 5300 | 48.9 | 46.9 | 44.5 | 32.1 | **28.34** |
| 5400 | 18.5 | 15.7 | 13.7 | 8.5 | **7.50** |
| 5500 | 8.1 | 6.6 | 5.3 | 2.3 | **1.99** |

Day-3 TV decay is faster for OTM strikes (5400, 5500) because S ended below where the strikes sat — those vouchers became deeper OTM. The extrapolation uses `TV[d+1] = TV[d] × √(T_new/T_old) = TV[d] × √(3.5/4.5) = 0.88×`. For round 4 live, expect K=5200 voucher to have TV around 34, K=5300 around 28.

## Microstructure: completely stable

Spreads, book depth, and top-of-book volumes are essentially unchanged across all 4 days. The slight tightening on day 3 for ATM vouchers is purely a level effect (S sat near them) and not a structural shift. **Same market-making opportunities apply for round 4 as did for round 3** — HYDROGEL_PACK and VEV_4000 remain the two tightest setups for clean two-sided MM.

## What's the round 4 LIVE day setup?

Day 3 closed at V = 5232. Round 4 live will likely open near there (no overnight gap in this market based on prior days' open-to-prior-close gaps of ≤ 2).

| Quantity | Value |
|---|---|
| Likely day 4 open | ~5232 |
| 4-day mean | 5247.4 |
| 4-day σ | 17.1 |
| **Open z-score** | **−0.90** |
| Recommended sizing (linear contrarian) | +0.36 (small long) |
| Recent context | Just rolled over from a small smoothed peak at day 3.94 (V=5257) — recent rally is mature |

**Translation: mild long bias, position small, no high-conviction trade at the open.** This is a **patient day**, not a max-bet day. Day 3 was the +2.85σ trap that called for max short; day 4 is a +0.4 fraction "lean long but stay nimble" setup.

## Recommended approach for round 4

1. **Anchor everything to (μ=5247.4, σ=17.1)** — these are your reference points
2. **Open with target ≈ −z_open / 2.5 × position_limit**: ~+0.36 × limit per product. Don't go max-long.
3. **Trade dynamically through the day**: as V moves, recompute z and adjust target. When |z| > 1.5 either way, take the contrarian trade with conviction.
4. **Don't reset state at midnight**: track running peak/trough across the entire 4-day reference window. Cycles overlap day boundaries.
5. **Resume the HYDROGEL_PACK MM** — it was never in any regime's target on round 3 and that left clean edge on the table.
6. **Use the extrapolated TV table** for option pricing — `TV[K, day 4] ≈ TV[K, day 3] × 0.88`.
7. **Stop loss**: no matter what the strategy says, if PnL drawdown exceeds 30k, close all positions and stop.

## Plot index

| File | What it shows |
|---|---|
| `R4_01_master.png` | 4-day continuous V with cycle pivots, ±1.5σ bands, where day 4 starts |
| `R4_02_tv_extrapolation.png` | TV curves across 4 days + the extrapolated day-4 curve |
| `R4_03_dashboard.png` | 6-panel summary: OHLC, net moves, σ, autocorr, open z-scores, recommended position |
| `R4_04_immediate_context.png` | Zoomed last 1.5 days showing cycle structure entering round 4 |
| `R4_05_spreads.png` | Per-product spread comparison across the 4 days (microstructure stable) |
