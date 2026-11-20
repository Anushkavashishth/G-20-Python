GROUP_CODE = "G20-G7NR"       
# Group: Dev Madanlal Malviya, Atharva Zade, Dhruv Rastogi, Anushka Vashishth, Shefali Mathur, Boyang Gao 
# Reference: G7NR

FEE = 0.001                
TARGET = 0.4              
SHORT_WINDOW = 10          
LONG_WINDOW = 100          
DIP = 0.02                 
BEAR_LIMIT = 0.90          

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
        self.closes = []          
        self.short_sum = 0.0      
        self.long_sum = 0.0       
        self.price = None         
        self.before = None       

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

    def price_vote(self):
        """+1 on a dip worth buying, -1 once the price is back above its average, else 0."""
        if len(self.closes) < SHORT_WINDOW:
            return 0                                    
        close = self.closes[-1]
        short_average = self.short_sum / SHORT_WINDOW
        if close > short_average:
            return -1
        if close < short_average * (1 - DIP):
            if len(self.closes) >= LONG_WINDOW:
                long_average = self.long_sum / LONG_WINDOW
                if close < long_average * BEAR_LIMIT:
                    return 0                            
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

    def buy_order(self, cash, shares):
        """How much to buy: top our shares up to TARGET of our money."""
        if self.price is None:
            return ("BUY", 1)          
        holding = shares * self.price
        money = cash + holding
        if holding >= money * TARGET / 2:
            return ("HOLD", 0)         
        count = int((money * TARGET - holding) / (self.price * (1 + FEE)))
        if count <= 0:
            return ("HOLD", 0)
        return ("BUY", count)

    def decide(self, bar, headlines, cash, shares, last_response):
        """Called once per day by the desk. Returns (action, amount)."""
        self.learn_fill_price(cash, shares, last_response)
        self.before = (cash, shares)

        vote = 0
        if bar is not None:                             
            self.remember_close(bar["close"])
            self.price = bar["close"]
            vote = vote + self.price_vote()
        if headlines is not None:                       
            vote = vote + self.news_vote(headlines)

        if vote < 0 and shares > 0:
            return ("SELL", -1)                        
        if vote > 0:
            return self.buy_order(cash, shares)
        return ("HOLD", 0)
