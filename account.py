# account.py -- the authority: the desk's ledger of cash and shares.
# Reference: <full name of the account-and-engine reference member>
#
# Every order, the agent's and the manual ones, goes through Account.execute. It is the
# only code in the program that changes cash or shares, and it can refuse.

import math

FEE = 0.001     # 0.1% charged on every buy and every sell
ACTIONS = ("BUY", "SELL", "HOLD")


def is_valid_order(order):
    """True for a well-formed order: a 2-item tuple or list, a known action, a finite number."""
    if not isinstance(order, (tuple, list)) or len(order) != 2:
        return False
    action, amount = order[0], order[1]
    if action not in ACTIONS:
        return False
    if isinstance(amount, bool):
        return False
    try:
        return math.isfinite(float(amount))
    except (TypeError, ValueError, OverflowError):
        return False


class Account:
    """Cash and shares, the fee, and the exact accept / reject replies of the contract."""

    def __init__(self, cash=10000.0, shares=0.0):
        assert cash >= 0, "cash cannot be negative"
        assert shares >= 0, "shares cannot be negative"
        self.cash = float(cash)
        self.shares = float(shares)
        self.trades = []            # one (day, action, shares, price) per filled order

    def __str__(self):
        return "cash " + str(round(self.cash, 2)) + " | shares " + str(round(self.shares, 4))

    def equity(self, price):
        """What the account is worth at a price: cash plus the value of the shares."""
        return self.cash + self.shares * price

    def max_affordable(self, price):
        """The largest whole number of shares the cash covers after the fee."""
        count = int(self.cash / (price * (1 + FEE)))
        # A division that lands exactly on a whole share can round up: take it back.
        if count > 0 and count * price * (1 + FEE) > self.cash:
            count = count - 1
        return count

    def execute(self, action, amount, price, day=None):
        """Carry out one order at one price and return the reply string.

        amount is a number of shares; any negative amount means "as much as possible".
        An order fills whole or not at all: a refused order changes nothing."""
        if action not in ACTIONS:
            raise ValueError("unknown action " + repr(action))
        amount = float(amount)
        if not math.isfinite(amount) or price <= 0:
            raise ValueError("an order needs a finite amount and a positive price")

        if action == "BUY":
            if amount < 0:
                amount = self.max_affordable(price)
            if amount == 0:
                return "ACCEPT"                     # nothing to buy
            cost = amount * price * (1 + FEE)
            if cost > self.cash:
                return "REJECT currency balance: " + str(round(self.cash, 2))
            self.cash = self.cash - cost
            self.shares = self.shares + amount
            self.trades.append((day, "BUY", amount, price))
            return "ACCEPT"

        if action == "SELL":
            if amount < 0:
                amount = self.shares
            if amount == 0:
                return "ACCEPT"                     # nothing to sell
            if amount > self.shares:
                return "REJECT stock owned: " + str(round(self.shares, 2))
            self.cash = self.cash + amount * price * (1 - FEE)
            self.shares = self.shares - amount
            self.trades.append((day, "SELL", amount, price))
            return "ACCEPT"

        return "ACCEPT"                             # HOLD
