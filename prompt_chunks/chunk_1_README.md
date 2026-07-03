# Analysis Chunk 1

do not give results without analyzing the csvs in detail.
Thought for 7m 31s

You are right to push on this. I reloaded the uploaded CSVs and recomputed the signals from the raw columns, not just from the charts. The main finding is uncomfortable but very useful:

Your current Phase 4 “executable-edge markout” is not truly executable if it is using future mid movement after a signal. Once I charge the actual bid/ask crossing cost, most of the apparent option alpha disappears.

That is exactly the kind of hidden issue that separates a top-3 bot from a normal bot.

The rules side is still correct: the final Round 3 live simulation uses TTE = 5, while historical days 0/1/2 use TTE = 8/7/6. The IV-smile plot also shows the analysis was correctly done using day-specific TTEs.

1. The biggest hidden insight: your option markout is mid-markout, not crossed PnL

Your Phase 4 chart shows positive markouts for several option signals. But after recomputing directly from the CSV:

For a buy signal, true crossed PnL should be:

future_option_mid - current_option_ask

For a sell signal, true crossed PnL should be:

current_option_bid - future_option_mid

When I recomputed this from the CSVs at horizon 10, I got:

Product	Side	Signal rule	Count	Mid-markout looked like	True crossed PnL
VEV_5000	buy	buy_edge > 0	1184	+0.76	-1.93
VEV_5100	buy	buy_edge > 0	841	+0.19	-1.60
VEV_5100	sell	sell_edge > 0	385	-0.54	-2.09
VEV_5200	sell	sell_edge > 0	12702	small positive in earlier view	-1.33
VEV_5300	sell	sell_edge > 0	23076	tiny positive in earlier view	-1.02
VEV_5400	buy	buy_edge > 0	28439	near flat/slightly positive	-0.68
VEV_5500	sell	sell_edge > 0	28608	near flat	-0.57

This changes the conclusion completely.

The option residuals do mean-revert — your residual mean-reversion plot is real. But the spread is eating the edge if you cross blindly.

So the top-3 insight is:

Do not build a taker-heavy option residual bot. Build an execution-aware options market-making bot around the residual surface.

2. The best edge is not “buy cheap options”; it is “provide liquidity when the surface says the other side is wrong”

Most teams will do this:

if model_fair > ask:
    buy
if model_fair < bid:
    sell

That looks logical, but your CSVs show this loses after crossing.

The better edge is:

if model says option is cheap:
    do not cross the ask
    post/join bid, or bid slightly inside spread

if model says option is rich:
    do not cross the bid
    post/join ask, or ask slightly inside spread

This is where your data becomes interesting.

I estimated passive-fill behavior using the public trade CSVs: after a signal, check whether a trade occurs within the next window at a price that would have hit your passive order.

The strongest passive edge I found is:

VEV_5400 passive buy

Signal:

model says VEV_5400 is cheap

Do not buy at ask.

Instead:

post buy at current best bid

From the CSV estimate:

Rule	Signals	Approx fills within 50 ticks	Fill rate	Mean PnL after fill
VEV_5400, buy at bid, buy_edge > 0.5	27965	6890	24.6%	+0.316
VEV_5400, buy at bid, buy_edge > 1.0	27261	6648	24.4%	+0.326
VEV_5400, buy at bid, buy_edge > 3.0	10276	2480	24.1%	+0.330

This is much more interesting than the taker result. Crossing the ask loses about -0.6 to -0.7 per unit, but passively bidding has positive expectancy.

That means the hidden edge is:

VEV_5400 is structurally cheap relative to a smooth surface, but the edge is only tradable as a maker, not as a taker.

This is exactly the kind of thing many teams miss.

3. Second hidden edge: selective passive selling in VEV_5200

VEV_5200 looks rich in the leave-one-out surface. The residual plot shows positive residuals for VEV_5200 and especially VEV_5300.

But crossing to sell VEV_5200 loses after spread:

VEV_5200 sell_edge > 0:
    true crossed PnL at h=10 ≈ -1.33

However, passive selling is different.

If you post at the ask instead of crossing the bid:

Rule	Approx fills	Mean PnL after fill
VEV_5200, sell at ask, fill within 10 ticks	18	+2.11
VEV_5200, sell at ask, fill within 50 ticks	169	+1.35

This is lower-frequency than VEV_5400, but the per-fill edge is larger.

So the second edge is:

Quote passive asks in VEV_5200 when the surface says it is rich. Do not aggressively sell it.
