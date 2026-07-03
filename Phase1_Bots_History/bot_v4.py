"""Probe R3-03: Fill Probability Mapper for Round 3

Cycles through quoting offsets 0, 1, 2, 3, 4, 5 ticks behind BBO.
Measures fill probability and time-to-fill at each offset.

Focus: HYDROGEL_PACK (wide spread=16, lots of room) and VEV_5200 (spread=3).

This is THE critical probe for calibrating the backtester's passive fill model.

What to extract:
  - P(fill | offset=k) for k=0..5 per product
  - Mean time-to-fill at each offset
  - Whether deep offsets (4-5) ever fill → hidden liquidity detection
  - Compare HGL (wide spread) vs options (tight spread) fill rates
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json

SIZE = 1
MAX_WAIT_MS = 4000
REST_MS = 400
OFFSETS = [0, 1, 2, 3, 4, 5]

PRODUCTS = ["HYDROGEL_PACK", "VEV_5200"]
LIMITS = {"HYDROGEL_PACK": 200, "VEV_5200": 300}


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


def pstate(store, prod, pos):
    ps = store.setdefault("ps", {})
    if prod not in ps:
        ps[prod] = {
            "ph": "rest", "ns": "buy", "wu": 0,
            "op": 0, "st": 0, "lp": pos, "oi": 0,  # oi = offset index
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
            ph = st["ph"]
            orders: List[Order] = []
            offset = OFFSETS[st["oi"] % len(OFFSETS)]

            # Detect fill
            if ph == "wait_buy" and pos > prev:
                emit(state.timestamp, product, "fill", side="buy",
                     off=offset, qp=st["op"], wait=state.timestamp - st["st"], pos=pos)
                st["ph"] = "flatten"
                ph = "flatten"
                st["oi"] = (st["oi"] + 1) % len(OFFSETS)
            elif ph == "wait_sell" and pos < prev:
                emit(state.timestamp, product, "fill", side="sell",
                     off=offset, qp=st["op"], wait=state.timestamp - st["st"], pos=pos)
                st["ph"] = "flatten"
                ph = "flatten"
                st["oi"] = (st["oi"] + 1) % len(OFFSETS)

            # Timeout
            if ph in ("wait_buy", "wait_sell") and state.timestamp - st["st"] >= MAX_WAIT_MS:
                emit(state.timestamp, product, "timeout",
                     side=ph.split("_")[1], off=offset, qp=st["op"])
                st["ph"] = "rest"
                st["ns"] = "sell" if ph == "wait_buy" else "buy"
                st["wu"] = state.timestamp + REST_MS
                st["oi"] = (st["oi"] + 1) % len(OFFSETS)
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

            # Maintain passive
            if ph == "wait_buy":
                orders.append(Order(product, st["op"], SIZE))
            elif ph == "wait_sell":
                orders.append(Order(product, st["op"], -SIZE))

            # Start new probe
            if ph == "rest" and pos == 0 and state.timestamp >= st["wu"]:
                offset = OFFSETS[st["oi"] % len(OFFSETS)]
                if st["ns"] == "buy":
                    px = bb - offset
                    if px > 0 and pos + SIZE <= limit:
                        st["ph"] = "wait_buy"
                        st["op"] = px
                        st["st"] = state.timestamp
                        vol = depth.buy_orders.get(px, 0)
                        emit(state.timestamp, product, "place", side="buy",
                             off=offset, px=px, vol=vol)
                        orders.append(Order(product, px, SIZE))
                elif st["ns"] == "sell":
                    px = ba + offset
                    if pos - SIZE >= -limit:
                        st["ph"] = "wait_sell"
                        st["op"] = px
                        st["st"] = state.timestamp
                        vol = abs(depth.sell_orders.get(px, 0))
                        emit(state.timestamp, product, "place", side="sell",
                             off=offset, px=px, vol=vol)
                        orders.append(Order(product, px, -SIZE))

            # Recover
            if ph == "rest" and pos != 0:
                if pos > 0:
                    orders.append(Order(product, bb, -pos))
                else:
                    orders.append(Order(product, ba, -pos))

            st["lp"] = pos
            result[product] = orders

        return result, 0, dump(store)