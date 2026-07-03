import json

log_file = "logs/113222.log"
pnl_history = {} # product -> list of pnls at each timestamp
trades_history = {}

with open(log_file, "r") as f:
    for line in f:
        # PnL isn't directly in the log if it is print log?
        # Let's check format of log.
        if "Sandbox logs:" in line:
            break

# The Prosperity logs typically have a format like Trade History or something. Let's see logs/113222.log directly.
