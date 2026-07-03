"""Probe R3-04: Impact & Recovery Meter for Round 3

Sends small aggressive orders of varying sizes into HYDROGEL_PACK and
VELVETFRUIT_EXTRACT, then measures mid-price displacement and recovery.

Cycles through sizes: 1, 5, 10, 20, 40
After each sweep, records mid-price for 15 ticks to measure decay.

What to extract:
  - impact(size) function: Δmid vs order size
  - Shape: linear, concave (√n), convex (n²)?
  - Recovery time constant τ per product
  - Whether VEV impact propagates to option prices
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json

SIZES = [1, 5, 10, 20, 40]
OBSERVE_TICKS = 15
REST_TICKS = 20

PRODUCTS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]
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


class Trader:
    def run(self, state: TradingState):
        store = load(state.traderData)
        result: Dict[str, List[Order]] = {}

        for product in sorted(state.order_depths):
            depth = state.order_depths[product]

            if product not in PRODUCTS:
                result[product] = []
                continue

            if not depth.buy_orders or not depth.sell_orders:
                result[product] = []
                continue

            bb = max(depth.buy_orders)
            ba = min(depth.sell_orders)
            mid = 0.5 * (bb + ba)
            pos = state.position.get(product, 0)
            limit = LIMITS.get(product, 200)

            ps = store.setdefault("ps", {})
            if product not in ps:
                ps[product] = {
                    "ph": "rest",     # phase: rest, sweep, observe, flatten
                    "si": 0,          # size index
                    "ns": "buy",      # next side
                    "tc": 0,          # tick counter for observe
                    "pm": 0.0,        # pre-sweep mid
                    "wu": 0,          # wait until timestamp
                    "rm": [],         # recovery mids
                }
            st = ps[product]
            ph = st["ph"]
            orders: List[Order] = []

            # ── Observe phase: record recovery mids ──────────────
            if ph == "observe":
                st["rm"].append(round(mid, 2))
                st["tc"] += 1
                if st["tc"] >= OBSERVE_TICKS:
                    emit(state.timestamp, product, "impact_result",
                         side=st["ns"], size=SIZES[st["si"]],
                         pre_mid=st["pm"],
                         post_mid=st["rm"][0] if st["rm"] else mid,
                         recovery=st["rm"],
                         final_mid=round(mid, 2))
                    st["ph"] = "flatten"
                    ph = "flatten"

            # ── Flatten phase: get back to 0 ─────────────────────
            if ph == "flatten":
                if pos > 0:
                    orders.append(Order(product, bb, -pos))
                elif pos < 0:
                    orders.append(Order(product, ba, -pos))
                else:
                    st["ph"] = "rest"
                    # Advance to next size/side
                    st["si"] = (st["si"] + 1) % len(SIZES)
                    if st["si"] == 0:
                        st["ns"] = "sell" if st["ns"] == "buy" else "buy"
                    st["wu"] = state.timestamp + REST_TICKS * 100
                    ph = "rest"

            # ── Rest phase: wait for cooldown ────────────────────
            if ph == "rest" and pos == 0 and state.timestamp >= st["wu"]:
                size = SIZES[st["si"]]
                side = st["ns"]

                if side == "buy" and pos + size <= limit:
                    st["pm"] = round(mid, 2)
                    # Aggressive buy at best ask
                    qty = min(size, limit - pos)
                    emit(state.timestamp, product, "sweep",
                         side="buy", size=qty, px=ba, pre_mid=st["pm"])
                    orders.append(Order(product, ba + 10, qty))  # overpay to ensure fill
                    st["ph"] = "observe"
                    st["tc"] = 0
                    st["rm"] = []
                elif side == "sell" and pos - size >= -limit:
                    st["pm"] = round(mid, 2)
                    qty = min(size, limit + pos)
                    emit(state.timestamp, product, "sweep",
                         side="sell", size=qty, px=bb, pre_mid=st["pm"])
                    orders.append(Order(product, bb - 10, -qty))  # underprice to ensure fill
                    st["ph"] = "observe"
                    st["tc"] = 0
                    st["rm"] = []

            result[product] = orders

        return result, 0, dump(store)