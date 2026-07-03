"""Probe R3-02: Queue Tracker for Round 3

Places 1-lot passive orders at the best bid/ask for each product.
Measures time-to-fill (queue priority) and fill probability.

Targets: HYDROGEL_PACK, VELVETFRUIT_EXTRACT, and 4 key options
(VEV_5000, VEV_5200, VEV_5300, VEV_5400) — skips deep ITM/OTM.

What to extract:
  - Queue fill time per product → FIFO vs Pro-Rata determination
  - Fill probability at BBO vs 1 tick behind
  - Whether options and delta-1 products use the same matching engine
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json

SIZE = 1
MAX_WAIT_MS = 5000
REST_MS = 600

# Products to probe (skip deep ITM/OTM options — no fills)
PRODUCTS = [
    "HYDROGEL_PACK", "VELVETFRUIT_EXTRACT",
    "VEV_5000", "VEV_5200", "VEV_5300", "VEV_5400",
]
LIMITS = {
    "HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200,
    "VEV_5000": 300, "VEV_5200": 300, "VEV_5300": 300, "VEV_5400": 300,
}


def emit(ts, prod, event, **kw):
    row = {"ts": ts, "p": prod, "e": event}
    row.update(kw)
    print(json.dumps(row, separators=(",", ":")))


def load(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except:
        return {}


def dump(d):
    return json.dumps(d, separators=(",", ":"))


def pstate(store, prod, pos):
    ps = store.setdefault("ps", {})
    if prod not in ps:
        ps[prod] = {
            "ph": "rest", "ns": "buy", "wu": 0,
            "op": 0, "st": 0, "lp": pos,
        }
    return ps[prod]


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
            pos = state.position.get(product, 0)
            limit = LIMITS.get(product, 300)
            st = pstate(store, product, pos)
            prev = st.get("lp", pos)
            delta = pos - prev

            if delta != 0:
                emit(state.timestamp, product, "pdelta", d=delta, pos=pos, ph=st["ph"])

            ph = st["ph"]
            orders: List[Order] = []

            # Detect fill
            if ph == "wait_buy" and pos > prev:
                emit(state.timestamp, product, "fill", side="buy",
                     qp=st["op"], wait=state.timestamp - st["st"], pos=pos,
                     vol_at=depth.buy_orders.get(st["op"], 0))
                st["ph"] = "flatten"
                ph = "flatten"
            elif ph == "wait_sell" and pos < prev:
                emit(state.timestamp, product, "fill", side="sell",
                     qp=st["op"], wait=state.timestamp - st["st"], pos=pos,
                     vol_at=abs(depth.sell_orders.get(st["op"], 0)))
                st["ph"] = "flatten"
                ph = "flatten"

            # Timeout
            if ph in ("wait_buy", "wait_sell") and state.timestamp - st["st"] >= MAX_WAIT_MS:
                emit(state.timestamp, product, "timeout", side=ph.split("_")[1],
                     qp=st["op"], wait=MAX_WAIT_MS)
                st["ph"] = "rest"
                ns = "sell" if ph == "wait_buy" else "buy"
                st["ns"] = ns
                st["wu"] = state.timestamp + REST_MS
                ph = "rest"

            # Flatten
            if ph == "flatten":
                if pos > 0:
                    orders.append(Order(product, bb, -pos))
                elif pos < 0:
                    orders.append(Order(product, ba, -pos))
                else:
                    st["ph"] = "rest"
                    st["ns"] = "sell" if st.get("ns") == "buy" else "buy"
                    st["wu"] = state.timestamp + REST_MS
                    ph = "rest"

            # Maintain passive during wait
            if ph == "wait_buy" and pos == prev:
                orders.append(Order(product, st["op"], SIZE))
            elif ph == "wait_sell" and pos == prev:
                orders.append(Order(product, st["op"], -SIZE))

            # Start new probe
            if ph == "rest" and pos == 0 and state.timestamp >= st["wu"]:
                if st["ns"] == "buy" and pos + SIZE <= limit:
                    st["ph"] = "wait_buy"
                    st["op"] = bb
                    st["st"] = state.timestamp
                    emit(state.timestamp, product, "join", side="buy",
                         px=bb, vol=depth.buy_orders.get(bb, 0))
                    orders.append(Order(product, bb, SIZE))
                elif st["ns"] == "sell" and pos - SIZE >= -limit:
                    st["ph"] = "wait_sell"
                    st["op"] = ba
                    st["st"] = state.timestamp
                    emit(state.timestamp, product, "join", side="sell",
                         px=ba, vol=abs(depth.sell_orders.get(ba, 0)))
                    orders.append(Order(product, ba, -SIZE))

            # Recover stale position
            if ph == "rest" and pos != 0:
                if pos > 0:
                    orders.append(Order(product, bb, -pos))
                else:
                    orders.append(Order(product, ba, -pos))

            st["lp"] = pos
            result[product] = orders

        return result, 0, dump(store)