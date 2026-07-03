"""
Prosperity Backend Bot Simulator
=================================
Reverse-engineered from 50 independent historical runs (192,000 OB ticks, 6,804 trades).

This module models the exact statistical mechanics of the Prosperity backend bots:
  - EMERALDS: 2-state OB machine pegged to 10,000
  - TOMATOES: drifting fair value with 2-regime spread model

Usage:
  from backend_simulator import EmeraldsBot, TomatoesBot

  em_bot = EmeraldsBot()
  book = em_bot.generate_book(timestamp)  # returns OrderDepth-like dict

  tm_bot = TomatoesBot(seed=42)
  book = tm_bot.generate_book(timestamp)
"""

import random
import math
from collections import defaultdict


class EmeraldsBot:
    """
    EMERALDS backend bot simulator.
    
    Observed invariants (across all 50 runs):
      - Fair value: EXACTLY 10,000 (never drifts)
      - L1 spread: 16 (97%) or 8 (3%)
      - L1 bid: 9992 or 10000
      - L1 ask: 10008 or 10000
      - L1 volume: Uniform[10, 15], bid==ask 97.2% of time
      - L2 bid: 9990, ask: 10010, volumes Uniform[10, 30]
      - Tight state lasts 1.1 ticks on average (max 3)
      - Volume regeneration: ≈1.2 units/tick net
    """
    
    FAIR_VALUE = 10000
    
    # === L1 price levels ===
    WIDE_BID = 9992
    WIDE_ASK = 10008
    
    # === L2 price levels ===
    L2_BID = 9990
    L2_ASK = 10010
    
    # === Volume bounds ===
    L1_VOL_MIN = 10
    L1_VOL_MAX = 15
    L2_VOL_MIN = 10
    L2_VOL_MAX = 30
    
    # === Tight state probability ===
    TIGHT_PROB = 0.030  # 3% of ticks
    
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.state = 'wide'
        self.tight_ticks_remaining = 0
        self.tight_direction = None  # 'bid_up' or 'ask_down'
        
        # Volume state
        self.bid_vol_1 = self.rng.randint(self.L1_VOL_MIN, self.L1_VOL_MAX)
        self.ask_vol_1 = self.bid_vol_1  # Symmetric start
        self.bid_vol_2 = self.rng.randint(self.L2_VOL_MIN, self.L2_VOL_MAX)
        self.ask_vol_2 = self.bid_vol_2
    
    def _regenerate_volume(self, current, vmin, vmax):
        """Volume changes by [-5, +10] per tick, clamped to [vmin, vmax]."""
        step = self.rng.choice([-5, -4, -3, -2, -1, 0, 0, +1, +1, +2, +3, +4, +5])
        return max(vmin, min(vmax, current + step))
    
    def step(self):
        """Advance one tick. Returns the order book state."""
        # State transition
        if self.state == 'tight':
            self.tight_ticks_remaining -= 1
            if self.tight_ticks_remaining <= 0:
                self.state = 'wide'
                self.tight_direction = None
        else:
            # Probability of entering tight state
            if self.rng.random() < self.TIGHT_PROB:
                self.state = 'tight'
                self.tight_ticks_remaining = self.rng.choices([1, 2, 3], weights=[0.85, 0.10, 0.05])[0]
                self.tight_direction = self.rng.choice(['bid_up', 'ask_down'])
        
        # Volume regeneration
        self.bid_vol_1 = self._regenerate_volume(self.bid_vol_1, self.L1_VOL_MIN, self.L1_VOL_MAX)
        self.ask_vol_1 = self._regenerate_volume(self.ask_vol_1, self.L1_VOL_MIN, self.L1_VOL_MAX)
        self.bid_vol_2 = self._regenerate_volume(self.bid_vol_2, self.L2_VOL_MIN, self.L2_VOL_MAX)
        self.ask_vol_2 = self._regenerate_volume(self.ask_vol_2, self.L2_VOL_MIN, self.L2_VOL_MAX)
        
        # Symmetric volume (97.2% of time)
        if self.rng.random() < 0.972:
            self.ask_vol_1 = self.bid_vol_1
        
        # Determine prices
        if self.state == 'tight':
            if self.tight_direction == 'bid_up':
                bid_1 = 10000
                ask_1 = 10008
            else:
                bid_1 = 9992
                ask_1 = 10000
            # L2 shifts in tight state
            bid_2 = 9992 if self.tight_direction == 'bid_up' else self.L2_BID
            ask_2 = 10008 if self.tight_direction == 'ask_down' else self.L2_ASK
        else:
            bid_1 = self.WIDE_BID
            ask_1 = self.WIDE_ASK
            bid_2 = self.L2_BID
            ask_2 = self.L2_ASK
        
        return {
            'bid_prices': [bid_1, bid_2],
            'bid_volumes': [self.bid_vol_1, self.bid_vol_2],
            'ask_prices': [ask_1, ask_2],
            'ask_volumes': [self.ask_vol_1, self.ask_vol_2],
            'mid_price': (bid_1 + ask_1) / 2,
            'spread': ask_1 - bid_1,
            'state': self.state,
        }
    
    def consume_bid(self, qty):
        """Simulate our sell order hitting their bid."""
        consumed = min(qty, self.bid_vol_1)
        self.bid_vol_1 -= consumed
        return consumed
    
    def consume_ask(self, qty):
        """Simulate our buy order hitting their ask."""
        consumed = min(qty, self.ask_vol_1)
        self.ask_vol_1 -= consumed
        return consumed


class TomatoesBot:
    """
    TOMATOES backend bot simulator.
    
    Observed invariants (across all 50 runs):
      - Fair value: drifts (~4991 mean, range 4974-5009, std 6.0)
      - L1 spread: 13-14 (93.8%) or 5-9 (6.2%)  
      - L1 volume: Uniform[5, 10], bid==ask 94.5% of time
      - L2 gap from L1: ~1.4 ticks, volumes Uniform[5, 25]
      - Tight state lasts 1.1 ticks, wide lasts 16.2 ticks
      - Volume regeneration: ≈1.2 units/tick net
      - Bid step sizes: {-7:-1,+1:+7} with ±1 being most common
      - CRITICAL: Start mid = 5006, total drift ≈ -9.5 over 200k ms
      - Autocorrelation: -0.44 at lag 1 (strong bid-ask bounce)
    """
    
    # === Initial conditions ===
    INITIAL_MID = 5006.0
    
    # === Fair value drift ===
    DRIFT_PER_TICK = -0.005  # Slight downward drift (-9.5 over 2000 ticks)
    NOISE_STD = 0.5  # Per-tick noise (calibrated to get tick vol ≈ 1.29)
    
    # === Spread regime ===
    WIDE_SPREAD_PROBS = {13: 0.534, 14: 0.466}  # Distribution within wide regime
    TIGHT_SPREAD_PROBS = {5: 0.184, 6: 0.160, 7: 0.288, 8: 0.312, 9: 0.056}
    WIDE_TO_TIGHT_PROB = 0.062  # Per-tick probability of tightening
    
    # === Volume bounds ===
    L1_VOL_MIN = 5
    L1_VOL_MAX = 10
    L2_VOL_MIN = 5
    L2_VOL_MAX = 25
    
    # === L2 gap ===
    L2_GAP = 1  # L2 is typically 1-2 ticks from L1
    
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.fair_value = self.INITIAL_MID
        self.prev_step = 0.0
        self.state = 'wide'
        self.tight_ticks_remaining = 0
        self.tight_direction = None  # 'ask_down' or 'bid_up'
        
        # Volume state
        self.bid_vol_1 = self.rng.randint(self.L1_VOL_MIN, self.L1_VOL_MAX)
        self.ask_vol_1 = self.bid_vol_1
        self.bid_vol_2 = self.rng.randint(self.L2_VOL_MIN, self.L2_VOL_MAX)
        self.ask_vol_2 = self.bid_vol_2
    
    def _regenerate_volume(self, current, vmin, vmax):
        step = self.rng.choice([-5, -4, -3, -2, -1, 0, 0, +1, +1, +2, +3, +4, +5])
        return max(vmin, min(vmax, current + step))
    
    def step(self):
        """Advance one tick. Returns the order book state."""
        
        # === 1. Fair value evolution (mean-reverting random walk) ===
        # Observed: autocorrelation of -0.44 ≈ slight bounce
        noise = self.rng.gauss(0, self.NOISE_STD)
        # Inject mean-reversion bounce: new step anti-correlates with previous
        bounce_factor = -0.44
        step = self.DRIFT_PER_TICK + noise + bounce_factor * self.prev_step
        self.fair_value += step
        self.prev_step = step
        
        # === 2. Spread regime transition ===
        if self.state == 'tight':
            self.tight_ticks_remaining -= 1
            if self.tight_ticks_remaining <= 0:
                self.state = 'wide'
                self.tight_direction = None
        else:
            if self.rng.random() < self.WIDE_TO_TIGHT_PROB:
                self.state = 'tight'
                self.tight_ticks_remaining = self.rng.choices([1, 2, 3], weights=[0.85, 0.10, 0.05])[0]
                self.tight_direction = self.rng.choice(['ask_down', 'bid_up'])
        
        # === 3. Compute prices ===
        fv_int = round(self.fair_value)
        
        if self.state == 'wide':
            spread = self.rng.choices(list(self.WIDE_SPREAD_PROBS.keys()),
                                      list(self.WIDE_SPREAD_PROBS.values()))[0]
            half = spread / 2
            bid_1 = int(fv_int - math.ceil(half))
            ask_1 = int(fv_int + math.floor(half))
            if (ask_1 - bid_1) != spread:
                ask_1 = bid_1 + spread
        else:
            spread = self.rng.choices(list(self.TIGHT_SPREAD_PROBS.keys()),
                                      list(self.TIGHT_SPREAD_PROBS.values()))[0]
            if self.tight_direction == 'ask_down':
                # Ask drops: price pressure from above
                ask_1 = int(fv_int + spread // 2 - 2)
                bid_1 = ask_1 - spread
            else:
                # Bid jumps: price pressure from below
                bid_1 = int(fv_int - spread // 2 + 2)
                ask_1 = bid_1 + spread
        
        # === 4. L2 levels ===
        bid_2 = bid_1 - self.rng.choice([1, 2])
        ask_2 = ask_1 + self.rng.choice([1, 2])
        
        # === 5. Volume regeneration ===
        self.bid_vol_1 = self._regenerate_volume(self.bid_vol_1, self.L1_VOL_MIN, self.L1_VOL_MAX)
        self.ask_vol_1 = self._regenerate_volume(self.ask_vol_1, self.L1_VOL_MIN, self.L1_VOL_MAX)
        self.bid_vol_2 = self._regenerate_volume(self.bid_vol_2, self.L2_VOL_MIN, self.L2_VOL_MAX)
        self.ask_vol_2 = self._regenerate_volume(self.ask_vol_2, self.L2_VOL_MIN, self.L2_VOL_MAX)
        
        # Symmetric (94.5% of time)
        if self.rng.random() < 0.945:
            self.ask_vol_1 = self.bid_vol_1
        
        return {
            'bid_prices': [bid_1, bid_2],
            'bid_volumes': [self.bid_vol_1, self.bid_vol_2],
            'ask_prices': [ask_1, ask_2],
            'ask_volumes': [self.ask_vol_1, self.ask_vol_2],
            'mid_price': (bid_1 + ask_1) / 2,
            'fair_value': self.fair_value,
            'spread': ask_1 - bid_1,
            'state': self.state,
            'tight_direction': self.tight_direction,
        }
    
    def consume_bid(self, qty):
        consumed = min(qty, self.bid_vol_1)
        self.bid_vol_1 -= consumed
        return consumed
    
    def consume_ask(self, qty):
        consumed = min(qty, self.ask_vol_1)
        self.ask_vol_1 -= consumed
        return consumed


# =============================================================================
# Validation: Compare simulated statistics against actual backend data
# =============================================================================
def validate_emeralds(n_ticks=2000, n_runs=50):
    """Run the EMERALDS simulator and compare against known statistics."""
    spreads = []
    volumes = []
    mids = []
    
    for run in range(n_runs):
        bot = EmeraldsBot(seed=run)
        for _ in range(n_ticks):
            book = bot.step()
            spreads.append(book['spread'])
            volumes.append(book['bid_volumes'][0])
            mids.append(book['mid_price'])
    
    import statistics
    n = len(spreads)
    tight_pct = sum(1 for s in spreads if s == 8) / n * 100
    mean_vol = statistics.mean(volumes)
    mean_mid = statistics.mean(mids)
    
    print("=== EMERALDS Simulator Validation ===")
    print(f"  Spread=16: {sum(1 for s in spreads if s==16)/n*100:.1f}% (target: 97.0%)")
    print(f"  Spread=8:  {tight_pct:.1f}% (target: 3.0%)")
    print(f"  Mean Vol L1: {mean_vol:.1f} (target: 12.4)")
    print(f"  Mean Mid: {mean_mid:.2f} (target: 10000.00)")


def validate_tomatoes(n_ticks=2000, n_runs=50):
    """Run the TOMATOES simulator and compare against known statistics."""
    spreads = []
    volumes = []
    mids = []
    returns = []
    prev_mid = None
    
    for run in range(n_runs):
        bot = TomatoesBot(seed=run)
        prev_mid = None
        for _ in range(n_ticks):
            book = bot.step()
            spreads.append(book['spread'])
            volumes.append(book['bid_volumes'][0])
            mids.append(book['mid_price'])
            if prev_mid is not None:
                returns.append(book['mid_price'] - prev_mid)
            prev_mid = book['mid_price']
    
    import statistics
    n = len(spreads)
    wide_pct = sum(1 for s in spreads if s >= 13) / n * 100
    tight_pct = sum(1 for s in spreads if s <= 9) / n * 100
    mean_vol = statistics.mean(volumes)
    mean_mid = statistics.mean(mids)
    ret_std = statistics.stdev(returns) if len(returns) > 1 else 0
    
    # Autocorrelation lag 1
    if len(returns) > 2:
        r1 = returns[:-1]
        r2 = returns[1:]
        mean_r = statistics.mean(returns)
        num = sum((a - mean_r) * (b - mean_r) for a, b in zip(r1, r2))
        den = sum((r - mean_r)**2 for r in returns)
        autocorr = num / den if den > 0 else 0
    else:
        autocorr = 0
    
    print("=== TOMATOES Simulator Validation ===")
    print(f"  Wide (13-14): {wide_pct:.1f}% (target: 93.8%)")
    print(f"  Tight (5-9):  {tight_pct:.1f}% (target: 6.2%)")
    print(f"  Mean Vol L1: {mean_vol:.1f} (target: 7.5)")
    print(f"  Mean Mid: {mean_mid:.2f} (target: 4991.05)")
    print(f"  Tick Vol: {ret_std:.2f} (target: 1.29)")
    print(f"  Autocorr lag1: {autocorr:.4f} (target: -0.44)")


if __name__ == "__main__":
    validate_emeralds()
    print()
    validate_tomatoes()
