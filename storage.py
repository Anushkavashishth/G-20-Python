# storage.py -- saving and loading our own outputs, in plain text.
# Reference: <full name of the saving-and-tests reference member>
#
# Three files, all ours (the market data is never written):
#   results.txt      one line per saved run:  name,final_equity,trades,return,max_dd,sharpe
#   leaderboard.txt  rewritten from every saved run, best final equity first:
#                    rank,name,final_equity
#   session.txt      the manual session, one key=value per line; its equity history is
#                    equity=v0;v1;... and its trades trades=day:action:shares:price|...
# Storage is the one class that knows these line formats; the desk only asks it to save
# and load.

RESULTS_FILE = "results.txt"
LEADERBOARD_FILE = "leaderboard.txt"
SESSION_FILE = "session.txt"
LEADERBOARD_HEADER = "rank,name,final_equity"
SESSION_KEYS = ("ticker", "folder", "day", "cash", "shares", "start_cash", "start_shares")


class Storage:
    """Reads and writes the results, the leaderboard and the session."""

    def __init__(self, results_file=RESULTS_FILE, leaderboard_file=LEADERBOARD_FILE,
                 session_file=SESSION_FILE):
        self.results_file = results_file
        self.leaderboard_file = leaderboard_file
        self.session_file = session_file

    # ---------- one line <-> one result ----------

    def format_result(self, name, final_equity, trades, total_return, max_dd, sharpe):
        """One result as one line. Commas in the name would break the format, so swap them."""
        name = name.replace(",", ";")
        return (name + "," + format(final_equity, ".2f") + "," + str(trades) + ","
                + format(total_return, ".6f") + "," + format(max_dd, ".6f") + ","
                + format(sharpe, ".6f"))

    def parse_result(self, line):
        """One line back into (name, final_equity, trades, return, max_dd, sharpe).

        Raises ValueError for a line that is not a result."""
        parts = line.strip().split(",")
        if len(parts) != 6:
            raise ValueError("expected 6 fields, found " + str(len(parts)))
        return (parts[0], float(parts[1]), int(parts[2]), float(parts[3]),
                float(parts[4]), float(parts[5]))

    # ---------- results and leaderboard ----------

    def load_results(self):
        """Every saved run. A missing file is an empty list; a damaged line is skipped."""
        results = []
        try:
            handle = open(self.results_file, encoding="utf-8")
        except FileNotFoundError:
            return results
        number = 0
        for line in handle:
            number = number + 1
            if line.strip() == "":
                continue
            try:
                results.append(self.parse_result(line))
            except ValueError as error:
                print("  (skipped line " + str(number) + " of " + self.results_file
                      + ": " + str(error) + ")")
        handle.close()
        return results

    def save_result(self, run):
        """Append one RunResult to results.txt, then rewrite the leaderboard.

        Appending is O(1) in the number of saved runs; the leaderboard rewrite reads and
        sorts every run, O(k log k) for k runs."""
        line = self.format_result(run.name + " [" + run.regime + "]", run.final_equity,
                                  len(run.trades), run.total_return, run.max_drawdown,
                                  run.sharpe)
        handle = open(self.results_file, "a", encoding="utf-8")
        handle.write(line + "\n")
        handle.close()
        self.write_leaderboard()

    def leaderboard(self):
        """[(rank, name, final_equity)], best final equity first."""
        rows = [[result[1], result[0]] for result in self.load_results()]
        rows.sort()
        rows.reverse()
        board = []
        rank = 1
        for final, name in rows:
            board.append((rank, name, final))
            rank = rank + 1
        return board

    def write_leaderboard(self):
        handle = open(self.leaderboard_file, "w", encoding="utf-8")
        handle.write(LEADERBOARD_HEADER + "\n")
        for rank, name, final in self.leaderboard():
            handle.write(str(rank) + "," + name + "," + format(final, ".2f") + "\n")
        handle.close()

    def load_leaderboard(self):
        """Read leaderboard.txt back. Missing file: an empty list."""
        board = []
        try:
            handle = open(self.leaderboard_file, encoding="utf-8")
        except FileNotFoundError:
            return board
        for line in handle:
            parts = line.strip().split(",")
            if len(parts) != 3 or parts[0] == "rank":
                continue
            try:
                board.append((int(parts[0]), parts[1], float(parts[2])))
            except ValueError:
                continue
        handle.close()
        return board

    # ---------- the manual session ----------

    def save_session(self, values, equity, trades):
        """values is a dict with every key in SESSION_KEYS; equity a list of numbers;
        trades a list of (day, action, shares, price)."""
        handle = open(self.session_file, "w", encoding="utf-8")
        for key in SESSION_KEYS:
            handle.write(key + "=" + str(values[key]) + "\n")
        handle.write("equity=" + ";".join([format(v, ".6f") for v in equity]) + "\n")
        parts = []
        for day, action, shares, price in trades:
            parts.append(str(day) + ":" + action + ":" + str(shares) + ":" + str(price))
        handle.write("trades=" + "|".join(parts) + "\n")
        handle.close()

    def load_session(self):
        """The saved session as a dict, typed. Raises FileNotFoundError or ValueError."""
        values = {}
        handle = open(self.session_file, encoding="utf-8")
        for line in handle:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                values[key] = value
        handle.close()
        for key in SESSION_KEYS:
            if key not in values:
                raise ValueError(self.session_file + " has no '" + key + "' line")
        values["day"] = int(values["day"])
        for key in ("cash", "shares", "start_cash", "start_shares"):
            values[key] = float(values[key])
        equity = []
        if values.get("equity", "") != "":
            equity = [float(v) for v in values["equity"].split(";")]
        trades = []
        if values.get("trades", "") != "":
            for item in values["trades"].split("|"):
                day, action, shares, price = item.split(":")
                trades.append((int(day), action, float(shares), float(price)))
        values["equity"] = equity
        values["trades"] = trades
        return values
