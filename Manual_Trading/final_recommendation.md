# Manual Trading – Final Recommendations

## How the Auction Works (Quick Recap)
1. You submit a single **limit order** (price + quantity) per product
2. You submit **LAST** (worst time priority at any price level)
3. Exchange picks a **clearing price** that maximizes total traded volume (ties → higher price)
4. All bids ≥ clearing and asks ≤ clearing execute **at the clearing price**
5. After auction, the Merchant Guild buys your inventory at a guaranteed price

---

## 🌾 DRYLAND FLAX

**Buyback:** 30/unit (no fees)

### Order Book Without Us
| Price | Cum Bids ≥P | Cum Asks ≤P | Traded Volume |
|:-----:|:-----------:|:-----------:|:-------------:|
| 27    | 75,000      | 0           | 0             |
| **28**| **47,000**  | **40,000**  | **40,000** ◄ (current clearing) |
| 29    | 35,000      | 40,000      | 35,000        |
| 30    | 30,000      | 40,000      | 30,000        |
| 31    | 0           | 60,000      | 0             |

### Why BID 29 × 5,000
- With our bid: P=29 → bids≥29 = 40k, asks≤29 = 40k → traded = 40k. Tie with P=28 → **clearing = 29** (higher price wins)
- Fill: Supply = 40k. Bids above 29: 30k (at P=30). Existing at 29: 5k (priority). Remaining: 5k → **we get 5k**
- Profit: (30 − 29) × 5,000 = **$5,000**

> ⚠️ Bidding at 30 shifts clearing to 30 → profit per unit = $0. Bidding at 28 gives zero fill (we're last in time at clearing level).

### ✅ Order: **BID price=29, qty=5,000** → Profit: **$5,000**

---

## 🍄 EMBER MUSHROOM

**Buyback:** 20/unit (fee: $0.10/unit → net 19.90/unit)

### Order Book Without Us
| Price | Cum Bids ≥P | Cum Asks ≤P | Traded Volume |
|:-----:|:-----------:|:-----------:|:-------------:|
| 13    | 103,000     | 45,000      | 45,000        |
| 14    | 96,000      | 80,000      | 80,000        |
| **15**| **86,000**  | **86,000**  | **86,000** ◄ (current clearing) |
| 16    | 81,000      | 91,000      | 81,000        |
| 17    | 71,000      | 91,000      | 71,000        |
| 18    | 66,000      | 101,000     | 66,000        |
| 19    | 60,000      | 113,000     | 60,000        |
| 20    | 43,000      | 113,000     | 43,000        |

### Why BID 19 × 40,000
- With our bid: P=18 → bids≥18 = 106k, asks≤18 = 101k → traded = **101k** (new max) → **clearing = 18**
- Fill: Supply at ≤18 = 101k. Bids above 18: 43k(P=20) + 17k(P=19 existing) + 40k(us@19) = 100k. We're last at P=19 → existing 17k fills first, then **we get 40k** (41k remain after 60k filled above)
- Profit: (20 − 0.10 − 18) × 40,000 = **$76,000**

### Why 19 beats 18
Bidding at **18** places us AT the clearing price. The existing 6k at P=18 gets priority → we only get 35k → profit = $66,500. By bidding **19** (above clearing), we jump the queue.

### ✅ Order: **BID price=19, qty=40,000** → Profit: **$76,000**

---

## 💰 COMBINED STRATEGY

| Product | Order | Clearing | Fill | Profit |
|---------|-------|:--------:|:----:|-------:|
| 🌾 Flax | BID 29 × 5,000 | 29 | 5,000 | $5,000 |
| 🍄 Mushroom | BID 19 × 40,000 | 18 | 40,000 | $76,000 |
| **TOTAL** | | | | **$81,000** |
