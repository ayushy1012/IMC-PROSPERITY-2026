"""Probe R3-05: Option-Underlying Coupling Probe

Tests whether trading VELVETFRUIT_EXTRACT causes option prices to move,
and vice versa. This is critical for delta hedging and cross-product strategies.

Protocol:
  Phase A: Buy 20 VEV aggressively, hold, observe ALL option mids for 10 ticks.
  Phase B: Flatten VEV, observe option mids for 10 ticks.
  Phase C: Buy 20 VEV_5200 aggressively, observe VEV mid for 10 ticks.
  Phase D: Flatten VEV_5200, rest.

What to extract:
  - Does aggressive VEV buying cause option asks to rise?
  - Does aggressive option buying cause VEV to move?
  - Coupling delay (instant or lagged?)
  - Whether NPC option quotes track VEV mid in real-time or with delay
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json

PHASES = ["buy_vev", "observe_opts", "flatten_vev", "rest1",
          "buy_opt", "observe_vev", "flatten_opt", "rest2"]
OBSERVE_TICKS = 10
REST_MS = 3000
SWEEP_SIZE = 20

OPT_PRODUCTS = [
    "VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500"
]


def emit(ts, prod, event, **kw):
    row = {"ts": ts, "p": prod, "e": event}
    row.update(kw)
    print(json.dumps(row, separators=(",", ":")))


def load(raw):
    try:
        return json.loads(raw) if raw else {}
    except:
        return {}


def dump(d):
    return json.dumps(d, separators=(",", ":"))


def get_mid(depth):
    if depth and depth.buy_orders and depth.sell_orders:
        return 0.5 * (max(depth.buy_orders) + min(depth.sell_orders))
    return None


def log_all_mids(state, label):
    """Log current mids for all products."""
    mids = {}
    for prod in sorted(state.order_depths):
        m = get_mid(state.order_depths[prod])
        if m is not None:
            mids[prod] = round(m, 2)
    emit(state.timestamp, "ALL", label, **mids)


class Trader:
    def run(self, state: TradingState):
        store = load(state.traderData)
        result: Dict[str, List[Order]] = {}

        # Initialize state
        if "ph" not in store:
            store.update({"ph": 0, "tc": 0, "wu": 0, "cyc": 0})

        phi = store["ph"]
        phase = PHASES[phi % len(PHASES)]
        tc = store["tc"]

        # Default: no orders for anything
        for prod in state.order_depths:
            result[prod] = []

        vev_d = state.order_depths.get("VELVETFRUIT_EXTRACT")
        opt_d = state.order_depths.get("VEV_5200")
        vev_pos = state.position.get("VELVETFRUIT_EXTRACT", 0)
        opt_pos = state.position.get("VEV_5200", 0)

        # ── Phase: buy VEV aggressively ──────────────────────
        if phase == "buy_vev":
            if vev_d and vev_d.sell_orders:
                ba = min(vev_d.sell_orders)
                qty = min(SWEEP_SIZE, 200 - vev_pos)
                if qty > 0:
                    result["VELVETFRUIT_EXTRACT"] = [Order("VELVETFRUIT_EXTRACT", ba + 20, qty)]
                    emit(state.timestamp, "VELVETFRUIT_EXTRACT", "echo_sweep",
                         side="buy", size=qty, px=ba)
                    log_all_mids(state, "pre_sweep")
            store["ph"] = phi + 1
            store["tc"] = 0

        # ── Phase: observe option mids after VEV sweep ───────
        elif phase == "observe_opts":
            log_all_mids(state, "post_vev_sweep")
            store["tc"] = tc + 1
            if tc >= OBSERVE_TICKS:
                store["ph"] = phi + 1

        # ── Phase: flatten VEV ───────────────────────────────
        elif phase == "flatten_vev":
            if vev_pos != 0 and vev_d:
                if vev_pos > 0 and vev_d.buy_orders:
                    bb = max(vev_d.buy_orders)
                    result["VELVETFRUIT_EXTRACT"] = [Order("VELVETFRUIT_EXTRACT", bb - 10, -vev_pos)]
                elif vev_pos < 0 and vev_d.sell_orders:
                    ba = min(vev_d.sell_orders)
                    result["VELVETFRUIT_EXTRACT"] = [Order("VELVETFRUIT_EXTRACT", ba + 10, -vev_pos)]
            if vev_pos == 0:
                store["ph"] = phi + 1
                store["wu"] = state.timestamp + REST_MS

        # ── Phase: rest ──────────────────────────────────────
        elif phase == "rest1":
            if state.timestamp >= store["wu"]:
                store["ph"] = phi + 1

        # ── Phase: buy option aggressively ───────────────────
        elif phase == "buy_opt":
            if opt_d and opt_d.sell_orders:
                ba = min(opt_d.sell_orders)
                qty = min(SWEEP_SIZE, 300 - opt_pos)
                if qty > 0:
                    result["VEV_5200"] = [Order("VEV_5200", ba + 20, qty)]
                    emit(state.timestamp, "VEV_5200", "echo_sweep",
                         side="buy", size=qty, px=ba)
                    log_all_mids(state, "pre_opt_sweep")
            store["ph"] = phi + 1
            store["tc"] = 0

        # ── Phase: observe VEV mid after option sweep ────────
        elif phase == "observe_vev":
            log_all_mids(state, "post_opt_sweep")
            store["tc"] = tc + 1
            if tc >= OBSERVE_TICKS:
                store["ph"] = phi + 1

        # ── Phase: flatten option ────────────────────────────
        elif phase == "flatten_opt":
            if opt_pos != 0 and opt_d:
                if opt_pos > 0 and opt_d.buy_orders:
                    bb = max(opt_d.buy_orders)
                    result["VEV_5200"] = [Order("VEV_5200", bb - 10, -opt_pos)]
                elif opt_pos < 0 and opt_d.sell_orders:
                    ba = min(opt_d.sell_orders)
                    result["VEV_5200"] = [Order("VEV_5200", ba + 10, -opt_pos)]
            if opt_pos == 0:
                store["ph"] = phi + 1
                store["wu"] = state.timestamp + REST_MS

        elif phase == "rest2":
            if state.timestamp >= store["wu"]:
                store["ph"] = phi + 1
                store["cyc"] = store.get("cyc", 0) + 1
                emit(state.timestamp, "ALL", "cycle_done", cycle=store["cyc"])

        return result, 0, dump(store)
