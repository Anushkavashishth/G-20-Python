# How the project works, end to end

This is the Glacial Pace Capital trading simulator: a text trading desk, a back-test engine, analytics, plain-text persistence, and a self-contained competition agent (`agent.py`). Everything follows the five rule documents (brief 01, library policy 02, agent contract 03, rubric 04, AI policy 05).

## 1. Folder layout

```
my_trading_desk/
    agent.py            the competition entry (TradingAgent)      <- piece: The agent
    account.py          the ledger: cash, shares, fee, replies    <- piece: Account and engine
    simulator.py        the back-test loop (no look-ahead)        <- piece: Account and engine
    data_loader.py      reads prices, news, lexicon               <- piece: Data loading
    analytics.py        returns, moving average, metrics, charts  <- piece: Analytics and charts
    storage.py          results, leaderboard, session (text)      <- piece: Saving and tests
    tests.py            asserts that prove the rules              <- piece: Saving and tests
    strategies.py       BuyAndHold / Hold benchmarks (inheritance)
    desk.py             THE FILE THAT STARTS THE PROGRAM          <- piece: The desk
    agent_unittest.py   course tool, do not edit
    selfcheck.py        course tool, do not edit
    data/training/      the nine training files, unchanged
```

Run everything from inside `my_trading_desk` (on Windows type `python` instead of `python3`):

```
python3 desk.py            the trading desk
python3 tests.py           our own asserts (9 tests + the optimization timing)
python3 agent_unittest.py  the course's protocol check
python3 selfcheck.py       the course's full check on your report market
```

## 2. The big design idea: thinking vs authority

- **The agent thinks.** `TradingAgent.decide(bar, headlines, cash, shares, last_response)` looks at today and its own stored history and *requests* an order such as `("BUY", 40)`. It never changes any money.
- **The desk decides.** `Account.execute(action, amount, price, day)` is the *only* code in the program that changes cash or shares. It charges the 0.1% fee and can refuse with exactly `REJECT currency balance: <cash>` or `REJECT stock owned: <shares>`.
- Because of this split, the same `agent.py` runs unchanged in our desk and in the lecturer's competition program.

## 3. What happens when you press keys (a walkthrough)

1. `python3 desk.py` runs `main()`: it reads any `--cash/--shares/--ticker/--folder` arguments (all have defaults), builds a `Desk`, and starts the menu loop (`while choice != "0":`, the café-register pattern).
2. **[1] Load dataset** → `data_loader.load_market("ZNTH", "data/training/")`. pandas reads `ZNTH.csv`; the columns are handed to numpy arrays right there (so later slices are positional — the supplement's trap). The news file is read line by line with `split(",", 1)` into `{day: [headlines]}`; the lexicon into `{word: score}`. A wrong ticker gives a clear message, never a traceback. A missing news file still loads the prices.
3. **[2] Set starting cash/shares** → rejects negatives, non-numbers, `nan`/`inf` and "nothing at all"; accepts `1e4`. Resets the session to day 0.
4. **[3] Step one day** → day + 1, today's headlines printed, the day's equity appended to the manual equity list.
5. **[4]/[5] Manual buy/sell** → `Account.execute` at **today's close** (you are at the counter; the price is on the board). Example from the course demo, reproduced exactly: 10 shares of ZNTH at 101.44 → cash 8984.59, equity 9998.99.
6. **[6] Run agent to end** → pick TradingAgent / BuyAndHold / Hold and the regime (both, prices only, news only). `Simulator.run()` makes a **fresh Account** with the starting balances and loops `for t in range(len(market) - 1)`:
   - gives the agent **day t only** (`bar` or `None`, `headlines` or `None`),
   - fills the order at **day t+1's open** (no look-ahead),
   - appends `cash + shares * close[t+1]` to the equity curve.
   It prints final equity, return, sharpe-like, max drawdown and number of trades.
7. **[7] Price chart** → closing price (gray), the 10-day moving average (orange), green ▲ at each buy and red ▼ at each sell, drawn **on the fill day at the fill price**.
8. **[8] Equity + drawdown** → equity curve, then the drawdown chart (fraction below the running peak). Each chart is also saved as a PNG.
9. **[9] Save / load / leaderboard** → `Storage` writes `session.txt`, appends the run to `results.txt` and rewrites `leaderboard.txt` best-first. After a restart, **[9] → l** reloads the market, the balances, the day, the equity history and the manual trades, and prints the leaderboard. No results file yet? An empty leaderboard and a message, not a crash.

## 4. The agent's strategy (what you say at the interview)

**In two sentences:** it buys when the price dips more than 2% below its 10-day moving average (unless the price is more than 10% under its 100-day average — a falling market) or when today's news is good, and it sells everything when the price is back above its 10-day average or the news turns bad. It never puts more than 40% of its money into shares, so a crash cannot halve the account.

How `decide()` works, line by line:
1. `learn_fill_price` — in the news-only run there is no price, so it reads the price off its own last fill: cash moved ÷ shares moved, with the fee taken out. The very first news-only buy is 1 share, just to learn the price.
2. If there is a bar: store the close, update two **running sums** (the optimization) and compute the **price vote**: +1 dip, −1 above average, 0 otherwise.
3. If there are headlines: the **news vote** — the week-4 sentiment score (split words, look each up in the embedded lexicon, add).
4. Votes are added. Negative and holding shares → `("SELL", -1)`. Positive → top shares up to 40% of money (`("BUY", n)`), unless already at least 20% invested. Otherwise `("HOLD", 0)`.

Why this strategy: we measured it. On the training data the news has a real next-day signal (correlation 0.13–0.23 between today's mood and tomorrow's move); trend-following moving-average crossovers lost money on all four markets, while buying dips made money on three of four. The competition scores the sharpe-like ratio and gives worst rank to any run that falls to half its peak, so position size is capped at 40%: that leaves the score almost unchanged but roughly halves drawdowns (worst training drawdown is 19%; on simulated 70–90% crashes it stayed under the 50% gate).

Training results (start 10,000):

| Market | prices only | news only | both | buy-and-hold |
|---|---|---|---|---|
| VOLT (volatile) | 12,520.84 | 15,275.16 | 19,078.13 | −66% |
| ZNTH (bull) | 11,273.74 | 11,596.60 | 12,366.84 | +17.6% |
| NOVA (sideways) | 11,152.72 | 13,324.77 | 12,202.78 | +6% |
| QBIT (bear) | 8,617.09 | 11,384.27 | 10,440.11 | −81% |

## 5. The indicators and metrics (all hand-built)

- **Daily returns:** `values[1:] / values[:-1] - 1` on a numpy array.
- **Moving average:** a running sum (add today, subtract the day leaving the window).
- **Return:** (final − start) / start.
- **Drawdown:** running-peak loop; max drawdown is the worst dip (negative fraction). Hand-trace for equity 100, 120, 90, 110 → 0, 0, −0.25, −0.0833 (tested in `tests.py`).
- **Sharpe-like:** mean of the equity's daily returns ÷ their numpy std.
- None of `rolling`, `shift`, `pct_change`, `cumprod`, `plt.hist`, datetime — checked.

## 6. Complexity and the one optimization

- The back-test loop visits each of the n days once; the engine's own work per day is O(1) (one execute, one append), so the engine is **O(n)**.
- The agent's work per day was O(w) (re-adding a w-day window for each moving average), making a run O(n·w).
- **The one optimization:** running sums for the moving averages, in `agent.py` and `analytics.moving_average`. Each day costs O(1), so the whole run is **O(n)**. `tests.py` times it: 20,000 values, window 100 — about 0.05 s re-adding vs 0.005 s with the running sum.
- Saving one result appends one line: O(1). Rewriting the leaderboard reads and sorts all k results: O(k log k).

## 7. Things you must still do yourselves

1. **`agent.py`**: replace `GXX-XXXX` with your group code from the email, and fill in `# Group:` and `# Reference:` with real names. Then run `python3 agent_unittest.py` (10/10) and `python3 selfcheck.py` (copy its three "ran end-to-end" lines into the report).
2. Replace each `# Reference: <...>` line at the top of every `.py` file with the member who owns that piece.
3. Write the report in your own words (see `REPORT_DRAFT.md` for the structure and the technical facts), save it as `Gxx_report.pdf` (G + two digits only).
4. Submit the `.py` files individually (not the data, not `agent_unittest.py`/`selfcheck.py`, not this guide).
5. Make sure every member can explain every file — the interview's live edit goes to each piece's reference member.

## 8. Practice live edits (the kind the interview asks)

- *"Hold whenever cash is under 100"* — in `decide()`, before the `if vote < 0` line: `if cash < 100: return ("HOLD", 0)`. Then `python3 agent_unittest.py`.
- *"Sell when the news is bad"* — already the case: a negative news vote makes the total negative.
- *"Handle a missing price"* — `data_loader.load_prices` already raises a clear `ValueError` for a missing open/close; the desk prints it.
- *"Change the fee"* — `FEE` in `account.py` (and in `agent.py`, which must stay self-contained).
