import pandas as pd
import numpy as np
from scipy.stats import norm
import os

def norm_cdf(x):
    return norm.cdf(x)

def bs_call_iv(S, K, T, r, C_target):
    # simple binary search for IV
    low = 0.001
    high = 2.0
    for _ in range(30):
        sigma = (low + high) / 2
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        C = S * norm_cdf(d1) - K * np.exp(-r * T) * norm_cdf(d2)
        if C < C_target:
            low = sigma
        else:
            high = sigma
    return (low + high) / 2

df = pd.read_csv('.accurate_backtester_cache/369917_round3/round3/prices_round_3_day_2.csv', sep=';')
df_vev = df[df['product'] == 'VELVETFRUIT_EXTRACT'].set_index('timestamp')

records = []
for t, group in df.groupby('timestamp'):
    if t not in df_vev.index: continue
    S = df_vev.loc[t, 'mid_price']
    for _, row in group.iterrows():
        p = row['product']
        if p.startswith('VEV_'):
            K = float(p.split('_')[1])
            C = row['mid_price']
            if pd.isna(C): continue
            iv = bs_call_iv(S, K, 5/252.0, 0.0, C) # Wait, is T=5 or 5/252? The platform uses T in years? Let's check how BS is implemented in Trader/366046.py
            records.append({'timestamp': t, 'K': K, 'S': S, 'moneyness': K/S, 'IV': iv})

res = pd.DataFrame(records)
coeffs = np.polyfit(res['moneyness'], res['IV'], 2)
print("Fitted Parabola (ax^2 + bx + c):", coeffs)
