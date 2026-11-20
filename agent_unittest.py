import ast
import math
import numbers
import sys

FEE = 0.001            
ALLOWED_IMPORTS = ("numpy", "pandas", "math", "random")


COMPETITION_LIBRARIES = (("numpy", 2), ("pandas", 3))
OLDER_LIBRARIES = "older than the competition's"
COMPETITION_STACK = (("Python", "3.12"), ("numpy", "2.5.3"), ("pandas", "3.0.6"))
CODE_ALPHABET = "34679ACDEFGHJKLMNPQRTUVWXY"
CODE_WEIGHTS = (3, 5, 7, 9, 11)
CODE_PLACEHOLDER = "GXX-XXXX"

ALL_CHECK_IDS = ("self_contained", "group_code", "loads", "regime_ohlcv", "regime_news",
                 "regime_both", "reject_reply", "none_last_response", "no_io",
                 "banned_shortcuts")


READ_CALLS = ("input", "eval", "exec", "__import__",
              "read_csv", "read_json", "read_pickle", "read_excel", "read_table",
              "read_fwf", "read_html", "read_parquet", "read_feather", "read_hdf",
              "read_sql", "read_xml", "read_clipboard",
              "loadtxt", "genfromtxt", "fromfile")


WRITE_CALLS = ("to_csv", "to_json", "to_xml", "to_pickle", "to_excel", "to_parquet",
               "to_feather", "to_hdf", "to_sql", "savetxt", "tofile")
WRITES_ONLY_WITH_PATH = ("to_csv", "to_json", "to_xml")
WRITE_WARNING = ("allowed on your own machine, for debugging; remove it before you submit: "
                 "the online check and the competition run agent.py where nothing can be "
                 "written, so there the write fails with OSError")


ALL_WARNING_IDS = ("writes_file", "never_traded", "unnamed")


NAMES_WARNING = ("under GROUP_CODE, add a '# Group:' comment with every member's full "
                 "name and a '# Reference:' comment with the member who makes any live "
                 "change to this file at the interview; the checks pass either way")


BANNED_SHORTCUTS = ("rolling", "shift", "pct_change", "cumprod")


def load_agent():
    """Import TradingAgent from agent.py and return (class, error_message).

    Deliberately NOT a module-level import, so that a broken agent.py becomes a reported
    FAIL rather than a traceback. Note it is the TEXT scan above, not this import, that
    catches you importing your own project files: those files sit next to agent.py on
    your machine, so the import succeeds here and fails in the competition, which loads
    agent.py on its own."""
    try:
        import agent
    except BaseException as error:

        return None, error_with_line(error) + not_installed(error)
    newer_only = fails_on_python_312(agent)
    if newer_only != "":
        return None, newer_only
    TradingAgent = getattr(agent, "TradingAgent", None)
    if TradingAgent is None:
        
        return None, ("agent.py has no class named TradingAgent -- the name is exact, "
                      "capitals included")
    return TradingAgent, ""


def not_installed(error):
    """The fix, when agent.py imports numpy or pandas and this Python does not have it.

    Both are allowed, so the finding is about this machine, not the file: without the
    hint, "No module named 'numpy'" under "loads on its own" reads as a forbidden
    import. pip installs into the Python that runs it, so the command has to be the one
    that runs this file (review 184). Only when the library itself is missing: `from numpy
    import NaN`, a name numpy 2 removed, and a submodule that does not exist are
    ImportErrors that name numpy too, and installing would mend neither (review 186)."""
    name = getattr(error, "name", None)
    if not isinstance(error, ModuleNotFoundError) or name not in ("numpy", "pandas"):
        return ""
    return (" -- " + name + " is allowed, but not installed for this Python: run "
            "python3 -m pip install numpy pandas matplotlib (on Windows, python -m pip "
            "...), with the same command you run this file with")


def stack_here():
    """"Python 3.15.0, numpy 2.5.4, pandas 3.0.6" for the Python running this file.

    selfcheck.py prints it inside each figure line, so the figures in a report say which
    stack made them: a re-run on another stack can then be told apart from a changed agent
    (review 185). Read from the package metadata, so nothing is imported."""
    parts = ["Python " + ".".join(str(part) for part in sys.version_info[:3])]
    try:
        from importlib import metadata
    except ImportError:                       
        return parts[0]
    for name in ("numpy", "pandas"):
        try:
            parts.append(name + " " + metadata.version(name))
        except Exception:                    
            parts.append(name + " not installed")
    return ", ".join(parts)


def competition_stack():
    """"Python 3.12, numpy 2.5.3, pandas 3.0.6": the stack the online check and the
    competition run, which selfcheck.py names under the figures so a student can compare."""
    return ", ".join(name + " " + version for name, version in COMPETITION_STACK)


def older_libraries():
    """[(name, version)] for numpy or pandas installed here at an older major version
    than the competition runs. Read from the installed package's metadata, so nothing is
    imported; a library that is not installed is not listed (an agent that imports it
    fails its loads check, with the fix)."""
    try:
        from importlib import metadata
    except ImportError:                      
        return []
    older = []
    for name, major in COMPETITION_LIBRARIES:
        try:
            installed = metadata.version(name)
            if int(installed.split(".")[0]) < major:
                older.append((name, installed))
        except Exception:                     
            continue
    return older


def older_libraries_warning(older):
    """(name, detail) of the warning for libraries older than the competition's."""
    found = ", ".join(name + " " + version for name, version in older)
    if sys.version_info < (3, 11):
        fix = ("pandas 3 needs Python 3.11 or newer, and this is "
               + ".".join(str(part) for part in sys.version_info[:3])
               + ": install the current Python from python.org, then python3 -m pip "
               "install numpy pandas matplotlib with it, and run this file with it")
    else:
        fix = ("update them: python3 -m pip install --upgrade numpy pandas (on Windows, "
               "python -m pip ...), with the same command you run this file with")
    return (found + " here, " + OLDER_LIBRARIES,
            "the competition runs numpy 2 and pandas 3, and your agent can trade "
            "differently there: pandas 3 never lets chained assignment, "
            "df[\"col\"][i] = x, change the frame. " + fix)


def fails_on_python_312(agent):
    """The error Python 3.12 gives agent.py, as "line 9: SyntaxError: ...", when it uses a
    form that loads only from Python 3.14 on; "" when it uses neither. The online check and
    the competition run Python 3.12, where such a file does not load at all, so it fails the
    'loads' check here on every version. The two forms:

    * `except A, B:` without its parentheses, which reads as `except (A, B):` from 3.14 on
      and is a SyntaxError before. Python's own reading of the file (`ast`) keeps a tuple of
      types either way, so the text of the tuple tells them apart: written with
      parentheses, it starts with the `(` that closes at its end.
    * a type hint naming something that does not exist. From 3.14 a hint is read only when
      something asks for it; 3.12 reads each hint of a function, a class and the file as it
      is defined, and stops with a NameError. Asking for every hint here reads them all.
      One case still passes here and fails on 3.12: a hint naming a class written lower in
      the file, which exists by the time this asks. The course never needs a type hint.

    Before 3.14 neither form gets past the import, so there is nothing to look for: and on
    3.9 a file without hints has no __annotations__ at all, so asking for it failed every
    agent there (review 184)."""
    if sys.version_info < (3, 14):
        return ""
    lines = read_agent_source() or []
    source = "".join(lines)
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return ""
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Tuple):
            if not in_parentheses(ast.get_source_segment(source, node.type) or ""):
                return ("line " + str(node.lineno) + ": SyntaxError: multiple exception "
                        "types must be parenthesized")
    for thing in hinted(agent):
        try:
            thing.__annotations__
        except BaseException as error:
            return error_with_line(error, called=thing)
    return ""


def in_parentheses(text):
    """True when the text is one pair of parentheses around everything: "(A, B)" is,
    "A, B" and "(A), (B)" are not."""
    if not text.startswith("("):
        return False
    depth = 0
    for position in range(len(text)):
        if text[position] == "(":
            depth = depth + 1
        elif text[position] == ")":
            depth = depth - 1
            if depth == 0:
                return position == len(text) - 1
    return False


def hinted(agent):
    """Everything in agent.py that can carry type hints: the file itself, the functions and
    classes it defines, and the methods of those classes, properties included."""
    found = [agent]
    for value in list(vars(agent).values()):
        if written_in_agent(value):
            found.append(value)
        elif isinstance(value, type) and value.__dict__.get("__module__") == agent.__name__:
            found.append(value)
            for member in list(vars(value).values()):
                for part in (member, read_quietly(member, "__func__"),
                             read_quietly(member, "fget"), read_quietly(member, "fset")):
                    if written_in_agent(part):
                        found.append(part)
    return found


def read_quietly(thing, name):
    """thing.name, or None when it has none or asking raises: an object of the agent's own
    may raise on any name it is asked for."""
    try:
        return getattr(thing, name, None)
    except BaseException:
        return None


def written_in_agent(thing):
    """True for a function written in agent.py."""
    code = read_quietly(thing, "__code__")
    return code is not None and is_agent_file(read_quietly(code, "co_filename") or "")


def is_agent_file(filename):
    """True for agent.py itself, wherever it sits: the name at the end of a path."""
    return str(filename).replace("\\", "/").split("/")[-1] == "agent.py"


CTRL_C = "stopped with Ctrl-C"


def defined_at(thing):
    """The line of agent.py where a function, a method or a class is defined, or 0.

    A class is found by reading the structure of agent.py with `ast`, as scan_code does,
    and the last class of that name wins, because that is the one Python keeps. Searching
    the text named the wrong line three ways: `class TradingAgentBase` above the agent
    starts with the same words, an older TradingAgent left above the new one comes first,
    and a string can hold a line that reads like a class.

    Never raises. It runs inside the handlers that report an agent's error, on whatever the
    agent's decide turned out to be, and an object whose own attribute lookup raises would
    otherwise escape the handler and take the whole report with it."""
    try:
        code = getattr(getattr(thing, "__func__", thing), "__code__", None)
        if code is not None and is_agent_file(code.co_filename):
            return code.co_firstlineno
        if isinstance(thing, type):
            line = 0
            for node in ast.walk(ast.parse("".join(read_agent_source() or []))):
                if isinstance(node, ast.ClassDef) and node.name == thing.__name__:
                    line = max(line, node.lineno)
            return line
    except BaseException:
        return 0
    return 0


def error_with_line(error, called=None):
    """'line 12: TypeError: ...' when the error went through agent.py, else 'TypeError: ...'.

    The line is the deepest one in agent.py the error passed through: where your code was
    when it went wrong, even when the error itself was raised inside pandas. A syntax error
    carries its own line, because the file never ran. Ctrl-C is reported as where your agent
    was when you pressed it, which is how a loop that never ends shows its line.

    `called` is what was being called when the error came. An error raised by the call
    itself never enters agent.py: decide() written with four parameters fails before its
    first line runs. The line named is then the one where `called` is defined, which is the
    line to fix."""
    if isinstance(error, SyntaxError) and error.lineno and is_agent_file(error.filename or ""):
        return ("line " + str(error.lineno) + ": " + type(error).__name__ + ": "
                + str(error.msg))
    try:
        message = str(error)
    except Exception:  
        message = ""
    if isinstance(error, KeyboardInterrupt):
        text = CTRL_C + " while your agent was running this line -- a loop that never ends?"
    elif message == "":
        text = type(error).__name__
    else:
        text = type(error).__name__ + ": " + message
    line = 0
    step = error.__traceback__
    while step is not None:
        if is_agent_file(step.tb_frame.f_code.co_filename):
            line = step.tb_lineno
        step = step.tb_next
    if line == 0 and called is not None:
        line = defined_at(called)
    if line == 0:
        if isinstance(error, KeyboardInterrupt):
            return CTRL_C
        return text
    return "line " + str(line) + ": " + text


def decide_of(agent):
    """What an error from calling decide() should point at: decide itself, or the class
    when it has no decide at all or looking it up raises.

    Never raises. It is called inside the handlers that report the error, and getattr with
    a default absorbs only AttributeError: a decide written as a property that raises would
    otherwise escape there and take the whole report with it."""
    try:
        found = getattr(agent, "decide", None)
    except BaseException:
        return type(agent)
    return found if found is not None else type(agent)


def call_decide(agent, bar, news, cash, shares, last_response):
    """Call agent.decide(...) and return (its order, the line of the return that gave it).

    The line comes from watching agent.py run (sys.settrace), so a malformed order can be
    pointed at: "line 21: got ('BUY', nan)". It is 0 when no return in agent.py was seen."""
    seen = [0]

    def inside_agent(frame, event, arg):
        if event == "return" and frame.f_code.co_name == "decide":
            seen[0] = frame.f_lineno
        return inside_agent

    def watch(frame, event, arg):
        if is_agent_file(frame.f_code.co_filename):
            return inside_agent
        return None

    before = sys.gettrace()
    sys.settrace(watch)
    try:
        order = agent.decide(bar, news, cash, shares, last_response)
    finally:
        sys.settrace(before)
    return order, seen[0]


def at_line(number):
    """'line 12: ' in front of a detail, or nothing when the line is not known."""
    if number:
        return "line " + str(number) + ": "
    return ""

def plain(amount):
    """An order's amount as Python's own number: a count that came out of numpy becomes an
    int, a numpy float a float, so the cash and shares it changes stay plain floats."""
    if isinstance(amount, bool) or not isinstance(amount, numbers.Real):
        return amount
    if isinstance(amount, numbers.Integral):
        return int(amount)
    return float(amount)


class FakeInterface:
    def __init__(self, cash):
        self.cash = float(cash)
        self.shares = 0.0

    def execute(self, order, price):
        action = order[0]
        amount = plain(order[1])
        if action == "BUY":
            if amount < 0:
                amount = int(self.cash / (price * (1.0 + FEE)))
                
                if amount * price * (1.0 + FEE) > self.cash:
                    amount = amount - 1
            if amount <= 0:
                return "ACCEPT"
            cost = amount * price * (1.0 + FEE)
            if cost > self.cash:
                return "REJECT currency balance: " + str(round(self.cash, 2))
            self.cash = self.cash - cost
            self.shares = self.shares + amount
            return "ACCEPT"
        if action == "SELL":
            if amount < 0:
                amount = self.shares
            if amount <= 0:
                return "ACCEPT"
            if amount > self.shares:
                return "REJECT stock owned: " + str(round(self.shares, 2))
            self.cash = self.cash + amount * price * (1.0 - FEE)
            self.shares = self.shares - amount
            return "ACCEPT"
        return "ACCEPT"

FAKE_BARS = [
    {"open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000.0},
    {"open": 101.0, "high": 103.0, "low": 100.0, "close": 100.0, "volume": 1200.0},
    {"open": 100.0, "high": 101.0, "low": 98.0, "close": 99.0, "volume": 900.0},
    {"open": 99.0, "high": 104.0, "low": 99.0, "close": 103.0, "volume": 1500.0},
    {"open": 103.0, "high": 106.0, "low": 102.0, "close": 105.0, "volume": 1700.0},
]
FAKE_NEWS = [
    ["VOLT surge as market rally"],
    ["VOLT slump amid selloff fear"],
    ["analysts update on VOLT today"],
    ["VOLT breakout as inflow boom"],
    ["VOLT drop as outflow panic"],
]


def is_valid_order(order):
    """An order must be a tuple/list (action, amount): a known action and a FINITE number.

    Any real number counts, a share count worked out with numpy included: `np.int64` is
    neither an int nor a float, and until 13 October 2026 it made a malformed order."""
    if not isinstance(order, (tuple, list)) or len(order) != 2:
        return False
    action = order[0]
    amount = order[1]
    if action not in ("BUY", "SELL", "HOLD"):
        return False
    if not isinstance(amount, numbers.Real):
        return False
    if amount != amount:
        return False           
    try:
        if not math.isfinite(amount):
            return False
    except OverflowError:
        return False
    return True


def check_char(number, token3):
    """The check character for a group number and the first three token characters.

    What it catches, stated honestly: every single-character slip, and every swap of two
    neighbors EXCEPT a pair whose alphabet values differ by exactly 13. Consecutive
    weights differ by 2, so swapping neighbors shifts the total by 2*(a - b), and that
    is invisible mod 26 only when a - b is 0 or 13. One check character buys this much;
    catching the rest needs a lookup table.
    """
    values = [number // 10, number % 10] + [CODE_ALPHABET.index(c) for c in token3]
    total = 0
    for weight, value in zip(CODE_WEIGHTS, values):
        total = total + weight * value
    return CODE_ALPHABET[total % 26]


def is_valid_code(code):
    """True if the code is well-formed and its own check character agrees.

    Shape first, then the check character, so a code of the wrong length never reaches
    the arithmetic."""
    if len(code) != 8 or code[0] != "G" or code[3] != "-":
        return False
   
    if code[1] not in "0123456789" or code[2] not in "0123456789":
        return False
    for c in code[4:8]:
        if c not in CODE_ALPHABET:
            return False
    return code[7] == check_char(int(code[1:3]), code[4:7])


def group_number(code):
    """The group number inside a well-formed code: "G07-4KQT" -> 7."""
    return int(code[1:3])


def read_group_code(lines):
    """Return (code, problem) from the GROUP_CODE line, WITHOUT running agent.py.

    Text, not import, for two reasons. The competition reads this out of files it has not
    run yet, and one of the ways an agent fails is to hang the instant it is imported. And
    a code that is computed at run time is not a code: it has to be a plain quoted string
    on one line so that any tool can read it out of the file.

    `problem` is "absent" if there is no such line, "not-a-literal" if there is one but it
    is not a plain quoted string, and "" if the code was read."""
    for line in lines:
        text = line.strip()
        if not text.startswith("GROUP_CODE"):
            continue
        rest = text[len("GROUP_CODE"):].strip()
        if not rest.startswith("="):
            continue                      
        value = rest[1:].strip()
        if len(value) < 2 or value[0] not in "\"'":
            return "", "not-a-literal"
        quote = value[0]
        end = value.find(quote, 1)
        if end < 0:
            return "", "not-a-literal"
        tail = value[end + 1:].strip()
        if tail != "" and not tail.startswith("#"):
            return "", "not-a-literal"    
        return value[1:end], ""
    return "", "absent"


def names_something(text):
    """True when the text after 'Group:' or 'Reference:' holds a name, not a placeholder.

    Anything between < and > is the stub's placeholder, so it is set aside; what is left has
    to carry at least one letter, in any alphabet."""
    kept = []
    depth = 0
    for c in text:
        if c == "<":
            depth = depth + 1
        elif c == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            kept.append(c)
    for c in kept:
        if c.isalpha():
            return True
    return False


def read_names(lines):
    """Return (group, reference): the line numbers of a '# Group:' comment and of a
    '# Reference:' comment that each carry a name, 0 where there is none.

    Text only, like the group code: comments are never run. The spelling of the label is
    forgiving (any case, spaces before the colon); the placeholder counts as no name."""
    found = {"group": 0, "reference": 0}
    number = 0
    for line in lines:
        number = number + 1
        text = line.strip()
        if not text.startswith("#"):
            continue
        label, colon, value = text[1:].partition(":")
        key = label.strip().lower()
        if colon and key in found and found[key] == 0 and names_something(value):
            found[key] = number
    return found["group"], found["reference"]


def group_code_line(lines):
    """The line number of the GROUP_CODE assignment in agent.py, or 0 if there is none."""
    number = 0
    for line in lines:
        number = number + 1
        text = line.strip()
        if text.startswith("GROUP_CODE") and text[len("GROUP_CODE"):].strip().startswith("="):
            return number
    return 0


def check_group_code(lines, results):
    """Add one result for the group code: present, a plain literal, and well-formed."""
    code, problem = read_group_code(lines)
    where = at_line(group_code_line(lines))
    if problem == "absent":
        results.append(("group_code", "group code is set", False,
                        "no GROUP_CODE line in agent.py -- add it at the top, exactly as "
                        "the code email spells it (a tutor can re-send it)"))
    elif problem == "not-a-literal":
        results.append(("group_code", "group code is set", False,
                        where + "GROUP_CODE must be a plain quoted string on one line, like "
                        "GROUP_CODE = \"G07-4KQT\""))
    elif code == CODE_PLACEHOLDER:
        results.append(("group_code", "group code is set", False,
                        where + "GROUP_CODE is still the placeholder -- replace " + CODE_PLACEHOLDER
                        + " with your group's own code"))
    elif not is_valid_code(code):
        results.append(("group_code", "group code is set", False,
                        where + "GROUP_CODE " + repr(code) + " is not a valid code -- check it "
                        "character by character against the code email"))
    else:
        results.append(("group_code", "group code is set (" + code[:3] + ")", True, ""))


def missing_agent_detail():
    """What to do when there is no agent.py here, naming the near miss when there is one.

    Windows hides a file's extension by default, so a stub renamed by typing agent.py is
    agent.py.py, and "not found" sent a student to the wrong folder (review 185)."""
    try:
        import os
        names = sorted(os.listdir("."))
    except OSError:
        names = []
    hidden = [name for name in names if name.lower().startswith("agent.py.")]
    if hidden:
        return ("found " + hidden[0] + " instead: Windows hid the real ending when it was "
                "renamed. Turn on File name extensions in File Explorer's View menu, then "
                "rename it to agent.py")
    if "agent_stub.py" in names:
        return ("found agent_stub.py: rename it to agent.py, the file your group builds "
                "and submits")
    return "not found -- run this from the folder that holds your agent.py"


def read_agent_source():
    """Return the lines of agent.py, or None if it is not in this folder.

    Every check starts here, so "you are in the wrong folder" has to be a reported
    result and never a traceback.

    utf-8-sig, because an editor that saves "UTF-8 with BOM" puts three invisible bytes in
    front of your first line, and without this the GROUP_CODE line stops being found while
    you are looking straight at it. errors="replace", because a file saved in some other
    encoding should be a check you can read, not a crash with no report at all."""
    try:
        handle = open("agent.py", encoding="utf-8-sig", errors="replace")
    except FileNotFoundError:
        return None
    lines = handle.readlines()
    handle.close()
    return lines


def bad_import_lines(lines):
    """(line number, line) for every import in agent.py outside numpy/pandas/math/random.

    It reads the structure of the code with `ast`, as scan_code does, so a line of a
    docstring or a string that starts with "from" or "import" is not an import: until 13
    October 2026 a docstring line "from day 30 on it also checks the trend" failed this
    check and disqualified the agent. Every module an import names is checked, so `import
    numpy, os` is caught, and a relative import (`from . import helpers`) is one of your own
    files. The line number is what the report shows you, so you can go straight to it. A
    file that does not parse is read line by line instead: the 'loads' check reports its
    syntax error, and this still names any import it can see."""
    try:
        tree = ast.parse("".join(lines))
    except (SyntaxError, ValueError, RecursionError):
        return text_import_lines(lines)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = ["." if node.level else (node.module or "")]
        else:
            continue
        for name in names:
            if name.split(".")[0] not in ALLOWED_IMPORTS:
                found.add(node.lineno)
                break
    return [(number, lines[number - 1].strip()) for number in sorted(found)]


def text_import_lines(lines):
    """bad_import_lines for a file that does not parse: every line that starts with
    `import` or `from`, read as text."""
    bad = []
    number = 0
    for line in lines:
        number = number + 1
        text = line.strip()
        if text.startswith("import "):
            for item in text[len("import "):].split(","):
                item = item.strip()
                if item:
                    module = item.split()[0].split(".")[0]
                    if module and module not in ALLOWED_IMPORTS:
                        bad.append((number, text))
                        break
        elif text.startswith("from "):
            parts = text.split()
            if len(parts) >= 2 and parts[1].split(".")[0] not in ALLOWED_IMPORTS:
                bad.append((number, text))
    return bad


def check_imports(lines):
    """Flag any import in agent.py outside numpy/pandas/math/random (the #1 way an agent
    is disqualified). Checks every module named on a line, so `import numpy, os` is
    caught. Returns the offending lines themselves, which is what the competition's own
    scanner returns too, so the two can be compared on the same files."""
    bad = []
    for number, text in bad_import_lines(lines):
        bad.append(text)
    return bad


def open_mode(call):
    """The mode an open() call is given, "r" when none is; None when it is not a plain string."""
    mode = None
    if len(call.args) >= 2:
        mode = call.args[1]
    for keyword in call.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    if mode is None:
        return "r"
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return mode.value
    return None


def scan_code(lines):
    """What agent.py calls that the rules care about: (reads, writes, shortcuts).

    Each is a sorted list of (line number, what was called). It reads the structure of the
    code with the standard library's `ast` module instead of searching the text, so a
    comment or a string that mentions `.rolling(` is not a finding. A function or method you
    define yourself under one of these names is yours, not the library's: calling it
    plainly, or as `self.name(...)`, is skipped.

    Returns None when agent.py does not parse. The 'loads' check reports that syntax error
    with its line number, and anything said here without the structure would be a guess."""
    try:
        tree = ast.parse("".join(lines))
    except (SyntaxError, ValueError, RecursionError):
        return None
    own = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            own.add(node.name)
    reads = []
    writes = []
    shortcuts = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name):
            name = function.id
            receiver = ""
            if name in own:
                continue
            shown = name + "()"
        elif isinstance(function, ast.Attribute):
            name = function.attr
            receiver = function.value.id if isinstance(function.value, ast.Name) else ""
            if receiver == "self" and name in own:
                continue
            shown = (receiver + "." if receiver != "" else ".") + name + "()"
        else:
            continue
        line = node.lineno
        if name == "open" and receiver == "":
            mode = open_mode(node)
            if mode is None:
                reads.append((line, "open() with a mode that is not a plain string"))
            elif "r" in mode or "+" in mode:
                reads.append((line, "open() for reading"))
            else:
                writes.append((line, "open() for writing"))
        elif (name in READ_CALLS or (receiver in ("pd", "pandas") and name.startswith("read_"))
              or (receiver in ("np", "numpy") and name == "load")):
            reads.append((line, shown))
        elif name in WRITE_CALLS or (receiver in ("np", "numpy")
                                     and name in ("save", "savez", "savez_compressed")):
            has_path = len(node.args) > 0
            for keyword in node.keywords:
                if keyword.arg in ("path_or_buf", "path"):
                    has_path = True
            if name in WRITES_ONLY_WITH_PATH and not has_path:
                continue
            writes.append((line, shown))
        elif name in BANNED_SHORTCUTS:
            shortcuts.append((line, shown))
    reads.sort()
    writes.sort()
    shortcuts.sort()
    return reads, writes, shortcuts


def describe(found, reason):
    """"line 12: open(); line 30: pd.read_csv() -- reason", short enough to read at once."""
    parts = []
    for number, what in found[:5]:
        parts.append("line " + str(number) + ": " + what)
    if len(found) > 5:
        parts.append("and " + str(len(found) - 5) + " more")
    return "; ".join(parts) + " -- " + reason


def content_checks(scanned):
    """The two checks that read what agent.py does, rather than run it, from scan_code.

    Returns their results, or an empty list when agent.py does not parse: then neither can
    say anything, and the report counts them among the checks that could not run."""
    if scanned is None:
        return []
    reads, writes, shortcuts = scanned
    results = []
    name = "reads no files or keyboard, runs no hidden code"
    if reads:
        results.append(("no_io", name, False,
                        describe(reads, "your agent is handed each day through decide(); it "
                                 "may not read files or the keyboard, or run code from a "
                                 "string")))
    else:
        results.append(("no_io", name, True, ""))
    name = "no banned shortcuts (rolling, shift, pct_change, cumprod)"
    if shortcuts:
        results.append(("banned_shortcuts", name, False,
                        describe(shortcuts, "the library policy bans these in submitted code; "
                                 "the time-series supplement has the loop that replaces "
                                 "each")))
    else:
        results.append(("banned_shortcuts", name, True, ""))
    return results


def collect_warnings():
    """Findings that fail nothing here, and still matter before you submit.

    Each is (warning_id, name, detail), a check result without a verdict: a file write,
    which debugging allows and the submitted file must not keep, and a file that names
    nobody. Empty when agent.py is missing; a file that does not parse can still be read
    for its names."""
    lines = read_agent_source()
    if lines is None:
        return []
    warnings = []
    scanned = scan_code(lines)
    if scanned is not None and scanned[1]:
        warnings.append(("writes_file", "writes a file", describe(scanned[1], WRITE_WARNING)))
    group, reference = read_names(lines)
    if not group and not reference:
        warnings.append(("unnamed", "names neither your group nor its reference",
                         NAMES_WARNING))
    elif not group:
        warnings.append(("unnamed", "names no group members", NAMES_WARNING))
    elif not reference:
        warnings.append(("unnamed", "names no reference member", NAMES_WARNING))
    return warnings


def drive_regime(agent_class, use_prices, use_news, check_id, label, results):
    """Run a fresh agent through the fake days in one regime, checking every reply.

    BaseException, not Exception, for the same reason load_agent uses it: a decide() that
    calls sys.exit() raises SystemExit, which is NOT an Exception, so catching the narrower
    one lets it escape and the whole report is never printed. You would run the tool and
    see nothing at all.

    Returns True when you pressed Ctrl-C during it: the checks after it would only hang in
    the same place, so collect_checks stops there."""
    try:
        agent = agent_class()
    except BaseException as error:
        results.append((check_id, label + ": TradingAgent() built", False,
                        error_with_line(error, agent_class.__init__)))
        return isinstance(error, KeyboardInterrupt)
    interface = FakeInterface(10000.0)
    last_response = None
    ok = True
    for t in range(len(FAKE_BARS)):
        bar = FAKE_BARS[t] if use_prices else None
        news = FAKE_NEWS[t] if use_news else None
        try:
            order, returned_at = call_decide(agent, bar, news, interface.cash,
                                             interface.shares, last_response)
        except BaseException as error:
            stopped = isinstance(error, KeyboardInterrupt)
            results.append((check_id, label + (": decide() never returned" if stopped
                                               else ": decide() crashed"), False,
                            error_with_line(error, decide_of(agent))))
            return stopped
        if not is_valid_order(order):
            results.append((check_id, label + ": well-formed order", False,
                            at_line(returned_at) + "got " + repr(order)))
            ok = False
            break
        # Protocol harness only: five fake bars, filled at today's close for brevity.
        # The real engine (and your Simulator) fills at TOMORROW'S OPEN -- see the brief.
        fill_price = bar["close"] if bar is not None else 100.0
        last_response = interface.execute(order, fill_price)
    if ok:
        results.append((check_id, label + ": well-formed orders every day", True, ""))
    return False


def report(results):
    """Print one line per check and return (passed, total)."""
    passed = 0
    print("=== agent_unittest: simulated-interface protocol check ===")
    for check_id, name, good, detail in results:
        mark = "OK  " if good else "FAIL"
        line = "  [" + mark + "] " + name
        if not good and detail != "":
            line = line + "   (" + detail + ")"
        print(line)
        if good:
            passed = passed + 1
    return passed, len(results)


def not_reached(results):
    """How many of the standard checks never got the chance to run.

    An early failure stops everything after it: if agent.py will not import, the five
    checks that have to call decide() cannot say anything at all. Counting them is the
    difference between "4/5 checks passed", which reads as nearly there, and "4 passed,
    5 never ran", which is the truth."""
    done = []
    for item in results:
        done.append(item[0])
    missing = 0
    for check_id in ALL_CHECK_IDS:
        if check_id not in done:
            missing = missing + 1
    return missing


def collect_checks():
    """Run every protocol check and RETURN the results, printing nothing.

    Each result is (check_id, name, passed, detail). Split out from run_checks below so
    that the deciding and the printing are separate jobs: the same split you make in week 7
    when the register stops printing from inside its own logic."""
    results = []

    lines = read_agent_source()
    if lines is None:
        results.append(("file_present", "agent.py is in this folder", False,
                        missing_agent_detail()))
        return results

    
    bad_imports = bad_import_lines(lines)
    if bad_imports:
        where = []
        for number, text in bad_imports:
            where.append("line " + str(number) + ": " + text)
        results.append(("self_contained", "self-contained (only numpy/pandas/math/random)",
                        False, "; ".join(where) + " -- only numpy, pandas, math and random, "
                        "and none of your own files"))
    else:
        results.append(("self_contained", "self-contained (only numpy/pandas/math/random)",
                        True, ""))

    text_results = content_checks(scan_code(lines))

    
    check_group_code(lines, results)

    
    TradingAgent, load_error = load_agent()
    if TradingAgent is None:
        results.append(("loads", "agent.py loads on its own", False, load_error))
        return results + text_results
    results.append(("loads", "agent.py loads on its own", True, ""))

   
    if drive_regime(TradingAgent, True, False, "regime_ohlcv", "OHLCV-only regime", results):
        return results + text_results
    if drive_regime(TradingAgent, False, True, "regime_news", "news-only regime", results):
        return results + text_results
    if drive_regime(TradingAgent, True, True, "regime_both", "OHLCV+news regime", results):
        return results + text_results

   
    called = TradingAgent.__init__
    try:
        agent = TradingAgent()
        called = decide_of(agent)
        order, returned_at = call_decide(agent, FAKE_BARS[0], FAKE_NEWS[0], 10.0, 0.0,
                                         "REJECT currency balance: 10.0")
        results.append(("reject_reply", "handles a REJECT reply", is_valid_order(order),
                        at_line(returned_at) + "got " + repr(order)))
    except BaseException as error:
        results.append(("reject_reply", "handles a REJECT reply", False,
                        error_with_line(error, called)))
        if isinstance(error, KeyboardInterrupt):
            return results + text_results

    
    called = TradingAgent.__init__
    try:
        agent = TradingAgent()
        called = decide_of(agent)
        order, returned_at = call_decide(agent, FAKE_BARS[0], FAKE_NEWS[0], 10000.0, 0.0, None)
        results.append(("none_last_response", "handles None last_response",
                        is_valid_order(order), at_line(returned_at) + "got " + repr(order)))
    except BaseException as error:
        results.append(("none_last_response", "handles None last_response", False,
                        error_with_line(error, called)))

    return results + text_results


def stopped_with_ctrl_c(results):
    """True when you pressed Ctrl-C during the checks, so the report ends early."""
    for item in results:
        if CTRL_C in item[3]:
            return True
    return False


def run_checks():
    """Run all protocol checks. Returns (passed, total) and prints a report.

    After a Ctrl-C it prints the report, says so, and raises KeyboardInterrupt again, so
    that selfcheck.py stops too rather than starting runs that would hang in the same place."""
    results = collect_checks()
    passed, total = report(results)
    
    for warning_id, name, detail in collect_warnings():
        print("  [WARN] " + name + "   (" + detail + ")")
    
    older = older_libraries()
    if older:
        name, detail = older_libraries_warning(older)
        print("  [WARN] " + name + "   (" + detail + ")")
    print("  " + str(passed) + "/" + str(total) + " checks passed.")
    missing = not_reached(results)
    if missing > 0:
        print("  " + str(missing) + " more could not run until that is fixed.")
    if missing == 0 and passed == total:
        print("  Your agent fits the competition contract.")
    else:
        print("  Fix the FAILs above before submitting to the competition.")
    if stopped_with_ctrl_c(results):
        print("  Stopped with Ctrl-C: the FAIL above names the line your agent was running.")
        raise KeyboardInterrupt
    return passed, total


if __name__ == "__main__":
    try:
        run_checks()
    except KeyboardInterrupt:
        sys.exit(130)
