import random
import sys

try:
    import numpy as np
    import pandas as pd
except ImportError as missing:
    print("=== selfcheck: extra formative checks ===")
    print("  [FAIL] numpy and pandas are not installed for this Python   (" + str(missing)
          + ": run python3 -m pip install numpy pandas matplotlib (on Windows, python -m "
          "pip ...), with the same command you run this file with. This is Python "
          + sys.version.split()[0] + ", at " + sys.executable + ")")
    sys.exit(1)

import agent_unittest
TICKERS = ("VOLT", "ZNTH", "NOVA", "QBIT")
DATA_DIRS = ("data/training/", "../data/training/")
EXPOSURE_FLOOR = 0.10
NEVER_TRADED = ("never had 10% of its money in shares",
                "on any of the three runs. Fine while you build; in the competition a "
                "run like that scores 0, and an agent with no run above 10% is not placed")


def ticker_for(number):
    """The training ticker a group number is assigned: 1 -> VOLT, 5 -> VOLT again."""
    return TICKERS[(number - 1) % len(TICKERS)]


def is_there(path):
    """True if we can actually open this file."""
    try:
        handle = open(path)
        handle.close()
        return True
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return False


def find_data_dir(ticker):
    """Return the first candidate folder holding BOTH files for this ticker, or "".

    Both, because the loader below reads both: probing only the prices would send us
    into a crash on the missing news file."""
    for folder in DATA_DIRS:
        if (is_there(folder + ticker + ".csv")
                and is_there(folder + ticker + "_news.txt")):
            return folder
    return ""


def name_what_is_missing(ticker):
    """When find_data_dir came back empty, say WHICH file is absent.

    "No data" and "you downloaded the prices but not the news" are different problems
    with different fixes, and a tool that cannot tell them apart sends you looking in
    the wrong place."""
    for folder in DATA_DIRS:
        has_prices = is_there(folder + ticker + ".csv")
        has_news = is_there(folder + ticker + "_news.txt")
        if has_prices and not has_news:
            return folder + ticker + "_news.txt is missing (the prices are there)"
        if has_news and not has_prices:
            return folder + ticker + ".csv is missing (the news file is there)"
    return ("no " + ticker + " data in " + " or ".join(DATA_DIRS)
            + " (both " + ticker + ".csv and " + ticker + "_news.txt are needed)")


def load_bars_and_news(ticker, folder):
    """Load one training ticker into a list of bar dicts and a day->headlines dict."""
    frame = pd.read_csv(folder + ticker + ".csv")
    bars = []
    i = 0
    while i < len(frame):
        row = frame.iloc[i]
        bars.append({"open": float(row["open"]), "high": float(row["high"]),
                     "low": float(row["low"]), "close": float(row["close"]),
                     "volume": float(row["volume"])})
        i = i + 1
    news = {}
    is_header = True
    for line in open(folder + ticker + "_news.txt", encoding="utf-8"):
        if is_header:
            is_header = False
            continue
        line = line.strip()
        if line == "":
            continue
        parts = line.split(",", 1)
        day = int(parts[0])
        if day not in news:
            news[day] = []
        news[day].append(parts[1])
    return bars, news


def line_of(agent, order, inputs):
    """'line 21: ' for the return in agent.py that gave this malformed order, or "".

    Called once, after the run has already failed: decide() is asked again with the same
    inputs while agent_unittest watches which return answers. Watching every day of a full
    run would slow it down, and the run is over anyway. The line is named only when the
    second answer is the same malformed order, so it is never a guess."""
    try:
        again, line = agent_unittest.call_decide(agent, *inputs)
    except Exception:
        return ""
    if repr(again) == repr(order):
        return agent_unittest.at_line(line)
    return ""


def run_on(agent_class, bars, news, use_prices, use_news):
    """The equity curve of one run, or a string saying what went wrong: see run_measured."""
    return run_measured(agent_class, bars, news, use_prices, use_news)[0]


def run_measured(agent_class, bars, news, use_prices, use_news):
    """Run a fresh TradingAgent over the bars. Returns (result, peak).

    `peak` is the largest share of its money the agent ever had in shares, from 0 to 1,
    measured at each day's close. `result` is the equity curve, or a string that
    says what went wrong: "crash on day N: line L: TypeError: ..." if it raises, and
    "malformed order on day N: line L: got ..." if it returns something that is not an order.

    A crash on day 300 of real data is a normal thing to hit while you are building, and
    it deserves a line in the report rather than a traceback on top of it. The line is the
    one in agent.py where it went wrong, whenever that can be known.

    Both random generators are seeded first, exactly as the competition host does before
    every run, so "deterministic" means here what it means there."""
    np.random.seed(12345)
    random.seed(12345)
    peak = 0.0
    try:
        agent = agent_class()
    except KeyboardInterrupt as error:
        return "TradingAgent(): " + agent_unittest.error_with_line(error), peak
    except Exception as error:
        return ("TradingAgent() crashed: "
                + agent_unittest.error_with_line(error, agent_class.__init__)), peak
    interface = agent_unittest.FakeInterface(10000.0)
    last_response = None
    equity = [interface.cash]
    t = 0
    while t < len(bars) - 1:
        bar = bars[t] if use_prices else None
        if use_news and t in news:
            headlines = news[t]
        elif use_news:
            headlines = []
        else:
            headlines = None
        try:
            order = agent.decide(bar, headlines, interface.cash, interface.shares,
                                 last_response)
        except KeyboardInterrupt as error:
            
            return "day " + str(t) + ": " + agent_unittest.error_with_line(error), peak
        except Exception as error:
            return ("crash on day " + str(t) + ": "
                    + agent_unittest.error_with_line(error, agent_unittest.decide_of(agent))), peak
        if not agent_unittest.is_valid_order(order):
            inputs = (bar, headlines, interface.cash, interface.shares, last_response)
            return ("malformed order on day " + str(t) + ": " + line_of(agent, order, inputs)
                    + "got " + repr(order)[:80]), peak
        fill_price = bars[t + 1]["open"]
        last_response = interface.execute(order, fill_price)
        held = interface.shares * bars[t + 1]["close"]
        value = interface.cash + held
        equity.append(value)
        if value > 0 and held / value > peak:
            peak = held / value
        t = t + 1
    return equity, peak


def main():
    passed, total = agent_unittest.run_checks()
    all_ok = (passed == total)
    print()
    lines = agent_unittest.read_agent_source() or []
    code, problem = agent_unittest.read_group_code(lines)
    if problem != "" or not agent_unittest.is_valid_code(code):
        print("=== selfcheck: extra formative checks ===")
        print("  [skip] I cannot tell which group this is, so I cannot tell which market")
        print("         your report's figures come from -- fix the group code above and")
        print("         run me again.")
        print()
        print("  Some checks failed -- read the lines above.")
        return

   
    public = code[:3]
    if len(sys.argv) > 1 and sys.argv[1].strip() != "":
        typed = sys.argv[1].strip().upper()
        if typed != public:
            where = agent_unittest.group_code_line(lines)
            print("=== selfcheck: extra formative checks ===")
            print("  [FAIL] you typed " + typed + ", but agent.py belongs to " + public
                  + " (its GROUP_CODE, line " + str(where) + ").")
            print("         One of the two is wrong. If " + public + " is not your group,")
            print("         you are working on somebody else's file.")
            return

    ticker = ticker_for(agent_unittest.group_number(code))
    print("=== selfcheck: extra formative checks (" + public + ", market " + ticker + ") ===")

    TradingAgent, load_error = agent_unittest.load_agent()
    if TradingAgent is None:
        print("  [skip] agent.py does not load on its own (" + load_error + ")")
        print()
        print("  Some checks failed -- read the lines above.")
        return

    folder = find_data_dir(ticker)
    if folder == "":
        print("  [skip] " + name_what_is_missing(ticker)
              + " -- skipping the data checks")
        print()
        if all_ok:
            print("  Everything I could check passed, but I could not run your agent "
                  + "on real data.")
        else:
            print("  Some checks failed -- read the lines above.")
        return
    try:
        bars, news = load_bars_and_news(ticker, folder)
    except Exception as error:
        print("  [FAIL] could not read the " + ticker + " data in " + folder + ": "
              + type(error).__name__ + ": " + str(error))
        print("         re-download it; the CSV needs the columns "
              + "day,open,high,low,close,volume")
        print()
        print("  Some checks failed -- read the lines above.")
        return
    regimes = [("OHLCV-only", True, False), ("news-only", False, True), ("both", True, True)]
    saved = {}
    peaks = []
    for label, up, un in regimes:
        equity, peak = run_measured(TradingAgent, bars, news, up, un)
        if isinstance(equity, str):
            print("  [FAIL] " + label + ": " + equity)
            all_ok = False
            if agent_unittest.CTRL_C in equity:
                print()
                print("  Stopped with Ctrl-C: the line above is where your agent was running.")
                return
        elif len(equity) != len(bars) or min(equity) <= 0:
            print("  [FAIL] " + label + ": equity curve looks wrong")
            all_ok = False
        else:
            print("  [OK  ] " + public + " " + ticker + " " + label
                  + ": ran end-to-end, final equity "
                  + str(round(equity[len(equity) - 1], 2)) + "   (data: " + folder + "; "
                  + agent_unittest.stack_here() + ")")
            saved[label] = equity
            peaks.append(peak)

    if "both" not in saved:
        print("  [skip] determinism: the 'both' run above did not finish, so there is "
              + "nothing to compare")
    else:
        again = run_on(TradingAgent, bars, news, True, True)
        if isinstance(again, str) and agent_unittest.CTRL_C in again:
            print("  [FAIL] determinism run: " + again)
            print()
            print("  Stopped with Ctrl-C: the line above is where your agent was running.")
            return
        if not isinstance(again, str) and again == saved["both"]:
            print("  [OK  ] deterministic: same data gives the same result twice")
        else:
            print("  [FAIL] not deterministic: the same data gave two different results.")
            print("         Something outside the seeded generators is varying: the "
                  + "clock, a set of floats, id(), or state kept between runs.")
            all_ok = False

    if len(peaks) == 3 and max(peaks) < EXPOSURE_FLOOR:
        print("  [WARN] " + NEVER_TRADED[0] + "   (" + NEVER_TRADED[1] + ")")

    print()
    if all_ok:
        print("  All checks passed.")
        print("  For your report, copy the three 'ran end-to-end' lines above.")
        print("  The online check and the competition run "
              + agent_unittest.competition_stack() + ".")
    else:
        print("  Some checks failed -- read the lines above.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        sys.exit(130)
