# tests.py -- asserts that prove the account's rules, the metrics and the engine.
# Reference: <full name of the saving-and-tests reference member>
#
# Run it with:   python3 tests.py       (on Windows: python tests.py)
# Every test is a plain function of asserts; the first one that fails stops with its message.

import time

import numpy as np

import analytics
from account import Account, is_valid_order
from data_loader import MarketData
from simulator import Simulator
from storage import Storage


def test_fee_and_buy_max():
    # The contract's worked example: $500 at $25 with the 0.1% fee buys 19 shares, not 20.
    account = Account(500.0, 0.0)
    assert account.max_affordable(25.0) == 19
    assert account.execute("BUY", -1, 25.0) == "ACCEPT"
    assert account.shares == 19
    assert abs(account.cash - (500.0 - 19 * 25.0 * 1.001)) < 1e-9


def test_reject_strings():
    account = Account(10.0, 0.0)
    assert account.execute("BUY", 1, 25.0) == "REJECT currency balance: 10.0"
    assert account.cash == 10.0 and account.shares == 0       # a reject changes nothing
    account = Account(1000.0, 19.0)
    assert account.execute("SELL", 20, 25.0) == "REJECT stock owned: 19.0"
    assert account.shares == 19
    # the number in the reply parses the way the contract says: split(": ") and float()
    assert float("REJECT stock owned: 19.0".split(": ")[1]) == 19.0


def test_sell_fee_and_sell_all():
    account = Account(0.0, 10.0)
    assert account.execute("SELL", -1, 100.0) == "ACCEPT"
    assert account.shares == 0
    assert abs(account.cash - 10 * 100.0 * 0.999) < 1e-9
    assert account.execute("SELL", -1, 100.0) == "ACCEPT"    # nothing left: still ACCEPT


def test_order_validation():
    assert is_valid_order(("BUY", 5))
    assert is_valid_order(["SELL", -1])
    assert is_valid_order(("HOLD", 0))
    assert not is_valid_order(("BUY", float("nan")))
    assert not is_valid_order(("buy", 5))
    assert not is_valid_order(("BUY",))
    assert not is_valid_order("HOLD")


def test_metrics_hand_trace():
    # The interview's hand-trace: equity 100, 120, 90, 110.
    equity = [100.0, 120.0, 90.0, 110.0]
    dd = analytics.drawdown_series(equity)
    assert dd[0] == 0 and dd[1] == 0
    assert abs(dd[2] - (-0.25)) < 1e-12
    assert abs(dd[3] - (110 / 120 - 1)) < 1e-12
    assert abs(analytics.max_drawdown(equity) - (-0.25)) < 1e-12
    assert abs(analytics.total_return(equity) - 0.10) < 1e-12
    returns = analytics.daily_returns(equity)
    assert abs(returns[0] - 0.2) < 1e-12 and abs(returns[1] - (-0.25)) < 1e-12
    expected = returns.mean() / returns.std()
    assert abs(analytics.sharpe_like(equity) - expected) < 1e-12


def test_moving_average():
    values = [1, 2, 3, 4, 5, 6]
    assert analytics.moving_average(values, 3) == [2.0, 3.0, 4.0, 5.0]
    fast = analytics.moving_average(values, 2)
    slow = analytics.moving_average_naive(values, 2)
    assert len(fast) == len(slow)
    for a, b in zip(fast, slow):
        assert abs(a - b) < 1e-12


class RecordingAgent:
    """Buys one share on day 0 and remembers every bar it is shown."""

    def __init__(self):
        self.seen = []

    def decide(self, bar, headlines, cash, shares, last_response):
        self.seen.append((bar, headlines, last_response))
        if len(self.seen) == 1:
            return ("BUY", 1)
        return ("HOLD", 0)


def tiny_market():
    opens = np.array([10.0, 20.0, 30.0])
    closes = np.array([11.0, 21.0, 31.0])
    return MarketData("TEST", "none/", opens, opens + 1, opens - 1, closes,
                      np.array([1.0, 1.0, 1.0]), {0: ["TEST surge"]})


def test_no_look_ahead():
    agent = RecordingAgent()
    result = Simulator(tiny_market(), agent, 100.0, 0.0, "both").run()
    assert len(agent.seen) == 2                       # every day but the last
    assert agent.seen[0][0]["close"] == 11.0          # day 0 sees day 0 only
    assert agent.seen[0][2] is None                   # first call: no reply yet
    assert agent.seen[1][2] == "ACCEPT"
    assert agent.seen[1][1] == []                     # a day without news: empty list
    day, action, shares, price = result.trades[0]
    assert day == 1 and price == 20.0                 # filled at the NEXT day's open
    assert len(result.equity) == 3
    assert abs(result.equity[1] - (100 - 20 * 1.001 + 21)) < 1e-9   # valued at the close


def test_regimes():
    agent = RecordingAgent()
    Simulator(tiny_market(), agent, 100.0, 0.0, "news").run()
    assert agent.seen[0][0] is None and agent.seen[0][1] == ["TEST surge"]
    agent = RecordingAgent()
    Simulator(tiny_market(), agent, 100.0, 0.0, "prices").run()
    assert agent.seen[0][1] is None and agent.seen[0][0] is not None


def test_result_line_round_trip():
    storage = Storage()
    line = storage.format_result("Agent, on ZNTH", 9224.48, 60, -0.0776, -0.291, -0.001)
    name, final, trades, ret, dd, sharpe = storage.parse_result(line)
    assert name == "Agent; on ZNTH" and final == 9224.48 and trades == 60
    try:
        storage.parse_result("not,a,result")
        assert False, "a damaged line must raise ValueError"
    except ValueError:
        pass


def time_the_optimization():
    """The one optimization, measured: a running-sum moving average against re-adding."""
    values = list(range(20000))
    start = time.time()
    analytics.moving_average_naive(values, 100)
    naive = time.time() - start
    start = time.time()
    analytics.moving_average(values, 100)
    running = time.time() - start
    print("  moving average of 20000 values, window 100: re-adding "
          + format(naive, ".4f") + "s, running sum " + format(running, ".4f") + "s")


def main():
    tests = [test_fee_and_buy_max, test_reject_strings, test_sell_fee_and_sell_all,
             test_order_validation, test_metrics_hand_trace, test_moving_average,
             test_no_look_ahead, test_regimes, test_result_line_round_trip]
    for test in tests:
        test()
        print("  [OK] " + test.__name__)
    print("  All " + str(len(tests)) + " tests passed.")
    time_the_optimization()


if __name__ == "__main__":
    main()
