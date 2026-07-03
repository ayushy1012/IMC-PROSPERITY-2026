"""Probe R3-07: NPC Fingerprinter for Round 3

Pure observer — logs full order book with every level for all products,
plus all NPC trades with buyer/seller identifiers.

Critical for understanding Round 3 NPC behavior:
  - How many distinct NPC bots exist per product?
  - Do option market-makers use BS pricing internally?
  - Do NPC option quotes update instantly when VEV moves?
  - Are HGL NPCs the same as VEV NPCs?
  - What are their typical quote sizes?
"""
from datamodel import Order, TradingState
from typing import Dict, List
import json


def emit(ts, prod, event, **kw):
    row = {"ts": ts, "p": prod, "e": event}
    row.update(kw)
    print(json.dumps(row, separators=(",", ":")))


class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        for product in sorted(state.order_depths):
            depth = state.order_depths[product]
            result[product] = []

            if not depth.buy_orders or not depth.sell_orders:
                continue

            bids = sorted(depth.buy_orders.items(), reverse=True)
            asks = sorted(depth.sell_orders.items())

            # Log full book structure (all levels, not just L1)
            bid_levels = [[p, q] for p, q in bids]
            ask_levels = [[p, abs(q)] for p, q in asks]

            emit(state.timestamp, product, "book",
                 bids=bid_levels, asks=ask_levels,
                 sp=asks[0][0] - bids[0][0])

            # Log every trade with buyer/seller identity
            for t in state.market_trades.get(product, []):
                emit(state.timestamp, product, "npc_trade",
                     px=t.price, q=t.quantity,
                     buyer=str(t.buyer) if t.buyer else "",
                     seller=str(t.seller) if t.seller else "")

        return result, 0, ""