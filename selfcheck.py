# selfcheck.py
#
# A friendlier, fuller self-check you can run while building your agent. It does NOT mark
# your project and is worth no points -- it just helps you find problems early, on your
# own machine, without seeing any solution code. It runs:
#   1. the basic protocol check (agent_unittest), which includes your group code;
#   2. an end-to-end run in all three regimes (no crashes, sane equity) on the training
#      market your group code picks out for your report's figures;
#   3. a determinism check -- with the generators seeded the way the competition host
#      seeds them, the same data must give the same result twice.
# It also warns when your agent never has 10% of its money in shares on any of the three
# runs: fine while you build, and the starting stub earns it, but in the competition a run
# like that scores 0 and an agent with no run above it is not placed.
#
# Run with:   python3 selfcheck.py           (it reads your group code out of agent.py)
#         or: python3 selfcheck.py G07       (the same, and it checks G07 is really you)
# On Windows, type python where these say python3.
#
# You never type a ticker. Your group code says which training market your report's
# figures come from, and the code lives in agent.py, so the tool reads it from the file
# rather than guessing or asking; you still build and test your agent on all four markets.
# Type the G-and-number half if you want it double-checked; never type the four characters
# after the dash into a terminal, they are not for screens other people see.
#
# Every problem it finds names its line in agent.py. If it seems to hang, press Ctrl-C
# once: the report names the line your agent was running, and nothing else starts.
#
# Keep this file and agent_unittest.py next to your agent.py. It looks for the training
# data in data/training/ and then in ../data/training/; if it finds neither it says so and
# still gives you a verdict on everything it could check.
#
# Note the classic bug it guards against: if you compute returns by slicing a pandas
# *Series* (close[1:] / close[:-1]) instead of a numpy array, pandas lines the slices up
# by index label and silently gives you all zeros. Always np.array(...) first.

import random
import sys

# numpy and pandas first, because nothing below runs without them. A Python that lacked
# them stopped here with a raw traceback, which Python 3.15 ends with "Did you mean:
# 'runpy'?" (review 184); the report now says what is missing and how to install it.
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

# The four training tickers, in the order that assigns them: group 1 gets the first,
# group 5 wraps back round to it. This order is the assignment, so re-sorting this tuple
# would quietly hand every group a different market.
TICKERS = ("VOLT", "ZNTH", "NOVA", "QBIT")

# Where the training data might be, depending on where you keep these files. We try each
# in turn and use the first one that is really there.
DATA_DIRS = ("data/training/", "../data/training/")

# The competition's exposure floor. A run on which your agent never had this share of its
# money in shares scores 0 there, as if it had not traded, and an agent with no run above
# the floor is not placed. Holding in a run your agent cannot read is fine: an agent that
# reads only prices holds in the news-only run and is placed on the others.
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
            # An agent that never returns on real data shows its line too, once you press
            # Ctrl-C, and main() stops there rather than starting the next run.
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
    # 1. Protocol conformance. Its verdict counts toward ours, and it is what reports a
    #    missing or mistyped group code, so we do it before anything that needs the code.
    passed, total = agent_unittest.run_checks()
    all_ok = (passed == total)
    print()

    # 2. Which market the report's figures come from. Not typed and never defaulted: it
    #    comes from the group code in your own agent.py, so there is nothing here to get
    #    wrong and nothing to guess.
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

    # If you named a group on the command line, it has to be the one in the file. This is
    # the check that catches an agent.py picked up from another group.
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

    # Nothing below can run if agent.py will not import on its own.
    TradingAgent, load_error = agent_unittest.load_agent()
    if TradingAgent is None:
        print("  [skip] agent.py does not load on its own (" + load_error + ")")
        print()
        print("  Some checks failed -- read the lines above.")
        return

    # 2. End-to-end on the training data, all three regimes.
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

    # 3. Determinism: run "both" again and compare. Only meaningful if "both" worked the
    #    first time; otherwise say what actually went wrong instead of blaming randomness.
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

    # A warning, never a failure: the stub holds every day and is a legal agent.
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
        # agent_unittest has already printed where your agent was; nothing to add.
        sys.exit(130)
