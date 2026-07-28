import asyncio

from .main_functions import terminate, load_image, create_sprite, get_values, extract_files, \
    add_fon, set_values, custom_font, get_font, screen_size, stretch_to
from .platform_compat import persist, reload_page, IS_WEB

import pygame
import os

try:  # в браузере модуля может не быть, ссылки тогда просто не открываются
    import webbrowser
except ImportError:
    webbrowser = None


class Settings:
    """Настройки"""
    values_screensize = ["1366x768", "1920x1080"]
    values_screenmode = ["window", "noframe", "fullscreen"]
    values_fps = [30, 60, 90, 120]
    values_difficulty = ["easiest", "easy", "normal", "hard", "impossible"]
    values_theme = ["day", "night", "by_time_of_day"]
    click = os.path.join("data", os.path.join("sound", "click.ogg"))
    enter = os.path.join("data", os.path.join("sound", "enter.ogg"))
    package = os.path.join("data", os.path.join("packages", "files.zip"))

    def __init__(self, screen, fps, path):
        self.path_config = os.path.join(path, "config.json")
        self.path_statistic = os.path.join(path, "statistic.json")
        self.path_achievements = os.path.join(path, "achievements.sqlite")
        self.screen, self.fps, self.path, self.size = screen, fps, path, screen_size()
        self.value_screensize = self.values_screensize.index(
            get_values(self.path_config, "screensize")[0])
        self.value_screenmode = self.values_screenmode.index(
            get_values(self.path_config, "screenmode")[0])
        self.value_fps = self.values_fps.index(
            get_values(self.path_config, "fps")[0])
        self.value_difficulty = self.values_difficulty.index(
            get_values(self.path_config, "difficulty")[0])
        self.value_theme = self.values_theme.index(
            get_values(self.path_config, "theme")[0])
        self.update = pygame.USEREVENT + 1, 1

    def _cycle(self, controls, pos):
        """Переключить настройку, если попали по её строке.

        Стрелки листают назад и вперёд, нажатие по самому значению — вперёд:
        так на телефоне не нужно целиться в стрелку.
        """
        for back, forward, value_area, _, field, values, _ in controls:
            if back.collidepoint(pos):
                step = -1
            elif forward.collidepoint(pos) or value_area.collidepoint(pos):
                step = 1
            else:
                continue

            setattr(self, field, (getattr(self, field) + step) % len(values))
            return True

        return False

    def restart(self):
        """Завершить игру после сброса из опасной зоны"""
        # Без этого в браузере сброс бесполезен: файлы перезаписаны только в
        # памяти, а при следующем запуске restore() вернёт из localStorage
        # ровно те сохранения, которые мы только что стёрли.
        persist(self.path)

        reload_page()  # в браузере игру заново не запустишь — перезагружаем сами
        terminate()

    def apply(self):
        """Действие "Применить\""""
        values = {
            "screensize": self.values_screensize[self.value_screensize],
            "screenmode": self.values_screenmode[self.value_screenmode],
            "fps": int(self.values_fps[self.value_fps]),
            "difficulty": self.values_difficulty[self.value_difficulty],
            "theme": self.values_theme[self.value_theme]
        }
        set_values(self.path_config, values)

        return "apply"

    def download(self):
        pass
        # login_request = \
        #     f"https://seabattle.aft-services.ru/{self.email}/{self.password}/api/get_data"
        # try:
        #     statistic = json.loads(requests.get(login_request).json()["user"]["statistic"])
        # except Exception:
        #     return -1
        # s, a = statistic["statistic"], statistic["achievements"]
        #
        # stat = {}
        # for i in s.keys():
        #     stat[i] = s[i]
        # set_values(self.path_statistic, stat)
        #
        # with sqlite3.connect(self.path_achievements) as con:
        #     cur = con.cursor()
        #     for i in a.keys():
        #         u = "UPDATE achievements"
        #         if a[i]['progress'] is not None:
        #             u += f"\nSET progress = {a[i]['progress']}"
        #         else:
        #             u += f"\nSET progress = 0"
        #
        #         if a[i]['date_of_completion'] is not None:
        #             u += f', date_of_completion = "{a[i]["date_of_completion"]}"'
        #         else:
        #             u += f', date_of_completion = NULL'
        #         u += f"\nWHERE id = {i}"
        #         cur.execute(u)
        #     con.commit()

    def load(self):
        pass
        # with open(self.path_statistic) as stat:
        #     s = json.load(stat)
        # achievements_list = get_values_sqlite(self.path_achievements, "achievements", None, "id",
        #                                       "progress", "date_of_completion")
        # achievements_dict = {}
        # for achievement in achievements_list:
        #     achievements_dict[achievement[0]] = {
        #         "progress": achievement[1],
        #         "date_of_completion": achievement[2]
        #     }
        #
        # statistic = json.dumps({
        #     "statistic": s,
        #     "achievements": achievements_dict
        # }, ensure_ascii=False)
        #
        # statistic_response = {
        #     "email": self.email,
        #     "password": self.password,
        #     "statistic": statistic
        # }
        #
        # statistic_request = "https://seabattle.aft-services.ru/api/edit_statistic"
        # try:
        #     requests.post(statistic_request, json=statistic_response)
        # except Exception:
        #     return -1

    async def menu(self):
        """Меню настроек"""
        clock = pygame.time.Clock()
        fon = pygame.transform.scale(load_image("fon_3.png"), self.size)

        settings_sprites = pygame.sprite.Group()

        x = pygame.sprite.Sprite()
        create_sprite(x, "x.png", self.size[0] - 100, 50, settings_sprites)

        mat = pygame.sprite.Sprite()
        create_sprite(mat, f"mat_6_{self.size[1]}.png", 50, 100, settings_sprites,
                      stretch_to(f"mat_6_{self.size[1]}.png", self.size[0] - 100))

        apply = pygame.sprite.Sprite()
        create_sprite(apply, "apply.png", self.size[0] - 350, self.size[1] - 150, settings_sprites)

        # Строки настроек описаны таблицей: раньше на каждую приходилось по две
        # почти одинаковых ветки обработки, а зоны нажатия были размером со
        # стрелку 50x50 — на телефоне это меньше сантиметра.
        rows = [
            ("Сложность: ", "value_difficulty", self.values_difficulty),
            ("Тема: ", "value_theme", self.values_theme),
        ]

        if not IS_WEB:
            # В браузере холст подстраивается под экран сам, а режим окна и
            # полноэкранный режим задаёт страница — менять тут нечего.
            rows = [
                ("Размер экрана: ", "value_screensize", self.values_screensize),
                ("Режим экрана: ", "value_screenmode", self.values_screenmode),
                ("FPS: ", "value_fps", self.values_fps),
            ] + rows

        # Освободившееся место отдаём строкам: на телефоне в них надо попадать
        # пальцем, а раньше шаг был впритык из-за пяти пунктов.
        row_step = 50 if len(rows) > 3 else 70
        row_top = 220 if len(rows) > 3 else 250

        left_x, right_x = int(self.size[0] * 0.33), int(self.size[0] * 0.66)

        controls = []  # (зона "назад", зона "вперёд", зона значения, подпись, поле, значения, y)
        for i, (caption, field, values) in enumerate(rows):
            y = row_top + i * row_step

            left = pygame.sprite.Sprite()
            create_sprite(left, "left_arrow.png", left_x, y, settings_sprites)
            right = pygame.sprite.Sprite()
            create_sprite(right, "right_arrow.png", right_x, y, settings_sprites)

            controls.append((left.rect.inflate(60, 0), right.rect.inflate(60, 0),
                             pygame.Rect(left_x + 60, y, right_x - left_x - 60, 50),
                             caption, field, values, y))

        # download = pygame.sprite.Sprite()
        # create_sprite(download, "download.png", self.size[0] - 350, 150, settings_sprites)

        # load = pygame.sprite.Sprite()
        # create_sprite(load, "load.png", self.size[0] - 220, 150, settings_sprites)

        developers = pygame.sprite.Sprite()
        create_sprite(developers, "developers.png", self.size[0] - 350, self.size[1] - 250,
                      settings_sprites)

        # Рамка опасной зоны — картинка фиксированной ширины 800, центруем её
        # вместе с кнопками, иначе на широком экране она липнет к левому краю.
        zone_x = (self.size[0] - 800) // 2

        danger_zone = pygame.sprite.Sprite()
        create_sprite(danger_zone, "danger_zone.png", zone_x, self.size[1] - 300,
                      settings_sprites)

        recovery_settings = pygame.sprite.Sprite()
        create_sprite(recovery_settings, "recovery_settings.png", zone_x + 125,
                      self.size[1] - 175, settings_sprites)

        new_game = pygame.sprite.Sprite()
        create_sprite(new_game, "new_game.png", zone_x + 425, self.size[1] - 175,
                      settings_sprites)

        # какая кнопка опасной зоны ждёт второго касания и сколько кадров ещё ждёт
        armed, armed_frames = None, 0

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # Любое касание снимает взвод опасной зоны; ниже он
                        # выставится заново, если попали в ту же кнопку.
                        was_armed, armed, armed_frames = armed, None, 0

                        if x.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.click).play()
                            return

                        elif self._cycle(controls, event.pos):
                            pygame.mixer.Sound(self.click).play()

                        # elif download.rect.collidepoint(event.pos):
                        #     pygame.mixer.Sound(self.enter).play()
                        #     self.download()
                        #
                        # elif load.rect.collidepoint(event.pos):
                        #     pygame.mixer.Sound(self.enter).play()
                        #     self.load()

                        elif developers.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            return "developers"

                        elif apply.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            return self.apply()

                        # Опасная зона срабатывала только по правой кнопке
                        # мыши, которой на телефоне нет. Двойное касание —
                        # такая же преграда от случайного нажатия.
                        elif recovery_settings.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.click).play()
                            if was_armed == "recovery":
                                extract_files(self.package, self.path, "config.json")
                                self.restart()
                            armed, armed_frames = "recovery", self.fps

                        elif new_game.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.click).play()
                            if was_armed == "new_game":
                                extract_files(self.package, self.path,
                                              "statistic.json", "achievements.sqlite")
                                self.restart()
                            armed, armed_frames = "new_game", self.fps

                    elif event.button == 3:
                        result, values = False, None
                        if recovery_settings.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            result, values = True, ["config.json"]

                        elif new_game.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            result, values = True, ["statistic.json", "achievements.sqlite"]

                        if result:
                            extract_files(self.package, self.path, *values)
                            self.restart()

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.mixer.Sound(self.click).play()
                        return

                    elif event.key == pygame.K_RETURN:
                        pygame.mixer.Sound(self.enter).play()
                        return self.apply()

            if armed_frames > 0:
                armed_frames -= 1
                if armed_frames == 0:
                    armed = None  # передумали — второе касание не засчитываем

            self.screen.blit(fon, (0, 0))

            settings_sprites.draw(self.screen)

            # Подсказка на месте стёртой из danger_zone.png строки про ПКМ
            if armed:
                hint, hint_color = "Коснитесь ещё раз, чтобы подтвердить", (255, 255, 0)
            else:
                hint, hint_color = ("Коснитесь кнопки дважды или нажмите ПКМ",
                                    (255, 80, 80))

            for line, color, offset in (
                    ("Действие необратимо, игра перезапустится", (255, 80, 80), 55),
                    (hint, hint_color, 80)):
                surface = get_font(custom_font(2), 17).render(line, True, color)
                self.screen.blit(surface, surface.get_rect(
                    center=(zone_x + 400, self.size[1] - 300 + offset)))

            for i in [["Настройки", (255, 255, 255), 50, 50, 50, 1],
                      [f"Версия конфигурационного файла: \
{get_values(self.path_config, 'version')[0]}",
                       (128, 128, 128), 100, 150, 25, 2]]:
                self.screen.blit(
                    get_font(custom_font(i[5]), i[4]).render(i[0], True, i[1]), (i[2], i[3]))

            for _, _, value_area, caption, field, values, y in controls:
                self.screen.blit(
                    get_font(custom_font(1), 50).render(caption, True, (255, 255, 255)), (100, y))

                value = get_font(custom_font(2), 50).render(
                    str(values[getattr(self, field)]), True, (255, 255, 255))
                self.screen.blit(value, value.get_rect(center=value_area.center))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)


class About:
    """Титры"""

    titles = os.path.join("data", os.path.join("txt", "titles.txt"))
    click = os.path.join("data", os.path.join("sound", "click.ogg"))
    enter = os.path.join("data", os.path.join("sound", "enter.ogg"))
    font_1 = os.path.join("data", os.path.join("fonts", "font_1.ttf"))
    font_2 = os.path.join("data", os.path.join("fonts", "font_2.ttf"))

    def __init__(self, screen, fps, path_config):
        self.screen, self.fps, self.size, self.update, self.path_config = screen, fps, screen_size(), pygame.USEREVENT + 1, path_config

    async def menu(self):
        """Меню с информацией"""
        fon = add_fon(get_values(self.path_config, "theme")[0], self.size)

        clock = pygame.time.Clock()

        about_sprites = pygame.sprite.Group()

        x = pygame.sprite.Sprite()
        create_sprite(x, "x.png", self.size[0] - 100, 50, about_sprites)

        with open(self.titles, encoding="utf-8") as titles:
            titles = titles.read().split("\n")

        mat = pygame.sprite.Sprite()
        create_sprite(mat, f"mat_6_{self.size[1]}.png", 50, 100, about_sprites,
                      stretch_to(f"mat_6_{self.size[1]}.png", self.size[0] - 100))

        discord = pygame.sprite.Sprite()
        create_sprite(discord, "discord.png", 300, 150, about_sprites)

        vk = pygame.sprite.Sprite()
        create_sprite(vk, "vk.png", 375, 150, about_sprites)

        youtube = pygame.sprite.Sprite()
        create_sprite(youtube, "youtube.png", 450, 150, about_sprites)

        pygame_sprite = pygame.sprite.Sprite()
        create_sprite(pygame_sprite, "pygame.png", self.size[0] - 200, self.size[1] - 100,
                      about_sprites)

        yandex = pygame.sprite.Sprite()
        create_sprite(yandex, "yandex.png", self.size[0] - 450, self.size[1] - 100, about_sprites)

        thank = pygame.sprite.Sprite()
        create_sprite(thank, "thank.png", 100, 250, about_sprites)

        # set_timer в WASM не работает, поэтому кадр анимации логотипа
        # переключаем по счётчику кадров: 200 мс — это fps / 5 кадров.
        n, animation_frames, animation_period = 1, 0, max(1, self.fps // 5)

        aft_games = pygame.sprite.Sprite()
        create_sprite(aft_games, os.path.join("animate", f"animate_{n}.png"), 100, 150,
                      about_sprites)
        while True:
            if n < 5:
                animation_frames += 1
                if animation_frames >= animation_period:
                    animation_frames = 0
                    n += 1
                    aft_games.image = load_image(os.path.join("animate", f"animate_{n}.png"))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if x.rect.collidepoint(event.pos):
                        pygame.mixer.Sound(self.click).play()
                        return

                    else:
                        link = None
                        if discord.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            link = "https://discord.gg/6BaXEbkJkw"

                        elif vk.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            link = "https://vk.com/c_aft"

                        elif youtube.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            link = "https://www.youtube.com/@aftbinko"

                        elif yandex.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            link = "https://yandex.ru"

                        elif pygame_sprite.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            link = "https://www.pygame.org"

                        elif thank.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.enter).play()
                            link = "https://www.donationalerts.com/r/binko"

                        if link is not None and webbrowser is not None:
                            try:
                                webbrowser.open(link, new=0)
                            except Exception:
                                pass

                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            self.screen.blit(fon, (0, 0))

            about_sprites.draw(self.screen)

            c, y = 15 if self.size[1] == 768 else 25, 250
            for line in titles:
                count = 1
                for symbol in line:
                    if symbol == "#":
                        count += 1
                    else:
                        break
                text = get_font(self.font_2, c * count).render(
                    line.lstrip("#" * (count - 1) + " "), True, (255, 255, 255))
                self.screen.blit(text, text.get_rect(center=(self.size[0] // 2, y)))
                y += c

            self.screen.blit(
                get_font(self.font_1, 50).render(
                    "Разработчики", True, (255, 255, 255)), (50, 50))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)
