# desk.py -- the Glacial Pace Capital trading desk: the text menu that starts the program.
# Reference: <full name of the desk reference member>
#
# Run it with:   python3 desk.py                     (on Windows: python desk.py)
# Optional settings, each with a default:
#   python3 desk.py --cash 5000 --shares 0 --ticker ZNTH --folder data/training/
#
# The desk owns the money for the manual session (an Account) and starts every agent run
# on a fresh Account of its own (the Simulator). A trade typed here fills at TODAY's
# close; an agent's order fills at TOMORROW's open.

import math
import sys

import analytics
import data_loader
from account import Account
from agent import TradingAgent
from simulator import Simulator, REGIMES
from storage import Storage
from strategies import BuyAndHoldAgent, HoldAgent

DEFAULT_CASH = 10000.0
DEFAULT_SHARES = 0.0
AGENTS = {"1": ("TradingAgent", TradingAgent), "2": ("BuyAndHold", BuyAndHoldAgent),
          "3": ("Hold", HoldAgent)}
REGIME_KEYS = {"b": "both", "p": "prices", "n": "news"}

MENU = """
========== Glacial Pace Capital trading desk ==========
 [1] Load dataset              [2] Set starting cash/shares
 [3] Step one day              [4] Manual buy
 [5] Manual sell               [6] Run agent to end
 [7] Show price chart          [8] Show equity + drawdown
 [9] Save / load / leaderboard [0] Quit
======================================================="""


# ---------- reading the keyboard safely ----------

def ask(prompt, default=""):
    """input() with a default shown in brackets; an empty answer means the default."""
    shown = prompt
    if default != "":
        shown = prompt + " [" + str(default) + "]"
    answer = input(shown + ": ").strip()
    if answer == "":
        return str(default)
    return answer


def ask_number(prompt, default):
    """Ask until the answer is a finite number. Returns a float."""
    while True:
        text = ask(prompt, default)
        try:
            value = float(text)
        except ValueError:
            print("  '" + text + "' is not a number, try again.")
            continue
        if not math.isfinite(value):
            print("  the amount has to be a finite number, try again.")
            continue
        return value


def parse_arguments(arguments):
    """Read --cash, --shares, --ticker and --folder from the command line.

    Every setting has a default, so the program also starts with no arguments at all."""
    settings = {"cash": DEFAULT_CASH, "shares": DEFAULT_SHARES, "ticker": "",
                "folder": data_loader.DEFAULT_FOLDER}
    i = 0
    while i < len(arguments):
        key = arguments[i].lstrip("-").lower()
        if key not in settings or i + 1 >= len(arguments):
            print("  (ignoring the command-line argument " + arguments[i] + ")")
            i = i + 1
            continue
        value = arguments[i + 1]
        if key in ("cash", "shares"):
            try:
                number = float(value)
                assert math.isfinite(number) and number >= 0
                settings[key] = number
            except (ValueError, AssertionError):
                print("  (--" + key + " " + value + " is not a usable amount; keeping "
                      + str(settings[key]) + ")")
        else:
            settings[key] = value
        i = i + 2
    return settings


# ---------- the desk ----------

class Desk:
    """The menu, the manual session and the last agent run."""

    def __init__(self, start_cash=DEFAULT_CASH, start_shares=DEFAULT_SHARES):
        self.market = None
        self.lexicon = {}
        self.start_cash = start_cash
        self.start_shares = start_shares
        self.account = Account(start_cash, start_shares)
        self.day = 0
        self.equity = []            # the manual session's equity, one value per day so far
        self.last_event = "none yet"
        self.last_run = None        # the latest RunResult from option 6
        self.run_saved = False
        self.storage = Storage()

    # ----- state shown after every action -----

    def price_today(self):
        return float(self.market.closes[self.day])

    def status(self):
        if self.market is None:
            return ("no dataset loaded | cash " + str(round(self.account.cash, 2))
                    + " | shares " + str(round(self.account.shares, 4)))
        price = self.price_today()
        headlines = self.market.headlines(self.day)
        mood = data_loader.mood_of(headlines, self.lexicon)
        return ("day " + str(self.day) + "/" + str(len(self.market) - 1)
                + " | price " + format(price, ".2f")
                + " | cash " + str(round(self.account.cash, 2))
                + " | shares " + str(round(self.account.shares, 4))
                + " | equity " + format(self.account.equity(price), ".2f")
                + "\n  news today: " + str(len(headlines)) + " headline(s), mood "
                + format(mood, "+.0f") + " | last event: " + self.last_event)

    def need_market(self):
        """True if a dataset is loaded; otherwise say what to do."""
        if self.market is None:
            print("  Load a dataset first (option 1).")
            return False
        return True

    def reset_session(self):
        """Back to day 0 with the starting balances."""
        self.account = Account(self.start_cash, self.start_shares)
        self.day = 0
        self.equity = []
        if self.market is not None:
            self.equity = [self.account.equity(self.price_today())]
        self.last_event = "session reset to day 0"

    # ----- the menu options -----

    def load_dataset(self, ticker="", folder=""):
        if ticker == "":
            ticker = ask("Ticker (e.g. VOLT, ZNTH, NOVA, QBIT)", "ZNTH")
        if folder == "":
            folder = ask("Data folder", data_loader.DEFAULT_FOLDER)
        try:
            market = data_loader.load_market(ticker, folder)
        except (FileNotFoundError, ValueError) as error:
            print("  Could not load: " + str(error))
            print("  Check the ticker and that the data sits in the folder you named.")
            return False
        except Exception as error:          # a damaged CSV pandas cannot parse
            print("  Could not read the price file: " + type(error).__name__ + ": "
                  + str(error))
            return False
        self.market = market
        self.lexicon = data_loader.load_lexicon(market.folder + data_loader.LEXICON_FILE)
        if len(self.lexicon) == 0:
            print("  (no sentiment_words.csv found: the news mood will show 0)")
        self.last_run = None
        self.reset_session()
        self.last_event = "loaded " + market.ticker
        print("  Loaded " + str(market) + ".")
        return True

    def set_balances(self):
        cash = ask_number("Starting cash (USD)", self.start_cash)
        shares = ask_number("Starting shares", self.start_shares)
        if cash < 0 or shares < 0:
            print("  Cash and shares cannot be negative: nothing changed.")
            return
        if cash == 0 and shares == 0:
            print("  An account with no cash and no shares cannot trade: nothing changed.")
            return
        self.start_cash = cash
        self.start_shares = shares
        self.reset_session()
        print("  Starting balances set: cash " + str(cash) + ", shares " + str(shares)
              + ". The session is back at day 0.")

    def step(self):
        if not self.need_market():
            return
        if self.day >= len(self.market) - 1:
            print("  Already at the last day of the data.")
            return
        self.day = self.day + 1
        self.equity.append(self.account.equity(self.price_today()))
        self.last_event = "stepped to day " + str(self.day)
        for line in self.market.headlines(self.day):
            print("  news: " + line)

    def manual_trade(self, action):
        """A trade typed at the desk fills at today's close, the price on the board."""
        if not self.need_market():
            return
        verb = "buy" if action == "BUY" else "sell"
        amount = ask_number("How many shares to " + verb + " (-1 = all/max)", -1)
        if amount < 0 and amount != -1:
            print("  A negative amount other than -1 makes no sense: nothing done.")
            return
        if amount == 0:
            print("  Zero shares: nothing to do.")
            return
        price = self.price_today()
        reply = self.account.execute(action, amount, price, day=self.day)
        self.equity[self.day] = self.account.equity(price)    # today's value has changed
        shown = "all/max" if amount == -1 else str(amount)
        self.last_event = (action + " " + shown + " at " + format(price, ".2f")
                           + " -> " + reply)
        print("  -> " + reply)

    def manual_buy(self):
        self.manual_trade("BUY")

    def manual_sell(self):
        self.manual_trade("SELL")

    def run_agent(self):
        if not self.need_market():
            return
        choice = ask("Agent: [1] TradingAgent  [2] BuyAndHold  [3] Hold", "1")
        if choice not in AGENTS:
            print("  No agent " + repr(choice) + ".")
            return
        regime_key = ask("What it sees: [b]oth, [p]rices only, [n]ews only", "b").lower()
        if regime_key not in REGIME_KEYS:
            print("  No such choice " + repr(regime_key) + ".")
            return
        name, agent_class = AGENTS[choice]
        try:
            simulator = Simulator(self.market, agent_class(), self.start_cash,
                                  self.start_shares, REGIME_KEYS[regime_key])
            result = simulator.run(name + " on " + self.market.ticker)
        except Exception as error:
            print("  The agent stopped the run: " + type(error).__name__ + ": " + str(error))
            return
        for problem in result.problems[:5]:
            print("  warning: " + problem)
        self.last_run = result
        self.run_saved = False
        self.last_event = "ran " + result.name + ", final " + format(result.final_equity, ".2f")
        print(result.summary())

    def chart_source(self):
        """(title, closes, trades, equity) of the agent run or of the manual session."""
        use_run = False
        if self.last_run is not None:
            use_run = ask("Charts for the [a]gent run or the [m]anual session", "a") != "m"
        if use_run:
            run = self.last_run
            return (run.name + " (" + run.regime + ")", self.market.closes,
                    run.trades, run.equity)
        return ("manual session on " + self.market.ticker,
                self.market.closes[:self.day + 1], self.account.trades, self.equity)

    def show_price_chart(self):
        if not self.need_market():
            return
        title, closes, trades, equity = self.chart_source()
        analytics.plot_price_with_trades(closes, trades, "Price with trades: " + title)

    def show_equity_charts(self):
        if not self.need_market():
            return
        title, closes, trades, equity = self.chart_source()
        if len(equity) < 2:
            print("  Only one day so far: step forward or run the agent first.")
            return
        print("  return " + format(analytics.total_return(equity) * 100, ".1f")
              + "% | max drawdown " + format(-analytics.max_drawdown(equity) * 100, ".1f")
              + "% | sharpe-like " + format(analytics.sharpe_like(equity), ".3f"))
        analytics.plot_equity(equity, "Equity curve: " + title)
        analytics.plot_drawdown(equity, "Drawdown: " + title)

    def save_or_load(self):
        choice = ask("[s]ave, [l]oad, or show the leader[b]oard", "s").lower()
        try:
            if choice == "s":
                self.save()
            elif choice == "l":
                self.load()
            elif choice == "b":
                self.print_leaderboard()
            else:
                print("  No such choice " + repr(choice) + ".")
        except OSError as error:
            print("  The file could not be used: " + str(error))

    def save(self):
        if self.market is not None:
            values = {"ticker": self.market.ticker, "folder": self.market.folder,
                      "day": self.day, "cash": self.account.cash,
                      "shares": self.account.shares, "start_cash": self.start_cash,
                      "start_shares": self.start_shares}
            self.storage.save_session(values, self.equity, self.account.trades)
            print("  Saved the session to " + self.storage.session_file + ".")
        if self.last_run is not None and not self.run_saved:
            self.storage.save_result(self.last_run)
            self.run_saved = True
            print("  Saved the run to " + self.storage.results_file + " and the leaderboard"
                  " to " + self.storage.leaderboard_file + ".")
        elif self.market is None:
            print("  Nothing to save yet: load a dataset or run an agent first.")

    def load(self):
        try:
            values = self.storage.load_session()
        except FileNotFoundError:
            print("  No saved session (" + self.storage.session_file + ") yet.")
            self.print_leaderboard()
            return
        except ValueError as error:
            print("  The saved session is damaged: " + str(error))
            return
        if not self.load_dataset(values["ticker"], values["folder"]):
            return
        if values["day"] < 0 or values["day"] > len(self.market) - 1:
            print("  The saved day is outside this market: starting at day 0.")
            return
        self.start_cash = values["start_cash"]
        self.start_shares = values["start_shares"]
        self.account = Account(values["cash"], values["shares"])
        self.account.trades = values["trades"]
        self.day = values["day"]
        self.equity = values["equity"]
        if len(self.equity) != self.day + 1:          # an older file without the history
            self.equity = [self.account.equity(self.price_today())] * (self.day + 1)
        self.last_event = "loaded session"
        print("  Loaded session: " + self.market.ticker + " day " + str(self.day) + ".")
        self.print_leaderboard()

    def print_leaderboard(self):
        board = self.storage.load_leaderboard()
        if len(board) == 0:
            print("  The leaderboard is empty: run an agent (6), then save (9).")
            return
        print("  Leaderboard, best final equity first:")
        for rank, name, final in board[:10]:
            print("  " + str(rank) + ". " + name + "  " + format(final, ".2f"))

    # ----- the loop -----

    def run(self):
        actions = {"1": self.load_dataset, "2": self.set_balances, "3": self.step,
                   "4": self.manual_buy, "5": self.manual_sell, "6": self.run_agent,
                   "7": self.show_price_chart, "8": self.show_equity_charts,
                   "9": self.save_or_load}
        choice = ""
        while choice != "0":
            print(MENU)
            choice = ask("Choose")
            if choice in actions:
                actions[choice]()
                print("  " + self.status())
            elif choice != "0":
                print("  Please type a number from 0 to 9.")
        print("Goodbye.")


def main():
    settings = parse_arguments(sys.argv[1:])
    desk = Desk(settings["cash"], settings["shares"])
    print("Welcome. Starting cash " + str(desk.start_cash) + ", shares "
          + str(desk.start_shares) + ".")
    try:
        if settings["ticker"] != "":
            desk.load_dataset(settings["ticker"], settings["folder"])
            print("  " + desk.status())
        desk.run()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
