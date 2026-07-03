"""
Round 4 Composite Bot — Prosperity 4
=====================================
Three independent alpha sources + risk controls:

1. HYDROGEL_PACK:  Two-sided market making (clone Mark 14)
2. VELVETFRUIT_EXTRACT + ATM vouchers:  Z-score mean reversion
3. OTM vouchers (5500/6000/6500):  Theta harvesting (passive sell)
4. Deep ITM vouchers (4000/4500):  Market making around intrinsic
"""

import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════

# Position limits per product
LIMITS = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300, "VEV_4500": 300,
    "VEV_5000": 300, "VEV_5100": 300, "VEV_5200": 300,
    "VEV_5300": 300, "VEV_5400": 300, "VEV_5500": 300,
    "VEV_6000": 300, "VEV_6500": 300,
}

# ── Strategy 1: Hydrogel MM parameters ──
H_BASE_SPREAD   = 3       # half-spread in ticks from fair value (~6 total vs 15.7 market)
H_SKEW_FACTOR   = 0.03    # ticks of skew per unit of inventory
H_INVENTORY_SOFT = 60     # start skewing harder beyond this
H_WIDEN_EXTRA    = 1      # minimal widening — we want flow
H_ORDER_SIZE     = 20     # size per quote level
H_EMA_ALPHA      = 0.12   # for fair-value EMA

# ── Strategy 2: Z-score reversion parameters ──
# Piecewise sizing: dead zone below |z|=1, linear ramp 1→1.5, flat at ±limit ≥1.5
Z_DEAD_ZONE    = 1.0          # no position below this |z|
Z_FULL_ZONE    = 1.5          # full position above this |z|
Z_TRADE_THRESH = 20           # minimum |target-pos| to act
Z_RUSH_THRESH  = 2.0          # |z| above which we cross the spread

# ── Options Strategy parameters ──
OTM_TARGET      = -300    # max short
OTM_SELL_SIZE   = 50      # size per passive sell order
DEEP_SPREAD     = 3       # half-spread around intrinsic
DEEP_ORDER_SIZE = 20
DEEP_SKEW       = 0.03

# ── Risk ──
STOP_LOSS_DRAWDOWN = 30000
SCALE_IN_TICKS     = 100   # reach full size in ~100 ticks ≈ 10 seconds

# ── Counterparty names ──
MARK_67 = "Mark 67"   # aggressive V buyer (uninformed, fade him)
MARK_38 = "Mark 38"   # aggressive H taker (feed him spread)
MARK_55 = "Mark 55"   # aggressive V noise trader (round-trips, capture both legs)
MARK_22 = "Mark 22"   # aggressive seller across all products (sell cascade)
MARK_01 = "Mark 01"   # passive buyer of OTM vouchers (exploit bids)

# ── Signal tracking parameters ──
M67_COOLDOWN_TICKS = 100    # after M67 buys, suppress our V buys for 100 ticks
M22_CASCADE_TICKS  = 50     # after M22 sells, widen bids for 50 ticks
M55_V_MM_SIZE      = 15     # size for V two-sided MM to capture M55 round-trips
M55_V_MM_SPREAD    = 1      # half-spread for V MM overlay


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def best_mid(depth: Optional[OrderDepth]) -> Optional[float]:
    """Compute mid price from order depth, or None if empty."""
    if depth is None:
        return None
    if not depth.buy_orders or not depth.sell_orders:
        return None
    return 0.5 * (max(depth.buy_orders) + min(depth.sell_orders))


def microprice(depth: OrderDepth) -> float:
    """Volume-weighted microprice (more accurate fair value)."""
    bb = max(depth.buy_orders)
    ba = min(depth.sell_orders)
    bv = abs(depth.buy_orders[bb])
    av = abs(depth.sell_orders[ba])
    return (bb * av + ba * bv) / (bv + av)


def clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def add_order(orders: List[Order], symbol: str, price: int, qty: int, pos: int, limit: int):
    """Add an order only if it wouldn't breach position limits.
    qty > 0 = buy, qty < 0 = sell."""
    if qty > 0:
        room = limit - pos
        qty = min(qty, room)
    elif qty < 0:
        room = limit + pos   # pos could be negative
        qty = max(qty, -room)
    if qty != 0:
        orders.append(Order(symbol, price, qty))


# ═══════════════════════════════════════════════════════════════════
#  STRATEGY 1: HYDROGEL_PACK MARKET MAKING
# ═══════════════════════════════════════════════════════════════════

def trade_hydrogel_mm(depth: OrderDepth, pos: int, data: dict) -> List[Order]:
    """Two-sided market making with inventory skew. Passive only."""
    if not depth.buy_orders or not depth.sell_orders:
        return []

    orders: List[Order] = []
    limit = LIMITS["HYDROGEL_PACK"]
    symbol = "HYDROGEL_PACK"

    # Fair value via EMA of microprice
    mp = microprice(depth)
    prev_fair = data.get("h_fair")
    if prev_fair is None:
        fair = mp
    else:
        fair = prev_fair + H_EMA_ALPHA * (mp - prev_fair)
    data["h_fair"] = fair

    # Inventory skew: shift both quotes toward reducing inventory
    skew = -pos * H_SKEW_FACTOR

    # Base half-spread
    half = H_BASE_SPREAD
    if abs(pos) > H_INVENTORY_SOFT:
        half += H_WIDEN_EXTRA

    # During sell cascade, pull bid further back
    cascade_extra = data.get("h_cascade_extra", 0)

    # Quote prices (integer)
    bid_price = int(math.floor(fair + skew - half - cascade_extra))
    ask_price = int(math.ceil(fair + skew + half))

    # Ensure we don't cross ourselves
    if bid_price >= ask_price:
        bid_price = ask_price - 1

    # Ensure we don't post inside the existing book spread
    # (we want to be inside Mark 14's quotes to capture Mark 38's flow)
    best_bid = max(depth.buy_orders)
    best_ask = min(depth.sell_orders)

    # Size: multiple levels
    for offset in range(3):
        bp = bid_price - offset
        ap = ask_price + offset
        sz = H_ORDER_SIZE
        add_order(orders, symbol, bp, sz, pos + sum(o.quantity for o in orders if o.quantity > 0), limit)
        add_order(orders, symbol, ap, -sz, pos + sum(o.quantity for o in orders if o.quantity < 0), limit)

    return orders


# ═══════════════════════════════════════════════════════════════════
#  STRATEGY 2: Z-SCORE MEAN REVERSION
# ═══════════════════════════════════════════════════════════════════

def piecewise_target(z: float, position_limit: int) -> int:
    """Piecewise z-score sizing:
    - |z| < 1.0: no position (dead zone, no edge worth spread cost)
    - 1.0 ≤ |z| < 1.5: linear ramp from 0 to ±limit
    - |z| ≥ 1.5: flat at ±limit (full conviction)
    """
    abs_z = abs(z)
    if abs_z < Z_DEAD_ZONE:
        return 0
    elif abs_z < Z_FULL_ZONE:
        # Linear ramp from 0 (at |z|=1.0) to ±limit (at |z|=1.5)
        frac = (abs_z - Z_DEAD_ZONE) / (Z_FULL_ZONE - Z_DEAD_ZONE)
        raw = int(position_limit * frac)
        return -raw if z > 0 else raw
    else:
        return -position_limit if z > 0 else position_limit


def compute_z_targets(v_mid: float, v_mean: float, v_std: float, fraction: float) -> Tuple[int, int, float]:
    """Compute V target and ATM option target from z-score using piecewise sizing."""
    if v_std == 0: v_std = 1.0  # fallback
    z = (v_mid - v_mean) / v_std

    v_target = piecewise_target(z, LIMITS["VELVETFRUIT_EXTRACT"])
    opt_target = piecewise_target(z, 300)

    # Apply scale-in fraction
    v_target = int(v_target * fraction)
    opt_target = int(opt_target * fraction)

    return v_target, opt_target, z


def trade_zscore_product(symbol: str, target: int, depth: OrderDepth, pos: int,
                         z: float, rush: bool = False) -> List[Order]:
    """Generate orders to move toward target position for a z-score product.
    When rush is True, posts BOTH aggressive and passive orders for faster convergence."""
    if not depth or not depth.buy_orders or not depth.sell_orders:
        return []

    diff = target - pos
    limit = LIMITS.get(symbol, 300)

    # Don't churn — require minimum threshold
    if abs(diff) < Z_TRADE_THRESH:
        return []

    orders: List[Order] = []
    best_bid = max(depth.buy_orders)
    best_ask = min(depth.sell_orders)

    if rush and abs(z) > Z_RUSH_THRESH:
        # Aggressive: cross the spread for immediate fills
        if diff > 0:
            agg_qty = min(diff, limit - pos)
            if agg_qty > 0:
                orders.append(Order(symbol, best_ask, agg_qty))
        else:
            agg_qty = max(diff, -limit - pos)
            if agg_qty < 0:
                orders.append(Order(symbol, best_bid, agg_qty))

    # Always ALSO post passive orders for free fills (even during rush)
    remaining = diff - sum(o.quantity for o in orders)
    if abs(remaining) >= Z_TRADE_THRESH:
        if remaining > 0:
            price = best_bid + 1
            qty = min(remaining, limit - pos - sum(o.quantity for o in orders if o.quantity > 0))
            if qty > 0:
                orders.append(Order(symbol, price, qty))
        else:
            price = best_ask - 1
            qty = max(remaining, -limit - pos - sum(o.quantity for o in orders if o.quantity < 0))
            if qty < 0:
                orders.append(Order(symbol, price, qty))

    return orders


# ═══════════════════════════════════════════════════════════════════
#  STRATEGY 3: OTM THETA HARVESTING
# ═══════════════════════════════════════════════════════════════════

def trade_otm_theta(symbol: str, depth: OrderDepth, pos: int) -> List[Order]:
    """Passively sell OTM vouchers to collect theta decay."""
    if not depth or not depth.buy_orders:
        return []

    orders: List[Order] = []
    limit = LIMITS.get(symbol, 300)
    target = OTM_TARGET  # -300

    diff = target - pos
    if diff >= 0:
        return []  # already at or past target

    # Sell passively: post ask at best_ask or slightly below
    # But also hit any bids that are available (free money for expiring-worthless options)
    for price, qty in sorted(depth.buy_orders.items(), reverse=True):
        if price <= 0:  # Bug 1 fix: never sell at price 0 (simulator floor)
            break
        # qty is positive on buy side
        sell_qty = min(qty, abs(diff))
        sell_qty = min(sell_qty, limit + pos)  # room to go shorter
        if sell_qty > 0:
            orders.append(Order(symbol, price, -sell_qty))
            diff += sell_qty
            if diff >= 0:
                break

    # Also post passive ask if there's still room
    if diff < 0 and depth.sell_orders:
        best_ask = min(depth.sell_orders)
        # Post at best_ask - 1 to improve
        post_price = max(1, best_ask - 1)
        sell_qty = min(abs(diff), OTM_SELL_SIZE)
        sell_qty = min(sell_qty, limit + pos - sum(abs(o.quantity) for o in orders))
        if sell_qty > 0:
            orders.append(Order(symbol, post_price, -sell_qty))

    return orders


# ═══════════════════════════════════════════════════════════════════
#  STRATEGY 4: DEEP ITM MARKET MAKING
# ═══════════════════════════════════════════════════════════════════

def trade_deep_itm_mm(symbol: str, strike: int, v_mid: float,
                       depth: OrderDepth, pos: int) -> List[Order]:
    """Market-make deep ITM vouchers around their intrinsic value."""
    if not depth or not depth.buy_orders or not depth.sell_orders:
        return []

    orders: List[Order] = []
    limit = LIMITS.get(symbol, 300)

    # Intrinsic value for a call = max(0, V - K)
    intrinsic = max(0.0, v_mid - strike)
    # Add a small time-value buffer (these are deep ITM so TV is small)
    fair = intrinsic + 2.0  # ~2 ticks of remaining TV at TTE=4d

    # Inventory skew
    skew = -pos * DEEP_SKEW
    half = DEEP_SPREAD

    bid_price = int(math.floor(fair + skew - half))
    ask_price = int(math.ceil(fair + skew + half))

    if bid_price >= ask_price:
        bid_price = ask_price - 1
    if bid_price < 1:
        bid_price = 1

    # Quote
    for offset in range(2):
        bp = bid_price - offset
        ap = ask_price + offset
        if bp >= 1:
            add_order(orders, symbol, bp, DEEP_ORDER_SIZE,
                     pos + sum(o.quantity for o in orders if o.quantity > 0), limit)
        add_order(orders, symbol, ap, -DEEP_ORDER_SIZE,
                 pos + sum(o.quantity for o in orders if o.quantity < 0), limit)

    return orders


# ═══════════════════════════════════════════════════════════════════
#  COUNTERPARTY SIGNAL TRACKING
# ═══════════════════════════════════════════════════════════════════

def scan_counterparty_signals(market_trades: dict, data: dict, tick: int) -> dict:
    """Scan all market trades for counterparty activity and maintain state."""
    signals = {
        "mark67_buying": False, "mark67_volume": 0,
        "mark55_net": 0, "mark55_active": False,
        "mark22_selling": False, "mark22_sell_volume": 0,
        "mark67_cooldown": False,
        "mark22_cascade": False,
    }

    cp_stats = data.setdefault("cp_stats", {})

    # ── Scan trades ──
    for product, trades in market_trades.items():
        for trade in trades:
            # 1. Update dynamic CP stats
            for cp_name, is_buy in [(trade.buyer, True), (trade.seller, False)]:
                if not cp_name:
                    continue
                if cp_name not in cp_stats:
                    cp_stats[cp_name] = {"buy_vol": 0.0, "sell_vol": 0.0, "v_buy": 0.0, "v_sell": 0.0, "last_tick": tick}
                
                stats = cp_stats[cp_name]
                ticks_elapsed = tick - stats["last_tick"]
                if ticks_elapsed > 0:
                    decay = 0.999 ** ticks_elapsed
                    stats["buy_vol"] *= decay
                    stats["sell_vol"] *= decay
                    stats["v_buy"] *= decay
                    stats["v_sell"] *= decay
                    stats["last_tick"] = tick
                
                if is_buy:
                    stats["buy_vol"] += trade.quantity
                    if product == "VELVETFRUIT_EXTRACT":
                        stats["v_buy"] += trade.quantity
                else:
                    stats["sell_vol"] += trade.quantity
                    if product == "VELVETFRUIT_EXTRACT":
                        stats["v_sell"] += trade.quantity

            # 2. Named + Dynamic Augmentation logic
            buyer = trade.buyer or ""
            seller = trade.seller or ""
            
            # M67: Aggressive V Buyer (Named OR Dynamic)
            is_m67 = (buyer == MARK_67)
            if not is_m67 and buyer in cp_stats and product == "VELVETFRUIT_EXTRACT":
                st = cp_stats[buyer]
                v_tot = max(1.0, st["v_buy"] + st["v_sell"])
                if v_tot > 50 and (st["v_buy"] / v_tot) > 0.85:
                    is_m67 = True
            
            if is_m67 and product == "VELVETFRUIT_EXTRACT":
                signals["mark67_buying"] = True
                signals["mark67_volume"] += trade.quantity
                data["m67_last_buy_tick"] = tick

            # M55: Noise round-tripper (Named OR Dynamic)
            is_m55_buyer = (buyer == MARK_55)
            is_m55_seller = (seller == MARK_55)
            
            if not is_m55_buyer and buyer in cp_stats and product == "VELVETFRUIT_EXTRACT":
                st = cp_stats[buyer]
                if st["v_buy"] > 30 and st["v_sell"] > 30:
                    is_m55_buyer = True
            if not is_m55_seller and seller in cp_stats and product == "VELVETFRUIT_EXTRACT":
                st = cp_stats[seller]
                if st["v_buy"] > 30 and st["v_sell"] > 30:
                    is_m55_seller = True

            if is_m55_buyer and product == "VELVETFRUIT_EXTRACT":
                signals["mark55_net"] += trade.quantity
                signals["mark55_active"] = True
            if is_m55_seller and product == "VELVETFRUIT_EXTRACT":
                signals["mark55_net"] -= trade.quantity
                signals["mark55_active"] = True

            # M22: Cascade seller across all products (Named OR Dynamic)
            is_m22 = (seller == MARK_22)
            if not is_m22 and seller in cp_stats:
                st = cp_stats[seller]
                tot = max(1.0, st["buy_vol"] + st["sell_vol"])
                if tot > 80 and (st["sell_vol"] / tot) > 0.85:
                    is_m22 = True

            if is_m22:
                signals["mark22_selling"] = True
                if product == "VELVETFRUIT_EXTRACT":
                    signals["mark22_sell_volume"] += trade.quantity
                data["m22_last_sell_tick"] = tick

    # ── Cooldown timers ──
    m67_last = data.get("m67_last_buy_tick", -999)
    if tick - m67_last < M67_COOLDOWN_TICKS:
        signals["mark67_cooldown"] = True

    m22_last = data.get("m22_last_sell_tick", -999)
    if tick - m22_last < M22_CASCADE_TICKS:
        signals["mark22_cascade"] = True

    # ── Track Mark 55 cumulative net for round-trip detection ──
    m55_cum = data.get("m55_cumulative_net", 0)
    m55_cum += signals["mark55_net"]
    data["m55_cumulative_net"] = m55_cum
    signals["mark55_cumulative"] = m55_cum

    return signals


def trade_v_mm_overlay(depth: OrderDepth, pos: int, signals: dict, z: float) -> List[Order]:
    """Two-sided V market making overlay to capture Mark 55 round-trips.
    Only active when Mark 55 has been trading recently AND z is not extreme."""
    if abs(z) > Z_RUSH_THRESH:  # Bug 3 fix: disable MM overlay when z is extreme
        return []
    if not signals["mark55_active"]:
        return []
    if not depth or not depth.buy_orders or not depth.sell_orders:
        return []

    orders: List[Order] = []
    limit = LIMITS["VELVETFRUIT_EXTRACT"]
    symbol = "VELVETFRUIT_EXTRACT"

    best_bid = max(depth.buy_orders)
    best_ask = min(depth.sell_orders)

    # Post inside the spread to capture M55's next leg
    bid_price = best_bid + 1
    ask_price = best_ask - 1

    if bid_price >= ask_price:
        # Spread is already 1 tick, just post at best
        bid_price = best_bid
        ask_price = best_ask

    sz = M55_V_MM_SIZE

    # Skew based on M55's recent direction: if they just bought, they'll sell next
    m55_cum = signals.get("mark55_cumulative", 0)
    if m55_cum > 10:
        # M55 is net long, they'll sell — make our bid bigger
        add_order(orders, symbol, bid_price, sz + 5, pos, limit)
        add_order(orders, symbol, ask_price, -sz, pos, limit)
    elif m55_cum < -10:
        # M55 is net short, they'll buy — make our ask bigger
        add_order(orders, symbol, bid_price, sz, pos, limit)
        add_order(orders, symbol, ask_price, -(sz + 5), pos, limit)
    else:
        add_order(orders, symbol, bid_price, sz, pos, limit)
        add_order(orders, symbol, ask_price, -sz, pos, limit)

    return orders


# ═══════════════════════════════════════════════════════════════════
#  TRADER CLASS
# ═══════════════════════════════════════════════════════════════════

class Trader:

    def bid(self) -> int:
        return 0

    def run(self, state: TradingState):
        try:
            data = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            data = {}

        # ── Tick counter (monotonic across days) ──
        data["tick_count"] = data.get("tick_count", -1) + 1
        tick = data["tick_count"]

        # ── MTM tracking for stop loss ──
        prev_pos = data.get("prev_pos", {})
        prev_mid = data.get("prev_mid", {})
        mtm = data.get("mtm", 0.0)

        current_mid = {}
        for product, depth in state.order_depths.items():
            mid = best_mid(depth)
            if mid is not None:
                current_mid[product] = mid

        # Mark-to-market PnL change from position × price movement
        for product, pos_val in prev_pos.items():
            if product in current_mid and product in prev_mid:
                mtm += pos_val * (current_mid[product] - prev_mid[product])

        data["mtm"] = mtm
        data["pnl_hist"] = data.get("pnl_hist", [])
        data["pnl_hist"].append(mtm)
        data["pnl_hist"] = data["pnl_hist"][-500:]

        peak = max(data["pnl_hist"]) if data["pnl_hist"] else 0
        drawdown = peak - mtm

        # ── STOP LOSS ──
        if drawdown > STOP_LOSS_DRAWDOWN or data.get("panicked", False):
            data["panicked"] = True
            panic_result = {}
            for prod, depth in state.order_depths.items():
                p = state.position.get(prod, 0)
                if p != 0 and depth.buy_orders and depth.sell_orders:
                    bb = max(depth.buy_orders)
                    ba = min(depth.sell_orders)
                    if p > 0:
                        panic_result[prod] = [Order(prod, bb, -p)]
                    else:
                        panic_result[prod] = [Order(prod, ba, -p)]
            data["prev_pos"] = {p: state.position.get(p, 0) for p in state.order_depths}
            data["prev_mid"] = current_mid
            return panic_result, 0, json.dumps(data, separators=(",", ":"))

        # ── Scale-in fraction ──
        fraction = min(1.0, tick / SCALE_IN_TICKS)

        # ── Counterparty signals ──
        signals = scan_counterparty_signals(state.market_trades, data, tick)

        result: Dict[str, List[Order]] = {}

        # ══════════════════════════════════════════════════════════
        #  STRATEGY 1: HYDROGEL_PACK MM
        #  (widen bid during Mark 22 sell cascades to avoid adverse fill)
        # ══════════════════════════════════════════════════════════
        h_depth = state.order_depths.get("HYDROGEL_PACK")
        h_pos = state.position.get("HYDROGEL_PACK", 0)
        if h_depth and h_depth.buy_orders and h_depth.sell_orders:
            # During Mark 22 sell cascade, temporarily widen our bid
            if signals["mark22_cascade"]:
                data["h_cascade_extra"] = 2  # extra ticks of bid widening
            else:
                data["h_cascade_extra"] = 0
            result["HYDROGEL_PACK"] = trade_hydrogel_mm(h_depth, h_pos, data)

        # ══════════════════════════════════════════════════════════
        #  STRATEGY 2: Z-SCORE MEAN REVERSION (V + ATM VOUCHERS)
        # ══════════════════════════════════════════════════════════
        v_mid = current_mid.get("VELVETFRUIT_EXTRACT")
        z = 0.0

        if v_mid is not None:
            # ── Online rolling statistics for V (Sliding Window) ──
            v_history = data.setdefault("v_history", [])
            v_history.append(v_mid)
            if len(v_history) > 10000:
                v_history.pop(0)
            
            n = len(v_history)
            v_mean_eff = sum(v_history) / n
            if n > 1:
                v_std_eff = math.sqrt(sum((x - v_mean_eff)**2 for x in v_history) / (n - 1))
            else:
                v_std_eff = 1.0

            v_target, opt_target, z = compute_z_targets(v_mid, v_mean_eff, v_std_eff, fraction)

            # ── Mark 67 spike-fade with cooldown ──
            # When M67 buys, add short bias AND suppress our own buying for 100 ticks
            if signals["mark67_buying"] and signals["mark67_volume"] > 5:
                fade_adj = -min(30, signals["mark67_volume"] * 2)
                v_target = clamp(v_target + fade_adj,
                                -LIMITS["VELVETFRUIT_EXTRACT"],
                                 LIMITS["VELVETFRUIT_EXTRACT"])

            # During M67 cooldown, don't go MORE long (the spike hasn't faded yet)
            if signals["mark67_cooldown"]:
                v_pos_now = state.position.get("VELVETFRUIT_EXTRACT", 0)
                if v_target > v_pos_now:
                    v_target = v_pos_now  # hold current, don't add long

            # ── Mark 22 cascade: don't buy V while selling wave in progress ──
            if signals["mark22_cascade"]:
                v_pos_now = state.position.get("VELVETFRUIT_EXTRACT", 0)
                if v_target > v_pos_now:
                    v_target = v_pos_now  # suppress buying during cascade

            # V orders (z-score directional)
            v_depth = state.order_depths.get("VELVETFRUIT_EXTRACT")
            v_pos = state.position.get("VELVETFRUIT_EXTRACT", 0)
            if v_depth:
                rush = abs(z) > Z_RUSH_THRESH
                z_orders = trade_zscore_product(
                    "VELVETFRUIT_EXTRACT", v_target, v_depth, v_pos, z, rush)

                # ── Mark 55 round-trip capture: overlay V MM ──
                mm_orders = trade_v_mm_overlay(v_depth, v_pos, signals, z)

                # Merge: z-score orders take priority, MM orders fill remaining room
                result["VELVETFRUIT_EXTRACT"] = z_orders + mm_orders

        # ══════════════════════════════════════════════════════════
        #  DYNAMIC OPTIONS ROUTING
        # ══════════════════════════════════════════════════════════
        if v_mid is not None:
            for symbol, depth in state.order_depths.items():
                if not symbol.startswith("VEV_"):
                    continue
                
                strike = int(symbol.split("_")[1])
                opt_pos = state.position.get(symbol, 0)
                
                if strike <= v_mid - 200:
                    # Deep ITM: Market Making around Intrinsic
                    result[symbol] = trade_deep_itm_mm(symbol, strike, v_mid, depth, opt_pos)
                elif strike >= v_mid + 200:
                    # OTM: Passive Theta Harvesting
                    result[symbol] = trade_otm_theta(symbol, depth, opt_pos)
                else:
                    # ATM: Z-Score Mean Reversion
                    rush = abs(z) > Z_RUSH_THRESH
                    atm_target = opt_target
                    if opt_pos < 0 and z > 0:  # hold-the-short ratchet
                        atm_target = min(atm_target, opt_pos)
                    elif opt_pos > 0 and z < 0:
                        atm_target = max(atm_target, opt_pos)
                    result[symbol] = trade_zscore_product(symbol, atm_target, depth, opt_pos, z, rush)

        # ── Save state ──
        data["prev_pos"] = {p: state.position.get(p, 0) for p in state.order_depths}
        data["prev_mid"] = current_mid

        # ── Diagnostic logging (every 100 ticks) ──
        if tick % 100 == 0:
            pos_str = " ".join(f"{p}={state.position.get(p,0)}" for p in ["VELVETFRUIT_EXTRACT", "HYDROGEL_PACK"])
            print(f"t={state.timestamp} z={z:.2f} mtm={mtm:.0f} dd={drawdown:.0f} {pos_str}")

        return result, 0, json.dumps(data, separators=(",", ":"))