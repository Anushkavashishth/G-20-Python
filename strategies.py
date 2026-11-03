# strategies.py -- simple benchmark agents to compare our TradingAgent against.
# Reference: <full name of the agent reference member>
#
# These live outside agent.py on purpose: agent.py must stand alone for the competition,
# so it cannot inherit from anything here. The benchmarks share a base class instead.
# Each has the same decide() signature as the contract, so the Simulator runs any of them.


class BaseAgent:
    """The shape every agent has. A subclass must write its own decide()."""

    name = "BaseAgent"

    def decide(self, bar, headlines, cash, shares, last_response):
        raise NotImplementedError("a subclass of BaseAgent must define decide()")

    def __str__(self):
        return self.name


class HoldAgent(BaseAgent):
    """Never trades: the 'do nothing' baseline."""

    name = "Hold"

    def decide(self, bar, headlines, cash, shares, last_response):
        return ("HOLD", 0)


class BuyAndHoldAgent(BaseAgent):
    """Buys everything on the first day and keeps it: the classic benchmark."""

    name = "BuyAndHold"

    def decide(self, bar, headlines, cash, shares, last_response):
        if shares == 0 and cash > 0:
            return ("BUY", -1)
        return ("HOLD", 0)
