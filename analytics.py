# analytics.py -- indicators, metrics and charts, built by hand.
# Reference: <full name of the analytics-and-charts reference member>
#
# No pandas shortcuts (rolling, shift, pct_change, cumprod) and no plt.hist: every number
# here comes from numpy slicing or a plain loop, as the time-series supplement shows.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MA_WINDOW = 10      # the moving average drawn on the price chart (the agent uses 10 too)


# ---------- indicators ----------

def daily_returns(values):
    """Day-on-day returns: today / yesterday - 1, by slicing a numpy array."""
    values = np.array(values, dtype=float)          # an array before we slice it
    if len(values) < 2:
        return np.array([])
    return values[1:] / values[:-1] - 1


def moving_average(values, window):
    """The mean of the last `window` values, one per day from day window-1 on.

    The optimization: a running sum. Each step adds the newest value and subtracts the one
    that leaves the window, so the whole series costs O(n) instead of the O(n * window) of
    re-adding every window from scratch."""
    assert window >= 1, "the window must be at least one day"
    values = [float(v) for v in values]
    averages = []
    running = 0.0
    for i in range(len(values)):
        running = running + values[i]
        if i >= window:
            running = running - values[i - window]
        if i >= window - 1:
            averages.append(running / window)
    return averages


def moving_average_naive(values, window):
    """The supplement's version, re-adding each window: kept only to time the difference."""
    values = np.array(values, dtype=float)
    averages = []
    for i in range(window, len(values) + 1):
        averages.append(values[i - window:i].mean())
    return averages


# ---------- the three metrics ----------

def total_return(equity):
    """(final equity - starting equity) / starting equity."""
    if len(equity) == 0 or equity[0] == 0:
        return 0.0
    return (equity[-1] - equity[0]) / equity[0]


def drawdown_series(equity):
    """How far each day sits below the best value so far, as a fraction (0 or negative)."""
    series = []
    peak = None
    for value in equity:
        if peak is None or value > peak:
            peak = value
        if peak > 0:
            series.append((value - peak) / peak)
        else:
            series.append(0.0)
    return series


def max_drawdown(equity):
    """The worst dip below a running peak: -0.16 is a 16% drawdown. One pass, O(n)."""
    worst = 0.0
    for dip in drawdown_series(equity):
        if dip < worst:
            worst = dip
    return worst


def sharpe_like(equity):
    """mean(daily returns of the equity) / std(the same returns), numpy's std."""
    returns = daily_returns(equity)
    if len(returns) == 0:
        return 0.0
    spread = returns.std()
    if spread == 0:
        return 0.0
    return float(returns.mean() / spread)


# ---------- the three charts ----------

def finish_chart(title, xlabel, ylabel, filename):
    """Title, labels and legend, save a PNG beside the program, then show the window."""
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    plt.savefig(filename)
    print("  saved " + filename + " (close the chart window to continue)")
    plt.show()
    plt.close()


def plot_price_with_trades(closes, trades, title, filename="chart_price.png"):
    """The closing price, its moving average, and a triangle at each fill (day and price)."""
    plt.figure(figsize=(10, 5))
    pd.Series(closes).plot(color="gray", label="close")
    averages = moving_average(closes, MA_WINDOW)
    days = list(range(MA_WINDOW - 1, len(closes)))
    plt.plot(days, averages, color="orange", linewidth=1,
             label=str(MA_WINDOW) + "-day moving average")
    buy_days, buy_prices, sell_days, sell_prices = [], [], [], []
    for day, action, shares, price in trades:
        if action == "BUY":
            buy_days.append(day)
            buy_prices.append(price)
        elif action == "SELL":
            sell_days.append(day)
            sell_prices.append(price)
    plt.scatter(buy_days, buy_prices, marker="^", color="green", label="buy", zorder=3)
    plt.scatter(sell_days, sell_prices, marker="v", color="red", label="sell", zorder=3)
    finish_chart(title, "day", "price (USD)", filename)


def plot_equity(equity, title, filename="chart_equity.png"):
    """The equity curve: cash plus the value of the shares, day by day."""
    plt.figure(figsize=(10, 5))
    pd.Series(equity).plot(label="equity")
    plt.axhline(equity[0], color="gray", linestyle="--", label="start")
    finish_chart(title, "day", "equity (USD)", filename)


def plot_drawdown(equity, title, filename="chart_drawdown.png"):
    """How far the equity sits below its best so far, as a fraction."""
    plt.figure(figsize=(10, 5))
    pd.Series(drawdown_series(equity)).plot(color="firebrick", label="drawdown")
    finish_chart(title, "day", "drawdown (fraction below the peak)", filename)
