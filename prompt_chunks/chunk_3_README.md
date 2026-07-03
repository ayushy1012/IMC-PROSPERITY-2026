# Analysis Chunk 3

10. What to do next

The next backtest should not be another mid-markout plot. Build this exact backtest:

Backtest 1 — crossed-only

This will probably show that most option residual trades lose.

Use it to confirm:

VEV_5000 buy_edge > 2 is the only meaningful crossed option trade.
Backtest 2 — passive maker simulation

Use public trades to approximate fill:

buy passive fill if future public trade price <= your bid
sell passive fill if future public trade price >= your ask

Test:

VEV_5400 passive bid
VEV_5200 passive ask
VEV_5300 passive ask strict
VEV_5500 passive ask strict

This is the backtest that may produce the top-3 edge.

Backtest 3 — inventory-aware maker strategy

Add:

position caps
delta bands
inventory skew
order size scaling

Example:

VEV_5400:
    max long 150 initially
    reduce bid aggressiveness above +100
    stop bidding above +180

VEV_5200:
    max short -120 initially
    reduce ask aggressiveness below -80
    stop selling below -150
Backtest 4 — final TTE stress

Run the same logic under:

TTE = 5
sigma ± 5%
underlying fair ± 3

If the passive VEV_5400/VEV_5200 edge survives, that is your actual top-rank strategy.

11. Final recommendation

The best non-obvious edge from the CSVs is:

Do not trade the option residual surface as a taker. Use the surface to decide where to provide liquidity. The strongest candidate is passive bidding in VEV_5400, with passive asking in VEV_5200 as the complementary trade.

Concrete production priorities:

1. Use TTE = 5 in final bot.
2. Compute smooth IV surface from central strikes.
3. Identify residual/kink:
       VEV_5400 cheap → passive bid
       VEV_5200 rich → passive ask
4. Cross only rare large VEV_5000 buy_edge > 2 events.
5. Avoid routine taker trades in VEV_5100/5200/5300/5400/5500.
6. Hedge total delta with Velvetfruit in bands.
7. Add Hydrogel slow mean-reversion as secondary PnL only.

This is more likely to separate you from other teams than just “Black-Scholes fair value + buy cheap/sell rich,” because the CSVs show that the naive version loses after spread.

are you sure this will improve the algorithm.
Thought for 1m 44s

I am not 100% sure it will improve your final leaderboard PnL. Nobody can honestly guarantee that from CSVs alone.

But I am sure of one thing from the CSV analysis:

A naive “option fair value says cheap/rich, so cross the ask/bid” strategy is weak and often loses after spread. So replacing it with execution-aware passive quoting is very likely to improve over the naive taker version.

That is the important distinction.

What I am confident about
1. The naive taker option strategy is not good enough

I recomputed this from the uploaded CSVs using:

buy crossed PnL  = future option mid - current option ask
sell crossed PnL = current option bid - future option mid

At horizon 10, several apparent model edges become negative after spread:

Product	Side	Threshold	Crossed PnL
VEV_5000	buy	edge > 0	-1.92
VEV_5100	buy	edge > 0	-1.60
VEV_5200	sell	edge > 0	-1.33
VEV_5300	sell	edge > 0	-1.02
VEV_5400	buy	edge > 0	-0.68
VEV_5500	sell	edge > 0	-0.57

So I would not trust a bot that simply does:

if fair > ask:
    buy
if fair < bid:
    sell

That is probably not top-3 material.

2. Passive quoting has better evidence than crossing

The strongest evidence from your CSVs is that VEV_5400 looks bad as a crossed buy, but better as a passive bid.

For VEV_5400:

Crossing ask loses around -0.60 to -0.68 per unit.
Passive bid fill estimate gives around +0.30 per filled unit.

That is a real qualitative difference.

For example, using the uploaded CSV/public trade approximation:

Strategy	Product	Approx fill rate	PnL to h=100 mid
Passive buy at bid	VEV_5400, edge > 0.5	~24.4%	+0.316
Passive buy at bid	VEV_5400, edge > 1.0	~24.2%	+0.326
Passive buy at bid	VEV_5400, edge > 3.0	~24.0%	+0.330

That does not prove final-live profitability, but it strongly suggests:

The signal exists, but the execution style must be maker/passive, not taker/aggressive.

This is exactly the kind of improvement a strong quant developer would make.

What I am not fully sure about

I am not fully sure that VEV_5400 passive bidding alone will improve the final algorithm, because:

Public trade files do not perfectly reveal your actual fill probability.
The final live round has TTE = 5, while historical data used TTE = 8/7/6. The Round 3 rules confirm this TTE shift.
Other teams’ bots can change the live liquidity environment.
Passive orders may not fill when you want them to.
If the market reprices options correctly at TTE 5, the historical residual shape may shift.

So the honest answer is:

I am sure the execution-aware approach is better than blindly crossing. I am not sure it guarantees higher final PnL until you run a proper event-driven backtest.

My current confidence ranking
Idea	Confidence it helps
Avoid naive taker trades in most VEVs	Very high
Use correct TTE: historical 8/7/6, final 5	Very high
Use VEV surface residuals as signal, not direct orders	High
Passive VEV_5400 bidding	Medium-high
Passive VEV_5200 asking	Medium
Aggressive VEV_5000 buy only when edge > 2	Medium
Routine VEV_5300 / VEV_5500 selling	Low
Far OTM VEV_6000 / VEV_6500 trading	Very low
Deep ITM VEV_4000 / VEV_4500 synthetic arbitrage	Low, rare
What I would do before trusting it

You need a direct A/B test:

Baseline A: current naive surface bot
Buy if fair - ask > threshold.
Sell if bid - fair > threshold.
Bot B: execution-aware bot
Do not cross most option signals.
Post passive bid in VEV_5400 when cheap.
Post passive ask in VEV_5200 when rich.
Cross only rare VEV_5000 extreme buy signals.
Use delta hedge bands.

Then compare:

PnL by day
PnL by product
max drawdown
max position
number of fills
PnL per fill
net delta exposure

Only accept the new version if it beats the old one under conservative assumptions.

My acceptance rule would be:

Use the new bot only if:
1. average PnL improves,
2. no single day becomes much worse,
3. drawdown decreases or remains similar,
4. PnL is not only from one fragile product,
5. option inventory remains controlled.

My best answer

Yes, I believe this direction should improve the algorithm if your current bot is taker-heavy.

But I would not say:

"This will definitely improve final leaderboard PnL."

I would say:

"The CSVs show that naive crossing is losing after spread. Therefore, converting the option residual signal into passive quoting is the correct next improvement. The highest-confidence candidate is VEV_5400 passive bidding, with VEV_5200 passive asking as a secondary edge. Now it must be validated in an inventory-aware backtest."

That is the strongest honest conclusion.
