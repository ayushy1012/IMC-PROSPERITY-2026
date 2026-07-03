import math
from scipy.stats import norm
from scipy.optimize import root_scalar

# 1. Competitor Distribution Assumptions
AFK_RATE = 0.15
MEAN_BID = 33.0
STD_DEV = 12.0

# 2. Speed Multiplier Function (y)
def expected_multiplier(x):
    if x <= 0: return 0.1
    # Calculate what % of active players bid less than x
    active_percentile = norm.cdf(x, loc=MEAN_BID, scale=STD_DEV)
    # Combine with the 15% who bid 0
    p_less_than_x = AFK_RATE + ((1 - AFK_RATE) * active_percentile)
    return 0.1 + (0.8 * p_less_than_x)

# 3. Deterministic R & S Optimizer
def optimize_r_s(x):
    # Solve the partial derivative equation for Research (r)
    def eq(r): return (100 - x - r) / (1 + r) - math.log(1 + r)
    res = root_scalar(eq, bracket=[0, 100-x], method='brentq')
    opt_r = res.root
    opt_s = 100 - x - opt_r
    return opt_r, opt_s

# 4. Global Maximum Search
max_net_pnl = 0
best_alloc = (0, 0, 0) # r, s, x

print(f"{'Speed (x)':<10} | {'Res (r)':<10} | {'Scale (s)':<10} | {'Mult (y)':<10} | {'Net PnL'}")
print("-" * 65)

for x in range(10, 60): # Search the relevant range
    y = expected_multiplier(x)
    r, s = optimize_r_s(x)
    
    # Calculate PnL
    research_val = 200000 * (math.log(1 + r) / math.log(101))
    scale_val = 7 * (s / 100)
    gross_pnl = research_val * scale_val * y
    net_pnl = gross_pnl - 50000
    
    if net_pnl > max_net_pnl:
        max_net_pnl = net_pnl
        best_alloc = (r, s, x, y)
        
    if x % 10 == 0: # Print checkpoints
        print(f"{x:<10.1f} | {r:<10.1f} | {s:<10.1f} | {y:<10.3f} | {net_pnl:,.0f}")

print("-" * 65)
print(f"OPTIMAL ALLOCATION: Speed: {best_alloc[2]}%, Research: {best_alloc[0]:.1f}%, Scale: {best_alloc[1]:.1f}%")
print(f"EXPECTED NET PNL: {max_net_pnl:,.0f} XIRECs")
