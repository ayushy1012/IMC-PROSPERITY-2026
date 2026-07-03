import pandas as pd
import glob
import matplotlib.pyplot as plt

def main():
    files = glob.glob('PAST_DATA_ROUND1/prices_*.csv')
    df_list = []
    for f in files:
        df_list.append(pd.read_csv(f, sep=';'))
    df = pd.concat(df_list).sort_values(['day', 'timestamp'])
    
    # Filter for new products
    df = df[df['product'].isin(['ASH_COATED_OSMIUM', 'INTARIAN_PEPPER_ROOT'])]
    
    for prod in df['product'].unique():
        prod_df = df[df['product'] == prod].copy()
        
        # Calculate mid price
        prod_df['mid_price'] = (prod_df['bid_price_1'] + prod_df['ask_price_1']) / 2
        prod_df['spread'] = prod_df['ask_price_1'] - prod_df['bid_price_1']
        
        # Plot price out to artifact
        plt.figure(figsize=(12, 6))
        plt.plot(prod_df['timestamp'] + prod_df['day'] * 1000000, prod_df['mid_price'], label='Mid Price')
        plt.title(f'{prod} Price History')
        plt.legend()
        plt.savefig(f'/Users/dmitt/.gemini/antigravity/brain/9fdfa8e0-d44f-42a8-823b-774cd5c09773/{prod}_price.png')
        plt.close()

        print(f"--- {prod} ---")
        print(f"Mean Mid: {prod_df['mid_price'].mean():.2f}")
        print(f"Std Dev:  {prod_df['mid_price'].std():.2f}")
        print(f"Min/Max Spread: {prod_df['spread'].min()} / {prod_df['spread'].max()}")
        print(f"Mean Spread: {prod_df['spread'].mean():.2f}")

if __name__ == '__main__':
    main()
