# Round 1 Physics Signal Inferences

## Core Read

- `ASH_COATED_OSMIUM` has a genuine low-frequency wave under the book noise. On the full-day spectra, low-frequency energy accounts for `0.506` on average, and the dominant period is long (`4616.0` samples median).
- `INTARIAN_PEPPER_ROOT` is the opposite: after removing the linear drift, the residual is almost entirely high-frequency chatter. High-frequency energy averages `0.698` of residual power.
- The most useful spectral feature for both products is the deviation of the live price from a low-pass reconstruction of the recent path.

## Trading Implications

- For `ASH_COATED_OSMIUM`, the filtered wave is tradable mean reversion:
  - `corr(spectral_dev, fwd5) = -0.4004`
  - cheapest decile mean `fwd5 = 1.666`
  - richest decile mean `fwd5 = -1.418`
- For `INTARIAN_PEPPER_ROOT`, the filtered residual is an execution filter, not a macro trend model:
  - `corr(spectral_dev, fwd5) = -0.6652`
  - cheapest decile mean `fwd5 = 2.732`
  - richest decile mean `fwd5 = -1.548`
- Pepper's macro move is still the slow drift. The spectral signal helps decide whether the current print is noisy-rich or noisy-cheap relative to that drift.

## Bot Changes To Keep

- Add a rolling low-pass fair adjustment for osmium and fade excursions away from that filtered wave.
- Keep pepper as a drift-carry product, but gate execution with a detrended spectral residual signal so we buy more readily when the residual is cheap and lean back when it is noisy-rich.
- Do not use the pepper spectral read as a reason to cross the book aggressively at the open; the residual mean reverts, but the opening spread still dominates short-horizon markout.
