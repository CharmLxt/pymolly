"""GuMolly (Molly Guard) — журналирование ошибок, мягкая остановка, чекпоинты."""
import sys
import json
import functools
import threading
import traceback
from datetime import datetime
from pathlib import Path

from . import charm_enhance as ui
from .analyzer import analyze_exception
from .molly import Molly


LOG_DIR = Path.home() / ".pymolly" / "all_logs"
DEF_LOGS = LOG_DIR / "def_logs"
CRIT_LOGS = LOG_DIR / "crit_logs"

CRITICAL_EXCEPTIONS = {
    "MemoryError", "RecursionError", "SystemError",
    "KeyboardInterrupt", "SystemExit",
}
CRIT_THRESHOLD = 3


class GuMolly:
    """Мягкая остановка + журналирование + чекпоинты."""

    _stop_flag = threading.Event()
    _session_errors = {}

    @classmethod
    def _ensure_dirs(cls):
        try:
            DEF_LOGS.mkdir(parents=True, exist_ok=True)
            CRIT_LOGS.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    @classmethod
    def _log_error(cls, exc, info):
        if not cls._ensure_dirs():
            return False

        exc_type = info["type"]

        is_crit = exc_type in CRITICAL_EXCEPTIONS
        count = cls._session_errors.get(exc_type, 0) + 1
        cls._session_errors[exc_type] = count
        if count >= CRIT_THRESHOLD:
            is_crit = True

        target_dir = CRIT_LOGS if is_crit else DEF_LOGS
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = target_dir / f"{date_str}.log"

        try:
            tb_str = "".join(traceback.format_exception(
                type(exc), exc, exc.__traceback__,
            ))
        except Exception:
            tb_str = "<traceback unavailable>"

        record = {
            "timestamp": datetime.now().isoformat(),
            "type": exc_type,
            "message": info.get("message", ""),
            "file": info.get("file"),
            "line": info.get("line"),
            "is_critical": is_crit,
            "session_count": count,
            "traceback": tb_str,
        }

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except Exception:
            return is_crit

        return is_crit

    @classmethod
    def log(cls, exc):
        info = analyze_exception(exc)
        is_crit = cls._log_error(exc, info)
        return info, is_crit

    @classmethod
    def catch(cls, exc, stop=False):
        info, is_crit = cls.log(exc)
        Molly.print_explanation(exc)
        if is_crit:
            ui.print_warning("Молли сохранила эту ошибку как критическую в журнале.")
        if stop:
            cls._stop_flag.set()
            ui.print_info("Молли мягко остановила выполнение. "
                          "Исправьте ошибку и вызовите GuMolly.resume().")
        return info, is_crit

    @classmethod
    def is_stopped(cls):
        return cls._stop_flag.is_set()

    @classmethod
    def resume(cls):
        cls._stop_flag.clear()
        ui.print_success("Молли возобновила работу.")

    @classmethod
    def reset(cls):
        cls._stop_flag.clear()
        cls._session_errors.clear()

    @classmethod
    def watch(cls, func, stop_on_error=True):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if cls._stop_flag.is_set():
                ui.print_warning("Молли: выполнение остановлено. "
                                 "Вызовите GuMolly.resume().")
                return None
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cls.catch(e, stop=stop_on_error)
                return None
        return wrapper

    @classmethod
    def install(cls):
        original = sys.excepthook

        def _hook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                original(exc_type, exc_value, exc_tb)
                return
            exc = exc_value.with_traceback(exc_tb) if exc_tb else exc_value
            try:
                cls.catch(exc, stop=False)
            except Exception:
                original(exc_type, exc_value, exc_tb)

        sys.excepthook = _hook

    @classmethod
    def uninstall(cls):
        sys.excepthook = sys.__excepthook__

    @classmethod
    def save_checkpoint(cls, state, path):
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "timestamp": datetime.now().isoformat(),
                "state": state,
            }
            p.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                "utf-8",
            )
            return True
        except Exception:
            return False

    @classmethod
    def load_checkpoint(cls, path):
        try:
            p = Path(path)
            if not p.exists():
                return None
            data = json.loads(p.read_text("utf-8"))
            return data.get("state")
        except Exception:
            return None

    @classmethod
    def run_with_checkpoint(cls, task_fn, state_path, max_iterations=1000,
                            show_progress=False, **kwargs):
        """
        Цикл с чекпоинтами.
        task_fn(state, iteration, **kwargs) -> new_state.
        """
        state = cls.load_checkpoint(state_path)
        start_iter = 0
        if isinstance(state, dict):
            start_iter = state.get("__iteration__", 0)
            ui.print_info(f"Молли возобновила с итерации {start_iter}")

        total = max_iterations - start_iter
        progress_ctx = ui.progress(total=total, label="Loop") if show_progress \
            else None

        if progress_ctx is not None:
            progress_ctx.__enter__()

        try:
            for i in range(start_iter, max_iterations):
                if cls._stop_flag.is_set():
                    ui.print_warning("Молли: выполнение остановлено. Состояние сохранено.")
                    return state

                try:
                    new_state = task_fn(state, i, **kwargs)
                    if isinstance(new_state, dict):
                        new_state["__iteration__"] = i + 1
                    cls.save_checkpoint(new_state, state_path)
                    state = new_state
                except Exception as e:
                    cls.catch(e, stop=True)
                    return state

                if progress_ctx is not None:
                    try:
                        progress_ctx.update(i - start_iter + 1)
                    except Exception:
                        pass
        finally:
            if progress_ctx is not None:
                try:
                    progress_ctx.__exit__(None, None, None)
                except Exception:
                    pass

        return state

    @classmethod
    def get_logs(cls, date=None, level="def"):
        cls._ensure_dirs()
        target_dir = CRIT_LOGS if level == "crit" else DEF_LOGS
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        log_file = target_dir / f"{date}.log"
        if not log_file.exists():
            return []
        try:
            lines = log_file.read_text("utf-8").splitlines()
            return [json.loads(line) for line in lines if line.strip()]
        except Exception:
            return []

    @classmethod
    def clear_logs(cls):
        for d in (DEF_LOGS, CRIT_LOGS):
            if d.exists():
                try:
                    for f in d.glob("*.log"):
                        f.unlink()
                except Exception:
                    pass


__all__ = ["GuMolly", "LOG_DIR", "DEF_LOGS", "CRIT_LOGS"]