"""MollyWaff (Molly with affection) — интерактивный автофикс с подтверждением."""
import sys
import difflib
import subprocess
from pathlib import Path

from . import charm_enhance as ui
from .analyzer import analyze_exception
from .molly import Molly
from .messages import (
    WAFF_INTRO_TEMPLATE, WAFF_FIXING_TEMPLATE,
    WAFF_SUCCESS_TEMPLATE, WAFF_FAILURE_TEMPLATE, WAFF_SUGGEST_TEMPLATE,
    get_encouragement,
)


_VIRTUAL_PATHS = {"<stdin>", "<string>", "<func>", "<module>"}


class MollyWaff:
    """Интерактивный автофикс: ловит ошибку, предлагает способы починить."""

    @classmethod
    def catch(cls, exc):
        info = analyze_exception(exc)
        exc_type = info["type"]

        fixes = cls._get_fixes(info)

        if not fixes:
            Molly.print_explanation(exc)
            return False

        fix_desc = "; ".join(f["description"] for f in fixes)
        intro_msg = WAFF_INTRO_TEMPLATE.format(
            type=exc_type,
            description=info["description"],
            fix_description=fix_desc,
        )
        ui.print_box(intro_msg, title="MollyWaff", color="#ff7518")

        options = [f["description"] for f in fixes] + ["Не чинить"]
        choice = ui.ask_choice("Что делаем?", options, default="Не чинить")

        if choice is None or choice == "Не чинить":
            ui.print_info("Хорошо, Молли не трогает код. Если передумаете — обращайтесь!")
            return False

        idx = options.index(choice)
        fix = fixes[idx]

        ui.print_info(WAFF_FIXING_TEMPLATE.format(fix_name=fix["name"]))
        try:
            success = fix["action"]()
        except Exception as e:
            ui.print_error(f"Ошибка при выполнении фикса: {e}")
            success = False

        if success:
            ui.print_success(WAFF_SUCCESS_TEMPLATE.format(fix_name=fix["name"]))
            return True

        ui.print_warning(WAFF_FAILURE_TEMPLATE.format(
            fix_name=fix["name"], problem=exc_type,
        ))
        alternatives = cls._get_alternatives(info)
        if alternatives:
            ui.print_info(WAFF_SUGGEST_TEMPLATE.format(alternative=alternatives[0]))
        ui.print_msg(get_encouragement(), color="#22c55e")
        return False

    @classmethod
    def _is_real_file(cls, path):
        if not path:
            return False
        return path not in _VIRTUAL_PATHS and not path.startswith("<")

    @classmethod
    def _get_fixes(cls, info):
        fixes = []
        exc_type = info["type"]

        if exc_type == "ModuleNotFoundError":
            module = info.get("missing_module")
            if module:
                fixes.append({
                    "name": f"pip install {module}",
                    "description": f"Установить модуль «{module}» через pip",
                    "action": lambda m=module: cls._fix_pip_install(m),
                })
                suggestion = cls._suggest_module(module)
                file_path = info.get("file")
                if (suggestion and suggestion != module
                        and cls._is_real_file(file_path)):
                    fixes.append({
                        "name": "замена имени модуля",
                        "description": (
                            f"Возможно, имелся в виду «{suggestion}» "
                            f"вместо «{module}»"
                        ),
                        "action": lambda f=file_path, o=module, n=suggestion:
                            cls._fix_replace_in_file(
                                f, f"import {o}", f"import {n}"
                            ),
                    })

        elif exc_type == "FileNotFoundError":
            missing = info.get("missing_file")
            if missing:
                fixes.append({
                    "name": f"создание файла «{missing}»",
                    "description": f"Создать пустой файл по пути «{missing}»",
                    "action": lambda p=missing: cls._fix_create_file(p),
                })
                suggestion = cls._suggest_similar_file(missing)
                if suggestion:
                    fixes.append({
                        "name": "переименование",
                        "description": (
                            f"Возможно, имелся в виду «{suggestion}» — "
                            f"переименовать?"
                        ),
                        "action": lambda o=suggestion, n=missing:
                            cls._fix_rename_file(o, n),
                    })

        elif exc_type == "NameError":
            name = info.get("missing_name")
            file_path = info.get("file")
            if name and cls._is_real_file(file_path):
                suggestion = cls._suggest_name_in_file(file_path, name)
                if suggestion:
                    fixes.append({
                        "name": "замена имени",
                        "description": (
                            f"Возможно, «{name}» — опечатка. "
                            f"Заменить на «{suggestion}» в файле?"
                        ),
                        "action": lambda f=file_path, o=name, n=suggestion:
                            cls._fix_replace_in_file(f, o, n),
                    })

        elif exc_type == "KeyError":
            key = info.get("missing_key")
            file_path = info.get("file")
            if key and cls._is_real_file(file_path):
                suggestion = cls._suggest_key_in_file(file_path, key)
                if suggestion:
                    fixes.append({
                        "name": "замена ключа",
                        "description": (
                            f"Ключ «{key}» не найден. Возможно, "
                            f"имелся в виду «{suggestion}»?"
                        ),
                        "action": lambda f=file_path, o=key, n=suggestion:
                            cls._fix_replace_in_file(
                                f, f"['{o}']", f"['{n}']"
                            ),
                    })

        if cls._is_real_file(info.get("file")):
            fixes.append({
                "name": "точечный фикс",
                "description": "Указать вручную, что изменить в файле",
                "action": lambda f=info["file"]: cls._fix_manual(f),
            })

        return fixes

    @classmethod
    def _get_alternatives(cls, info):
        return list(info.get("suggestions", []))[:2]

    # ============================================================
    # Фиксы
    # ============================================================
    @classmethod
    def _fix_pip_install(cls, module):
        try:
            ui.print_info(f"pip install {module} (это может занять время)...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", module],
                capture_output=True, text=True, timeout=180,
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def _fix_create_file(cls, path):
        try:
            p = Path(path)
            if p.exists():
                return True
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
            return True
        except Exception:
            return False

    @classmethod
    def _fix_rename_file(cls, old, new):
        try:
            old_path = Path(old)
            new_path = Path(new)
            if not old_path.exists() or new_path.exists():
                return False
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.rename(new_path)
            return True
        except Exception:
            return False

    @classmethod
    def _fix_replace_in_file(cls, filepath, old, new):
        try:
            path = Path(filepath)
            if not path.exists():
                return False
            content = path.read_text("utf-8", errors="replace")
            if old not in content:
                return False
            path.write_text(content.replace(old, new), "utf-8")
            return True
        except Exception:
            return False

    @classmethod
    def _fix_manual(cls, filepath):
        try:
            path = Path(filepath)
            if not path.exists():
                ui.print_error(f"Файл не найден: {path}")
                return False

            line_str = ui.ask("Номер строки (1-based)")
            if not line_str:
                return False
            try:
                line_num = int(line_str)
            except (ValueError, TypeError):
                ui.print_error("Нужно число")
                return False

            remove_str = ui.ask("Сколько символов удалить с начала строки?", default="0")
            try:
                remove_count = int(remove_str or 0)
            except (ValueError, TypeError):
                remove_count = 0

            replacement = ui.ask("На что заменить (Enter — пусто)") or ""

            lines = path.read_text("utf-8", errors="replace").splitlines(keepends=True)
            if not (1 <= line_num <= len(lines)):
                ui.print_error(f"Строка {line_num} вне файла (всего {len(lines)})")
                return False

            old_line = lines[line_num - 1]
            new_line = replacement + old_line[remove_count:]
            lines[line_num - 1] = new_line

            path.write_text("".join(lines), "utf-8")
            return True
        except Exception as e:
            ui.print_error(f"Ошибка: {e}")
            return False

    # ============================================================
    # Подсказки
    # ============================================================
    @classmethod
    def _suggest_similar_file(cls, missing):
        try:
            p = Path(missing)
            parent = p.parent if p.is_absolute() else Path.cwd()
            if not parent.exists():
                return None
            names = [f.name for f in parent.iterdir() if f.is_file()]
            matches = difflib.get_close_matches(p.name, names, n=1, cutoff=0.6)
            if matches:
                return str(parent / matches[0])
        except Exception:
            pass
        return None

    @classmethod
    def _suggest_module(cls, missing):
        """Ищет похожий модуль среди установленных и загруженных."""
        try:
            import pkgutil
            candidates = set(sys.modules.keys()) | set(sys.builtin_module_names)
            try:
                candidates |= {m.name for m in pkgutil.iter_modules()}
            except Exception:
                pass
            candidates = {
                c for c in candidates
                if isinstance(c, str) and not c.startswith("_") and len(c) >= 3
            }
            matches = difflib.get_close_matches(
                missing, list(candidates), n=1, cutoff=0.7
            )
            return matches[0] if matches else None
        except Exception:
            return None

    @classmethod
    def _suggest_name_in_file(cls, filepath, name):
        import ast
        try:
            path = Path(filepath)
            if not path.exists():
                return None
            tree = ast.parse(path.read_text("utf-8", errors="replace"))
            defined = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined.add(node.name)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    defined.add(node.id)
                elif isinstance(node, ast.arg):
                    defined.add(node.arg)
            candidates = [d for d in defined if len(d) >= 3]
            matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.7)
            return matches[0] if matches else None
        except Exception:
            return None

    @classmethod
    def _suggest_key_in_file(cls, filepath, key):
        """Ищет похожий строковый литерал в файле (для KeyError)."""
        import ast
        try:
            path = Path(filepath)
            if not path.exists():
                return None
            tree = ast.parse(path.read_text("utf-8", errors="replace"))
            strings = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    strings.add(node.value)
            candidates = [s for s in strings if len(s) >= 3 and s != key]
            matches = difflib.get_close_matches(key, candidates, n=1, cutoff=0.6)
            return matches[0] if matches else None
        except Exception:
            return None

    # ============================================================
    # Декоратор и контекстный менеджер
    # ============================================================
    @classmethod
    def watch(cls, func):
        import functools

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
            MollyWaff.catch(exc)
            return True
        return False


__all__ = ["MollyWaff"]