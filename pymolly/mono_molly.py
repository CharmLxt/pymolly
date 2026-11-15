"""monoMolly — специализированный баг-репортер для сетевых ошибок Monogrammer."""
import socket
import ssl
import functools
from . import charm_enhance as ui
from .analyzer import analyze_exception
from .molly import Molly

NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    socket.gaierror,
    socket.herror,
    socket.timeout,
    ssl.SSLError,
)


class monoMolly:
    """Перехватывает сетевые ошибки и дает специфичные советы."""

    @classmethod
    def catch(cls, exc):
        if isinstance(exc, NETWORK_EXCEPTIONS) or isinstance(exc, OSError):
            info = analyze_exception(exc)
            msg = f"Сетевая ошибка: {type(exc).__name__}\n"
            msg += f"Суть: {info['description']}\n\n"
            
            if isinstance(exc, ConnectionRefusedError):
                msg += "💡 Совет для Monogrammer:\n"
                msg += "  1. Убедитесь, что на ПК друга запущен Агент.\n"
                msg += "  2. Проверьте, что порт 8080 не блокируется брандмауэром.\n"
                msg += "  3. Проверьте Host IP (он мог измениться)."
            elif isinstance(exc, (TimeoutError, socket.timeout)):
                msg += "💡 Совет для Monogrammer:\n"
                msg += "  1. Проверьте стабильность сети (запустите ndVpi).\n"
                msg += "  2. Возможно, сервер перегружен видео-потоком.\n"
                msg += "  3. Попробуйте снизить качество видео в настройках пульта."
            elif isinstance(exc, ssl.SSLError):
                msg += "💡 Совет для Monogrammer:\n"
                msg += "  1. Проверьте системное время (сертификаты зависят от него).\n"
                msg += "  2. Обновите certifi: pip install --upgrade certifi."
            elif isinstance(exc, socket.gaierror):
                msg += "💡 Совет для Monogrammer:\n"
                msg += "  1. Проверьте, правильно ли введен IP-адрес.\n"
                msg += "  2. Убедитесь, что DNS работает."
            else:
                msg += "💡 Совет: проверьте подключение и настройки сети."
                
            ui.print_box(msg, title="monoMolly (Network)", color="#ef4444")
            return True
        else:
            # Если ошибка не сетевая, передаем базовой Молли
            Molly.print_explanation(exc)
            return False

    @classmethod
    def watch(cls, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cls.catch(e)
                return None
        return wrapper

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            monoMolly.catch(exc)
            return True
        return False