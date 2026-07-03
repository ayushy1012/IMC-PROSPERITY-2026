# Manual Trading Round 1 – Order Books & Analysis

## Auction Rules (from wiki)
- You submit a **single limit order** (price, quantity) per product
- You submit **LAST** — no other orders arrive after you
- Clearing price is chosen to **maximize total traded volume**, ties broken by **higher price**
- All bids ≥ clearing price and asks ≤ clearing price execute at the clearing price
- You are **last in line** at any price level you join (time priority)

## Guaranteed Buyback Prices
- **DRYLAND_FLAX**: 30 per unit (no fees)
- **EMBER_MUSHROOM**: 20 per unit (fee: 0.10 per unit traded)

---

## 🌾 Dryland Flax Order Book

### Bids (People wanting to BUY Flax from you)
| Price | Volume |
|-------|--------|
| 30    | 30k    |
| 29    | 5k     |
| 28    | 12k    |
| 27    | 28k    |

### Asks (People wanting to SELL Flax to you)
| Price | Volume |
|-------|--------|
| 28    | 40k    |
| 31    | 20k    |
| 32    | 20k    |
| 33    | 30k    |

---

## 🍄 Ember Mushroom Order Book

### Bids (People wanting to BUY Mushrooms from you)
| Price | Volume |
|-------|--------|
| 20    | 43k    |
| 19    | 17k    |
| 18    | 6k     |
| 17    | 5k     |
| 16    | 10k    |
| 15    | 5k     |
| 14    | 10k    |
| 13    | 7k     |

### Asks (People wanting to SELL Mushrooms to you)
| Price | Volume |
|-------|--------|
| 12    | 20k    |
| 13    | 25k    |
| 14    | 35k    |
| 15    | 6k     |
| 16    | 5k     |
| 17    | 0      |
| 18    | 10k    |
| 19    | 12k    |
