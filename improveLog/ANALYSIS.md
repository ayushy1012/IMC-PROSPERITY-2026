# Run 505724 — Analysis & Improvements

## Final result: **+12,637 XIRECS** (FINISHED)

This is the **first profitable run**. Same opening conditions as the round-3 disaster (V opens at 5295.5, z=+2.81), but this time the bot was correctly positioned to fade the extreme open and made +12k. That's a +97k swing from the same starting state.

---

## Where the log data comes from (your direct question)

The `505724.log` and `505724.json` files are produced by the **IMC simulator**, not by your bot. The simulator runs your `Trader.run(state)` once per tick and captures everything:

| Field | What it is | Who fills it |
|---|---|---|
| `submissionId` | UUID for this run | simulator |
| `activitiesLog` | CSV of order book at every (day, ts, product) | simulator records the book |
| `tradeHistory` | every executed trade with buyer/seller names | simulator records matches |
| `logs[i].sandboxLog` | error/exception messages | simulator (empty if no errors) |
| `logs[i].lambdaLog` | **anything your bot prints** | YOUR `print()` statements |
| `logs[i].timestamp` | tick number | simulator |
| `profit` | final PnL | simulator computes from cash + positions × close mid |
| `positions` | final per-product positions | simulator |
| `graphLog` | pre-aggregated equity curve `timestamp;value` | simulator |

**All 1000 `lambdaLog` entries in this run are empty** because the bot has zero `print()` statements. If you want to debug-trace a future run, add prints inside `Trader.run` — they show up in `lambdaLog[i]`. Example:

```python
print(f"t={state.timestamp} z={z:.2f} v_target={v_target} pos={state.position}")
```

These print outputs are truncated per tick (~hundreds of chars), so keep them concise.

### Important: this run is only 10% of a real day

Look at this:

```
Run timestamps: 0 → 99,900 in steps of 100  (= 1,000 ticks)
Real day:       0 → 999,900 in steps of 100  (= 10,000 ticks)
```

The IMC simulator on the website runs a **short "Lite" simulation** (10% of a day) for quick feedback. The actual leaderboard scoring is on a much longer run. Two implications:

1. PnL extrapolated to a full day might be ~ +12k × 10 = **+126k** (very rough — non-linear because some edges saturate at position limits)
2. Some bugs that don't show up in 10% of a day will compound over the full run

---

## What worked (in priority order)

| Strategy | PnL | Notes |
|---|---:|---|
| ATM voucher z-score short (5000/5100/5200/5300) | **+9,296** | The big winner. Same setup as round 3 disaster, this time short |
| V z-score short | +1,820 | Smaller because the V position oscillated between -47 and +20 |
| OTM theta short on VEV_5500 | +847 | Sold 300 at avg 6.32, end mid 3.5 |
| OTM theta short on VEV_5400 | +400 | Lots of churn (923 trades for +400) |
| HYDROGEL_PACK MM | +231 | 95% of the day's HGL volume captured, but spread thin |
| Deep ITM (4000/4500) | +85 | Tiny activity, basically dormant |

**Total wins: +12,679**

## What didn't work — concrete bugs

### Bug 1: VEV_6000 / VEV_6500 sold at price 0 (−300 total)

In `trade_otm_theta()`, the bot walks the bid book hitting any non-zero quantity:

```python
for price, qty in sorted(depth.buy_orders.items(), reverse=True):
    sell_qty = min(qty, abs(diff))
    if sell_qty > 0:
        orders.append(Order(symbol, price, -sell_qty))
```

VEV_6000 and VEV_6500 have a "bid" at price **0** with quantity > 0 (it's the floor of the simulator's tick grid). The bot sold 300 at price 0 → cash = 0 → mark-to-mid at 0.5 → loss of 150 each.

**Fix (1 line):**

```python
for price, qty in sorted(depth.buy_orders.items(), reverse=True):
    if price <= 0:                    # ← add this guard
        break
    sell_qty = min(qty, abs(diff))
    ...
```

Better still, never short these floored vouchers at all:

```python
OTM_PRODUCTS = ["VEV_5500"]            # remove 6000/6500 entirely
```

These are pinned at 0.5 with no real market — there's nothing to harvest.

### Bug 2: VEV_5400 gets churned by overlapping strategies (923 trades for +400)

`VEV_5400` is in `ATM_VOUCHERS` (gets z-score sells) but **also** would benefit from being in `OTM_PRODUCTS` (it expires at 0.5 mid, mostly worthless). Currently the bot:

1. Z-score logic targets `-100` (because z×100 = max ATM target)
2. Z-score reaches that target and stops
3. Mid drifts down → bot's stale buy quotes get filled (add inventory)
4. Z-score reduces target → bot sells back what it just bought
5. Repeat for 923 trades, capturing only 0.71 ticks of edge per round-trip

The strategies fight each other.

**Fix:** classify VEV_5400 (and arguably VEV_5300) as OTM theta, not ATM z-score. With V around 5260 these are 100+ points OTM and dominated by theta decay, not delta.

```python
ATM_VOUCHERS = ["VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300"]  # remove 5400
OTM_PRODUCTS = ["VEV_5400", "VEV_5500"]                            # add 5400, drop 6000/6500
```

VEV_5400's avg sell price was 13.60. Held to expiry probably ~0. That's ~13 ticks × 300 size = **+3,900 on a clean short** vs the +400 actually achieved.

### Bug 3: Z-score V target not reached

Configuration: `Z_V_SCALE = 200/3 = 66.7`. At z=+2.81, target = −187 (max position). But the actual V trajectory was:

- min: −47 (well short of −187)
- max: +20 (the bot was net long for ~1/3 of the day!)
- final: −1

Why? Three layers fight on V:

1. **Z-score logic** wants V short to −187
2. **Mark 55 round-trip MM overlay** posts both bid and ask, regardless of z-score direction
3. **Mark 67 cooldown** suppresses buying — but doesn't suppress *selling*, so it's not the issue

The MM overlay's bid keeps getting hit when V dips, building unwanted long exposure. Then z-score sells it back. Repeat.

**Fix:** when |z| > rush threshold (2.0), disable the MM overlay entirely. The MM overlay is for capturing noise — when there's a strong directional signal, MM overlay is just noise on top of signal.

```python
def trade_v_mm_overlay(depth, pos, signals, z):
    if abs(z) > Z_RUSH_THRESH:        # ← gate by z
        return []
    if not signals["mark55_active"]:
        return []
    # ... existing logic
```

### Bug 4: ATM voucher position never reaches z-score target

Final positions were −68/−59/−72/−27 vs targets of approximately −94/−94/−94/−66 (z×100). The bot stopped converging when:
- It reached the limit *during the rush phase* (before fraction = 1.0)
- Then z-score decayed (V drifted toward mean) → target shrunk → bot didn't add more

This is **mostly fine for this run** because z came down to +0.36 by close (intended behaviour: less z means smaller short). But notice that VEV_5300 only got to −27 final. It's still profitable but undersized.

**Fix:** when position is short of target by more than `Z_TRADE_THRESH=20`, post both passive *and* aggressive orders simultaneously. Currently the bot picks one or the other based on `rush`. Better: always post a passive order for free fills, and *also* take if z is extreme.

### Bug 5: HYDROGEL MM is high-volume but low-edge (+231)

The bot captured 95% of HGL volume (191 of 201 quantity). But average buy was 10029.28 and average sell was 10032.73 — only **3.45 ticks of spread** captured per round-trip. The actual market spread on HGL is 16. The bot is quoting too tight (or fighting too aggressive an inventory skew).

Actual MM math: 191 qty × 3.45 / 2 = +329. We got +231 (close, the difference is unrealised inventory mark).

**Fix:** widen the HGL passive quotes to capture more of the 16-tick spread. Right now `H_BASE_SPREAD = 2` (4-tick total). Try 4 or 5 (8–10 total). The volume might drop a bit but per-trade edge will quadruple.

```python
H_BASE_SPREAD = 4   # was 2 — try 4 or 5
```

### Bug 6: Stop loss never triggered, but trough was −1,763

The cumulative PnL went from −1,763 in the first ~2k ticks (during initial scale-in) to +13,684 peak. Drawdown stayed under 4k throughout. So `STOP_LOSS_DRAWDOWN = 30000` is way too lenient for this run, but on a full-length day it may be appropriate. **No change needed — but worth instrumenting** with a `print` line each tick capturing `mtm`, `peak`, `drawdown` for future diagnostics.

---

## Concrete patch summary

Six changes, ranked by impact:

```python
# 1. (Bug 1) Don't sell at price 0
def trade_otm_theta(symbol, depth, pos):
    for price, qty in sorted(depth.buy_orders.items(), reverse=True):
        if price <= 0:                           # ← new
            break
        # ... existing

# 2. (Bug 2) Reclassify vouchers
ATM_VOUCHERS = ["VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300"]
OTM_PRODUCTS = ["VEV_5400", "VEV_5500"]          # remove 6000/6500, add 5400
# Optionally: remove 6000/6500 entirely from any list

# 3. (Bug 3) Gate MM overlay by z
def trade_v_mm_overlay(depth, pos, signals, z):
    if abs(z) > Z_RUSH_THRESH:
        return []
    # ... existing
# And pass z in the caller:
mm_orders = trade_v_mm_overlay(v_depth, v_pos, signals, z)

# 4. (Bug 4) Allow simultaneous passive + aggressive when far from target
def trade_zscore_product(symbol, target, depth, pos, z, rush):
    diff = target - pos
    orders = []
    if rush and abs(z) > Z_RUSH_THRESH:
        # Take some now
        # ... existing aggressive code
    # Always post passive too (existing code) — remove the else
    # ... existing passive code

# 5. (Bug 5) Widen HGL spread
H_BASE_SPREAD = 4   # was 2

# 6. (Diagnostic) Add lambdaLog tracing
def run(self, state):
    # ... at end:
    if data['tick_count'] % 100 == 0:
        print(f"t={state.timestamp} z={z:.2f} mtm={mtm:.0f} dd={drawdown:.0f}")
```

## Estimated impact (back-of-envelope)

If applied to the same run:

| Fix | Expected delta |
|---|---:|
| Bug 1 (no sell at 0) | +300 (recover the −150 × 2 loss) |
| Bug 2 (5400 → OTM) | +3,500 (clean short instead of churn) |
| Bug 3 (gate MM) | +300 (better V execution) |
| Bug 4 (always-passive) | +500 (fuller voucher position) |
| Bug 5 (wider HGL) | +500 (deeper spread captured) |
| **Total** | **+5,100 → ~+17,700** |

Multiplied by 10× for a full day, this projects ~+177k. That's a swag — actual will depend heavily on day's V trajectory.

## What NOT to change

- **Don't change `V_MEAN`/`V_STD`**. They're 4-day historical (5247.4 / 17.1) and worked perfectly here (V opened at z=+2.81, bot shorted, V drifted back toward mean → profit).
- **Don't disable the bot signal layer** (Mark 67 cooldown, Mark 22 cascade detection). It's quiet in the data but helped avoid the round-3 trap of buying at the open.
- **Don't add a directional bias on HGL**. HGL is mean-reverting around 9990, and the bot's EMA fair-value tracking is correct.
- **Don't reduce position limits**. The bot is already conservative (final positions are well below limits on most products).

---

## Plot

`r505_summary.png` shows per-product position trajectories, mid prices, and the cumulative PnL curve.
