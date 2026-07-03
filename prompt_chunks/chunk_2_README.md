# Analysis Chunk 2

4. What not to do: the apparent VEV_5300, VEV_5500 edges are mostly traps

The residual chart makes VEV_5300 and VEV_5500 look very rich. But the executable CSV recomputation says:

Product	Side	Crossed h=10 result
VEV_5300	sell	around -1.02
VEV_5300, sell_edge > 3	sell	around -0.79
VEV_5500	sell	around -0.57
VEV_5500, sell_edge > 3	sell	around -0.48

So these are not strong taker trades.

For VEV_5300, the model says “rich,” but the market does not correct fast enough after spread. For VEV_5500, the option is too close to the low-price/tick-floor region. Small theoretical edges are not monetizable.

Final conclusion:

VEV_5300:
    maybe passive ask only, but not core.

VEV_5500:
    avoid except extreme mispricing.

VEV_6000 / VEV_6500:
    ignore.

5. Another trap: deep ITM VEV_4000 and VEV_4500 are not true synthetic arbitrage

The markout chart makes VEV_4000 and VEV_4500 buy signals look huge.

But I tested the actual synthetic relation:

VEV_K + K ≈ VELVETFRUIT_EXTRACT

Executable synthetic buy edge:

underlying_bid - (option_ask + K)

Results:

Product	Mean synthetic buy edge	Max synthetic buy edge	Positive events
VEV_4000	-12.9	+1.0	1 event
VEV_4500	-10.4	+1.0	1 event

So there is basically no repeatable synthetic arbitrage.

The positive deep-ITM markout is mostly directional exposure to Velvetfruit, not a clean arbitrage. Do not build the bot around it.

6. Static arbitrage also does not give the hidden edge

I checked executable vertical-spread arbitrage:

C(K1) - C(K2) should be between 0 and K2-K1

Using executable bid/ask:

No vertical pair had true executable arbitrage.

I also checked butterfly-style structures. The surface has a visible kink around VEV_5300/VEV_5400/VEV_5500, but when you form executable butterfly trades, the apparent credit is not risk-free and the historical markout is negative.

Example crossed butterfly-style markouts at horizon 10:

Middle strike	Structure	Mean PnL
5100	buy middle / sell wings	-8.76
5200	buy middle / sell wings	-6.09
5300	buy middle / sell wings	-4.24
5400	buy middle / sell wings	-3.01

So do not waste time on pure static-arb structures unless the live book becomes much more distorted.

7. The real top-3 edge from the CSVs

The best edge I see is:

Execution-aware volatility-surface market making.

More specifically:

1. Use the TTE-corrected IV surface.
2. Detect persistent smile residuals.
3. Do not cross the spread except in rare extreme cases.
4. Post passive orders on the side supported by the surface.
5. Let fills come to you.
6. Hedge Velvetfruit delta only in bands.

The highest-priority product is not VEV_5000 taker buying. It is:

VEV_5400 passive bid strategy

because:

- it has many signals,
- it has meaningful public-trade fill probability,
- crossing loses,
- passive bid has positive expectancy,
- the residual kink is persistent across days.

The second-priority product is:

VEV_5200 passive ask strategy

because:

- fewer fills,
- larger per-fill edge,
- useful as a complement to VEV_5400 long exposure.

The third-priority product is:

rare VEV_5000 aggressive buy only when edge is extreme

From crossed-PnL recomputation:

Rule	Count	h=10 crossed PnL	h=20 crossed PnL	h=100 crossed PnL
VEV_5000 buy_edge > 0	1184	-1.93	negative/weak	+1.20
VEV_5000 buy_edge > 1.5	40	+0.31	+1.53	+2.69
VEV_5000 buy_edge > 2.0	12	+0.58	+2.50	+7.00

So VEV_5000 is not a broad trade. It is a rare extreme-edge taker trade.

8. Final algorithmic change I would make

Your current strategy should become three-layered.

Layer A — maker options engine

This is the most important upgrade.

VEV_5400

If model says cheap:

buy_edge_to_bid = fair - best_bid

Then:

if buy_edge_to_bid > threshold and position not too long:
    post buy at best_bid

Use thresholds like:

VEV_5400 passive buy:
    fair - bid > 2.0 or 3.0

Do not buy at ask unless the edge is enormous.

VEV_5200

If model says rich:

sell_edge_to_ask = best_ask - fair

Then:

if sell_edge_to_ask > threshold and position not too short:
    post sell at best_ask

Use:

VEV_5200 passive sell:
    ask - fair > 1.0 or 1.5
VEV_5300 and VEV_5500

Only quote passively with stricter thresholds:

VEV_5300 passive sell only if ask - fair > 2.5
VEV_5500 passive sell only if ask - fair > 3.0
Layer B — rare taker options engine

Only cross when the edge survives the spread.

Allowed taker rules:

VEV_5000:
    buy at ask only if fair - ask > 1.5 or 2.0

VEV_4000 / VEV_4500:
    only if synthetic parity confirms, otherwise skip

VEV_5100:
    avoid taker trading unless edge is extreme

VEV_5200 / 5300 / 5400 / 5500:
    do not cross under normal residual signal

This is a big correction from “surface residual = trade.”

Layer C — delta/risk engine

Because VEV_5400 passive bidding may accumulate long calls, you need portfolio delta control.

Use:

net_delta =
    VELVETFRUIT_EXTRACT_position
    + Σ option_position_i * option_delta_i

Then:

if net_delta > +120:
    sell Velvetfruit toward +60

if net_delta < -120:
    buy Velvetfruit toward -60

Do not fully hedge every tick. The spread on Velvetfruit is around 5, so over-hedging will burn PnL. The delta-1 spread chart confirms Velvetfruit is much tighter than Hydrogel but still not free to cross repeatedly.

9. The production logic should be different from the research logic

Research model:

historical day 0 → TTE 8
historical day 1 → TTE 7
historical day 2 → TTE 6

Production model:

live Round 3 → TTE 5

This means the final bot must not hardcode historical prices. It must recompute fair values at TTE 5. The rules confirm final Round 3 uses TTE 5.

This is crucial because the live TTE effect is large:

Product	Day 2 historical fair → live TTE 5 fair drop
VEV_5100	about -3.05
VEV_5200	about -4.89
VEV_5300	about -5.04
VEV_5400	about -3.65
VEV_5500	about -1.18

So any bot using day-2 option levels directly will overvalue options in the final.
