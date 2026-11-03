# agent.py -- Glacial Pace Capital competition entry.
#
# The thinking half of the project: given one day at a time, decide an order.
# It never touches the money. The desk (account.py) owns cash and shares and can refuse.
#
# Self-contained on purpose: it imports nothing, reads no file and writes no file, so the
# competition can load it on its own. The sentiment lexicon is copied in below as a dict.
#
# Strategy in two sentences: buy a dip (today's close more than 2% under its 10-day
# average, unless the market is in a deep downtrend) or good news, and sell when the price
# is back above its average or the news turns bad. Never put more than 40% of the money
# into shares, so that one bad run cannot halve the account.

GROUP_CODE = "G20-G7NR"       
# Group: Dev Madanlal Malviya, Atharva Zade, Dhruv Rastogi, Anushka Vashishth, Shefali Mathur, Boyang Gao 
# Reference: G7NR

FEE = 0.001                # 0.1% fee on every trade, the same as the desk charges
TARGET = 0.4               # when we buy, aim for 40% of our money in shares
SHORT_WINDOW = 10          # days in the moving average a "dip" is measured against
LONG_WINDOW = 100          # days in the moving average that tells us the long trend
DIP = 0.02                 # a dip: close more than 2% under the short average
BEAR_LIMIT = 0.90          # close under 90% of the long average: a downtrend, skip dips

# The 28 scored words of sentiment_words.csv (the 12 neutral words score 0, so they can
# stay out). Copied in because agent.py may not read files.
LEXICON = {
    "surge": 1, "rally": 1, "soar": 1, "gain": 1, "bullish": 1, "breakout": 1,
    "upgrade": 1, "beat": 1, "record": 1, "boom": 1, "jump": 1, "optimism": 1,
    "inflow": 1, "adoption": 1,
    "crash": -1, "plunge": -1, "slump": -1, "loss": -1, "bearish": -1, "selloff": -1,
    "downgrade": -1, "miss": -1, "fear": -1, "dump": -1, "drop": -1, "panic": -1,
    "outflow": -1, "ban": -1,
}


class TradingAgent:
    """Dip-buying plus news-reading agent. Works in all three regimes."""

    def __init__(self):
        self.closes = []          # every close we have seen, oldest first
        self.short_sum = 0.0      # running sum of the last SHORT_WINDOW closes
        self.long_sum = 0.0       # running sum of the last LONG_WINDOW closes
        self.price = None         # the latest price we know (a close, or our own fill)
        self.before = None        # (cash, shares) when we sent our previous order

    # ---------- what we remember ----------

    def remember_close(self, close):
        """Store today's close and keep both moving-average sums up to date.

        The optimization: adding today and dropping the day that leaves the window costs
        the same whatever the window, instead of re-adding the whole window every day."""
        self.closes.append(close)
        self.short_sum = self.short_sum + close
        self.long_sum = self.long_sum + close
        if len(self.closes) > SHORT_WINDOW:
            self.short_sum = self.short_sum - self.closes[-SHORT_WINDOW - 1]
        if len(self.closes) > LONG_WINDOW:
            self.long_sum = self.long_sum - self.closes[-LONG_WINDOW - 1]

    def learn_fill_price(self, cash, shares, last_response):
        """In the news-only run there is no bar, so read the price off our own last trade:
        the cash that moved divided by the shares that moved, with the fee taken out."""
        if self.before is None or last_response != "ACCEPT":
            return
        old_cash, old_shares = self.before
        moved = shares - old_shares
        if moved > 0:                                   # we bought
            self.price = (old_cash - cash) / (moved * (1 + FEE))
        elif moved < 0:                                 # we sold
            self.price = (cash - old_cash) / (-moved * (1 - FEE))

    # ---------- the two votes ----------

    def price_vote(self):
        """+1 on a dip worth buying, -1 once the price is back above its average, else 0."""
        if len(self.closes) < SHORT_WINDOW:
            return 0                                    # not enough history yet
        close = self.closes[-1]
        short_average = self.short_sum / SHORT_WINDOW
        if close > short_average:
            return -1
        if close < short_average * (1 - DIP):
            if len(self.closes) >= LONG_WINDOW:
                long_average = self.long_sum / LONG_WINDOW
                if close < long_average * BEAR_LIMIT:
                    return 0                            # falling knife: do not buy it
            return 1
        return 0

    def news_vote(self, headlines):
        """The week-4 sentiment score: split each headline into words and add their scores."""
        mood = 0
        for line in headlines:
            for word in line.lower().split():
                word = word.strip(":,.!?")
                if word in LEXICON:
                    mood = mood + LEXICON[word]
        return mood

    # ---------- the order ----------

    def buy_order(self, cash, shares):
        """How much to buy: top our shares up to TARGET of our money."""
        if self.price is None:
            return ("BUY", 1)          # news-only, first trade: one share tells us the price
        holding = shares * self.price
        money = cash + holding
        if holding >= money * TARGET / 2:
            return ("HOLD", 0)         # already invested enough
        count = int((money * TARGET - holding) / (self.price * (1 + FEE)))
        if count <= 0:
            return ("HOLD", 0)
        return ("BUY", count)

    def decide(self, bar, headlines, cash, shares, last_response):
        """Called once per day by the desk. Returns (action, amount)."""
        self.learn_fill_price(cash, shares, last_response)
        self.before = (cash, shares)

        vote = 0
        if bar is not None:                             # OHLCV-only and both runs
            self.remember_close(bar["close"])
            self.price = bar["close"]
            vote = vote + self.price_vote()
        if headlines is not None:                       # news-only and both runs
            vote = vote + self.news_vote(headlines)

        if vote < 0 and shares > 0:
            return ("SELL", -1)                         # get out completely
        if vote > 0:
            return self.buy_order(cash, shares)
        return ("HOLD", 0)
