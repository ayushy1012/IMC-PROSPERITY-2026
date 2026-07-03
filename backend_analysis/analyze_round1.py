import pandas as pd
import glob
import numpy as np

def analyze_patterns():
    files = glob.glob('PAST_DATA_ROUND1/prices_*.csv')
    df_list = [pd.read_csv(f, sep=';') for f in files]
    df = pd.concat(df_list).sort_values(['day', 'timestamp']).reset_index(drop=True)
    
    ash_df = df[df['product'] == 'ASH_COATED_OSMIUM'].copy()
    ash_df['mid_price'] = (ash_df['bid_price_1'] + ash_df['ask_price_1']) / 2
    
    root_df = df[df['product'] == 'INTARIAN_PEPPER_ROOT'].copy()
    root_df['mid_price'] = (root_df['bid_price_1'] + root_df['ask_price_1']) / 2
    
    # Check for mean-reverting behavior or autocorrelation
    ash_returns = ash_df['mid_price'].diff().dropna()
    root_returns = root_df['mid_price'].diff().dropna()
    
    print("ASH_COATED_OSMIUM Autocorrelation (Lags 1-5):")
    for lag in range(1, 6):
        print(f"Lag {lag}: {ash_returns.autocorr(lag):.4f}")
    
    print("INTARIAN Autocorrelation (Lags 1-5):")
    for lag in range(1, 6):
        print(f"Lag {lag}: {root_returns.autocorr(lag):.4f}")

if __name__ == '__main__':
    analyze_patterns()
