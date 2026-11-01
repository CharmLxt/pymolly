"""Molly — базовый баг-репортер."""
import sys
import functools

from . import charm_enhance as ui
from .analyzer import analyze_exception, short_location
from .messages import build_standard_message, RESOLVED_MESSAGE


class Molly:
    """
    Базовый баг-репортер. Ловит исключение и объясняет его простым языком.

    Использование:
        # 1. Как контекстный менеджер (создаём экземпляр!)
        with Molly():
            risky_code()

        # 2. Как декоратор
        @Molly.watch
        def risky_function(): ...

        # 3. Вручную
        try:
            risky_code()
        except Exception as e:
            Molly.catch(e)

        # 4. Глобальный хук (все непойманные ошибки пройдут через Молли)
        Molly.install_global_hook()
    """

    @classmethod
    def explain(cls, exc):
        """Возвращает готовое сообщение (строкой), не печатает."""
        info = analyze_exception(exc)
        message = build_standard_message(info)
        location = short_location(info)
        if location:
            message += f" (место: {location})"
        return message

    @classmethod
    def catch(cls, exc, reraise=False):
        """Печатает объяснение. Если reraise=True — пробрасывает исключение дальше."""
        cls.print_explanation(exc)
        if reraise:
            raise exc

    @classmethod
    def print_explanation(cls, exc):
        message = cls.explain(exc)
        ui.print_box(message, title="Молли")

    @classmethod
    def mark_resolved(cls):
        """Печатает сообщение об успешном исправлении."""
        ui.print_success(RESOLVED_MESSAGE)

    @classmethod
    def watch(cls, func):
        """Декоратор: ловит исключение в func и объясняет его."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cls.catch(e)
                return None
        return wrapper

    @classmethod
    def install_global_hook(cls):
        """Ставит sys.excepthook, чтобы все непойманные ошибки шли через Молли."""
        original = sys.excepthook

        def _hook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                original(exc_type, exc_value, exc_tb)
                return
            exc = exc_value.with_traceback(exc_tb) if exc_tb else exc_value
            try:
                cls.print_explanation(exc)
            except Exception:
                original(exc_type, exc_value, exc_tb)

        sys.excepthook = _hook

    @classmethod
    def uninstall_global_hook(cls):
        sys.excepthook = sys.__excepthook__

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            try:
                self.print_explanation(exc)
            except Exception:
                return False
            return True
        return False


__all__ = ["Molly"]