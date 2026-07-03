"""Probe R3-06: Markout Profiler for Round 3

Aggressively takes 1 lot, holds for 20 ticks recording mid-price at each step,
then flattens. Alternates buy/sell. Runs on HYDROGEL_PACK and VELVETFRUIT_EXTRACT.

What to extract:
  - markout_5: E[mid(t+5) - entry_mid] after aggressive buy
  - markout_10: E[mid(t+10) - entry_mid]
  - markout_20: E[mid(t+20) - entry_mid]
  - Adverse selection: negative markout = NPC knows more than you
  - Optimal take_margin = -E[markout_5] + spread/2

Also runs on VEV_5200 to test option markout dynamics.
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json

HOLD_TICKS = 20
REST_MS = 600
SIZE = 1

PRODUCTS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT", "VEV_5200"]
LIMITS = {"HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200, "VEV_5200": 300}


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
            limit = LIMITS.get(product, 300)

            ps = store.setdefault("ps", {})
            if product not in ps:
                ps[product] = {
                    "ph": "rest", "ns": "buy", "wu": 0,
                    "em": 0.0, "rm": [], "tc": 0, "lp": pos,
                }
            st = ps[product]
            ph = st["ph"]
            orders: List[Order] = []

            # ── Detect initial fill ──────────────────────────
            if ph == "wait_fill":
                prev = st.get("lp", pos)
                if (st["ns"] == "buy" and pos > prev) or (st["ns"] == "sell" and pos < prev):
                    st["em"] = round(mid, 2)
                    st["rm"] = [round(mid, 2)]
                    st["tc"] = 0
                    st["ph"] = "hold"
                    ph = "hold"
                    emit(state.timestamp, product, "fill",
                         side=st["ns"], entry_mid=st["em"], px=ba if st["ns"] == "buy" else bb)

            # ── Hold and observe ─────────────────────────────
            if ph == "hold":
                st["rm"].append(round(mid, 2))
                st["tc"] += 1

                if st["tc"] >= HOLD_TICKS:
                    entry = st["em"]
                    mids = st["rm"]
                    m5 = mids[5] - entry if len(mids) > 5 else 0
                    m10 = mids[10] - entry if len(mids) > 10 else 0
                    m20 = mids[-1] - entry

                    emit(state.timestamp, product, "markout",
                         side=st["ns"], entry_mid=entry,
                         m5=round(m5, 2), m10=round(m10, 2), m20=round(m20, 2),
                         path=mids)
                    st["ph"] = "flatten"
                    ph = "flatten"

            # ── Flatten ──────────────────────────────────────
            if ph == "flatten":
                if pos > 0:
                    orders.append(Order(product, bb, -pos))
                elif pos < 0:
                    orders.append(Order(product, ba, -pos))
                else:
                    st["ph"] = "rest"
                    st["ns"] = "sell" if st["ns"] == "buy" else "buy"
                    st["wu"] = state.timestamp + REST_MS
                    ph = "rest"

            # ── Start new probe ──────────────────────────────
            if ph == "rest" and pos == 0 and state.timestamp >= st["wu"]:
                if st["ns"] == "buy" and pos + SIZE <= limit:
                    orders.append(Order(product, ba, SIZE))  # aggressive buy at ask
                    st["ph"] = "wait_fill"
                    emit(state.timestamp, product, "send", side="buy", px=ba)
                elif st["ns"] == "sell" and pos - SIZE >= -limit:
                    orders.append(Order(product, bb, -SIZE))  # aggressive sell at bid
                    st["ph"] = "wait_fill"
                    emit(state.timestamp, product, "send", side="sell", px=bb)

            # Recover stale pos
            if ph == "rest" and pos != 0:
                if pos > 0:
                    orders.append(Order(product, bb, -pos))
                else:
                    orders.append(Order(product, ba, -pos))

            st["lp"] = pos
            result[product] = orders

        return result, 0, dump(store)
