"""Совместимость с платформами.

Игра изначально писалась под Windows и хранила сохранения в "Документах".
В браузере (pygbag/WASM) файловая система живёт в памяти и пропадает при
перезагрузке страницы, поэтому сохранения дополнительно зеркалируются
в localStorage.
"""

import base64
import os
import sys

IS_WEB = sys.platform == "emscripten"

#: Файлы, которые составляют весь прогресс игрока.
SAVE_FILES = ("config.json", "statistic.json", "achievements.sqlite")

_STORAGE_PREFIX = "sea_battle/"


def user_data_dir():
    """Каталог с сохранениями, свой для каждой платформы"""
    # Позволяет прогонять сборку, не задевая сохранения установленной игры
    override = os.environ.get("SEA_BATTLE_DATA_DIR")
    if override:
        return override

    if IS_WEB:
        # MEMFS, содержимое зеркалируется в localStorage
        return os.path.join("/tmp", "Sea Battle")

    if sys.platform == "win32":
        # оригинальное поведение: папка "Документы" текущего пользователя
        import ctypes.wintypes

        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
        return os.path.join(buf.value, "Sea Battle")

    return os.path.join(os.path.expanduser("~"), ".local", "share", "Sea Battle")


def web_log(*args):
    """Написать в консоль браузера.

    Обычный print уходит во внутренний терминал pygbag, который не виден
    ни в devtools, ни в логах — а разбирать ошибки на телефоне надо как-то.
    """
    message = " ".join(str(a) for a in args)
    if not IS_WEB:
        print(message)
        return
    try:
        import platform

        platform.window.console.log("[sea_battle] " + message)
    except Exception:
        print(message)


def _storage():
    """localStorage браузера, либо None вне браузера"""
    if not IS_WEB:
        return None
    try:
        import platform

        return platform.window.localStorage
    except Exception:
        return None


def restore(path):
    """Достать сохранения из localStorage в файловую систему.

    Возвращает True, если хоть один файл был восстановлен: в этом случае
    распаковывать эталонные файлы из архива уже не нужно.
    """
    storage = _storage()
    if storage is None:
        return False

    restored = False
    for name in SAVE_FILES:
        try:
            blob = storage.getItem(_STORAGE_PREFIX + name)
        except Exception:
            blob = None

        if not blob:
            continue

        try:
            with open(os.path.join(path, name), "wb") as file:
                file.write(base64.b64decode(blob))
            restored = True
        except Exception as error:
            print(f"restore {name} failed: {error!r}")

    return restored


def persist(path):
    """Сохранить файлы прогресса в localStorage"""
    storage = _storage()
    if storage is None:
        return

    for name in SAVE_FILES:
        file_path = os.path.join(path, name)
        if not os.path.isfile(file_path):
            continue

        try:
            with open(file_path, "rb") as file:
                blob = base64.b64encode(file.read()).decode("ascii")
            storage.setItem(_STORAGE_PREFIX + name, blob)
        except Exception as error:
            print(f"persist {name} failed: {error!r}")
