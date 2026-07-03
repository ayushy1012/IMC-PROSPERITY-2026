"""
Manual Trading Auction – Brute Force Optimizer
================================================
Tries every possible (price, quantity) combination for both
Dryland Flax and Ember Mushroom to find the profit-maximizing order.

Usage:
    python3 Manual_Trading/bruteforce_auction.py

Modify the order books below if they change on the website.
"""

# ══════════════════════════════════════════════════════════════════════
#  ORDER BOOKS — Update these if the website order book changes
# ══════════════════════════════════════════════════════════════════════

# Format: list of (price, volume) tuples

FLAX_BIDS = [          # People wanting to BUY Flax from you
    (30, 30000),
    (29, 5000),
    (28, 12000),
    (27, 28000),
]
FLAX_ASKS = [          # People wanting to SELL Flax to you
    (28, 40000),
    (31, 20000),
    (32, 20000),
    (33, 30000),
]
FLAX_BUYBACK = 30      # Guild buys at this price
FLAX_FEE = 0.0         # No fee

MUSH_BIDS = [          # People wanting to BUY Mushrooms from you
    (20, 43000),
    (19, 17000),
    (18, 6000),
    (17, 5000),
    (16, 10000),
    (15, 5000),
    (14, 10000),
    (13, 7000),
]
MUSH_ASKS = [          # People wanting to SELL Mushrooms to you
    (12, 20000),
    (13, 25000),
    (14, 35000),
    (15, 6000),
    (16, 5000),
    (17, 0),
    (18, 10000),
    (19, 12000),
]
MUSH_BUYBACK = 20      # Guild buys at this price
MUSH_FEE = 0.10        # Fee per unit


# ══════════════════════════════════════════════════════════════════════
#  AUCTION ENGINE
# ══════════════════════════════════════════════════════════════════════

def find_clearing_price(bids, asks):
    """
    Find the clearing price that maximizes traded volume.
    Ties broken by higher price.
    Returns (clearing_price, max_volume).
    """
    all_prices = sorted(set(p for p, _ in bids + asks))
    best_vol = -1
    best_price = -1

    for P in all_prices:
        cum_bid = sum(v for p, v in bids if p >= P)
        cum_ask = sum(v for p, v in asks if p <= P)
        traded = min(cum_bid, cum_ask)
        if traded > best_vol or (traded == best_vol and P > best_price):
            best_vol = traded
            best_price = P

    return best_price, best_vol


def compute_our_fill(existing_bids, our_price, our_qty, asks, clearing):
    """
    Compute how many units WE get filled at the clearing price.
    We are LAST in time priority at our price level.
    """
    if our_price < clearing:
        return 0  # Our bid is below clearing, no fill

    # Total supply available
    supply = sum(v for p, v in asks if p <= clearing)

    # Build fill queue: (price, volume, is_us)
    # Higher price = higher priority. Same price: existing before us.
    queue = []
    for p, v in existing_bids:
        if p >= clearing:
            queue.append((p, v, False))
    if our_price >= clearing:
        queue.append((our_price, our_qty, True))

    # Sort: descending price, existing before us at same price
    queue.sort(key=lambda x: (-x[0], x[2]))

    remaining = supply
    our_fill = 0
    for price, vol, is_us in queue:
        fill = min(vol, remaining)
        if is_us:
            our_fill = fill
        remaining -= fill
        if remaining <= 0:
            break

    return our_fill


def simulate_order(existing_bids, existing_asks, our_price, our_qty, buyback, fee):
    """
    Simulate placing a BID order in the auction.
    Returns (clearing_price, our_fill, profit).
    """
    # Add our bid to the book
    all_bids = existing_bids + [(our_price, our_qty)]

    # Find clearing price with our order included
    clearing, total_vol = find_clearing_price(all_bids, existing_asks)

    # Compute our fill
    our_fill = compute_our_fill(existing_bids, our_price, our_qty, existing_asks, clearing)

    # Profit: buy at clearing, sell to guild at buyback, minus fees
    profit = (buyback - fee - clearing) * our_fill

    return clearing, our_fill, profit


# ══════════════════════════════════════════════════════════════════════
#  BRUTE FORCE SEARCH
# ══════════════════════════════════════════════════════════════════════

def bruteforce(name, existing_bids, existing_asks, buyback, fee,
               price_range, qty_range):
    """
    Try every (price, qty) combination. Return sorted results.
    """
    results = []
    for price in price_range:
        for qty in qty_range:
            clearing, fill, profit = simulate_order(
                existing_bids, existing_asks, price, qty, buyback, fee
            )
            results.append({
                'price': price,
                'qty': qty,
                'clearing': clearing,
                'fill': fill,
                'profit': profit,
            })

    results.sort(key=lambda x: -x['profit'])
    return results


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  AUCTION BRUTE FORCE OPTIMIZER")
    print("=" * 70)

    # ── FLAX ──────────────────────────────────────────────────────────
    print(f"\n  🌾 DRYLAND FLAX (Buyback={FLAX_BUYBACK}, Fee={FLAX_FEE})")
    print(f"  Searching prices 1–50, quantities 1–200,000...")

    flax_results = bruteforce(
        "FLAX", FLAX_BIDS, FLAX_ASKS, FLAX_BUYBACK, FLAX_FEE,
        price_range=range(1, 51),
        qty_range=list(range(1, 101)) +
                  list(range(100, 1001, 100)) +
                  list(range(1000, 10001, 1000)) +
                  list(range(10000, 50001, 1000)) +
                  list(range(50000, 200001, 5000)),
    )

    # Top 20
    print(f"\n  {'Rank':>4} {'Price':>5} {'Qty':>8} {'Clear':>5} {'Fill':>8} {'Profit':>12}")
    print(f"  {'─'*4} {'─'*5} {'─'*8} {'─'*5} {'─'*8} {'─'*12}")
    seen = set()
    count = 0
    for r in flax_results:
        key = (r['price'], r['clearing'], r['fill'], r['profit'])
        if key in seen:
            continue
        seen.add(key)
        count += 1
        if count > 20:
            break
        marker = " ◄ BEST" if count == 1 else ""
        print(f"  {count:>4} {r['price']:>5} {r['qty']:>8,} {r['clearing']:>5} "
              f"{r['fill']:>8,} ${r['profit']:>11,.0f}{marker}")

    best_flax = flax_results[0]

    # ── MUSHROOM ──────────────────────────────────────────────────────
    print(f"\n  🍄 EMBER MUSHROOM (Buyback={MUSH_BUYBACK}, Fee={MUSH_FEE})")
    print(f"  Searching prices 1–30, quantities 1–200,000...")

    mush_results = bruteforce(
        "MUSHROOM", MUSH_BIDS, MUSH_ASKS, MUSH_BUYBACK, MUSH_FEE,
        price_range=range(1, 31),
        qty_range=list(range(1, 101)) +
                  list(range(100, 1001, 100)) +
                  list(range(1000, 10001, 1000)) +
                  list(range(10000, 50001, 1000)) +
                  list(range(50000, 200001, 5000)),
    )

    print(f"\n  {'Rank':>4} {'Price':>5} {'Qty':>8} {'Clear':>5} {'Fill':>8} {'Profit':>12}")
    print(f"  {'─'*4} {'─'*5} {'─'*8} {'─'*5} {'─'*8} {'─'*12}")
    seen = set()
    count = 0
    for r in mush_results:
        key = (r['price'], r['clearing'], r['fill'], r['profit'])
        if key in seen:
            continue
        seen.add(key)
        count += 1
        if count > 20:
            break
        marker = " ◄ BEST" if count == 1 else ""
        print(f"  {count:>4} {r['price']:>5} {r['qty']:>8,} {r['clearing']:>5} "
              f"{r['fill']:>8,} ${r['profit']:>11,.0f}{marker}")

    best_mush = mush_results[0]

    # ── FINAL ANSWER ──────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  💰 OPTIMAL ORDERS")
    print(f"{'='*70}")
    print(f"  🌾 FLAX:      BID price={best_flax['price']}, qty={best_flax['qty']:,}")
    print(f"                Clearing={best_flax['clearing']}, Fill={best_flax['fill']:,}, "
          f"Profit=${best_flax['profit']:,.0f}")
    print(f"  🍄 MUSHROOM:  BID price={best_mush['price']}, qty={best_mush['qty']:,}")
    print(f"                Clearing={best_mush['clearing']}, Fill={best_mush['fill']:,}, "
          f"Profit=${best_mush['profit']:,.0f}")
    print(f"  ──────────────────────────────────────────")
    print(f"  💰 TOTAL PROFIT: ${best_flax['profit'] + best_mush['profit']:,.0f}")
    print(f"{'='*70}")
