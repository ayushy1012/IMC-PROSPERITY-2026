"""Gridsearch IPR parameters through quote_with_target to maximize PnL."""
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
        [".venv/bin/prosperity4bt", TRADER_PATH, "1"],
        capture_output=True, text=True
    )
    ash = 0
    ipr = 0
    for line in res.stdout.splitlines():
        if line.startswith("ASH_COATED_OSMIUM:"):
            raw = line.split(":")[-1].strip().replace(",", "")
            try: ash += float(raw)
            except: pass
        elif line.startswith("INTARIAN_PEPPER_ROOT:"):
            raw = line.split(":")[-1].strip().replace(",", "")
            try: ipr += float(raw)
            except: pass
    if ipr == 0: ipr = -999999
    if ash == 0: ash = -999999
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
    
    # Coarse grid to avoid overfitting and excessive run time
    param_grid = {
        "IPR_BASE_TARGET": [12.0, 24.15],
        "IPR_TREND_TARGET_W": [40.0, 60.0],
        "IPR_TAKE_MARGIN": [3.0, 4.09, 5.5],
        "IPR_RESERVATION_W": [12.0, 16.9, 22.0],
    }
    
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(itertools.product(*values))
    
    best_ipr = -999999
    best_total = -999999
    best_params = {}
    
    print(f"----- IPR GRIDSEARCH ({len(combinations)} combos) -----")
    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        write_trader(modify_code(original_code, params))
        ash, ipr = run_simulation()
        total = ash + ipr
        
        # We optimize for IPR directly
        if ipr > best_ipr:
            best_ipr = ipr
            best_total = total
            best_params = params
            print(f"[{i+1}/{len(combinations)}] 🚀 IPR={ipr:.0f} ASH={ash:.0f} | {params}")
        elif i % 20 == 0:
            print(f"[{i+1}/{len(combinations)}] IPR={ipr:.0f} ASH={ash:.0f}")
            
    print(f"\n================ BEST ================")
    print(f"IPR PnL: {best_ipr:.0f}  Total: {best_total:.0f}")
    for k, v in best_params.items():
        print(f"  {k} = {v}")
    
    write_trader(modify_code(original_code, best_params))
    print("Committed best params to trader.py")

if __name__ == '__main__':
    gridsearch()
