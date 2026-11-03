# simulator.py -- the back-test engine: streams days to an agent, with no look-ahead.
# Reference: <full name of the account-and-engine reference member>
#
# The golden rule: on day t the agent sees days 0..t only, and its order fills at the
# OPEN of day t+1. The engine never hands the agent a future bar, so peeking is impossible.

import analytics
from account import Account, is_valid_order

# The three information regimes of the competition: (label, sees prices, sees news).
REGIMES = {
    "both": ("OHLCV+news", True, True),
    "prices": ("OHLCV-only", True, False),
    "news": ("news-only", False, True),
}


class RunResult:
    """Everything one back-test produced: the equity curve, the trades and the metrics."""

    def __init__(self, name, ticker, regime, equity, trades, problems):
        self.name = name                # e.g. "TradingAgent on ZNTH"
        self.ticker = ticker
        self.regime = regime
        self.equity = equity            # one value per day, cash + shares * close
        self.trades = trades            # (day, action, shares, price), day = the fill day
        self.problems = problems        # messages about malformed orders, if any
        self.final_equity = equity[-1]
        self.total_return = analytics.total_return(equity)
        self.max_drawdown = analytics.max_drawdown(equity)
        self.sharpe = analytics.sharpe_like(equity)

    def summary(self):
        """The report the desk prints after a run."""
        lines = [
            "Ran " + self.name + " (" + self.regime + "):",
            "  final equity : " + format(self.final_equity, ".2f"),
            "  total return : " + format(self.total_return * 100, ".1f") + "%",
            "  sharpe-like  : " + format(self.sharpe, ".3f"),
            "  max drawdown : " + format(-self.max_drawdown * 100, ".1f") + "%",
            "  trades       : " + str(len(self.trades)),
        ]
        return "\n".join(lines)


class Simulator:
    """Runs one agent over one market, from day 0 to the last day."""

    def __init__(self, market, agent, start_cash=10000.0, start_shares=0.0, regime="both"):
        if regime not in REGIMES:
            raise ValueError("unknown regime " + repr(regime))
        self.market = market
        self.agent = agent
        self.account = Account(start_cash, start_shares)
        self.regime = regime

    def inputs_for(self, day):
        """What the agent is allowed to see on a day, in this regime: today only."""
        label, sees_prices, sees_news = REGIMES[self.regime]
        bar = self.market.bar(day) if sees_prices else None
        headlines = self.market.headlines(day) if sees_news else None
        return bar, headlines

    def run(self, name=None):
        """The back-test loop. One pass over the days: O(n) for the engine itself.

        decide() is called on every day but the last, whose order would fill on a day
        that does not exist."""
        closes = self.market.closes
        opens = self.market.opens
        equity = [self.account.equity(closes[0])]
        problems = []
        last_response = None
        for t in range(len(self.market) - 1):
            bar, headlines = self.inputs_for(t)
            order = self.agent.decide(bar, headlines, self.account.cash,
                                      self.account.shares, last_response)
            if not is_valid_order(order):
                problems.append("day " + str(t) + ": malformed order " + repr(order)[:60]
                                + ", treated as HOLD")
                order = ("HOLD", 0)
            fill_price = float(opens[t + 1])            # tomorrow's open, never today's
            last_response = self.account.execute(order[0], order[1], fill_price, day=t + 1)
            equity.append(self.account.equity(closes[t + 1]))   # valued at tomorrow's close
        if name is None:
            name = type(self.agent).__name__ + " on " + self.market.ticker
        return RunResult(name, self.market.ticker, REGIMES[self.regime][0], equity,
                         list(self.account.trades), problems)
