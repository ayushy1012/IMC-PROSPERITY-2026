"""Gridsearch new quant parameters (TFI, VOL) via accurate_backtester to maximize PnL."""
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
        [".venv/bin/python3", "Backtester/accurate_backtester.py", TRADER_PATH, "logs/115554.log", "--official-mode", "reproduce"],
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
            
    # Also parse from error output if it accidentally went there, but usually it's in stdout.
    
    if ipr == 0 and ash == 0:
        return -999999, -999999
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
    
    # Coarse grid to avoid overfitting
    param_grid = {
        "OSM_TFI_FAIR_W": [0.0, 0.5, 1.5],
        "OSM_TFI_TARGET_W": [0.0, 0.5],
        "OSM_VOL_MARGIN_W": [0.0, 0.5, 1.0],
        
        "IPR_TFI_FAIR_W": [0.0, 1.5, 4.0],
        "IPR_TFI_TARGET_W": [0.0, 1.5],
        "IPR_VOL_MARGIN_W": [0.0, 1.0, 3.0],
    }
    
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(itertools.product(*values))
    
    best_total = -999999
    best_params = {}
    
    print(f"----- QUANT GRIDSEARCH ({len(combinations)} combos) -----")
    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        write_trader(modify_code(original_code, params))
        ash, ipr = run_simulation()
        total = ash + ipr
        
        if total > best_total:
            best_total = total
            best_params = params
            print(f"[{i+1}/{len(combinations)}] 🚀 TOTAL={total:.0f} (IPR={ipr:.0f} ASH={ash:.0f}) | {params}")
        elif i % 20 == 0:
            print(f"[{i+1}/{len(combinations)}] TOTAL={total:.0f}")
            
    print(f"\n================ BEST ================")
    print(f"Total PnL: {best_total:.0f}")
    for k, v in best_params.items():
        print(f"  {k} = {v}")
    
    write_trader(modify_code(original_code, best_params))
    print("Committed best params to trader.py")

if __name__ == '__main__':
    gridsearch()
