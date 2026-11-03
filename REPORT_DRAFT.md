# REPORT DRAFT — structure and facts only

> **Read first.** The AI policy (project document 05) says the report is graded as *your own words*, and that report text an LLM wrote that you could not have written yourselves is a risk. Use this as a checklist and a source of the technical facts, then write each section yourselves. Save the final as `Gxx_report.pdf` (G plus the two digits of your group code, nothing else).

---

## 1. Cover page
- Title: *Glacial Pace Capital Trading Simulator — MIS41110 Programming for Analytics, 2026/27*
- Group number (e.g. G07 — never the four characters after the dash)
- Every member's full name and student ID

## 2. Contribution statement
One reference per piece (match the `# Reference:` lines in the code). In a group of five, one member takes data loading together with saving and tests.

| Piece | Files | Reference | Also wrote |
|---|---|---|---|
| Data loading | data_loader.py | | |
| Account and engine | account.py, simulator.py | | |
| The agent | agent.py, strategies.py | | |
| The desk | desk.py | | |
| Analytics and charts | analytics.py | | |
| Saving and tests | storage.py, tests.py | | |

## 3. User manual (1–3 pages)
Points to cover:
- Requirements: Python 3.11+ with numpy, pandas, matplotlib.
- Folder: put the code files together, with the nine training files in `data/training/`.
- **Start the program with `python3 desk.py`** (Windows: `python desk.py`). Optional: `--cash 5000 --shares 0 --ticker ZNTH --folder data/training/`; every setting has a default.
- Menu options 0–9, one line each (load; set balances; step; manual buy; manual sell; run agent — choose agent and regime; price chart; equity + drawdown; save/load/leaderboard; quit).
- The status line: day, price, cash, shares, equity, today's news count and mood, last event.
- Fill rules: manual trades at today's close; agent orders at the next day's open; 0.1% fee both ways; `-1` = all/max.
- Files written: `session.txt`, `results.txt`, `leaderboard.txt`, `chart_*.png`. The data files are never changed.
- What the error messages mean (unknown ticker, not a number, negative amount, REJECT replies).

## 4. UML activity diagram
Insert `uml_activity_diagram.png` (12 nodes: start → load dataset → menu decision → step / trade by hand / run the agent / show a chart / save-load / set balances → back to menu, or quit → end). Redraw it yourselves in your own tool if you prefer.

## 5. Complexity note (facts)
- Back-test loop: each of n days once; engine work per day O(1) → O(n).
- Agent's moving averages originally re-summed a w-day window every day → O(n·w).
- **One optimization:** running sums (add the new close, subtract the one leaving the window) in `agent.py` and `analytics.moving_average` → O(1) per day, O(n) per run. Measured by `tests.py`: about 10× faster for 20,000 values with a 100-day window.
- No nested loops over days anywhere; max drawdown is one pass.
- Saving a result appends one line, O(1); rewriting the leaderboard sorts k results, O(k log k).

## 6. Library justification (facts)
- numpy — arrays, slicing for returns, mean/std for the sharpe-like score.
- pandas — `read_csv` for the price files only; handed to numpy straight away.
- matplotlib.pyplot — the three charts (line, scatter, axhline).
- math — `isfinite` to reject `nan`/`inf` amounts; sys — command-line arguments; time — timing the optimization.
- Plain-text file I/O for news, lexicon, results, leaderboard and session.
- agent.py imports nothing at all. No banned library or method (rolling, shift, pct_change, cumprod, plt.hist, datetime).

## 7. AI declaration
Required either way (project document 05): which tool, what for, and where. Be accurate — this codebase and this draft were generated with Claude (Anthropic), so the declaration must say so, together with what each member did to understand, test and change the code.

## 8. Self-check record
After putting your real group code in `agent.py`, run `python3 selfcheck.py` and paste the three `ran end-to-end` lines exactly as printed. Which market they come from is decided by your group code. For reference, the figures on each market are:

| Market | OHLCV-only | news-only | both |
|---|---|---|---|
| VOLT | 12520.84 | 15275.16 | 19078.13 |
| ZNTH | 11273.74 | 11596.6 | 12366.84 |
| NOVA | 11152.72 | 13324.77 | 12202.78 |
| QBIT | 8617.09 | 11384.27 | 10440.11 |
