from datetime import datetime
from zipfile import ZipFile

import sqlite3
import pygame
import json
import sys
import os

from .platform_compat import IS_WEB, viewport_aspect


#: Насколько можно увести палец, чтобы касание всё ещё считалось нажатием
TAP_SLOP = 12

#: Доля ширины экрана на одну клетку поля 10x10. От неё же зависят размеры
#: кораблей и панели с ними, поэтому число одно на всю игру.
#: Предел — два поля рядом в бою: больше 0.044 второе не помещается по ширине.
CELL_RATIO = 0.041

#: Сколько высоты занято подписями сверху и кнопками снизу
BOARD_MARGINS = 130


def cell_size(width, height):
    """Размер клетки поля.

    Считается от ширины, но обязательно упирается в высоту: холст тянется
    только вбок, и на широком экране поле иначе вылезает за нижний край.
    """
    return max(20, min(int(width * CELL_RATIO), (height - BOARD_MARGINS) // 10))


class DragScroll:
    """Прокрутка списков протяжкой пальца.

    Списки листались только колесом мыши и стрелками, а на телефоне нет ни
    того, ни другого. Класс превращает движение прижатого пальца в смещение
    содержимого в пикселях.
    """

    def __init__(self, slop=TAP_SLOP, friction=0.9):
        self.slop = slop
        self.friction = friction
        self.pressed = False
        self.last_y = 0
        self.moved = 0
        self.velocity = 0.0

    def handle(self, event):
        """Обработать событие и вернуть сдвиг содержимого по вертикали"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pressed = True
            self.last_y = event.pos[1]
            self.moved = 0
            self.velocity = 0.0  # палец опустили — инерцию гасим

        elif event.type == pygame.MOUSEMOTION and self.pressed:
            delta = event.pos[1] - self.last_y
            self.last_y = event.pos[1]
            self.moved += abs(delta)
            # сглаживаем: одиночные события дрожат
            self.velocity = self.velocity * 0.6 + delta * 0.4
            return delta

        elif event.type == pygame.MOUSEBUTTONUP:
            self.pressed = False

        return 0

    def momentum(self):
        """Докрутка по инерции после того, как палец отпустили.

        Вызывается раз за кадр. Без неё список останавливается ровно там,
        где оторвали палец, и это ощущается мёртвым.
        """
        if self.pressed or abs(self.velocity) < 0.5:
            self.velocity = 0.0
            return 0

        self.velocity *= self.friction
        return self.velocity

    def stop(self):
        """Погасить инерцию — например, когда упёрлись в край списка"""
        self.velocity = 0.0

    def is_tap(self):
        """Было ли это касанием, а не протяжкой"""
        return self.moved <= self.slop


def terminate():
    """Стандартная функция для безопасного выхода"""
    pygame.quit()
    sys.exit()


#: Кэши: экраны перерисовываются целиком каждый кадр, и без них достижения
#: успевали за кадр прочитать с диска 90 картинок и заново разобрать 242 ttf.
_image_cache = {}
_font_cache = {}


def load_image(name):
    """Стандартная функция для импорта изображения"""
    image = _image_cache.get(name)
    if image is not None:
        return image

    image = pygame.image.load(os.path.join("data", os.path.join("img", name)))

    # Без convert_alpha() каждый блит пересчитывает формат пикселей заново,
    # и полноэкранный фон один съедал больше половины кадра.
    if pygame.display.get_surface() is not None:
        image = image.convert_alpha()
        _image_cache[name] = image  # кэшируем только уже готовое к выводу

    return image


def stretch_to(name, width):
    """Размер для create_sprite: заданная ширина, исходная высота.

    Подложки нарисованы под холст 1366 px. Раз ширина теперь зависит от
    устройства, их надо растягивать, иначе на широком экране справа остаётся
    непокрытая полоса.
    """
    return width, load_image(name).get_height()


def get_font(path, size):
    """Шрифт из кэша: pygame.font.Font заново читает ttf при каждом вызове"""
    key = (path, size)
    font = _font_cache.get(key)
    if font is None:
        font = pygame.font.Font(path, size)
        _font_cache[key] = font
    return font


_text_cache = {}


def render_text(path, size, text, color, antialias=True):
    """Готовая надпись из кэша.

    Шрифт кэшируется отдельно, но render() всё равно растеризует строку
    заново на каждом кадре, а надписи в списках не меняются.
    """
    key = (path, size, text, tuple(color))
    surface = _text_cache.get(key)
    if surface is None:
        if len(_text_cache) > 512:  # страховка от бесконечного роста
            _text_cache.clear()
        surface = get_font(path, size).render(text, antialias, color)
        _text_cache[key] = surface
    return surface


def draw_scrollbar(screen, x, top, height, progress, thumb_ratio, width=12):
    """Полоска прокрутки у края экрана.

    На телефоне иначе никак не понять, что список вообще листается:
    ни колеса, ни полосы браузера тут нет. Фон под полоской — пёстрая
    картинка кабины, поэтому нужен контраст, а не аккуратный серый.
    """
    if thumb_ratio >= 1:
        return  # листать нечего

    radius = width // 2
    pygame.draw.rect(screen, (20, 20, 20), (x, top, width, height), border_radius=radius)

    thumb_height = max(40, int(height * thumb_ratio))
    thumb_y = top + int((height - thumb_height) * min(1.0, max(0.0, progress)))
    pygame.draw.rect(screen, (245, 245, 245), (x, thumb_y, width, thumb_height),
                     border_radius=radius)
    # тёмный кант, чтобы бегунок не сливался со светлыми участками фона
    pygame.draw.rect(screen, (20, 20, 20), (x, thumb_y, width, thumb_height), 2,
                     border_radius=radius)


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
    return pygame.transform.scale(load_image("fon_2.jpg"), size) if not (theme_value == "day" or (
            theme_value == "by_time_of_day" and 8 <= int(datetime.now().time().strftime("%H")
                                                         ) <= 18)) else pygame.transform.scale(
        load_image("fon_1.jpg"), size)


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


#: Высота холста. Вся вёрстка построена под неё, поэтому она не меняется —
#: подстраивается только ширина, под пропорции устройства.
DESIGN_HEIGHT = 768

#: Пределы ширины: уже 4:3 и шире 21:9 макеты уже разъезжаются.
MIN_WIDTH, MAX_WIDTH = 1024, 1920


def web_window_size():
    """Размер холста под пропорции окна браузера"""
    aspect = viewport_aspect()
    if not aspect:
        return 1366, DESIGN_HEIGHT

    width = int(round(DESIGN_HEIGHT * aspect))
    return max(MIN_WIDTH, min(MAX_WIDTH, width)), DESIGN_HEIGHT


def screen_size():
    """Фактический размер холста.

    Раньше вёрстка бралась из config.json, но теперь холст подстраивается
    под устройство, и файл о его размере ничего не знает.
    """
    surface = pygame.display.get_surface()
    return surface.get_size() if surface is not None else (1366, DESIGN_HEIGHT)


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
        # Холст подгоняем под пропорции экрана телефона, иначе по краям
        # остаются чёрные полосы. Высоту держим равной 768: вся вёрстка игры
        # рассчитана на неё, и менять надо только горизонталь.
        size = web_window_size()
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
