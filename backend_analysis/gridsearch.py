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
        [".venv/bin/python3", "Backtester/accurate_backtester.py", TRADER_PATH, "logs/108259.log"],
        capture_output=True, text=True
    )
    val = -999999
    for line in res.stdout.splitlines():
        if "ASH_COATED_OSMIUM:" in line:
            raw = line.split(":")[-1].strip().replace(",", "")
            try: val = float(raw)
            except: pass
            break
    return val

def modify_code(code, params):
    modified = code
    for k, v in params.items():
        if k == "SWITCH_TIMESTAMP": 
            modified = re.sub(rf"({k}\s*=\s*)[-0-9.]+", rf"\g<1>{int(v)}", modified, count=1)
        else:
            modified = re.sub(rf"({k}\s*=\s*)[-0-9.]+", rf"\g<1>{v:.4f}", modified, count=1)
    return modified

def gridsearch():
    print("Backing up trader.py...")
    shutil.copy(TRADER_PATH, BACKUP_PATH)
    
    original_code = read_trader()
    
    # Negative and positive
    os_micro_w = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]
    os_take_m = [0.0, 0.2, 0.4, 0.6]

    combinations = list(itertools.product(os_micro_w, os_take_m))
    
    best_pnl = -999999
    best_params = {}
    
    print(f"----- OPTIMIZING OSMIUM ({len(combinations)} COMBINATIONS) -----")
    for i, (mw, tm) in enumerate(combinations):
        params = {
            "SWITCH_TIMESTAMP": 99999,
            "OS_MICRO_W": mw,
            "OS_TAKE_MARGIN": tm,
        }
        write_trader(modify_code(original_code, params))
        pnl = run_simulation()
        
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = params
            print(f"[{i+1}/{len(combinations)}] 🚀 NEW OSMIUM BEST: {pnl:.0f} | {params}")

    print("\n================ FINAL BEST OSMIUM ================")
    print(f"Osmium PnL: {best_pnl}")
    for k, v in best_params.items():
        print(f"{k} = {v:.4f}")
        
    write_trader(modify_code(original_code, best_params))
    print("Successfully committed to Trader/trader.py!")

if __name__ == '__main__':
    gridsearch()
