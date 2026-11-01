"""Мягкая интеграция с CharmPkk: красивый вывод + интерактив + безопасные спиннеры."""
import sys

_charm = None
_c = None
_available = False

try:
    from charmpkk import console as _c
    _charm = __import__("charmpkk")
    _available = True
except Exception:
    _available = False


# ============================================================
# Менеджер активных спиннеров (чтобы не ломать input())
# ============================================================
_ACTIVE_SPINNERS = []


def _pause_spinners():
    for sp in list(_ACTIVE_SPINNERS):
        try:
            sp.pause()
        except Exception:
            pass


def _resume_spinners():
    for sp in list(_ACTIVE_SPINNERS):
        try:
            sp.resume()
        except Exception:
            pass


# ============================================================
# Базовые помощники
# ============================================================
def has_charm():
    return _available


def theme(name="halloween"):
    if not _available:
        return None
    try:
        return _c.get_theme(name)
    except Exception:
        return None


def _fg(color):
    if not _available or not color:
        return None
    if isinstance(color, str) and color.startswith("#"):
        try:
            return _c.fg_hex(color)
        except Exception:
            return None
    return color


def colorize(text, color=None, style=None):
    if _available:
        try:
            return _c.colorize(text, fg=_fg(color), style=style)
        except Exception:
            return text
    return text


# ============================================================
# Печать сообщений
# ============================================================
def print_msg(text, color="#ff7518"):
    if _available:
        try:
            print(_c.colorize(text, fg=_fg(color)))
            return
        except Exception:
            pass
    print(text)


def print_box(content, title=None, color="#ff7518"):
    if _available:
        try:
            print(_c.box(content, title=title, border_fg=_fg(color)))
            return
        except Exception:
            pass

    lines = content.split("\n") if isinstance(content, str) else [str(x) for x in content]
    max_w = max((len(line) for line in lines), default=0)
    if title:
        max_w = max(max_w, len(title) + 2)
    max_w = min(max_w, 100)

    top = "+" + "-" * (max_w + 2) + "+"
    print(top)
    if title:
        print(f"| {title.center(max_w)} |")
        print("+" + "-" * (max_w + 2) + "+")
    for line in lines:
        print(f"| {line.ljust(max_w)[:max_w]} |")
    print(top)


def print_success(text):
    if _available:
        try:
            print(_c.success(text))
            return
        except Exception:
            pass
    print(f"[OK] {text}")


def print_warning(text):
    if _available:
        try:
            print(_c.warning(text))
            return
        except Exception:
            pass
    print(f"[!] {text}")


def print_error(text):
    if _available:
        try:
            print(_c.error(text))
            return
        except Exception:
            pass
    print(f"[X] {text}")


def print_info(text):
    if _available:
        try:
            print(_c.info(text))
            return
        except Exception:
            pass
    print(f"[i] {text}")


# ============================================================
# Интерактив (с автоматической паузой спиннеров)
# ============================================================
def ask(prompt, default=None):
    _pause_spinners()
    try:
        if _available:
            try:
                return _c.ask(prompt, default=default)
            except Exception:
                pass
        hint = f" [{default}]" if default is not None else ""
        try:
            v = input(f"? {prompt}{hint}: ").strip()
            return v or default
        except (EOFError, KeyboardInterrupt):
            return default
    finally:
        _resume_spinners()


def ask_choice(prompt, options, default=None):
    if not options:
        return default

    _pause_spinners()
    try:
        if _available:
            try:
                result = _c.select(prompt, options)
                return result if result is not None else default
            except Exception:
                pass

        print(f"? {prompt}")
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        hint = f" [{default}]" if default else ""
        try:
            raw = input(f"Номер{hint}: ").strip()
            if not raw:
                return default
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        return default
    finally:
        _resume_spinners()


def confirm(prompt, default=False):
    _pause_spinners()
    try:
        if _available:
            try:
                return _c.confirm(prompt, default=default)
            except Exception:
                pass
        d = "Y/n" if default else "y/N"
        try:
            v = input(f"? {prompt} ({d}): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return default
        return v.startswith("y") if v else default
    finally:
        _resume_spinners()


def select(title, options, color="#ff7518"):
    return ask_choice(title, options)


# ============================================================
# Спиннер
# ============================================================
class _NullSpinner:
    def __init__(self, text):
        self.text = text
        self._printed = False
        self._paused = False

    def __enter__(self):
        _ACTIVE_SPINNERS.append(self)
        if sys.stdout.isatty():
            sys.stdout.write(f"  {self.text}...")
            sys.stdout.flush()
            self._printed = True
        else:
            print(f"  {self.text}...")
        return self

    def __exit__(self, *exc):
        if self in _ACTIVE_SPINNERS:
            _ACTIVE_SPINNERS.remove(self)
        if self._printed and sys.stdout.isatty():
            sys.stdout.write("\r" + " " * (len(self.text) + 8) + "\r")
            sys.stdout.flush()
        return False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self, final=None):
        if final:
            print(f"  {final}")


class _CharmSpinnerWrapper:
    """Обёртка над CharmPkk Spinner с поддержкой pause/resume для input()."""

    def __init__(self, inner):
        self.inner = inner
        self._paused = False

    def __enter__(self):
        _ACTIVE_SPINNERS.append(self)
        try:
            self.inner.__enter__()
        except Exception:
            pass
        return self

    def __exit__(self, *exc):
        if self in _ACTIVE_SPINNERS:
            _ACTIVE_SPINNERS.remove(self)
        try:
            self.inner.__exit__(*exc)
        except Exception:
            pass
        return False

    def pause(self):
        if self._paused:
            return
        self._paused = True
        try:
            self.inner.stop()
        except Exception:
            pass

    def resume(self):
        if not self._paused:
            return
        self._paused = False
        try:
            self.inner.start()
        except Exception:
            pass

    def stop(self, final=None):
        try:
            self.inner.stop(final)
        except Exception:
            pass


def spinner(text="Loading", color="#ff7518"):
    if _available:
        try:
            inner = _c.Spinner(text, fg=_fg(color))
            return _CharmSpinnerWrapper(inner)
        except Exception:
            pass
    return _NullSpinner(text)


# ============================================================
# Прогресс-бар
# ============================================================
class _NullProgress:
    def __init__(self, total, label):
        self.total = total
        self.label = label
        self.current = 0
        self._started = False

    def __enter__(self):
        self._started = True
        return self

    def __exit__(self, *exc):
        if sys.stdout.isatty() and self._started:
            sys.stdout.write("\n")
            sys.stdout.flush()
        return False

    def update(self, current):
        self.current = current
        if not sys.stdout.isatty():
            return
        pct = int(current / self.total * 100) if self.total else 0
        bar_w = 30
        filled = int(pct * bar_w / 100)
        bar = "█" * filled + "░" * (bar_w - filled)
        sys.stdout.write(f"\r  {self.label} [{bar}] {pct:3d}%")
        sys.stdout.flush()

    def finish(self, msg=None):
        if sys.stdout.isatty() and self._started:
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()
        if msg:
            print(msg)


def progress(total=100, label="", color="#ff7518"):
    if _available:
        try:
            return _c.FancyProgressBar(total=total, label=label, fg=_fg(color))
        except Exception:
            pass
    return _NullProgress(total, label)