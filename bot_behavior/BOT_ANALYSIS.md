# Bot Behavioral Analysis — Round 4 Historical Data

Round 4 trade files include named bot identifiers (round 3 had them anonymized). This unlocks a complete read on the market: who's trading what, who's winning, and who's losing.

## The 7 bots (3-day totals)

| Bot | Volume | Aggressor% | Net dir | Estimated PnL |
|---|---:|---:|---:|---:|
| **Mark 14** | 8,718 | 0% | flat | **+38,594** |
| Mark 22 | 5,889 | 86% | strong SHORT | +21,592 |
| Mark 49 | 1,186 | 1% | SHORT V | +6,704 |
| Mark 01 | 7,428 | 0% | strong LONG | −3,714 |
| Mark 67 | 1,510 | 100% | LONG V only | −8,765 |
| Mark 55 | 6,551 | 100% | flat | −16,304 |
| Mark 38 | 5,000 | 100% | flat | −32,905 |

(PnL marked-to-mid at end of day 3; the M67 figure differs from the V-only deconstruction because we mark inventory at every product's last mid.)

The pattern is clean: **aggressive bots lose, passive bots win.** The market-makers extract spread from the takers, and that's basically the entire PnL distribution. There's also a **two-bot tandem structure**: Mark 38 + Mark 14 trade against each other on HYDROGEL_PACK, Mark 22 + Mark 01 trade against each other on OTM vouchers.

## Profile of each bot

### Mark 14 — Pure 2-sided market maker (+38,594) ★ winner
- Volume 8,718 split almost perfectly 51/49 BUY/SELL
- 100% passive (sits on bids and asks, never crosses)
- Active in HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_4000 (the 3 widest-spread products)
- This is the textbook MM strategy, and it works because Mark 38 keeps feeding it spread

### Mark 38 — Aggressive 2-sided taker (−32,905) ✗ loser
- Volume 5,000 split 50/50 BUY/SELL
- 100% aggressor — pays the spread on every trade
- Mostly trades HYDROGEL_PACK and VEV_4000 (16-tick and 21-tick spreads)
- Loses ~32k by paying ~16/2 = 8 ticks × 5000 = ~40k of spread

This is a "pay the spread to manage inventory" bot. If we can quote inside Mark 14, we steal Mark 38's flow.

### Mark 22 — Aggressive directional seller (+21,592) ★ winner
- Volume 5,889, only 3.5% buys (essentially pure seller)
- 86% aggressor — sells by hitting bids
- Sells everything: V, ATM vouchers, OTM vouchers
- **Wins because the OTM vouchers expired worthless** — selling them at any non-zero price was free money

### Mark 01 — Passive directional buyer (−3,714) ✗ small loser
- Volume 7,428, 81.5% buys
- 100% passive — sits on bids and lets sellers come to them
- Mirror image of Mark 22 — buys whatever Mark 22 sells (4,636 of M22's 5,683 sell volume goes directly to M01)
- Loses despite collecting the spread because the OTM vouchers they accumulated worth ~10/share are now worth ~0

The Mark 01 + Mark 22 pair is the ultimate diagnostic: **OTM vouchers are systematic shorts**. The buyer (M01) loses because the underlying drifts and theta decays. The seller (M22) wins for the same reason.

### Mark 49 — Passive directional seller (+6,704) ★ small winner
- Volume only 1,186, 90% sells
- 99% passive — quotes the ask side and lets aggressive buyers (Mark 67, Mark 55) hit them
- V only — doesn't touch other products
- A small but profitable "fade the buy flow" specialist

### Mark 55 — Aggressive 2-sided V noise trader (−16,304) ✗ loser
- Volume 6,551 split 50/50 BUY/SELL
- 100% aggressor on V only
- Round-trips both directions, paying spread each time
- Pure noise trader — bleeds money slowly via spread cost

### Mark 67 — Aggressive V buyer ONLY (−26,130) ✗✗ biggest underperformer
- Volume 1,510, **100% buys, never sells**
- 100% aggressor — only ever lifts offers
- V only
- Built up a +1,510 long V position; lost on day 3 when V crashed

This bot is essentially the lab-rat version of *our* round 3 bot — accumulates long V via aggressive lifting, pays the spread, then gets killed when V mean-reverts. Look at the directional position bias. Then look at our round 3 trader. Same shape.

## Counterparty network

The trading is highly clustered into pairs/groups:

| Buyer | Seller | Volume | What |
|---|---|---:|---|
| Mark 01 | Mark 22 | 4,636 | OTM voucher trade — the dominant pair |
| Mark 38 | Mark 14 | 2,447 | HYDROGEL aggressive→passive |
| Mark 14 | Mark 38 | 2,445 | HYDROGEL passive→aggressive (perfect symmetry) |
| Mark 14 | Mark 55 | 1,761 | V passive bid hit by aggressive seller |
| Mark 55 | Mark 14 | 1,763 | V passive ask lifted by aggressive buyer |
| Mark 01 | Mark 55 | 1,417 | M55's V sells absorbed by M01 |
| Mark 67 | Mark 49 | 963 | M67's V buys lifted from M49's offers |
| Mark 67 | Mark 22 | 546 | M67's V buys lifted from M22's offers |

Two structural insights:
1. **Mark 14 is in the middle** of every market-making relationship. Most spread-paying flow goes through them.
2. **The OTM voucher market is a single bilateral game** — Mark 01 buys, Mark 22 sells, almost nobody else participates.

## Predictive value of bot signals

I tested whether any bot's trades predict V's future move (5000-tick horizon):

| Bot trade | n | V move after | t-stat | Excess vs baseline |
|---|---:|---:|---:|---:|
| Mark 67 BUY V | 165 | +1.92 | 3.93 | +1.99 |
| Mark 49 SELL V | 105 | +1.99 | 3.20 | +2.06 |
| Mark 22 SELL V | 101 | +1.87 | 3.05 | +1.94 |
| Mark 55 BUY V | 598 | +0.39 | 1.42 | +0.46 |
| Mark 55 SELL V | 600 | −0.39 | −1.49 | −0.31 |

The first three (low-volume V trades) all precede a +2 move on average. **But this is mean reversion, not information** — they all trade at z ≈ 0 (mean V), and V over a long-enough horizon drifts back toward the long-run mean, which sat slightly above the round 4 historical period's mean. None of these signals are exploitable as predictors.

The takeaway: **the bots have no information edge.** They are uninformed flow. The question is purely whether you make or pay spread.

## Where our round 3 bot fits

Our bot was effectively **Mark 67 plus a regime FSM**: aggressively long V with no exit. Mark 67 has the same profile (100% aggressor, 100% buyer, V-only directional) and was on track for −26k by end of day 3. Our bot did the same thing across 7 products simultaneously and lost 85k. The mechanism was identical — pay spread on entry, hold while V mean-reverts, lose.

## The competitive landscape — what does it tell us about strategy?

**The market is dominated by pure flow trading, not informed trading.** This is the defining fact for round 4. None of the bots have information edge. PnL is determined entirely by:
1. Whether you are net spread-payer or spread-collector
2. Whether your inventory ends up on the right side of any drift
3. Whether you pick assets with structural drift (OTM voucher decay)

This means there's only **one strategy that consistently makes money**: be the market maker. Quote two-sided, stay near flat, collect the spread Mark 38 / Mark 55 / Mark 67 keep paying.

For Mark 14's role to be defended (~+38k over 3 days), all you need is to:
1. Quote tighter than Mark 14 by 1 tick on HYDROGEL_PACK and V (the wide-spread products)
2. Maintain low inventory (skew quotes when inventory builds)
3. Never cross the spread unless there's a clear arb (e.g. voucher mispricing)

For Mark 22's role (+21k), strategy is:
1. Always be net short OTM vouchers (VEV_5500, 6000, 6500) at any non-zero price
2. Position size limited by 300 cap per voucher

These are the two **edges that demonstrably exist** in this market. Everything else is noise.

## Concrete plan for round 4 live

Combine the insights from previous analysis with this bot info:

| Strategy | Source bot | Rationale | Position |
|---|---|---|---|
| MM HYDROGEL_PACK 2-sided | Mark 14 | 15.7-tick spread, balanced flow, +EV per round-trip | quote ±1 from mid |
| MM VEV_4000/4500 (deep ITM) 2-sided | Mark 14 | 16–21 tick spread, balanced flow | quote ±1 from intrinsic |
| MM VELVETFRUIT_EXTRACT 2-sided | Mark 14 | 5-tick spread, balanced flow | quote ±1 from fair |
| Short OTM vouchers (5500, 6000, 6500) | Mark 22 | Theta decays to 0 by expiry | sell to limit, hold |
| z-score-based V/voucher tilt | Round 3 lesson | When V z-score extreme, lean against it | overlay on MM |
| Stop-loss at −30k | (Defensive) | Catastrophic drawdown protection | global |

**Avoid the Mark 67 trap.** Don't accumulate large directional positions by lifting offers. Especially: don't open max-long at the start of the day regardless of regime.

## Plot index

| File | What it shows |
|---|---|
| `B01_bot_pnl_curves.png` | PnL over time for each of 7 bots + leaderboard |
| `B02_counterparty_matrix.png` | Heatmap of who buys from whom (volume) |
| `B03_per_product_positions.png` | Net position per (bot, product) at end of round |
| `B04_style_scatter.png` | 2D plot: aggressor% vs buy% vs PnL — the "passive wins" diagonal |
| `B05_timing.png` | Activity histogram per bot — all trade evenly through the day |
| `B06_ecosystem.png` | Visual summary of bot relationships and PnL flows |
