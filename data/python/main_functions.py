from datetime import datetime
from zipfile import ZipFile

import sqlite3
import pygame
import json
import sys
import os

from .platform_compat import IS_WEB


def terminate():
    """Стандартная функция для безопасного выхода"""
    pygame.quit()
    sys.exit()


def load_image(name):
    """Стандартная функция для импорта изображения"""
    return pygame.image.load(os.path.join("data", os.path.join("img", name)))


def put_sprite(sprite, x, y):
    """Функция редактирует расположение sprite"""
    sprite.rect.x = x
    sprite.rect.y = y


def create_sprite(sprite, name, x, y, group, transform=None):
    """Функция помогает быстрее поставить sprite"""

    image = load_image(name)

    if transform:
        image = pygame.transform.scale(image, transform)

    sprite.image = image
    sprite.rect = sprite.image.get_rect()
    put_sprite(sprite, x, y)
    group.add(sprite)


def add_fon(theme_value, size):
    """Функция ставит фон"""
    return pygame.transform.scale(load_image("fon_2.png"), size) if not (theme_value == "day" or (
            theme_value == "by_time_of_day" and 8 <= int(datetime.now().time().strftime("%H")
                                                         ) <= 18)) else pygame.transform.scale(
        load_image("fon_1.png"), size)


def custom_font(x):
    return os.path.join("data", os.path.join("fonts", f"font_{x}.ttf"))


def set_statistic(path, value, key="XP", add=True, t=None):
    """Функция устанавливает либо добавляет значение статистики"""
    if t is None:
        t = type(value)
    with open(path) as statistic_for_read:
        statistic = json.load(statistic_for_read)

    if add:
        statistic[key] = t(int(statistic[key]) + value)
    else:
        statistic[key] = t(value)

    with open(path, "w") as statistic_for_write:
        json.dump(statistic, statistic_for_write, ensure_ascii=False, indent="\t")


def format_xp(path):
    """Функция возвращает отформатированный уровень"""
    with open(path) as statistic_for_read:
        statistic = json.load(statistic_for_read)

        xp = statistic["XP"]

    level, requirement, x = None, None, xp

    for i in range(100):
        level, requirement = i, 100 * (i + 1)

        if requirement - x > 0:
            return f"{level} LVL\n{x}/{requirement} XP", level, x, requirement
        x -= requirement

    return f"100 LVL\n{x} XP", 100, x


def get_values(path, *values, a=False, d=False):  # a = all, d = dict
    """Функция получает значения переменных в файле"""
    with open(path, encoding="utf-8") as file:
        js = json.load(file)

        if d:
            vals = {}
            if a:
                for key in js.keys():
                    vals[key] = js[key]
            else:
                for value in values:
                    vals[value] = js[value]
        else:
            vals = []
            if a:
                for value in js.values():
                    vals.append(value)
            else:
                for value in values:
                    vals.append(js[value])

        return vals


def set_values(path, values: dict):
    """Функция ставит переменные в файле"""
    with open(path, encoding="utf-8") as file_read:
        js = json.load(file_read)

    for value in values.keys():
        js[value] = values[value]

    with open(path, "w") as file_write:
        json.dump(js, file_write, ensure_ascii=False, indent="\t")


def get_values_sqlite(path, table, condition=None, *values):
    """Функция получает значения переменной в базе данных"""
    with sqlite3.connect(path) as con:
        cur = con.cursor()

        c = f"SELECT {', '.join(values)} FROM {table}"
        if condition is not None:
            c += f"\nWHERE {condition}"

        return cur.execute(c).fetchall()


def extract_files(path_archive, path_extract, *values, a=False):
    """Функция распаковывает нужные файлы"""
    with ZipFile(path_archive, "r") as archive:
        if a:
            archive.extractall(path_extract)
        else:
            for file in values:
                archive.extract(file, path_extract)


def create_window(path):
    """Функция создаёт окно pygame"""
    path_config = os.path.join(path, "config.json")
    version, screensize, screenmode, fps = get_values(path_config, "version", "screensize",
                                                      "screenmode", "fps")

    if version != "1.3":
        old_values = get_values(path_config, a=True, d=True)
        old_values["version"] = "1.3"

        extract_files(os.path.join("data", os.path.join("packages", "files.zip")), path,
                      "config.json")

        set_values(path_config, old_values)

    size, screen = tuple(map(int, screensize.split("x"))), None

    if IS_WEB:
        # В браузере холст всегда один и масштабируется средствами страницы,
        # поэтому режимы окна (рамка/полный экран) смысла не имеют.
        screen = pygame.display.set_mode(size)

    elif screenmode == "window":
        screen = pygame.display.set_mode(size)  # создаём окно
        pygame.display.set_caption("Sea Battle")  # ставим заголовок

    elif screenmode == "noframe":
        screen = pygame.display.set_mode(size, pygame.NOFRAME)

    elif screenmode == "fullscreen":
        screen = pygame.display.set_mode(size, pygame.FULLSCREEN)

    pygame.display.set_icon(load_image("icon.png"))

    return screen, int(fps)
