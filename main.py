"""Точка входа.

pygbag требует, чтобы запускаемый файл назывался main.py и содержал
asyncio.run(...) — отсюда стартует и веб-сборка, и обычный десктоп.
"""

import asyncio
import traceback

# pygbag решает, какие пакеты доставить в браузер, по импортам именно этого
# файла. Без явного import pygame сюда приезжает заглушка без подмодулей,
# и игра падает на pygame.sprite ещё до первого кадра.
import pygame
import pygame.sprite
import pygame.image
import pygame.transform
import pygame.mixer
import pygame.font

from data.python.platform_compat import web_log


async def _main():
    # Без этого любая ошибка уходит во внутренний терминал pygbag и в браузере
    # выглядит как молчаливое зависание на этапе загрузки.
    try:
        from run import run

        web_log("start")
        await run()
    except SystemExit:
        raise
    except BaseException:
        web_log("CRASH\n" + traceback.format_exc())
        raise


asyncio.run(_main())
