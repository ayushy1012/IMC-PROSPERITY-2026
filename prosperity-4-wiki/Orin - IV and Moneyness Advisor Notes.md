# Orin's Advisor Notes — Round 3: Options Strategy

> Advisor: **Orin** (Celestial Gardeners' Guild)
> Topic: Implied Volatility, Moneyness, and Position Sizing for VEV Vouchers

---

## 1. Implied Volatility & Moneyness

**Core task**: Compute the **Implied Volatility (IV)** embedded in each VEV voucher using Black-Scholes, then study how IV varies across strikes and time.

**Moneyness** = relationship between each voucher's strike price and the current VEV underlying price.

### What to do:
1. For each voucher, back out the IV from the market price using BS inversion
2. Plot **IV vs moneyness** (the "volatility smile" or "skew")
3. Look for whether the pattern is consistent or uneven across strikes

> *"If you plot Implied Volatility against moneyness, a pattern tends to emerge. The market is always saying something with that pattern, whether it intends to or not."*

### Key insight:
The IV surface tells you what the market **expects or fears** — not what it knows. Structural patterns in the IV-moneyness relationship reveal the market's risk pricing.

---

## 2. Positioning With IV and Moneyness

**Core question**: Does the IV distribution hold together, or do certain vouchers deviate from the broader structure?

### What to look for:
- A voucher implying **more uncertainty** than its neighbors → market may be **overestimating** vol
- A voucher implying **less uncertainty** than expected → market may be **underestimating** vol
- These deviations from the IV curve are potential mispricings

### Decision framework:
| Observation | Interpretation | Action |
|-------------|---------------|--------|
| IV too high vs neighbors | Market overpricing uncertainty | **Sell** the voucher (short vol) |
| IV too low vs neighbors | Market underpricing uncertainty | **Buy** the voucher (long vol) |
| IV consistent across curve | No structural mispricing | **Stay put** |

> *"Deviation does not automatically mean opportunity. It means something is misaligned. Whether that misalignment is worth acting on, and in which direction, is the judgment call that separates a trader from someone who is simply guessing."*

---

## 3. Volume / Position Sizing

**Core principle**: Volume should reflect the **strength of your conviction**, not the size of your hope.

### Guidelines:
- **Magnitude matters**: A voucher that is slightly misaligned ≠ one that is significantly off. Proportional exposure is justified for stronger signals.
- **Larger volume amplifies both returns AND losses**
- **Markets can stay misaligned longer than expected** — even well-reasoned IV interpretations can be wrong
- **Before committing, ask**:
  1. How confident am I in my IV reading?
  2. How much damage can my strategy absorb if I'm wrong?

### Sizing heuristic (implied by Orin):
```
position_size ∝ magnitude_of_IV_deviation × confidence_level
```

> *"Conviction is not certainty."*

---

## Actionable Takeaways for Our Algo

1. **Compute IV per strike** by inverting BS: given market mid price, solve for σ
2. **Fit a smooth IV curve** (e.g., quadratic in moneyness) across all strikes
3. **Identify outliers**: strikes where market IV deviates significantly from the fitted curve
4. **Trade the deviation**: sell overpriced IV (too high vs curve), buy underpriced IV (too low)
5. **Size proportionally**: bigger position for bigger deviation, but cap risk exposure
6. **Monitor over time**: IV structure can shift — recalibrate each tick or at regular intervals
