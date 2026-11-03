# data_loader.py -- reading the market files, kept apart from any strategy.
# Reference: <full name of the data-loading reference member>
#
# The training files are read exactly as distributed, at run time, every time. Nothing
# here converts, cleans or re-saves them; a held-back market in the same schema loads
# with no change.

import numpy as np
import pandas as pd

DEFAULT_FOLDER = "data/training/"
PRICE_COLUMNS = ["day", "open", "high", "low", "close", "volume"]
LEXICON_FILE = "sentiment_words.csv"


class MarketData:
    """One market: its price bars (as numpy arrays) and its headlines (a dict by day)."""

    def __init__(self, ticker, folder, opens, highs, lows, closes, volumes, news):
        self.ticker = ticker
        self.folder = folder
        self.opens = opens
        self.highs = highs
        self.lows = lows
        self.closes = closes
        self.volumes = volumes
        self.news = news            # {day: [headline, ...]}; a day with no news is absent

    def __len__(self):
        return len(self.closes)

    def __str__(self):
        return self.ticker + " (" + str(len(self)) + " days, from " + self.folder + ")"

    def bar(self, day):
        """The price bar of one day, as the dict the agent contract describes."""
        return {"open": float(self.opens[day]), "high": float(self.highs[day]),
                "low": float(self.lows[day]), "close": float(self.closes[day]),
                "volume": float(self.volumes[day])}

    def headlines(self, day):
        """The headlines of one day: an empty list on a day without news."""
        if day in self.news:
            return list(self.news[day])
        return []


def normalise_folder(folder):
    """Make sure a folder name ends in a slash, so a file name can be added to it."""
    folder = folder.strip()
    if folder == "":
        return DEFAULT_FOLDER
    if not folder.endswith("/") and not folder.endswith("\\"):
        folder = folder + "/"
    return folder


def load_prices(path):
    """Read a <TICKER>.csv into five numpy arrays (open, high, low, close, volume).

    pandas reads the table; the hand-over to numpy happens here, once, so that every
    later slice is positional (see the time-series supplement's trap)."""
    frame = pd.read_csv(path)
    for column in PRICE_COLUMNS:
        if column not in frame.columns:
            raise ValueError(path + " has no '" + column + "' column")
    if len(frame) < 2:
        raise ValueError(path + " needs at least two days of prices")
    opens = np.array(frame["open"], dtype=float)
    highs = np.array(frame["high"], dtype=float)
    lows = np.array(frame["low"], dtype=float)
    closes = np.array(frame["close"], dtype=float)
    volumes = np.array(frame["volume"], dtype=float)
    if np.isnan(opens).any() or np.isnan(closes).any():
        raise ValueError(path + " has a missing open or close price")
    if (closes <= 0).any() or (opens <= 0).any():
        raise ValueError(path + " has a price that is zero or negative")
    return opens, highs, lows, closes, volumes


def load_news(path):
    """Read a <TICKER>_news.txt into {day: [headline, ...]}.

    split(",", 1) splits only at the first comma, so a headline that ever holds a comma
    stays whole. A line that cannot be read is skipped and counted, not fatal."""
    news = {}
    skipped = 0
    handle = open(path, encoding="utf-8")
    for line in handle:
        line = line.strip()
        if line == "" or line.startswith("day"):
            continue                            # blank line or the header
        parts = line.split(",", 1)
        try:
            day = int(parts[0])
            headline = parts[1].strip()
        except (ValueError, IndexError):
            skipped = skipped + 1
            continue
        if day not in news:
            news[day] = []
        news[day].append(headline)
    handle.close()
    if skipped > 0:
        print("  (skipped " + str(skipped) + " unreadable line(s) in " + path + ")")
    return news


def load_lexicon(path):
    """Read sentiment_words.csv into {word: score}. Missing file: an empty dict."""
    scores = {}
    try:
        handle = open(path, encoding="utf-8")
    except FileNotFoundError:
        return scores
    for line in handle:
        if line.startswith("word"):
            continue
        parts = line.strip().split(",")
        if len(parts) == 2:
            try:
                scores[parts[0]] = float(parts[1])
            except ValueError:
                continue
    handle.close()
    return scores


def load_market(ticker, folder=DEFAULT_FOLDER):
    """Load one market by ticker. The prices are required; the news is optional.

    Raises FileNotFoundError or ValueError with a message a user can act on."""
    ticker = ticker.strip().upper()
    if ticker == "":
        raise ValueError("no ticker given")
    folder = normalise_folder(folder)
    price_path = folder + ticker + ".csv"
    try:
        opens, highs, lows, closes, volumes = load_prices(price_path)
    except FileNotFoundError:
        raise FileNotFoundError("cannot find " + price_path)
    try:
        news = load_news(folder + ticker + "_news.txt")
    except FileNotFoundError:
        print("  (no news file for " + ticker + ": loading the prices only)")
        news = {}
    return MarketData(ticker, folder, opens, highs, lows, closes, volumes, news)


def mood_of(headlines, lexicon):
    """Sum of the lexicon scores of every word in a list of headlines."""
    total = 0.0
    for line in headlines:
        for word in line.lower().split():
            total = total + lexicon.get(word.strip(":,.!?"), 0.0)
    return total
