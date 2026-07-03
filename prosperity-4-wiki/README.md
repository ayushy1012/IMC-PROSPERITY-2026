# IMC Prosperity 4 Wiki Notes & Cheatsheet

This README contains crucial technical notes, competition format details, and limitations pulled from the Prosperity 4 Wiki documentation. It serves as our rapid-reference guide as we build our trading algorithms.

## Competition Format
* **Challenge Structure:** 5 Rounds + 1 Intermission + Tutorial Round.
  * Round 1 & 2: 72 hours each. (Starts April 14, 2026 as per schedule)
  * Round 3, 4 & 5: 48 hours each. 
* **Evaluation:** At the end of every round, the last submitted/active Python algorithm is locked in and participates in a **full day of algorithmic trading against Prosperity's bots** for evaluation (10,000 algorithmic iterations).
* **Two Sub-Challenges:** The overall leaderboard and PnL metrics are separated into Algorithmic and Manual trading. 

## Technical Limitations & Rules
* **Language & Execution:** 
  * Only python (3.12 syntax) is supported. 
  * The program runs in an AWS Lambda environment.
  * Strict execution time limit per iteration: **900ms** (Average should be ≤ 100ms per iteration). 
* **Libraries Supported:** `pandas`, `NumPy`, `statistics`, `math`, `typing`, and `jsonpickle`. External libraries are not supported.
* **Persistent State:**
  * Since Lambda is stateless, class variables might clear between iterations.
  * You must use `state.traderData` (a string) to persist data across iterations. 
  * ⚠️ `traderData` character limit is strictly **50,000 characters**. Exceeding this crashes/times out the algorithm. Consider compression or concise JSON serializations.
* **Order Execution:** Instantaneous. If crossing a matching bot order (in Price-Time Priority), execution happens instantly within that tick.

## The Algorithmic Structure
We must define a `Trader` class containing a `run(self, state: TradingState)` method.
* **Input (`state: TradingState`)** includes:
  * `timestamp: int` — The current timestamp of the execution step.
  * `order_depths: Dict[str, OrderDepth]` — Unexecuted resting market orders (Quotes) from bots on the exchange, divided into `buy_orders` and `sell_orders` per level.
  * `own_trades: Dict[str, List[Trade]]` — Fills that our algorithm made since the last iteration.
  * `market_trades: Dict[str, List[Trade]]` — Fills that occurred between other bots since the last iteration.
  * `position: Dict[str, int]` — Current held absolute position (+ Long, - Short) for each product.
  * `observations: Observation` — Additional meta/conversion data.
  * `traderData: str` — String serialized state from the previous iteration.
* **Output:**
  * Must return `result` (Dict of Product -> List of `Order` objects), `conversions` (int), and `traderData` (str).
  * For **Round 2 only**, the class implies needing a `bid(self)` method to be defined, though it returns a hardcoded or dynamic value (as noted in the Wiki snippet). 

## Product specific knowledge (Tutorial Round)
* **EMERALDS:** Stable value product. Limit = 80
* **TOMATOES:** Fluctuating value product. Limit = 80
* NOTE: If an iteration attempts to submit orders that would exceed the active limit if fully executed, **ALL** orders within that iteration for that product will be cancelled/rejected automatically by the exchange matching engine. 

## Algorithmic Trading Concepts Used
* `OrderDepth` separates books. **Bid side** (`buy_orders`) maps positive quantities `Price -> Qty`. **Ask side** (`sell_orders`) maps negative quantities `Price -> -Qty`.
* Attempting `Market Making` behavior requires managing inventory risk.

---
*Ready to trade Intara! Let's get to coding.*
