# Round 1 Analysis Summary

- `ASH_COATED_OSMIUM` is a stationary spread-capture product around 10,000 with strong top-of-book imbalance and short-term mean reversion.
- `INTARIAN_PEPPER_ROOT` has an almost perfectly linear intraday drift of about `0.001` price units per timestamp plus smaller residual mean reversion.
- A pure max-long accumulation in pepper root is already highly profitable on every provided day, so the trader should treat it as a deliberate inventory-carry trade rather than a symmetric market-making product.
- Osmium still benefits from a fair-value maker built from `micro_dev`, `obi1`, and EMA deviation.
