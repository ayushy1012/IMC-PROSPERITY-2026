# Round 3 Market Probe Bots

## Purpose

Reverse-engineer the Round 3 exchange microstructure to build a faithful backtester.
These probes target the **actual Round 3 products**: `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`,
and the 10 VEV option vouchers.

> The old probes (probe_01 through probe_17) were built for Round 1/2 products
> (ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT) and are kept for reference only.

---

## Round 3 Probe Suite

### Execution Order (least → most invasive):

| # | File | Impact | What It Measures |
|---|------|--------|------------------|
| 01 | `r3_probe_01_baseline.py` | **None** | Clean market baseline — spread, depth, OBI, NPC trades, BS fair vs market for options |
| 07 | `r3_probe_07_npc_fingerprint.py` | **None** | Full order book at ALL levels + NPC buyer/seller identities per trade |
| 02 | `r3_probe_02_queue_tracker.py` | **Minimal** | Queue fill time at BBO — FIFO vs Pro-Rata for HGL, VEV, and 4 options |
| 03 | `r3_probe_03_fill_probability.py` | **Low** | P(fill \| offset=k) for k=0..5 ticks behind BBO — the fill decay curve |
| 06 | `r3_probe_06_markout.py` | **Low** | Post-trade markout at 5/10/20 ticks — measures adverse selection |
| 04 | `r3_probe_04_impact_recovery.py` | **Moderate** | Impact(size) function + exponential recovery curve for HGL and VEV |
| 05 | `r3_probe_05_option_coupling.py` | **Moderate** | Does VEV move → option quotes update? Does option buy → VEV move? |
| 08 | `r3_probe_08_kamikaze.py` | **Maximum** | Full book obliteration + 25-tick recovery — gives α, β, τ for the impact model |

---

## What Each Probe Gives the Backtester

| Backtester Component | Probed By | Parameter |
|---------------------|-----------|-----------|
| **Matching engine** | #02 | FIFO vs Pro-Rata, queue position rules |
| **Fill probability** | #03 | `P(fill \| offset, product)` — maker's fill curve |
| **Adverse selection** | #06 | Markout curve → optimal take_margin |
| **Impact function** | #04, #08 | `Δmid = α × size^γ` — impact per lot |
| **Recovery model** | #04, #08 | `τ` — mean reversion time constant |
| **NPC behavior** | #01, #07 | Number of bots, quote sizes, BS tracking |
| **Cross-coupling** | #05 | VEV ↔ option quote coupling coefficient |
| **Baseline** | #01 | Natural spread, depth, vol without interference |

---

## How to Run

1. **Submit one probe at a time** to the Prosperity platform
2. Download the resulting `.log` and `.json` files
3. Place them in `probe_logs/r3_probe_XX_name/`
4. Extract events: `python extract_probe_events.py probe_logs/r3_probe_01_baseline/<run_id>.log`

### Recommended Order

```
Day 1: r3_probe_01_baseline + r3_probe_07_npc_fingerprint  (zero impact, safe)
Day 2: r3_probe_02_queue_tracker + r3_probe_03_fill_probability  (minimal impact)
Day 3: r3_probe_06_markout + r3_probe_04_impact_recovery  (moderate impact)
Day 4: r3_probe_05_option_coupling + r3_probe_08_kamikaze  (high impact)
```

---

## Key Differences from Round 1/2 Probes

1. **Products**: All probes target Round 3 products with correct position limits (200 for HGL/VEV, 300 for options)
2. **Options coverage**: Baseline and NPC fingerprinter log ALL 10 option books + BS fair value comparison
3. **Cross-asset coupling**: New probe (#05) specifically tests VEV ↔ option price coupling
4. **BS validation**: Baseline probe computes real-time BS fair value and logs the error vs market mid
5. **Compact logging**: Events use shortened keys (`p`, `e`, `ts`) to fit more data in the lambdaLog

---

## Legacy Probes (Round 1/2)

The following files are kept for reference but target old products:

```
probe_01_queue_tracker.py      → probe_17_mean_reversion_clock.py
```

These use `ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT` with position limit 80.
Do NOT submit these for Round 3.
