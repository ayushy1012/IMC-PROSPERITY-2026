import pandas as pd
import numpy as np
import glob
import matplotlib.pyplot as plt

def analyze_assets():
    # Load all 3 days
    files = glob.glob('PAST_DATA_ROUND1/prices_round_1_day_*.csv')
    df = pd.concat([pd.read_csv(f, sep=';') for f in files]).sort_values(['day', 'timestamp'])
    
    # Analyze OSMIUM
    osmium = df[df['product'] == 'ASH_COATED_OSMIUM'].copy()
    osmium['mid'] = (osmium['bid_price_1'] + osmium['ask_price_1']) / 2
    osmium['microprice'] = (osmium['bid_price_1'] * osmium['ask_volume_1'] + 
                            osmium['ask_price_1'] * osmium['bid_volume_1']) / (osmium['ask_volume_1'] + osmium['bid_volume_1'])
    
    osmium['returns_1'] = osmium['mid'].shift(-1) - osmium['mid']
    
    print("--- ASH_COATED_OSMIUM ---")
    print(f"Mean Mid: {osmium['mid'].mean():.2f}")
    print(f"Mid Std Dev: {osmium['mid'].std():.2f}")
    
    # Autocorrelation of returns
    rets = osmium['mid'].diff().dropna()
    print(f"Lag 1 Autocorr of Returns: {rets.autocorr(1):.4f}")
    
    # Correlation between microprice offset and next-tick mid return
    osmium['micro_offset'] = osmium['microprice'] - osmium['mid']
    corr = osmium[['micro_offset', 'returns_1']].corr().iloc[0,1]
    print(f"Correlation (Microprice Offset -> Next Tick Return): {corr:.4f}")

    # Analyze PEPPER_ROOT
    pepper = df[df['product'] == 'INTARIAN_PEPPER_ROOT'].copy()
    pepper['mid'] = (pepper['bid_price_1'] + pepper['ask_price_1']) / 2
    pepper['microprice'] = (pepper['bid_price_1'] * pepper['ask_volume_1'] + 
                            pepper['ask_price_1'] * pepper['bid_volume_1']) / (pepper['ask_volume_1'] + pepper['bid_volume_1'])
    pepper['returns_1'] = pepper['mid'].shift(-1) - pepper['mid']
    
    print("\n--- INTARIAN_PEPPER_ROOT ---")
    print(f"Mean Mid: {pepper['mid'].mean():.2f}")
    print(f"Mid Std Dev: {pepper['mid'].std():.2f}")
    
    pepper['micro_offset'] = pepper['microprice'] - pepper['mid']
    corr_p = pepper[['micro_offset', 'returns_1']].corr().iloc[0,1]
    print(f"Correlation (Microprice Offset -> Next Tick Return): {corr_p:.4f}")

    # Check for long-term trending in PEPPER (diff over 10 ticks)
    pepper['returns_10'] = pepper['mid'].shift(-10) - pepper['mid']
    # EMA signal imitation
    pepper['ema_36'] = pepper['mid'].ewm(span=36, adjust=False).mean()
    pepper['ema_offset'] = pepper['mid'] - pepper['ema_36']
    corr_ema = pepper[['ema_offset', 'returns_10']].corr().iloc[0,1]
    print(f"Correlation (EMA Offset -> 10-Tick Return): {corr_ema:.4f}")

if __name__ == '__main__':
    analyze_assets()
