import numpy as np

def run_simulation():
    np.random.seed(42)

    S0 = 50.0
    vol = 2.51
    days_per_year = 252
    steps_per_day = 4
    total_steps = 15 * steps_per_day  # 60 steps
    dt = 1.0 / (days_per_year * steps_per_day)

    n_paths_total = 20_000_000
    chunk_size = 2_000_000

    drift = -0.5 * vol**2 * dt
    diffusion = vol * np.sqrt(dt)

    sum_S_60 = 0
    sum_P_50_3w = 0
    sum_C_50_3w = 0
    sum_P_35_3w = 0
    sum_P_40_3w = 0
    sum_P_45_3w = 0
    sum_C_60_3w = 0
    sum_P_50_2w = 0
    sum_C_50_2w = 0
    sum_chooser = 0
    sum_binary = 0
    sum_ko = 0

    for i in range(n_paths_total // chunk_size):
        Z = np.random.randn(chunk_size // 2, total_steps)
        Z = np.concatenate((Z, -Z), axis=0)

        log_rets = drift + diffusion * Z
        log_S = np.zeros((chunk_size, total_steps + 1))
        log_S[:, 0] = np.log(S0)
        log_S[:, 1:] = np.log(S0) + np.cumsum(log_rets, axis=1)

        S = np.exp(log_S)

        S_40 = S[:, 40]
        S_60 = S[:, 60]

        sum_S_60 += np.sum(S_60)
        sum_P_50_3w += np.sum(np.maximum(0, 50 - S_60))
        sum_C_50_3w += np.sum(np.maximum(0, S_60 - 50))
        sum_P_35_3w += np.sum(np.maximum(0, 35 - S_60))
        sum_P_40_3w += np.sum(np.maximum(0, 40 - S_60))
        sum_P_45_3w += np.sum(np.maximum(0, 45 - S_60))
        sum_C_60_3w += np.sum(np.maximum(0, S_60 - 60))
        sum_P_50_2w += np.sum(np.maximum(0, 50 - S_40))
        sum_C_50_2w += np.sum(np.maximum(0, S_40 - 50))

        chooser_payoff = np.where(S_40 > 50, np.maximum(0, S_60 - 50), np.maximum(0, 50 - S_60))
        sum_chooser += np.sum(chooser_payoff)

        binary_put = np.where(S_60 < 40, 10.0, 0.0)
        sum_binary += np.sum(binary_put)

        min_S = np.min(S, axis=1)
        ko_put = np.where(min_S < 35, 0.0, np.maximum(0, 45 - S_60))
        sum_ko += np.sum(ko_put)

    fair_values = {
        'AC': sum_S_60 / n_paths_total,
        'AC_50_P': sum_P_50_3w / n_paths_total,
        'AC_50_C': sum_C_50_3w / n_paths_total,
        'AC_35_P': sum_P_35_3w / n_paths_total,
        'AC_40_P': sum_P_40_3w / n_paths_total,
        'AC_45_P': sum_P_45_3w / n_paths_total,
        'AC_60_C': sum_C_60_3w / n_paths_total,
        'AC_50_P_2': sum_P_50_2w / n_paths_total,
        'AC_50_C_2': sum_C_50_2w / n_paths_total,
        'AC_50_CO': sum_chooser / n_paths_total,
        'AC_40_BP': sum_binary / n_paths_total,
        'AC_45_KO': sum_ko / n_paths_total
    }

    market = {
        'AC': (49.975, 50.025, 200),
        'AC_50_P': (12.00, 12.05, 50),
        'AC_50_C': (12.00, 12.05, 50),
        'AC_35_P': (4.33, 4.35, 50),
        'AC_40_P': (6.50, 6.55, 50),
        'AC_45_P': (9.05, 9.10, 50),
        'AC_60_C': (8.80, 8.85, 50),
        'AC_50_P_2': (9.70, 9.75, 50),
        'AC_50_C_2': (9.70, 9.75, 50),
        'AC_50_CO': (22.20, 22.30, 50),
        'AC_40_BP': (5.00, 5.10, 50),
        'AC_45_KO': (0.15, 0.175, 500)
    }

    print("Results:")
    print(f"{'Product':<12} {'Fair Value':<12} {'Bid':<8} {'Ask':<8} {'Action':<6} {'Qty':<5} {'Edge/Unit':<12} {'Total EV':<10}")

    total_ev = 0
    for prod, (bid, ask, vol) in market.items():
        fv = fair_values[prod]
        edge_buy = fv - ask
        edge_sell = bid - fv
        
        action = "HOLD"
        qty = 0
        edge = 0.0
        
        if edge_buy > 0 and edge_buy > edge_sell:
            action = "BUY"
            qty = vol
            edge = edge_buy
        elif edge_sell > 0:
            action = "SELL"
            qty = vol
            edge = edge_sell
            
        tot_edge = qty * edge * 3000  # Size is 3000
        total_ev += tot_edge
        
        print(f"{prod:<12} {fv:<12.4f} {bid:<8.3f} {ask:<8.3f} {action:<6} {qty:<5} {edge:<12.4f} {tot_edge:<10.2f}")

    print(f"\nTotal Expected Value (x3000): {total_ev:.2f}")

if __name__ == '__main__':
    run_simulation()
