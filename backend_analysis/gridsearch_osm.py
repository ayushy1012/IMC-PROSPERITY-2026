"""Gridsearch OSMIUM parameters through quote_with_target to maximize PnL."""
import subprocess
import itertools
import re
import shutil

TRADER_PATH = "Trader/trader.py"
BACKUP_PATH = "Trader/trader.py.bak"

def read_trader():
    with open(TRADER_PATH, 'r') as f:
        return f.read()

def write_trader(content):
    with open(TRADER_PATH, 'w') as f:
        f.write(content)

def run_simulation():
    res = subprocess.run(
        [".venv/bin/python3", "Backtester/accurate_backtester.py", TRADER_PATH, "logs/113222.log"],
        capture_output=True, text=True
    )
    ash = -999999
    ipr = -999999
    for line in res.stdout.splitlines():
        if "ASH_COATED_OSMIUM:" in line:
            raw = line.split(":")[-1].strip().replace(",", "")
            try: ash = float(raw)
            except: pass
        elif "INTARIAN_PEPPER_ROOT:" in line:
            raw = line.split(":")[-1].strip().replace(",", "")
            try: ipr = float(raw)
            except: pass
    return ash, ipr

def modify_code(code, params):
    modified = code
    for k, v in params.items():
        modified = re.sub(rf"({k}\s*=\s*)[-0-9.]+", rf"\g<1>{v:.4f}", modified, count=1)
    return modified

def gridsearch():
    print("Backing up trader.py...")
    shutil.copy(TRADER_PATH, BACKUP_PATH)
    original_code = read_trader()
    
    # Parameters to search
    param_grid = {
        "OSM_HALF_SPREAD": [0.5, 1.0, 1.5, 2.0],
        "OSM_RESERVATION_W": [0.0, 1.0, 2.5, 5.0],
        "OSM_BASE_SIZE": [20, 24, 28],
        "OSM_SUPPRESS_THRESHOLD": [50, 60, 70],
    }
    
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(itertools.product(*values))
    
    best_ash = -999999
    best_total = -999999
    best_params = {}
    
    print(f"----- OSMIUM GRIDSEARCH ({len(combinations)} combos) -----")
    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        write_trader(modify_code(original_code, params))
        ash, ipr = run_simulation()
        total = ash + ipr
        
        if ash > best_ash:
            best_ash = ash
            best_total = total
            best_params = params
            print(f"[{i+1}/{len(combinations)}] 🚀 ASH={ash:.0f} IPR={ipr:.0f} T={total:.0f} | {params}")
    
    print(f"\n================ BEST ================")
    print(f"ASH PnL: {best_ash:.0f}  Total: {best_total:.0f}")
    for k, v in best_params.items():
        print(f"  {k} = {v}")
    
    write_trader(modify_code(original_code, best_params))
    print("Committed best params to trader.py")

if __name__ == '__main__':
    gridsearch()
