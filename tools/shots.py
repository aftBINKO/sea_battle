"""Отрисовка всех экранов игры без окна — для проверки вёрстки.

Холст в браузере подстраивается под устройство, поэтому одну и ту же
раскладку надо смотреть на разных ширинах. Открывать игру руками ради
каждой правки долго, а половина разъездов видна только на краях диапазона.

    python tools/shots.py                      # 1366, полная версия
    python tools/shots.py --widths 1024,1920   # несколько ширин
    python tools/shots.py --web                # как в браузере: демо и урезанные настройки
    python tools/shots.py --only menu,settings # только нужные экраны
    python tools/shots.py --sheet              # собрать всё в один лист

Кадры кладутся в build/shots (каталог не в репозитории). Сохранения берутся
из отдельной папки там же, боевые не задеваются.
"""

import argparse
import asyncio
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Окно не нужно и звук тоже; выставляем до импорта pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

OUT_DIR = os.path.join(ROOT, "build", "shots")
os.environ.setdefault("SEA_BATTLE_DATA_DIR", os.path.join(OUT_DIR, "save"))

import pygame  # noqa: E402  (после SDL_VIDEODRIVER)

from data.python.main_functions import create_window, extract_files, set_values  # noqa: E402
from data.python.platform_compat import user_data_dir  # noqa: E402

#: Высота холста зафиксирована во всей игре, меняется только ширина
HEIGHT = 768

#: Состояние сохранений, при котором видно все экраны: пролог пройден,
#: режимы открыты, статистика непустая
SAVE_STATE = {"mission": "2", "XP": 1250, "games": 12, "victories": 7, "defeats": 5}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--widths", default="1366",
                       help="ширины холста через запятую (по умолчанию 1366)")
    parser.add_argument("--only", default="",
                       help="только эти экраны, через запятую")
    parser.add_argument("--web", action="store_true",
                       help="притвориться браузером: демо-режим и урезанные настройки")
    parser.add_argument("--sheet", action="store_true",
                       help="дополнительно собрать контактный лист")
    parser.add_argument("--out", default=OUT_DIR, help="куда складывать кадры")
    parser.add_argument("--frames", type=int, default=14,
                       help="сколько кадров прокрутить перед снимком")
    return parser.parse_args()


def prepare(args):
    """Подготовить сохранения и окно"""
    os.makedirs(args.out, exist_ok=True)

    path = user_data_dir()
    os.makedirs(path, exist_ok=True)
    for name in ("config.json", "statistic.json", "achievements.sqlite"):
        if not os.path.isfile(os.path.join(path, name)):
            extract_files(os.path.join("data", "packages", "files.zip"), path, name)

    pygame.init()
    pygame.mixer.init()
    create_window(path)

    if args.web:
        # Флаги читаются на импорте, поэтому подменяем их в самих модулях
        from data.python import menu, play, settings
        settings.IS_WEB = True
        menu.WEB_DEMO = play.WEB_DEMO = True

    set_values(os.path.join(path, "statistic.json"), SAVE_STATE)
    return path


def screens(path, web):
    """Список экранов: (имя, как построить)"""
    from data.python.custom_map import Customization
    from data.python.menu import Instruction, Menu, Statistic
    from data.python.play import GameOver, Play
    from data.python.settings import About, Settings

    fps = 60
    items = [
        ("menu", lambda s: Menu(s, fps, path, None).menu),
        ("settings", lambda s: Settings(s, fps, path).menu),
        ("about", lambda s: About(s, fps, os.path.join(path, "config.json")).menu),
        ("statistic", lambda s: Statistic(s, fps, path).menu),
        ("instruction", lambda s: Instruction(s, fps, path).menu),
        ("mission", lambda s: Play(s, fps, path).menu),
        ("customization", lambda s: Customization(s, fps, path, True).map_customization),
        ("gameover", lambda s: GameOver(s, fps, path, True, 20, 300, 3).menu),
    ]

    if not web:  # в демо этих экранов нет
        from data.python.achievements import Achievements, Titles
        items[3:3] = [("achievements", lambda s: Achievements(s, fps, path).menu),
                      ("titles", lambda s: Titles(s, fps, path).menu)]
    return items


async def capture(name, make, width, args):
    """Отрисовать экран и сохранить кадр. Возвращает True при успехе."""
    screen = pygame.display.set_mode((width, HEIGHT))

    # эти модули держат размеры в глобальных переменных
    from data.python import custom_map, play
    for module in (play, custom_map):
        module.display_width, module.display_height = width, HEIGHT

    try:
        run = make(screen)
    except Exception:
        print(f"  {name}: НЕ СОЗДАЛСЯ")
        traceback.print_exc()
        return False

    task = asyncio.ensure_future(run())
    for _ in range(args.frames):
        await asyncio.sleep(0)

    if task.done() and task.exception():
        print(f"  {name}: ОШИБКА")
        traceback.print_exception(task.exception())
        return False

    pygame.image.save(screen, os.path.join(args.out, f"{name}_{width}.png"))
    task.cancel()
    try:
        await task
    except BaseException:
        pass

    print(f"  {name}_{width}.png")
    return True


def build_sheet(names, width, args):
    """Собрать кадры одной ширины в общий лист"""
    columns = 2
    cell_w, cell_h = 900, int(900 * HEIGHT / width)
    rows = (len(names) + columns - 1) // columns

    sheet = pygame.Surface((cell_w * columns, cell_h * rows))
    sheet.fill((25, 25, 30))
    font = pygame.font.Font(None, 30)

    for i, name in enumerate(names):
        frame = pygame.image.load(os.path.join(args.out, f"{name}_{width}.png"))
        frame = pygame.transform.smoothscale(frame, (cell_w - 8, cell_h - 8))

        x, y = (i % columns) * cell_w, (i // columns) * cell_h
        sheet.blit(frame, (x + 4, y + 4))
        pygame.draw.rect(sheet, (255, 200, 0), (x + 4, y + 4, cell_w - 8, cell_h - 8), 2)
        sheet.blit(font.render(name, True, (255, 220, 0)), (x + 14, y + 12))

    out = os.path.join(args.out, f"sheet_{width}.png")
    pygame.image.save(sheet, out)
    print(f"  лист: {out}")


async def main():
    args = parse_args()
    path = prepare(args)

    wanted = set(filter(None, args.only.split(",")))
    items = [(n, m) for n, m in screens(path, args.web) if not wanted or n in wanted]
    if not items:
        print(f"нет таких экранов: {args.only}")
        return 1

    failed = []
    for width in (int(w) for w in args.widths.split(",")):
        print(f"--- ширина {width} ---")
        done = []
        for name, make in items:
            if await capture(name, make, width, args):
                done.append(name)
            else:
                failed.append(f"{name}@{width}")

        if args.sheet and done:
            build_sheet(done, width, args)

    if failed:
        print("\nне отрисовались:", ", ".join(failed))
        return 1

    print(f"\nготово, кадры в {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
