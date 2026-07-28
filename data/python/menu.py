import asyncio
import os
import sqlite3

import pygame

from .main_functions import terminate, create_sprite, put_sprite, format_xp, get_values, \
    get_values_sqlite, add_fon, load_image, extract_files, custom_font, get_font

try:  # для воспроизведения заставки по кадрам; в браузере OpenCV недоступен
    from cv2 import VideoCapture
except ImportError:
    VideoCapture = None


class Menu:
    """Главное меню"""

    # ogg вместо wav: в 20 раз легче и это единственный формат, который
    # pygbag принимает для веб-сборки
    sound_screensaver = os.path.join("data", os.path.join("sound", "screensaver.ogg"))
    package = os.path.join("data", os.path.join("packages", "files.zip"))
    sound_achievement = os.path.join("data", os.path.join("sound", "achievement.ogg"))
    click = os.path.join("data", os.path.join("sound", "click.ogg"))
    enter = os.path.join("data", os.path.join("sound", "enter.ogg"))
    font_1 = os.path.join("data", os.path.join("fonts", "font_1.ttf"))
    font_2 = os.path.join("data", os.path.join("fonts", "font_2.ttf"))

    def __init__(self, screen, fps, path, push):
        self.path_config, self.path_achievements, self.path_statistic, self.path = os.path.join(
            path, "config.json"), os.path.join(path, "achievements.sqlite"), os.path.join(
            path, "statistic.json"), path
        self.screen, self.fps, self.size, self.n, self.push = screen, fps, tuple(
            map(int, (get_values(self.path_config, "screensize")[0].split("x")))), 0, push
        self.path_screensaver = os.path.join("data",
                                             os.path.join("video", f"screensaver{self.size[1]}.mp4"))

    async def screensaver(self):
        """Заставка"""
        if VideoCapture is None:
            # В вебе видео весит 8 МБ и OpenCV недоступен — показываем статичную
            # заставку под тот же звук, её можно пропустить касанием.
            return await self._screensaver_static()

        # воспроизводим видео, в соответствии разрешения
        cap = VideoCapture(self.path_screensaver)

        # т.к видео воспроизводится без звука, мы его добавим вручную
        s = pygame.mixer.Sound(self.sound_screensaver)

        running, img = cap.read()  # running — кадры остались? img — изображение
        shape = img.shape[1::-1]
        clock = pygame.time.Clock()
        s.play()  # воспроизводим звук

        while running:
            clock.tick(self.fps)
            running, img = cap.read()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_DELETE:
                    extract_files(self.package, self.path, a=True)

            try:
                self.screen.blit(pygame.image.frombuffer(img.tobytes(), shape, "BGR"), (0, 0))
            except AttributeError:
                pass

            pygame.display.update()
            await asyncio.sleep(0)
        s.stop()

    async def _screensaver_static(self):
        """Заставка без видео: логотип и название под звук вступления"""
        try:
            sound = pygame.mixer.Sound(self.sound_screensaver)
            sound.play()
        except pygame.error:
            sound = None

        fon = add_fon(get_values(self.path_config, "theme")[0], self.size)

        logo = pygame.transform.scale(load_image("aft_games.png"), (200, 200))
        logo_rect = logo.get_rect(center=(self.size[0] // 2, self.size[1] // 2 - 50))

        title = get_font(self.font_1, 90).render("Sea Battle", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.size[0] // 2, self.size[1] // 2 + 120))

        hint = get_font(self.font_2, 25).render(
            "нажмите, чтобы продолжить", True, (192, 192, 192))
        hint_rect = hint.get_rect(center=(self.size[0] // 2, self.size[1] - 60))

        clock, frames, total = pygame.time.Clock(), 0, self.fps * 5
        while frames < total:
            frames += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    frames = total

            # плавное появление и затухание
            if frames < self.fps:
                alpha = int(255 * frames / self.fps)
            elif frames > total - self.fps:
                alpha = int(255 * (total - frames) / self.fps)
            else:
                alpha = 255

            self.screen.blit(fon, (0, 0))
            for surface, rect in ((logo, logo_rect), (title, title_rect), (hint, hint_rect)):
                surface.set_alpha(alpha)
                self.screen.blit(surface, rect)

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)

        if sound is not None:
            sound.stop()

    #: Подписи в buttons.png лежат лентой: 8 штук по 250 px с шагом 300.
    LABEL_WIDTH, LABEL_PITCH, LABEL_HEIGHT = 250, 300, 50

    def _tiles(self):
        """Плитки меню: (индекс подписи в ленте, что вернуть при нажатии).

        Недоступные режимы просто не показываем — в карусели они занимали
        место и молча ничего не делали при выборе.
        """
        unlocked = int(get_values(self.path_statistic, "mission")[0]) > 1

        items = [(0, "Play")]
        if unlocked:
            items += [(1, "Play_With_Bot"), (2, "Farm")]
        items += [(3, "Settings"), (4, "Achievements"), (5, "Statistic"),
                  (6, "Instruction"), (7, "Exit")]
        return items

    async def menu(self):
        """Меню"""
        fon = add_fon(get_values(self.path_config, "theme")[0], self.size)

        clock = pygame.time.Clock()

        menu_sprites = pygame.sprite.Group()

        title, t = get_values(self.path_statistic, "title")[0], pygame.sprite.Sprite()
        if title != "not":
            create_sprite(t, get_values_sqlite(self.path_achievements, "titles", f"id = {title}",
                                               "image")[0][0], self.size[0] - 100,
                          self.size[1] - 100, menu_sprites)

        # Сетка плиток вместо карусели: по кнопке видно, что это кнопка, и
        # нажимается она сразу, без перелистывания к нужной.
        items = self._tiles()
        big = self.size[1] != 768

        tile_w, tile_h = (500, 100) if big else (420, 84)
        gap_x, gap_y = (100, 40) if big else (80, 32)
        columns = 2
        rows = (len(items) + columns - 1) // columns

        grid_w = columns * tile_w + (columns - 1) * gap_x
        grid_h = rows * tile_h + (rows - 1) * gap_y
        top_margin = 210 if big else 150
        grid_x = (self.size[0] - grid_w) // 2
        grid_y = top_margin + max(
            0, (self.size[1] - top_margin - (170 if big else 120) - grid_h) // 2)

        strip = load_image("buttons.png")
        frame_image = pygame.transform.scale(load_image("frame_6.png"), (tile_w, tile_h))

        # Подписи в ленте прозрачные, а фон меню — светлая фотография моря.
        # Без подложки белый текст на небе почти не читается.
        plate = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
        plate.fill((12, 18, 28, 210))

        # Шапка с уровнем и названием — по той же причине, что и подложки плиток
        header_height = 150 if big else 110
        header = pygame.Surface((self.size[0], header_height), pygame.SRCALPHA)
        header.fill((12, 18, 28, 150))

        tiles = []  # (прямоугольник, готовая подпись, что вернуть)
        for i, (label_index, action) in enumerate(items):
            rect = pygame.Rect(
                grid_x + (i % columns) * (tile_w + gap_x),
                grid_y + (i // columns) * (tile_h + gap_y), tile_w, tile_h)
            label = pygame.transform.scale(
                strip.subsurface(pygame.Rect(label_index * self.LABEL_PITCH, 0,
                                             self.LABEL_WIDTH, self.LABEL_HEIGHT)),
                (tile_w, tile_h))
            tiles.append((rect, label, action))

        # Подсветка нужна только при управлении с клавиатуры: на телефоне
        # «текущей» кнопки нет, там просто попадают пальцем.
        self.n = min(self.n, len(tiles) - 1)
        keyboard = False

        # pygame.time.set_timer в WASM не реализован, поэтому выдержку в 3
        # секунды перед уходом плашки считаем кадрами.
        o, push, timer_frames, timer_flag, back, up = -100, None, 0, False, False, True
        if self.push:
            push = pygame.sprite.Sprite()
            create_sprite(push, "mat_4.png", self.size[0] // 2 - 200, o, menu_sprites)

        hint = None
        if not int(get_values(self.path_statistic, "mission")[0]) > 1:
            hint = 'Чтобы открыть все режимы, пройди "Пролог"'

        while True:
            if self.push:
                if o + 5 <= 0 and up:
                    o += 5
                else:
                    if not timer_flag:
                        timer_flag = True
                        timer_frames = self.fps * 3
                        pygame.mixer.Sound(self.sound_achievement).play()

                if timer_frames > 0:
                    timer_frames -= 1
                    if timer_frames == 0:
                        back, up = True, False

                if back and o - 5 >= -100:
                    o -= 5
                elif not up:
                    self.push = False

            if self.push:
                put_sprite(push, self.size[0] // 2 - 200, o)

            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        terminate()

                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        try:
                            if t.rect.collidepoint(event.pos):
                                pygame.mixer.Sound(self.click).play()
                                return "Titles"
                        except AttributeError:
                            pass

                        for i, (rect, _, action) in enumerate(tiles):
                            if rect.collidepoint(event.pos):
                                pygame.mixer.Sound(self.enter).play()
                                self.n = i
                                if action == "Exit":
                                    terminate()
                                return action

                    elif event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_LEFT, pygame.K_RIGHT,
                                         pygame.K_UP, pygame.K_DOWN):
                            keyboard = True
                            pygame.mixer.Sound(self.click).play()
                            self.n = max(0, min(len(tiles) - 1, self.n + {
                                pygame.K_LEFT: -1, pygame.K_RIGHT: 1,
                                pygame.K_UP: -columns, pygame.K_DOWN: columns}[event.key]))

                        elif event.key == pygame.K_RETURN:
                            pygame.mixer.Sound(self.enter).play()
                            if tiles[self.n][2] == "Exit":
                                terminate()
                            return tiles[self.n][2]

                        elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                            terminate()
            except pygame.error:
                terminate()

            self.screen.blit(fon, (0, 0))
            self.screen.blit(header, (0, 0))

            for i, (rect, label, _) in enumerate(tiles):
                self.screen.blit(plate, rect)
                self.screen.blit(label, rect)
                self.screen.blit(frame_image, rect)
                if keyboard and i == self.n:
                    pygame.draw.rect(self.screen, (255, 255, 0), rect.inflate(12, 12), 4)

            menu_sprites.draw(self.screen)

            y = 5
            for line in format_xp(self.path_statistic)[0].split("\n"):
                self.screen.blit(
                    get_font(self.font_1, 50).render(line, True, (255, 255, 255)), (20, y))
                y += 50

            caption = get_font(self.font_1, 80 if big else 60).render(
                "Sea Battle", True, (255, 255, 255))
            self.screen.blit(caption, caption.get_rect(
                center=(self.size[0] // 2, 105 if big else 75)))

            if hint:
                surface = get_font(custom_font(2), 25).render(hint, True, (255, 255, 255))
                self.screen.blit(surface, surface.get_rect(
                    center=(self.size[0] // 2, self.size[1] - 30)))

            if self.push:
                for line in [("Получены награды", 40, o + 25),
                             ('Загляните в "Достижения"', 20, o + 65)]:
                    text = get_font(self.font_2, line[1]).render(line[0], True,
                                                                         (255, 255, 255))
                    self.screen.blit(text, text.get_rect(center=(self.size[0] // 2, line[2])))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)

    def set_n(self, n):
        """Поставить элемент"""
        self.n = n

    def get_n(self):
        """Получить элемент"""
        return self.n


class Statistic:
    """Статистика"""

    click = os.path.join("data", os.path.join("sound", "click.ogg"))

    def __init__(self, screen, fps, path):
        self.path_config, self.path_achievements, self.path_statistic = os.path.join(
            path, "config.json"), os.path.join(path, "achievements.sqlite"), os.path.join(
            path, "statistic.json")
        self.screen, self.fps, self.size = screen, fps, tuple(
            map(int, (get_values(self.path_config, "screensize")[0].split("x"))))

    async def menu(self):
        """Меню статистики"""
        fon, s = add_fon(get_values(self.path_config, "theme")[0], self.size), pygame.mixer.Sound(
            self.click)

        clock = pygame.time.Clock()

        menu_sprites = pygame.sprite.Group()

        x = pygame.sprite.Sprite()
        create_sprite(x, "x.png", self.size[0] - 100, 50, menu_sprites)

        mat = pygame.sprite.Sprite()
        create_sprite(mat, f"mat_6_{self.size[1]}.png", 50, 100, menu_sprites)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and \
                        x.rect.collidepoint(event.pos):
                    s.play()
                    return

                elif event.type == pygame.KEYDOWN and (
                        event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE):
                    s.play()
                    return

            self.screen.blit(fon, (0, 0))
            menu_sprites.draw(self.screen)

            xp, t, g, v, d, il, ca, m = get_values(self.path_statistic, a=True)
            try:
                t = get_values_sqlite(self.path_achievements, "titles", f"id = {t}", "name")[0][0]
            except sqlite3.OperationalError:
                t = "отсутствует"
            text = [["Статистика", (255, 255, 255), 50, 50, 50, 1],
                    [f"Всего опыта: {xp} XP", (255, 255, 255), 100, 150, 50, 2],
                    [f"Уровень: {format_xp(self.path_statistic)[1]}/100", (255, 255, 255), 100, 200,
                     50, 2], [f"Титул: {t}", (255, 255, 255), 100, 250, 50, 2],
                    [f"Количество игр: {g}", (255, 255, 255), 100, 300, 50, 2],
                    [f"Побед: {v}", (255, 255, 255), 100, 350, 50, 2],
                    [f"Поражений: {d}", (255, 255, 255), 100, 400, 50, 2],
                    [f"Невозможных уровней выиграно: {il}", (255, 255, 255), 100, 450, 50, 2],
                    [f"Достижений выполнено: \
{ca}/{len(get_values_sqlite(self.path_achievements, 'achievements', None, 'id'))}", (255, 255, 255),
                     100, 500, 50, 2],
                    [f"Сюжет: {int(((int(m) - 1) / 8) * 100) if m not in ['8a', '8b'] else 100}%",
                     (255, 255, 255), 100, 550, 50, 2]]
            for j in text:
                self.screen.blit(
                    get_font(custom_font(j[5]), j[4]).render(
                        j[0], True, j[1]), (j[2], j[3]))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)


class Instruction:
    """Обучение"""

    instruction = os.path.join("data", os.path.join("txt", "instruction.txt"))
    click = os.path.join("data", os.path.join("sound", "click.ogg"))
    enter = os.path.join("data", os.path.join("sound", "enter.ogg"))
    font_1 = os.path.join("data", os.path.join("fonts", "font_1.ttf"))
    font_2 = os.path.join("data", os.path.join("fonts", "font_2.ttf"))

    def __init__(self, screen, fps, path):
        self.path_config = os.path.join(path, "config.json")
        self.screen, self.fps, self.size = screen, fps, tuple(
            map(int, (get_values(self.path_config, "screensize")[0].split("x"))))

    async def menu(self):
        """Меню обучения"""
        fon, s, text = pygame.transform.scale(load_image("fon_6.png"),
                                              self.size), pygame.mixer.Sound(
            self.click), [["Обучение", (255, 255, 255), 50, 50, 50, 1]]

        with open(self.instruction, encoding="utf-8") as f:
            t, y, c = f.read().split("\n"), 150, 25 if self.size[1] == 768 else 35
            for line in t:
                text.append([line, (255, 255, 255), 100, y, c, 2])
                y += c

        clock = pygame.time.Clock()

        menu_sprites = pygame.sprite.Group()

        x = pygame.sprite.Sprite()
        create_sprite(x, "x.png", self.size[0] - 100, 50, menu_sprites)

        mat = pygame.sprite.Sprite()
        create_sprite(mat, f"mat_6_{self.size[1]}.png", 50, 100, menu_sprites)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and \
                        x.rect.collidepoint(event.pos):
                    s.play()
                    return

                elif event.type == pygame.KEYDOWN and (
                        event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE):
                    s.play()
                    return

            self.screen.blit(fon, (0, 0))
            menu_sprites.draw(self.screen)

            for j in text:
                self.screen.blit(
                    get_font(custom_font(j[5]), j[4]).render(j[0], True, j[1]), (j[2], j[3]))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)
