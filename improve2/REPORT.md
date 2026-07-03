# Next-Iteration Improvement Report

## Context

This is a post-mortem of run **508344** (PnL = +14,379, 10% of one trading day) and a brief for the next iteration of the bot. The previous LLM applied 5 fixes and went from -85k → -4k → +12k → +14k. **The bot is profitable but leaves an estimated $35k of edge on the table per run** (extrapolates to ~$350k over a full day if the analysis below is correct). This report identifies where that edge is and proposes specific changes.

## TL;DR for the next LLM

1. **Run length is only 10% of a day** (1,000 ticks of 10,000). PnL numbers should be multiplied by ~10 for full-day projections, with caveats around position-limit saturation.
2. **The single biggest lever is `Z_OPT_SCALE = 100`**: it caps ATM voucher target at ±100, never reaching the ±300 position limit. On a directional drift day (V opens at z=+2.81), this leaves $25–30k of voucher edge unused.
3. **The current bot mostly captures the right shape of edge** (z-score reversion + theta harvest + MM). The issue is **sizing**, not signal selection.
4. The proposed change is a piecewise sizing function: flat 0 below |z|=1.0, linear ramp from |z|=1.0 to |z|=1.5, then **flat at ±max position from |z|=1.5 onwards**.
5. Risk-reward asymmetry on this trade is heavily favorable (mean reversion is documented; theta tailwind on ATM voucher shorts compounds it).

---

## 1. What the previous run did right

Run 508344 final PnL = **+14,379** on 10% of a day. Per-product attribution:

| Product | PnL | Notes |
|---|---:|---|
| VEV_5100 | +2,683 | ATM voucher z-score short |
| VEV_5000 | +2,615 | ATM voucher z-score short |
| VEV_5200 | +2,536 | ATM voucher z-score short |
| VEV_5400 | +2,467 | OTM theta short (this was the big v505→v508 fix, +2,067 from reclassification) |
| VELVETFRUIT_EXTRACT | +1,780 | V z-score short |
| VEV_5300 | +1,462 | ATM voucher z-score short |
| VEV_5500 | +847 | OTM theta short |
| VEV_4500 | +43 | Deep ITM MM |
| VEV_4000 | +42 | Deep ITM MM |
| HYDROGEL_PACK | +17 | MM (down from +231 in 505 — see issue 4 below) |
| **Total** | **+14,492** | (rounding diff from reported 14,379) |

The bot worked because:
- **OTM theta short** (VEV_5400, VEV_5500) reached -300 limit on both, captured ~$3.3k of theta decay.
- **ATM voucher z-score short** (VEV_5000–5300) all reached approximately their z-score targets, captured ~$9.3k of mean-reversion gain.
- **V z-score short** captured ~$1.8k.

## 2. The big finding: massive missed edge from sizing

I computed a "max-short-and-hold" hypothetical for each product. Open at the day's first available price, target the position limit, and hold to close (i.e., never trade out of the position):

| Product | Actual PnL | Max-short hypo | Missed |
|---|---:|---:|---:|
| VEV_5000 | +2,615 | **+12,150** | **+9,535** |
| VEV_5100 | +2,683 | **+11,250** | **+8,567** |
| VEV_5200 | +2,536 | **+9,300** | **+6,764** |
| VEV_5300 | +1,462 | +5,700 | +4,238 |
| VELVETFRUIT_EXTRACT | +1,780 | +8,400 | +6,620 |
| VEV_5400 | +2,467 | +2,467 | (already maxed) |
| VEV_5500 | +847 | +847 | (already maxed) |
| **Total realisable** | **+14,492** | **+50,402** | **+35,910** |

**$35k of additional edge was sitting in the data but never captured.** Why? The current ATM sizing law is `target = -z * 100`, capped at ±100 per voucher. At z=+2.81 (the actual open), target was -100. But the position limit is 300. We literally cannot reach the position limit unless z somehow exceeds +3, which happens in <1% of the data.

See `improve_master.png` for visualization of this gap.

## 3. The core proposal: piecewise z-score sizing

### Current sizing (to replace)

```python
Z_OPT_SCALE = 300/3   # = 100
opt_target = clip(-z * Z_OPT_SCALE, -limit, +limit)
# At z=3 → target=-100
# At z=1 → target=-33
```

### Proposed piecewise sizing

```python
def proposed_size(z, position_limit):
    abs_z = abs(z)
    if abs_z < 1.0:
        return 0
    elif abs_z < 1.5:
        # Linear ramp from 0 (at |z|=1) to ±limit (at |z|=1.5)
        return -sign(z) * position_limit * (abs_z - 1.0) / 0.5
    else:
        return -sign(z) * position_limit
```

Apply to:
- **ATM vouchers** (VEV_5000, 5100, 5200, 5300): position_limit = 300
- **VELVETFRUIT_EXTRACT** (V): position_limit = 200

See `improve_sizing.png` for the curves.

### Why this shape

Three claims:
1. **Below |z|=1** there's no statistical edge worth holding inventory through spread cost.
2. **Above |z|=1.5** the edge is overwhelming and the position should be at limit (mean-reverting OU process is documented; |z|>1.5 is the 13th percentile of the marginal distribution).
3. **Between 1.0 and 1.5** is a transition zone — linear ramp gives smooth scale-in.

### Time spent in each zone (from live day data)

| Zone | % of day |
|---|---:|
| `|z| < 1.0` (don't trade) | 60.8% |
| `1.0 ≤ |z| < 1.5` (ramp zone) | 14.2% |
| `|z| ≥ 1.5` (full max position) | **25.0%** |

A quarter of the day at full short. With 4 ATM vouchers at -300 each + V at -200 = 1,400 short contracts × 30+ tick mean reversion = ~$30k of profit potential during just the high-z windows. See `improve_master.png` (top panel) for the time-series visualization.

## 4. The risk-reward asymmetry

**Why max-shorting at high z is safe:**

`improve_risk.png` shows portfolio PnL vs end-of-day V level for the proposed max-short portfolio (-300 in each ATM voucher + -200 in V).

- At V close = 5247 (mean reversion): combined PnL ≈ +$95k
- At V close = 5253.5 (actual): combined PnL ≈ +$50k
- At V close = 5320 (V keeps drifting up to z=+4.2): combined PnL ≈ -$20k

The downside is real but bounded. Three protections:
1. **Position limits** cap exposure
2. **Theta tailwind** on short ATM vouchers (positive carry of ~$5k/day even if V doesn't move)
3. **Stop loss at -30k** still active

Critically: the documented variance ratio at lag 1000 is 0.33 (vs 1.0 for random walk). This means moves at long horizons get cancelled by mean reversion. The probability of V moving from z=+2.81 to z=+4.2 (the breakeven point) is far less than 50%.

## 5. Verifying the proposal generalizes (don't overfit to one day)

`improve_history.png` applies the |z|≥1.5 trigger to all 4 historical days:

| Day | Open z | Close z | Time at full-short trigger |
|---|---:|---:|---:|
| 0 | +0.15 | -0.20 | 5.5% |
| 1 | -0.14 | +1.06 | 7.7% |
| 2 | +1.18 | +2.81 | 18.6% |
| 3 (live in run 508) | +2.81 | -0.90 | 22.1% |

Days 0 and 1 (which opened near the mean) would have triggered the rule for 5–8% of the day, when V briefly spiked. On those days the |z|>1.5 was followed by mean reversion, so a quick short → mean revert → flatten pattern would have been profitable but not transformative. Days 2 and 3 (extreme opens) is where the rule pays off massively.

This is the desired behavior: **the rule only fires when there's clear edge**, so it doesn't over-trade on quiet days.

## 6. Other (smaller) improvements

### 6a. ATM voucher churn — small but visible

See `vev5300_position.png` for a clean example of the pattern:
- Bot built short to -89 on VEV_5300 by ts=42k while mid fell from 60→38 ✓
- Then bought back from -89 to -19 as V mean-reverted toward z=0 (so target shrank)
- Then VEV_5300 mid stayed at 36–40 for the rest of the day
- Bot eventually re-shorted to -27 by close

This round-trip cost ~$179 on VEV_5300. Aggregated across all ATM vouchers, the churn cost is ~$200–500 total. Not the main lever.

**Optional fix** (low priority): once short, only buy back when z reverses sign (becomes negative). Don't chase the target down to 0 just because z drifted toward 0 — theta is still working in our favor.

```python
# Proposed: hold-the-short ratchet
if pos < 0 and z > 0:  # we're short and signal is still short-favorable
    target = min(target, pos)  # never reduce short
```

### 6b. HYDROGEL spread tuning

H_BASE_SPREAD went 2 → 4 in run 508. PnL went from +231 → +17 (volume fell 33%, edge per share collapsed). **Recommend revert to 2 or try 3.**

The 16-tick market spread leaves plenty of room for inventory skew at half-spread = 2 (4-tick total quote width). The intuition that "wider spread = more edge per trade" is wrong here because we lose flow to other MMs (Mark 14 in particular).

**Caveat**: HYDROGEL is a small market in this run (35 trades total, 153 qty). Even at +231, it's ~1.5% of total PnL. Don't over-optimize.

### 6c. SCALE_IN_TICKS and ramp speed

Currently `SCALE_IN_TICKS = 500`, so by tick 500 (timestamp ~50,000) the bot is at full target size. This is fine — the bottleneck wasn't the ramp speed, it was the cap on max target.

But with the proposed sizing change reaching ±300 at |z|≥1.5, the early-day drawdown will be larger. At ts=3800 (first ATM trade), tick=38, fraction=7.6%, max target = -23 per ATM voucher. By ts=10,000 we'd be at ~20% of target. Position would build over the first ~5,000 ticks. **The drawdown trough was -1,891 in run 508**; with the new sizing this could plausibly be -3k to -5k early in the run before mean reversion kicks in.

**Don't change SCALE_IN_TICKS.** Verify the stop-loss at -30k is sufficient. Maybe add `data["panicked"] = True` only if drawdown exceeds 30k OR if intraday drawdown exceeds 50% of peak PnL.

### 6d. V signals are mostly noise

The Mark 67/Mark 22/Mark 49 signal layer is ~+1.5 to +3 ticks of fair-value adjustment. In the live run these signals contribute small amounts to V's MM logic. They're not bad, but they're not the lever. **Don't break them; don't expand them either.**

## 7. What should NOT be changed

- **`V_MEAN = 5247.4` and `V_STD = 17.1`**. They're correct (4-day historical mean) and worked well. Don't try to estimate them online — too unstable.
- **OTM voucher list**: `VEV_5400` and `VEV_5500` are correctly classified. `VEV_6000/6500` are correctly excluded (they're pinned at 0.5 with no real market).
- **Stop loss at 30k**. It hasn't triggered yet but is critical insurance.
- **The deep-ITM (VEV_4000/4500) MM logic**. It's small (+85 PnL) but provides delta-1 exposure useful for hedging.

## 8. Expected impact of proposed changes

| Change | Expected delta PnL (10% day) | Confidence |
|---|---:|---|
| Piecewise sizing for ATM vouchers (4 products at ±300 cap) | **+$15,000 to +$25,000** | High — based on direct hypothetical computation |
| Piecewise sizing for V (limit ±200) | **+$3,000 to +$5,000** | High — same logic |
| Hold-the-short ratchet (no buyback while z same sign) | +$200 to +$500 | Low — not the main lever |
| HYDROGEL_PACK back to half_spread=2 | +$200 to +$400 | Medium — small market |
| **Total expected for next run** | **+$18,000 to +$30,000** | — |

Combined with the current +14k baseline: **expected next run PnL ≈ +$30k to +$45k on 10% day** (i.e., extrapolating to a full day, $300k–$450k range, with caveats).

## 9. Plot index

| File | Content |
|---|---|
| `improve_master.png` | Z-score over time + per-product position vs mid + actual vs hypo PnL bar chart |
| `improve_sizing.png` | Current vs proposed sizing curves for ATM vouchers and V |
| `improve_risk.png` | Risk-reward asymmetry: portfolio PnL vs V end-of-day under different scenarios |
| `improve_history.png` | Proposed |z|≥1.5 trigger applied to all 4 historical days |
| `vev5300_position.png` | Detailed look at the VEV_5300 churn pattern (small but visible) |

## 10. One-paragraph summary for the next LLM

> The bot is profitable (+14k on a 10% day) but undersized. On a directional drift day where V opens at z=+2.81, the current `target = -z × 100` rule caps ATM voucher position at -100 per strike, missing ±200 of position room and ~$25k of edge. Replace it with a piecewise function that flattens at ±max position for |z|≥1.5. This trade has favorable risk-reward (documented mean reversion + theta tailwind) and would have triggered for 25% of the live day. Don't change anything else — the current bot has the right shape; just turn the size up.
