"""Probe R3-08: Kamikaze Sweeper for Round 3

Maximum-impact stress test. Sends a huge aggressive order to obliterate
all visible liquidity, then observes the full recovery.

Runs on HYDROGEL_PACK (limit=200) and VELVETFRUIT_EXTRACT (limit=200).

Protocol:
  1. Wait for calm market (stable spread for 5 ticks)
  2. Sweep: aggressive buy for 150 lots (near max capacity)
  3. Observe: record mid, spread, depth for 25 ticks
  4. Flatten: dump entire position
  5. Observe recovery for another 25 ticks
  6. Rest, then do the same on sell side
  7. Repeat on other product

What to extract:
  - α: immediate impact coefficient (Δmid per lot)
  - β: decay rate (how fast spread recovers)
  - τ: time constant for mean reversion
  - Whether liquidity fully recovers or stays impaired
  - Whether sweeping VEV causes HGL to react (cross-product)
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json

SWEEP_SIZE = 150
OBSERVE_TICKS = 25
REST_MS = 5000
CALM_TICKS = 5

TARGETS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]
LIMITS = {"HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200}


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


def get_book_stats(depth):
    if not depth.buy_orders or not depth.sell_orders:
        return None
    bb = max(depth.buy_orders)
    ba = min(depth.sell_orders)
    return {
        "mid": round(0.5 * (bb + ba), 2),
        "sp": ba - bb,
        "d_bid": sum(depth.buy_orders.values()),
        "d_ask": sum(abs(v) for v in depth.sell_orders.values()),
    }


class Trader:
    def run(self, state: TradingState):
        store = load(state.traderData)
        result: Dict[str, List[Order]] = {}

        if "ph" not in store:
            store.update({
                "ph": "calm",     # calm, sweep, observe1, flatten, observe2, rest
                "ti": 0,          # target index
                "ns": "buy",      # next side
                "tc": 0,          # tick counter
                "pm": 0.0,        # pre-sweep mid
                "rm": [],         # recovery mids
                "wu": 0,          # wait until
                "calm_count": 0,
                "last_sp": 0,
            })

        # All products get empty orders by default
        for prod in state.order_depths:
            result[prod] = []

        target = TARGETS[store["ti"] % len(TARGETS)]
        depth = state.order_depths.get(target)
        if not depth or not depth.buy_orders or not depth.sell_orders:
            return result, 0, dump(store)

        bb = max(depth.buy_orders)
        ba = min(depth.sell_orders)
        mid = 0.5 * (bb + ba)
        sp = ba - bb
        pos = state.position.get(target, 0)
        limit = LIMITS.get(target, 200)
        ph = store["ph"]

        # Log all product mids for cross-product analysis
        all_mids = {}
        for p2 in state.order_depths:
            stats = get_book_stats(state.order_depths[p2])
            if stats:
                all_mids[p2] = stats["mid"]

        # ── Calm: wait for stable spread ─────────────────────
        if ph == "calm":
            if sp == store.get("last_sp", sp):
                store["calm_count"] = store.get("calm_count", 0) + 1
            else:
                store["calm_count"] = 0
            store["last_sp"] = sp

            if store["calm_count"] >= CALM_TICKS and pos == 0:
                store["pm"] = round(mid, 2)
                store["ph"] = "sweep"
                ph = "sweep"

        # ── Sweep: obliterate the book ───────────────────────
        if ph == "sweep":
            side = store["ns"]
            qty = min(SWEEP_SIZE, limit - abs(pos))
            if side == "buy" and qty > 0:
                result[target] = [Order(target, ba + 50, qty)]
                emit(state.timestamp, target, "kamikaze",
                     side="buy", size=qty, pre_mid=store["pm"])
            elif side == "sell" and qty > 0:
                result[target] = [Order(target, bb - 50, -qty)]
                emit(state.timestamp, target, "kamikaze",
                     side="sell", size=qty, pre_mid=store["pm"])
            store["ph"] = "observe1"
            store["tc"] = 0
            store["rm"] = []

        # ── Observe post-sweep ───────────────────────────────
        elif ph == "observe1":
            store["rm"].append({"mid": round(mid, 2), "sp": sp, "all": all_mids})
            store["tc"] += 1
            if store["tc"] >= OBSERVE_TICKS:
                emit(state.timestamp, target, "post_sweep",
                     side=store["ns"], pre_mid=store["pm"],
                     recovery=[r["mid"] for r in store["rm"]],
                     spreads=[r["sp"] for r in store["rm"]])
                store["ph"] = "flatten"

        # ── Flatten ──────────────────────────────────────────
        elif ph == "flatten":
            if pos > 0:
                result[target] = [Order(target, bb - 20, -pos)]
            elif pos < 0:
                result[target] = [Order(target, ba + 20, -pos)]
            else:
                store["ph"] = "observe2"
                store["tc"] = 0
                store["rm"] = []

        # ── Observe post-flatten recovery ────────────────────
        elif ph == "observe2":
            store["rm"].append({"mid": round(mid, 2), "sp": sp})
            store["tc"] += 1
            if store["tc"] >= OBSERVE_TICKS:
                emit(state.timestamp, target, "post_flatten_recovery",
                     side=store["ns"], pre_mid=store["pm"],
                     recovery=[r["mid"] for r in store["rm"]],
                     spreads=[r["sp"] for r in store["rm"]])
                store["ph"] = "rest"
                store["wu"] = state.timestamp + REST_MS
                # Advance side then target
                if store["ns"] == "buy":
                    store["ns"] = "sell"
                else:
                    store["ns"] = "buy"
                    store["ti"] = (store["ti"] + 1) % len(TARGETS)

        # ── Rest ─────────────────────────────────────────────
        elif ph == "rest":
            if state.timestamp >= store["wu"] and pos == 0:
                store["ph"] = "calm"
                store["calm_count"] = 0

        return result, 0, dump(store)