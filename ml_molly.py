"""mlMolly (Maniacal Molly) — предварительная проверка кода на опечатки через AST."""
import ast
import inspect
import functools
import textwrap
import difflib
from pathlib import Path

from . import charm_enhance as ui
from .molly import Molly
from .typo_db import suggest_fix, PYTHON_KEYWORDS, BUILTIN_NAMES, KNOWN_TYPOS


_CHECKED_CACHE = {}


class MLMolly:
    """
    Умная Molly: перед запуском проверяет исходник на явные опечатки
    (имена переменных, функций, импортов) и оборачивает вызов в базовую Molly.
    """

    @classmethod
    def check_source(cls, source, filename="<string>"):
        """Проверяет исходник через AST. Возвращает список dict с предупреждениями."""
        warnings = []
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as e:
            warnings.append({
                "line": e.lineno or 0,
                "name": str(e.msg or e),
                "suggestion": "исправьте синтаксис — Python не может разобрать файл",
                "kind": "syntax",
            })
            return warnings

        # Собираем все определённые имена (функции, классы, переменные, аргументы, импорты)
        defined = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
                if hasattr(node, "args"):
                    for arg in node.args.args:
                        defined.add(arg.arg)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            elif isinstance(node, ast.arg):
                defined.add(node.arg)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    defined.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    defined.add(alias.asname or alias.name)

        # Кандидаты для difflib = defined + builtin + keyword
        candidates = defined | BUILTIN_NAMES | PYTHON_KEYWORDS
        # Убираем слишком короткие имена (1-2 символа) — они дают шум
        candidates = {c for c in candidates if isinstance(c, str) and len(c) >= 3}

        seen = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Name):
                continue

            name = node.id
            line = node.lineno
            key = (line, name)
            if key in seen:
                continue

            # 1. Имя есть в базе известных опечаток — ловим всегда
            if name in KNOWN_TYPOS:
                seen.add(key)
                warnings.append({
                    "line": line,
                    "name": name,
                    "suggestion": KNOWN_TYPOS[name],
                    "kind": "typo",
                })
                continue

            # 2. Load-имена, которых нет в defined и не встроенные — difflib среди candidates
            if isinstance(node.ctx, ast.Load):
                if name in defined or name in BUILTIN_NAMES or name in ("self", "cls"):
                    continue
                if len(name) < 3:
                    continue
                matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.75)
                if matches and matches[0] != name:
                    seen.add(key)
                    warnings.append({
                        "line": line,
                        "name": name,
                        "suggestion": matches[0],
                        "kind": "typo",
                    })

        return warnings

    @classmethod
    def check_function(cls, func, silent=False):
        """Проверяет исходник одной функции."""
        try:
            source = inspect.getsource(func)
        except (OSError, TypeError) as e:
            if not silent:
                ui.print_warning(f"mlMolly: не удалось прочитать исходник {func.__name__}: {e}")
            return []

        source = textwrap.dedent(source)

        filename = "<func>"
        code = getattr(func, "__code__", None)
        if code is not None:
            filename = code.co_filename

        warnings = cls.check_source(source, filename=filename)

        if warnings and not silent:
            cls._print_warnings(warnings, context=f"функция {func.__name__}")

        return warnings

    @classmethod
    def check_file(cls, path, silent=False):
        """Проверяет файл целиком."""
        path = Path(path)
        if not path.exists():
            if not silent:
                ui.print_error(f"mlMolly: файл не найден: {path}")
            return []

        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0

        cache_key = (str(path.resolve()), mtime)
        if cache_key in _CHECKED_CACHE:
            warnings = _CHECKED_CACHE[cache_key]
        else:
            try:
                with ui.spinner(f"mlMolly: сканирую {path.name}", color="#22c55e"):
                    source = path.read_text("utf-8")
            except (OSError, UnicodeDecodeError) as e:
                if not silent:
                    ui.print_error(f"mlMolly: не удалось прочитать {path}: {e}")
                return []

            warnings = cls.check_source(source, filename=str(path))
            _CHECKED_CACHE[cache_key] = warnings

        if warnings and not silent:
            cls._print_warnings(warnings, context=f"файл {path.name}")

        return warnings

    @classmethod
    def _print_warnings(cls, warnings, context=""):
        if not warnings:
            return

        lines = []
        if context:
            lines.append(f"Контекст: {context}")
            lines.append("")

        for w in warnings:
            kind = w.get("kind", "typo")
            line = w.get("line", 0)
            name = w.get("name", "?")
            sugg = w.get("suggestion", "")

            if kind == "syntax":
                lines.append(f"  Строка {line}: синтаксическая проблема — {name}")
                lines.append(f"    → {sugg}")
            else:
                lines.append(f"  Строка {line}: «{name}» — возможно, опечатка")
                if sugg:
                    lines.append(f"    → Возможно, вы имели в виду: «{sugg}»")

        ui.print_box(
            "\n".join(lines),
            title="mlMolly: предупреждения",
            color="#f59e0b",
        )

    @classmethod
    def watch(cls, func):
        """Декоратор: проверяет функцию перед первым вызовом и оборачивает в Molly."""
        checked = {"done": False}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not checked["done"]:
                cls.check_function(func, silent=False)
                checked["done"] = True

            try:
                return func(*args, **kwargs)
            except Exception as e:
                Molly.catch(e)
                return None

        return wrapper

    @classmethod
    def catch(cls, exc, reraise=False):
        return Molly.catch(exc, reraise=reraise)

    @classmethod
    def explain(cls, exc):
        return Molly.explain(exc)

    @classmethod
    def mark_resolved(cls):
        return Molly.mark_resolved()

    @classmethod
    def install_global_hook(cls):
        Molly.install_global_hook()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            Molly.print_explanation(exc)
            return True
        return False


__all__ = ["MLMolly"]