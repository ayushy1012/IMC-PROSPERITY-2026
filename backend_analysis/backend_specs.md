# Prosperity Backend Bot Reverse Engineering — Deep Specification

_Analysis of 50 independent historical runs, 192,000 order-book ticks, 6,804 trades._

---

## 1. EMERALDS — The Pegged Asset

### 1.1 Core Mechanics

EMERALDS is pegged to an immovable fair value of **exactly 10,000**. The backend bots enforce this peg through a deterministic 2-state order book machine.

### 1.2 Order Book State Machine

The EMERALDS order book has exactly **2 states**:

| State | Bid L1 | Ask L1 | Spread | Frequency |
|-------|--------|--------|--------|-----------|
| **Wide** | 9,992 | 10,008 | 16 | 97.0% |
| **Tight (bid up)** | 10,000 | 10,008 | 8 | ~1.5% |
| **Tight (ask down)** | 9,992 | 10,000 | 8 | ~1.5% |

**Tight states last only 1-3 ticks** (mean 1.1 ticks), then snap back to Wide.

### 1.3 Volume Model

- **L1 volumes**: Uniformly distributed in **[10, 15]**, always symmetric (bid_vol == ask_vol 97.2% of ticks)
- **L2 levels**: Bid=9990, Ask=10010 (always exactly 2 ticks from L1), volumes in [10, 30]
- **Volume regeneration**: After consumption, volume recovers ~1.2 units/tick on average. Step sizes follow a near-symmetric distribution centered on 0 with range [-9, +10].

### 1.4 Alpha Signals

| Signal | → fwd1 | → fwd5 | → fwd10 | → fwd20 |
|--------|--------|--------|---------|---------|
| **OBI** | +0.629 | +0.634 | +0.635 | +0.626 |
| **Distance from 10k** | -0.683 | -0.701 | -0.707 | -0.704 |
| **Prev Return** | -0.473 | -0.478 | -0.483 | -0.480 |
| Bid Vol L1 | +0.160 | +0.179 | +0.176 | +0.168 |
| Ask Vol L1 | -0.198 | -0.183 | -0.185 | -0.190 |

**Key insight**: The mean-reversion correlation is **-0.70** and barely decays from fwd5 to fwd20. This means the bots deterministically force the price back to 10k — the signal doesn't weaken over any horizon we tested. OBI is the single strongest predictive feature at +0.63.

### 1.5 Bot-to-Bot Trades

Only **112 bot-to-bot trades** across 50 runs. These occur at exactly the L1 bid (9992) or L1 ask (10008), with quantities 3-8. They represent the internal churn of the market-making bots rebalancing amongst themselves.

### 1.6 Trading Edge Extraction

With fair value exactly at 10,000:
- Buy at/below 9993, sell at/above 10007 = guaranteed ~14 edge per round-trip
- **Submission VWAP**: Buys at 9995.74, Sells at 10004.13 → Edge per trade = **8.38**

---

## 2. TOMATOES — The Dynamic Asset

### 2.1 Core Mechanics

TOMATOES has a **drifting fair value** around ~4991 (ranging 4974-5009 across runs). Unlike EMERALDS, the fair value is **not static** — it evolves through a random walk with mean-reverting characteristics.

### 2.2 Order Book State Machine

TOMATOES has **2 spread regimes**:

| Regime | Spread | Frequency | Duration (mean) |
|--------|--------|-----------|-----------------|
| **Wide** | 13-14 | 93.8% | 16.2 ticks |
| **Tight** | 5-9 | 6.2% | 1.1 ticks |

**Critical discovery: Tight spread direction predicts future returns!**

| Tight State Entry | fwd5 Return | Interpretation |
|-------------------|-------------|----------------|
| **Ask dropped down** (aggressive seller appeared) | **+2.56** | Price bounces UP after ask-side aggression |
| **Bid jumped up** (aggressive buyer appeared) | **-1.61** | Price bounces DOWN after bid-side aggression |

This is the bots' mean-reversion mechanism for TOMATOES — when an aggressive trader hits one side, the bots tighten the spread on the opposite side then push price back.

### 2.3 Volume Model

- **L1 volumes**: Distributed in **[5, 10]** (main mass), symmetric 94.5% of the time
- **L2 levels**: ~1.4 ticks from L1, volumes in [5, 25]
- **L3 data**: Present in ~3% of tight-spread ticks
- **Volume regeneration**: Same ~1.2 units/tick recovery pattern as EMERALDS

### 2.4 Alpha Signals

| Signal | → fwd1 | → fwd5 | → fwd10 | → fwd20 |
|--------|--------|--------|---------|---------|
| **OBI** | +0.267 | +0.190 | +0.187 | +0.132 |
| **Prev Return** | -0.439 | -0.351 | -0.284 | -0.207 |
| Spread | -0.092 | -0.107 | -0.105 | -0.121 |
| **Spread=5 (ask dn)** | +3.83 return | +4.04 | +3.91 | +3.89 |

**Key insights**:
1. **Mean-reversion decays**: Unlike EMERALDS, the autocorrelation drops from -0.44 at lag 1 to -0.21 at lag 20. The fair value IS drifting.
2. **OBI decays**: Drops from +0.27 at fwd1 to +0.13 at fwd20. OBI is a short-term signal for TOMATOES.
3. **Spread tightening is the most powerful signal**: When spread=5 (ask dropped), next 5 ticks return +4.04. When spread=9, next 5 ticks return -2.86. The magnitude dwarfs all other signals.

### 2.5 Bot-to-Bot Trades

**713 bot-to-bot trades** across 50 runs. These cluster around the lower end of the price range (4976-4990), quantities 2-5. They represent internal bot rebalancing mostly at the bid side.

### 2.6 Trading Edge Extraction

**Submission VWAP**: Buys at 4986.82, Sells at 4993.07 → Edge per trade = **6.26**

---

## 3. Cross-Asset Analysis

**Zero cross-asset signal.** EMERALDS and TOMATOES are statistically independent:
- Contemporaneous return correlation: 0.017
- Lead-lag correlations: all < 0.01
- OBI cross-prediction: all < 0.01

Each product must be traded independently.

---

## 4. Summary: Exploitable Backend Behaviours

### EMERALDS
1. **Peg to 10,000** — Fair value is ALWAYS 10,000. Never deviate.
2. **OBI predicts direction** — If bid_vol > ask_vol, price will tick up next. Correlation +0.63.
3. **Volumes are symmetric and uniform [10,15]** — Any asymmetry is the bots leaning.

### TOMATOES
1. **Spread regime is the alpha** — When spread tightens to ≤9, it signals a bot-driven mean reversion event.
2. **Direction of tightening matters** — Ask dropping = buy signal (+4 ticks). Bid jumping = sell signal (-1.6 ticks).
3. **OBI is predictive but decays** — Use for 1-5 tick horizon only.
4. **Autocorrelation = fade momentum** — Any 1-tick move has -0.44 chance of reversing.
