"""База типичных опечаток Python и нечёткий поиск подсказок."""

PYTHON_KEYWORDS = {
    "def", "class", "return", "import", "from", "as", "if", "elif", "else",
    "for", "while", "break", "continue", "try", "except", "finally", "raise",
    "with", "yield", "lambda", "pass", "global", "nonlocal", "assert",
    "del", "in", "is", "not", "and", "or", "None", "True", "False",
    "async", "await",
}

BUILTIN_NAMES = {
    "print", "len", "range", "str", "int", "float", "bool", "list", "dict",
    "set", "tuple", "type", "isinstance", "issubclass", "open", "input",
    "iter", "next", "enumerate", "zip", "map", "filter", "sum", "min", "max",
    "abs", "round", "sorted", "reversed", "any", "all", "hasattr", "getattr",
    "setattr", "delattr", "callable", "super", "vars", "dir", "id", "hash",
    "repr", "format", "exec", "eval", "compile", "globals", "locals",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "NameError", "AttributeError", "RuntimeError", "StopIteration",
    "NotImplementedError", "OSError", "IOError", "FileNotFoundError",
    "PermissionError", "ZeroDivisionError", "OverflowError",
    "RecursionError", "MemoryError", "AssertionError", "SyntaxError",
}

# Явные опечатки → правильное написание (без дубликатов)
KNOWN_TYPOS = {
    "lenght": "length",
    "heigth": "height",
    "widht": "width",
    "improt": "import",
    "imoprt": "import",
    "ipmort": "import",
    "imort": "import",
    "retrun": "return",
    "retrurn": "return",
    "rturn": "return",
    "fucntion": "function",
    "fnction": "function",
    "functon": "function",
    "calss": "class",
    "clas": "class",
    "prnit": "print",
    "pirnt": "print",
    "prnt": "print",
    "els": "else",
    "esle": "else",
    "wihle": "while",
    "whlie": "while",
    "wlile": "while",
    "fro": "for",
    "itme": "item",
    "interable": "iterable",
    "iterabel": "iterable",
    "dic": "dict",
    "dcit": "dict",
    "lsit": "list",
    "tupple": "tuple",
    "tupel": "tuple",
    "strng": "string",
    "sring": "string",
    "stirng": "string",
    "inpt": "input",
    "inp": "input",
    "opne": "open",
    "excpet": "except",
    "exept": "except",
    "fnally": "finally",
    "finnaly": "finally",
    "trry": "try",
    "tryy": "try",
    "yeild": "yield",
    "yelid": "yield",
    "yiled": "yield",
    "asnyc": "async",
    "awiat": "await",
    "Nonne": "None",
    "Ture": "True",
    "Flase": "False",
    "Fasle": "False",
    "sefl": "self",
    "slef": "self",
}


def suggest_fix(name):
    """Возвращает предложение исправления для имени или None."""
    if not name:
        return None
    if name in KNOWN_TYPOS:
        return KNOWN_TYPOS[name]

    import difflib
    candidates = PYTHON_KEYWORDS | BUILTIN_NAMES | set(KNOWN_TYPOS.values())
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.75)
    if matches:
        return matches[0]
    return None


__all__ = ["PYTHON_KEYWORDS", "BUILTIN_NAMES", "KNOWN_TYPOS", "suggest_fix"]