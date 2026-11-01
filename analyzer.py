"""Разбор исключений: тип, файл, строка, извлечение конкретики."""
import re

from .error_db import get_error_info


def analyze_exception(exc):
    exc_type = type(exc).__name__
    exc_msg = str(exc)

    file_path = None
    line_no = None
    tb = exc.__traceback__
    if tb is not None:
        while tb.tb_next is not None:
            tb = tb.tb_next
        file_path = tb.tb_frame.f_code.co_filename
        line_no = tb.tb_lineno

    info = get_error_info(exc_type)

    result = {
        "type": exc_type,
        "message": exc_msg,
        "file": file_path,
        "line": line_no,
        "description": info["description"],
        "causes": list(info["causes"]),
        "suggestions": list(info["suggestions"]),
        "auto_fixable": info.get("auto_fixable", False),
    }

    if exc_type == "ModuleNotFoundError":
        result["missing_module"] = _extract_missing_module(exc_msg)
    elif exc_type == "NameError":
        result["missing_name"] = _extract_missing_name(exc_msg)
    elif exc_type == "FileNotFoundError":
        result["missing_file"] = _extract_missing_file(exc_msg)
    elif exc_type == "KeyError":
        result["missing_key"] = _extract_missing_key(exc_msg)

    return result


def _extract_missing_module(msg):
    m = re.search(r"No module named '([^']+)'", msg)
    return m.group(1) if m else None


def _extract_missing_name(msg):
    m = re.search(r"name '([^']+)' is not defined", msg)
    return m.group(1) if m else None


def _extract_missing_file(msg):
    m = re.search(r"No such file or directory: '([^']+)'", msg)
    return m.group(1) if m else None


def _extract_missing_key(msg):
    # KeyError("emial") -> str() = "'emial'"
    # Отрезаем кавычки
    s = msg.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s or None


def short_location(info):
    if info.get("file") and info.get("line"):
        from pathlib import Path
        fname = Path(info["file"]).name
        return f"{fname}:{info['line']}"
    return ""


__all__ = ["analyze_exception", "short_location"]