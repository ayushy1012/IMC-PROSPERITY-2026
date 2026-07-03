"""Probe R3-01: Baseline Recorder for Round 3
 
Zero-interference observer. Records the full book state for ALL Round 3 products
every tick: HYDROGEL_PACK, VELVETFRUIT_EXTRACT, and all 10 VEV options.

Purpose: Establish the control baseline so every other probe's results can be
compared against natural market behavior.

What to extract:
  - Natural spread distribution per product
  - NPC trade frequency, size, and buyer/seller identities
  - Book depth at L1/L2/L3 per product
  - Mid-price autocorrelation and volatility per product
  - Option bid-ask spread vs BS fair value deviation
  - Cross-product correlation (VEV mid vs option mids)
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json
import math


def emit(ts: int, prod: str, event: str, **kw) -> None:
    row = {"ts": ts, "p": prod, "e": event}
    row.update(kw)
    print(json.dumps(row, separators=(",", ":")))


# ── BS math for option fair value logging ────────────────────
def _ncdf(x):
    return 0.5 * (1.0 + math.erf(x / 1.4142135623730951))

def bs_call(S, K, T, sigma):
    if S <= 0 or sigma <= 0 or T <= 0:
        return max(0.0, S - K)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * _ncdf(d1) - K * _ncdf(d2)


STRIKES = {
    "VEV_4000": 4000, "VEV_4500": 4500,
    "VEV_5000": 5000, "VEV_5100": 5100, "VEV_5200": 5200,
    "VEV_5300": 5300, "VEV_5400": 5400, "VEV_5500": 5500,
    "VEV_6000": 6000, "VEV_6500": 6500,
}
OPT_SIGMA = {
    4000: 0.012, 4500: 0.012, 5000: 0.0123, 5100: 0.0121,
    5200: 0.0123, 5300: 0.0124, 5400: 0.0116, 5500: 0.0126,
    6000: 0.012, 6500: 0.012,
}
TTE = 5  # Round 3


class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        # Get VEV mid for BS reference
        vev_mid = None
        vev_depth = state.order_depths.get("VELVETFRUIT_EXTRACT")
        if vev_depth and vev_depth.buy_orders and vev_depth.sell_orders:
            vev_mid = 0.5 * (max(vev_depth.buy_orders) + min(vev_depth.sell_orders))

        for product in sorted(state.order_depths):
            depth = state.order_depths[product]
            result[product] = []

            if not depth.buy_orders or not depth.sell_orders:
                emit(state.timestamp, product, "no_book")
                continue

            bids = sorted(depth.buy_orders.items(), reverse=True)
            asks = sorted(depth.sell_orders.items())
            bb, bq = bids[0][0], bids[0][1]
            ba, aq = asks[0][0], abs(asks[0][1])
            mid = 0.5 * (bb + ba)
            spread = ba - bb

            d3_bid = sum(q for _, q in bids[:3])
            d3_ask = sum(abs(q) for _, q in asks[:3])
            obi = (bq - aq) / (bq + aq) if (bq + aq) > 0 else 0.0

            snap = dict(
                mid=round(mid, 2), sp=spread, bb=bb, ba=ba,
                bq=bq, aq=aq, d3b=d3_bid, d3a=d3_ask,
                obi=round(obi, 4), nl=len(bids), na=len(asks),
            )

            # Add BS fair for options
            K = STRIKES.get(product)
            if K and vev_mid:
                sigma = OPT_SIGMA.get(K, 0.012)
                bs_fair = bs_call(vev_mid, K, TTE, sigma)
                snap["bs"] = round(bs_fair, 2)
                snap["bs_err"] = round(mid - bs_fair, 2)

            emit(state.timestamp, product, "snap", **snap)

            # Log NPC trades
            for t in state.market_trades.get(product, []):
                emit(state.timestamp, product, "trade",
                     px=t.price, q=t.quantity, b=t.buyer, s=t.seller)

        return result, 0, ""