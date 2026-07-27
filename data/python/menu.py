import asyncio
import os
import sqlite3

import pygame

from .main_functions import terminate, create_sprite, put_sprite, format_xp, get_values, \
    get_values_sqlite, add_fon, load_image, extract_files, custom_font

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

        title = pygame.font.Font(self.font_1, 90).render("Sea Battle", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.size[0] // 2, self.size[1] // 2 + 120))

        hint = pygame.font.Font(self.font_2, 25).render(
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

    async def menu(self):
        """Меню"""
        if int(get_values(self.path_statistic, "mission")[0]) > 1:
            bot, farm = "Play_With_Bot", "Farm"
        else:
            bot, farm = None, None
        buttons_tuple = ("Play", bot, farm, "Settings", "Achievements", "Statistic", "Instruction")
        fon = add_fon(get_values(self.path_config, "theme")[0], self.size)

        clock = pygame.time.Clock()

        menu_sprites = pygame.sprite.Group()

        x = 300 * self.n

        buttons = pygame.sprite.Sprite()
        create_sprite(buttons, "buttons.png", self.size[0] / 2 - 125 - x,
                      self.size[1] - (200 if self.size[1] == 768 else 300), menu_sprites)

        mat = pygame.sprite.Sprite()
        create_sprite(mat, f"mat_{self.size[1]}.png", 0,
                      self.size[1] - (200 if self.size[1] == 768 else 300), menu_sprites)

        frame = pygame.sprite.Sprite()
        create_sprite(frame, "frame_6.png", self.size[0] / 2 - 125,
                      self.size[1] - (200 if self.size[1] == 768 else 300), menu_sprites)

        c = (250 if self.size[1] == 768 else 350)
        down_arrow = pygame.sprite.Sprite()
        create_sprite(down_arrow, "down_arrow.png", self.size[0] / 2 - 25,
                      self.size[1] - (250 if self.size[1] == 768 else 350), menu_sprites)

        title, t = get_values(self.path_statistic, "title")[0], pygame.sprite.Sprite()
        if title != "not":
            create_sprite(t, get_values_sqlite(self.path_achievements, "titles", f"id = {title}",
                                               "image")[0][0], self.size[0] - 100,
                          self.size[1] - 100, menu_sprites)

        # pygame.time.set_timer в WASM не реализован, поэтому выдержку в 3
        # секунды перед уходом плашки считаем кадрами.
        o, push, timer_frames, timer_flag, back, up = -100, None, 0, False, False, True
        if self.push:
            push = pygame.sprite.Sprite()
            create_sprite(push, "mat_4.png", self.size[0] // 2 - 200, o, menu_sprites)

        left, right, down, text_menu = False, False, True, [
            ["Sea Battle", (255, 255, 255), 50, 200 if self.size[1] == 768 else 300, 50, 1]]

        if not int(get_values(self.path_statistic, "mission")[0]) > 1:
            text_menu.append(
                ['Чтобы открыть все режимы, пройди "Пролог"', (255, 255, 255), 0, self.size[1] - 25,
                 25, 2])
        while True:
            if right:
                if x < (300 * self.n) - 1:
                    x += 150

                else:
                    x += 1  # корректировка
                    right = False

            if left:
                if x > (300 * self.n) + 1:
                    x -= 150

                else:
                    x -= 1
                    left = False

            if down:
                c -= 2
                if c <= (230 if self.size[1] == 768 else 330):
                    down = False

            else:
                c += 2
                if c >= (250 if self.size[1] == 768 else 350):
                    down = True
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

            put_sprite(buttons, self.size[0] / 2 - 125 - x,
                       self.size[1] - (200 if self.size[1] == 768 else 300))

            put_sprite(down_arrow, self.size[0] / 2 - 25, self.size[1] - c)

            if self.push:
                put_sprite(push, self.size[0] // 2 - 200, o)

            arrow_sprites = pygame.sprite.Group()

            left_arrow = pygame.sprite.Sprite()
            if self.n - 1 >= 0:
                create_sprite(left_arrow, "left_arrow.png", self.size[0] / 2 - 175,
                              self.size[1] - (200 if self.size[1] == 768 else 300), arrow_sprites)
            else:
                left_arrow.kill()

            right_arrow = pygame.sprite.Sprite()
            if self.n + 1 <= len(buttons_tuple):
                create_sprite(right_arrow, "right_arrow.png", self.size[0] / 2 + 125,
                              self.size[1] - (200 if self.size[1] == 768 else 300), arrow_sprites)
            else:
                right_arrow.kill()

            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        terminate()

                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            s = pygame.mixer.Sound(self.click)

                            try:
                                if left_arrow.rect.collidepoint(event.pos):
                                    s.play()
                                    x = 300 * self.n + 1
                                    left = True
                                    self.n -= 1
                            except AttributeError:
                                pass

                            try:
                                if right_arrow.rect.collidepoint(event.pos):
                                    s.play()
                                    x = 300 * self.n - 1
                                    right = True
                                    self.n += 1
                            except AttributeError:
                                pass

                            try:
                                if t.rect.collidepoint(event.pos):
                                    s.play()
                                    return "Titles"
                            except AttributeError:
                                pass

                            if frame.rect.collidepoint(event.pos):
                                pygame.mixer.Sound(self.enter).play()
                                if self.n == len(buttons_tuple):
                                    terminate()
                                return buttons_tuple[self.n]

                        elif event.button == 4 and self.n - 1 >= 0:
                            x = 300 * self.n + 1
                            left = True
                            self.n -= 1

                        elif event.button == 5 and self.n + 1 <= len(buttons_tuple):
                            x = 300 * self.n - 1
                            right = True
                            self.n += 1

                    elif event.type == pygame.KEYDOWN:
                        s = pygame.mixer.Sound(self.click)
                        if event.key == pygame.K_LEFT and self.n - 1 >= 0:
                            s.play()
                            x = 300 * self.n + 1
                            left = True
                            self.n -= 1

                        elif event.key == pygame.K_RIGHT and self.n + 1 <= len(buttons_tuple):
                            s.play()
                            x = 300 * self.n - 1
                            right = True
                            self.n += 1

                        elif event.key == pygame.K_RETURN:
                            pygame.mixer.Sound(self.enter).play()
                            if self.n == len(buttons_tuple):
                                terminate()
                            return buttons_tuple[self.n]

                        elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                            terminate()
            except pygame.error:
                terminate()

            self.screen.blit(fon, (0, 0))
            menu_sprites.draw(self.screen)
            arrow_sprites.draw(self.screen)
            text = format_xp(self.path_statistic)[0].split("\n")
            y = 0
            for line in text:
                self.screen.blit(
                    pygame.font.Font(self.font_1, 50).render(line, True, (255, 255, 255)), (0, y))
                y += 50
            for j in text_menu:
                self.screen.blit(
                    pygame.font.Font(custom_font(j[5]), j[4]).render(j[0], True, j[1]), (j[2], j[3]))

            # text = pygame.font.Font(self.font_1, 50).render(self.nickname, True, (255, 255, 255))
            # text_rect = text.get_rect()
            # self.screen.blit(text, (self.size[0] - tuple(text_rect)[2], 0))

            if self.push:
                for line in [("Получены награды", 40, o + 25),
                             ('Загляните в "Достижения"', 20, o + 65)]:
                    text = pygame.font.Font(self.font_2, line[1]).render(line[0], True,
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
                    pygame.font.Font(custom_font(j[5]), j[4]).render(
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
                    pygame.font.Font(custom_font(j[5]), j[4]).render(j[0], True, j[1]), (j[2], j[3]))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)
