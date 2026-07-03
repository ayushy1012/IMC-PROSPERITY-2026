# Round 3 — Data Inferences for Monte-Carlo Simulator

Three days of historical data (TTE = 8d → 5d), 12 products, ~30k snapshots/day at 100-unit timestamps. The goal here is **what the data tells us about the data-generating process, not what to trade**. The simulator should reproduce these features.

---

## 1. Asset taxonomy (the 12 products fall into 4 buckets)

| Bucket | Products | Behaviour |
|---|---|---|
| Mean-reverting "delta-1" | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT` | OU/AR(1) around fixed level |
| Synthetic delta-1 (deep ITM) | `VEV_4000`, `VEV_4500` | mid ≈ S − K, time value ≈ 0 |
| Real options | `VEV_5000` … `VEV_5500` | non-trivial time value, decays day-over-day |
| Floored OTM | `VEV_6000`, `VEV_6500` | mid stuck at 0.5 (bid 0 / ask 1), no signal |

So you really have **2 independent stochastic drivers** (HYDROGEL_PACK, VELVETFRUIT_EXTRACT) and 6 derivative products that are functions of S = VELVETFRUIT_EXTRACT.

---

## 2. The two delta-1 underlyings

Both behave the same way; they are *not* correlated.

| | HYDROGEL_PACK | VELVETFRUIT_EXTRACT |
|---|---|---|
| Mean | 9990.8 | 5250.1 |
| Std | 31.9 | 15.6 |
| Range | 9891 – 10079 | 5198 – 5300 |
| Lag-1 autocorr of ΔS | −0.13 | −0.16 |
| Variance ratio at lag 1000 | 0.33 | 0.35 |
| Per-step σ of log-returns | 0.00022 | 0.00022 |
| Returns correlation between them | **0.006** | (independent) |

**Inferences for the simulator:**

- Use an **Ornstein-Uhlenbeck / AR(1) on level**, not GBM. Variance ratio crashing to 0.35 at lag 1000 directly contradicts a random walk.
- Fit per asset: `S_{t+1} − μ = ρ (S_t − μ) + ε_t` with `μ ≈ 9990 / 5250`, σ_ε ≈ ~1 / ~0.5 (per 100-step).
- Lag-1 autocorr of ΔS ≈ −0.15 is **bid-ask bounce**, not a real signal — the *true* mid is smoother than the observed mid. If the simulator generates an integer-grid mid, this naturally appears.
- The two assets are independent → generate separately.

See `07_underlying_dynamics.png`.

---

## 3. Voucher pricing — empirical, NOT Black-Scholes

The discord poster is right that BS is the wrong frame, but for a subtler reason than they said: BS assumes the underlying is a martingale (random walk) on the way to expiry. **S here is mean-reverting**, so the *terminal* variance is much smaller than σ² · T, and BS with realised σ over-prices long-dated options. The market knows this — IV is lower than realised vol per step.

### 3.1 Time-value structure

Average time value (= mid − max(S−K, 0)) per day:

| K \ Day | 0 (TTE 8→7d) | 1 (TTE 7→6d) | 2 (TTE 6→5d) |
|---|---|---|---|
| 4000 | 0.01 | 0.02 | 0.01 |
| 4500 | 0.01 | 0.01 | 0.01 |
| **5000** | **6.75** | **4.87** | **3.15** |
| **5100** | **21.6** | **16.6** | **11.9** |
| **5200** | **51.0** | **46.7** | **38.7** |
| **5300** | **48.9** | **46.9** | **44.5** |
| **5400** | **18.5** | **15.7** | **13.7** |
| **5500** | **8.1** | **6.6** | **5.3** |
| 6000 | 0.5 | 0.5 | 0.5 (floor) |
| 6500 | 0.5 | 0.5 | 0.5 (floor) |

**Inferences:**

- Deep ITM (4000, 4500): TV is essentially 0. Treat the voucher as a **synthetic long S with strike-cost K** (delta = 1, see `05_deep_itm_delta1.png`).
- Floored OTM (6000, 6500): completely pinned. Not modelable beyond "stays at 0.5".
- Real options (5000–5500): TV declines monotonically across days. The **best fit** is an **empirical lookup table** of TV(K, TTE) — not a parametric formula.
- The TV-vs-K curve has the classic single-peak ATM shape (`06_tv_vs_strike_per_day.png`), peaking around K = 5200 / 5300.

### 3.2 Implied vol (BS, just to characterise the surface)

Using TTE in days:

| K \ Day | 0 | 1 | 2 |
|---|---|---|---|
| 5000 | 0.0127 | 0.0127 | 0.0128 |
| 5100 | 0.0128 | 0.0125 | 0.0124 |
| 5200 | 0.0126 | 0.0128 | 0.0128 |
| 5300 | 0.0126 | 0.0130 | 0.0130 |
| 5400 | 0.0120 | 0.0121 | 0.0121 |
| 5500 | 0.0129 | 0.0131 | 0.0132 |

The smile is **flat at σ ≈ 0.0125 per √day** for tradable strikes (`03_iv_smile.png`). The "wings" at K=4000/6500 are noise — the prices there are dominated by the integer tick-grid and the 0.5 floor.

So if you really want a parametric model: **σ ≈ 0.0125 / √day, no skew, no smile**. But again, BS+constant-σ on an OU underlying is mis-specified; the simulator should propagate S as OU and price options by Monte Carlo of S_T against the actual TTE.

---

## 4. Microstructure — where the inefficiencies actually live

Spreads (`04_spreads.png`):

| Product | Mean spread (ticks) |
|---|---|
| VEV_4000 | **20.8** ⟵ huge |
| VEV_4500 | **15.9** |
| HYDROGEL_PACK | **15.7** |
| VEV_5000 | 6.0 |
| VELVETFRUIT_EXTRACT | 5.0 |
| VEV_5100 | 4.3 |
| VEV_5200 | 2.9 |
| VEV_5300 | 2.1 |
| VEV_5400 | 1.4 |
| VEV_5500 | 1.1 |
| VEV_6000 / 6500 | 1.0 (locked) |

### 4.1 Naïve "make a tight market inside the wide spread" edge

Edge per side computed against an EWMA fair value (`08_edge_per_voucher.png`):

| Voucher | E[buy@bid edge] | E[sell@ask edge] | Round-trip |
|---|---|---|---|
| VEV_4000 | 10.4 | 10.4 | **20.8** |
| VEV_4500 | 7.9 | 7.9 | **15.9** |
| VEV_5000 | 3.5 | 2.6 | 6.0 |
| VEV_5100 | 3.3 | 1.0 | 4.3 |
| VEV_5200 | 3.1 | −0.2 | 2.9 |
| VEV_5300 | 1.4 | 0.7 | 2.1 |
| HYDROGEL_PACK | 7.1 | 8.7 | **15.7** |
| VELVETFRUIT_EXTRACT | ~2.5 | ~2.5 | ~5 |

The numbers say "VEV_4000 looks amazing — 20 ticks of round-trip edge". **Don't be fooled by this in isolation.** It must be combined with order flow.

### 4.2 Order flow — this is the second half of the picture

Where do printed trades land relative to BBO?

| Product | At bid | At ask | Total trades (3 days) | Flow direction |
|---|---|---|---|---|
| HYDROGEL_PACK | 48% | 52% | 1010 | Two-sided (MM works) |
| VELVETFRUIT_EXTRACT | 43% | 57% | 1372 | Two-sided (MM works) |
| VEV_4000 | 51% | 49% | 464 | Two-sided (MM works) |
| VEV_4500 | — | — | **1** | No flow — wide spread is a mirage |
| VEV_5000 | — | — | **1** | No flow |
| VEV_5100 | — | — | **1** | No flow |
| VEV_5200 | 94% | 6% | 18 | Sellers only |
| VEV_5300 | 98% | 1% | 121 | Sellers only |
| VEV_5400 | 100% | 0% | 225 | Sellers only |
| VEV_5500 | 100% | 0% | 267 | Sellers only |
| VEV_6000 | 100% | 0% | 284 | Sellers only |
| VEV_6500 | 100% | 0% | 284 | Sellers only |

This is the cleanest signal in the whole dataset. Three regimes:

1. **Liquid two-sided** (HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_4000): wide spread + balanced flow → classic market-making, the simulator should generate counterparty fills on both sides at non-trivial rates.

2. **No flow** (VEV_4500, VEV_5000, VEV_5100): spreads exist on paper but **3 trades total in 3 days**. Quoting tighter than the BBO probably won't fill. The simulator should reflect ~0 fill rate here unless your quote crosses the existing BBO.

3. **One-sided sellers** (VEV_5200 → VEV_6500): bots almost exclusively cross down to the bid. A passive bid below mid will fill steadily; a passive ask above mid almost never will. The simulator must distinguish "fill probability at bid" from "fill probability at ask" — they are very different here. This also means counterparty sizing is asymmetric: if you simulate equal flow both ways you'll badly mis-estimate inventory.

---

## 5. Microstructure tick-grid

- All quoted prices are integers; mid is integer or .5 (when spread = 1).
- Tick size = 1 across all products.
- Levels populated: avg ~1–2 levels per side. Level 1 carries volume ~10–25 typically, level 2 ~20–30 (where present).
- The 0.5 floor on VEV_6000 / VEV_6500 is hard-coded by the bid price never going below 0 — it's not a real bid.

---

## 6. Cross-day calendar effect

TTE inside the simulator advances 1 day per round. Within a day, TTE advances continuously by `gts/1_000_000`. Empirically:

- For real options (K = 5000–5500), the time-value at the **end** of a day is roughly the time-value at the **start** of the next day → decay is reasonably continuous, not stepwise. So the simulator should treat TTE as a continuous variable, not a per-day constant.
- The cross-day decay factor is roughly **70–80% of previous day's TV** (e.g. K=5100: 21.6 → 16.6 → 11.9 ≈ ×0.77 each day).

---

## 7. What the simulator must contain

For round 3 specifically (TTE 5d → 4d in the live simulation):

1. **Two independent OU processes** for HYDROGEL_PACK and VELVETFRUIT_EXTRACT, fit (μ, ρ, σ_ε) from the 3-day data above. Per-step σ_ε ≈ 1.15 for HYDROGEL, ≈ 1.16 for VELVETFRUIT (from std × √(1−ρ²)).

2. **Voucher pricing** as `mid = max(S − K, 0) + TV(K, TTE)` where TV is an **empirical 2-D lookup** (K × TTE) extrapolated from the 3-day table — **not** a BS formula. For round 3 use TTE=5–4d; the 3-day data covered TTE=8–5d, so you're at the lower edge but it should extrapolate cleanly given the linear-ish daily decay.

3. **Tick-grid quantisation** — round mids to 0.5 increments and BBO to integers.

4. **Spread model** per product, drawn from the empirical distribution (modes from Section 4 above).

5. **Counterparty flow model**, with three classes:
 - Two-sided: Poisson rate × (5050 split bid/ask)
 - No flow: ~zero fills unless you cross the spread
 - One-sided seller: fills only when YOU bid; effectively zero fills on YOUR ask

6. **No expiry payoff** is hit during the historical data (the data covers TTE 8d → 5d, never reaches 0). For end-of-round liquidation the rules say "open positions liquidated against a hidden fair value" — the safe estimate of that fair value is the same `intrinsic + TV(K, TTE_end)` formula.

---

## Reference plots

| File | What it shows |
|---|---|
| `01_underlying_vs_strikes.png` | S timeline + strike levels (visualises where each strike sits) |
| `02_time_value_decay.png` | TV(t) for K=5100/5200/5300/5400 across 3 days |
| `03_iv_smile.png` | Flat IV smile per day |
| `04_spreads.png` | Mean BBO spread per product |
| `05_deep_itm_delta1.png` | Voucher mid vs (S−K) for K=4000/4500/5000 |
| `06_tv_vs_strike_per_day.png` | TV(K) curve, one line per day |
| `07_underlying_dynamics.png` | S distribution + variance-ratio mean-reversion test |
| `08_edge_per_voucher.png` | One-sided edge vs empirical FV per voucher |
