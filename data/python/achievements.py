import asyncio
import sqlite3
import pygame
import os

from datetime import datetime, date

from .main_functions import terminate, load_image, create_sprite, set_statistic, get_values, \
    custom_font


class Achievements:
    """Достижения"""

    click = os.path.join("data", os.path.join("sound", "click.ogg"))

    def __init__(self, screen, fps, path):
        self.path_config, self.path_achievements, self.path_statistic = os.path.join(
            path, "config.json"), os.path.join(path, "achievements.sqlite"), os.path.join(
            path, "statistic.json")
        self.screen, self.fps, self.path, self.size = screen, fps, path, tuple(
            map(int, (get_values(self.path_config, "screensize")[0].split("x"))))

        with sqlite3.connect(self.path_achievements) as con:
            cur = con.cursor()

            """Эти строки сортируют сначала по описанию, потом по заголовку, id, опыту, дате,
            если имеется, сложности и наконец, по проценту выполнения"""
            s = sorted(sorted(sorted(
                sorted(cur.execute("""SELECT * FROM achievements""").fetchall(), key=lambda x: x[2]),
                key=lambda x: x[1]), key=lambda x: int(x[0])), key=lambda x: int(x[6]), reverse=True)
            try:
                s = sorted(s, key=lambda x: date(int(x[5].split(".")[2]), int(x[5].split(".")[1]),
                                                 int(x[5].split(".")[0])))
            except AttributeError:
                pass
            self.achievements = sorted(sorted(s, key=lambda x: int(x[3]), reverse=True),
                                       key=lambda x: float(x[4]), reverse=True)

    async def menu(self):
        """Меню достижений"""
        fon = pygame.transform.scale(load_image("fon_4.png"), self.size)

        clock = pygame.time.Clock()

        menu_sprites = pygame.sprite.Group()

        m1 = pygame.sprite.Sprite()
        create_sprite(m1, f"mat_2_{self.size[1]}.png", 0, 0, menu_sprites)

        m2 = pygame.sprite.Sprite()
        create_sprite(m2, f"mat_3_{self.size[1]}.png", 0,
                      self.size[1] - (100 if self.size[1] == 768 else 250), menu_sprites)

        title_page = pygame.sprite.Sprite()
        create_sprite(title_page, "title_page.png", self.size[0] - 300, self.size[1] - 100,
                      menu_sprites)

        a = 100
        progress_line = pygame.sprite.Sprite()
        create_sprite(progress_line, "progress_line.png", a, self.size[1] - 100, menu_sprites)
        a += 10

        completed = int(
            len(list(filter(lambda q: q[4] == 1, self.achievements))) / len(self.achievements) * 100)
        if completed - 4 > 0:  # Учитываем погрешность из-за закруглённых краёв
            for _ in range(completed - 4):
                progress = pygame.sprite.Sprite()
                create_sprite(progress, "progress.png", a, self.size[1] - 100, menu_sprites)
                a += 5

        x = pygame.sprite.Sprite()
        create_sprite(x, "x.png", self.size[0] - 100, 50, menu_sprites)

        a, f = 150, 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if x.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.click).play()
                            return
                        elif title_page.rect.collidepoint(event.pos):
                            pygame.mixer.Sound(self.click).play()
                            return "titles"
                    elif event.button == 4:
                        if f - 1 >= 0:
                            a, f = a + 175, f - 1
                    elif event.button == 5:
                        if f + 1 < len(self.achievements) - (2 if self.size[1] == 768 else 3):
                            a, f = a - 175, f + 1
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        if f - 1 >= 0:
                            a, f = a + 175, f - 1
                    elif event.key == pygame.K_DOWN:
                        if f + 1 < len(self.achievements) - (2 if self.size[1] == 768 else 3):
                            a, f = a - 175, f + 1
                    elif event.key == pygame.K_ESCAPE:
                        pygame.mixer.Sound(self.click).play()
                        return

            self.screen.blit(fon, (0, 0))

            achievement_sprites, y, text, text_achievements = pygame.sprite.Group(), a, [
                ["Достижения", (255, 255, 255), 50, 50, 50, 1],
                [f"{completed}%", (0, 0, 0), 625,
                 self.size[1] - 100, 25, 1]], []
            for i, achievement in enumerate(self.achievements, start=1):
                mat = pygame.sprite.Sprite()
                create_sprite(mat, f"mat_{str(achievement[4]).split('.')[0]}_{self.size[1]}.png", 50,
                              y, achievement_sprites)

                frame = pygame.sprite.Sprite()
                create_sprite(frame, f"frame_{achievement[3]}.png", 145, y + 25, achievement_sprites)

                try:
                    image = pygame.sprite.Sprite()
                    create_sprite(image, achievement[7], 150, y + 30, achievement_sprites)
                except TypeError:
                    pass

                text_achievements.extend([[str(i), (255, 255, 255), 75, y + 25, 50, 1],
                                          [achievement[1], (255, 255, 255), 400, y + 25, 50, 1],
                                          [achievement[2], (192, 192, 192), 400, y + 100, 20, 2],
                                          ["Прогресс", (192, 192, 192),
                                           1000 if self.size[1] == 768 else 1100,
                                           y + 10, 25, 2],
                                          [f"{int(achievement[4] * 100)}%", (255, 255, 255),
                                           1000 if self.size[1] == 768 else 1100, y + 45, 40, 1],
                                          ["Награда", (192, 192, 192),
                                           1150 if self.size[1] == 768 else 1500,
                                           y + 10, 25, 2], [f"{achievement[6]} XP", (255, 255, 255),
                                                            1150 if self.size[1] == 768 else 1500,
                                                            y + 45, 40, 1],
                                          [achievement[5], (255, 255, 255),
                                           1000 if self.size[1] == 768 else 1100,
                                           y + 100, 25, 2]])
                if achievement[8] is not None:
                    with sqlite3.connect(self.path_achievements) as con:
                        cur = con.cursor()
                        text_achievements.append([cur.execute(f"""SELECT name FROM titles
WHERE id = {achievement[8]}""").fetchone()[0], (255, 255, 0),
                                                  1150 if self.size[1] == 768 else 1500, y + 100, 25,
                                                  1])
                y += 175

            achievement_sprites.draw(self.screen)

            for j in text_achievements:
                self.screen.blit(
                    pygame.font.Font(custom_font(j[5]), j[4]).render(
                        j[0], True, j[1]), (j[2], j[3]))

            menu_sprites.draw(self.screen)

            for j in text:
                self.screen.blit(
                    pygame.font.Font(custom_font(j[5]), j[4]).render(
                        j[0], True, j[1]), (j[2], j[3]))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)

    def set_progress(self, number, i, add=False):
        """Установить прогресс"""
        with sqlite3.connect(self.path_achievements) as con:
            cur = con.cursor()
            if float(cur.execute(f"""SELECT progress FROM achievements
WHERE id = {i}""").fetchone()[0]) != 1:
                if add:
                    pre_result = float(cur.execute(f"""SELECT progress FROM achievements
    WHERE id = {i}""").fetchone()[0]) + number
                    result = pre_result if pre_result < 1 else 1
                else:
                    result = number if number < 1 else 1
                cur.execute(f"""UPDATE achievements
SET progress = {result}
WHERE id = {i}""")
                con.commit()
                if float(cur.execute(f"""SELECT progress FROM achievements
WHERE id = {i}""").fetchone()[0]) == 1:
                    cur.execute(f"""UPDATE achievements
SET date_of_completion = '{datetime.now().date().strftime("%d.%m.%Y")}'
WHERE id = {i}""")
                    con.commit()
                    xp, title = cur.execute(f"""SELECT experience, title FROM achievements
WHERE id = {i}""").fetchone()
                    set_statistic(self.path_statistic, xp)
                    if title is not None:
                        self.set_title(title)
                    return True

    def set_title(self, i):
        """Открыть доступ к титулу"""
        with sqlite3.connect(self.path_achievements) as con:
            cur = con.cursor()
            cur.execute(f"""UPDATE titles
SET completed = 1
WHERE id = {i}""")
            con.commit()


class Titles:
    """Титульная"""

    click = os.path.join("data", os.path.join("sound", "click.ogg"))

    def __init__(self, screen, fps, path):
        self.path_config, self.path_achievements, self.path_statistic = os.path.join(
            path, "config.json"), os.path.join(path, "achievements.sqlite"), os.path.join(
            path, "statistic.json")
        self.screen, self.fps, self.path, self.size = screen, fps, path, tuple(
            map(int, (get_values(self.path_config, "screensize")[0].split("x"))))

        with sqlite3.connect(self.path_achievements) as con:
            cur = con.cursor()

            # Сортируем сначала по описанию, потом по заголовку, id, и по выполнению
            self.titles = sorted(sorted(sorted(sorted(cur.execute(
                """SELECT * FROM titles""").fetchall(), key=lambda x: x[2]),
                                               key=lambda x: x[1]), key=lambda x: int(x[0])),
                                 key=lambda x: int(x[3]), reverse=True)

    async def menu(self):
        """Меню титулов"""
        fon, s = pygame.transform.scale(load_image("fon_5.png"), self.size), pygame.mixer.Sound(
            self.click)

        clock = pygame.time.Clock()

        menu_sprites = pygame.sprite.Group()

        mat = pygame.sprite.Sprite()
        create_sprite(mat, f"mat_6_{self.size[1]}.png", 50, 100, menu_sprites)

        x = pygame.sprite.Sprite()
        create_sprite(x, "x.png", self.size[0] - 100, 50, menu_sprites)

        title_sprites, a, b, text, p, n = pygame.sprite.Group(), 100, 150, [
            ["Титульная", (255, 255, 255), 50, 50, 50, 1]], {}, {}  # p и n — словари кнопок
        for title in self.titles:
            square = pygame.sprite.Sprite()
            create_sprite(square, f"square_{title[3]}.png", a, b, title_sprites)

            image = pygame.sprite.Sprite()
            create_sprite(image, title[4], a + 25, b + 25, title_sprites)

            if title[3] == 1:
                if get_values(self.path_statistic, "title")[0] != str(title[0]):
                    apply = pygame.sprite.Sprite()
                    create_sprite(apply, "apply_white.png", a + 125, b + 150, title_sprites)
                    # добавляем в список кнопку и id титула, к которому она принадлежит
                    p[apply] = title[0]
                else:
                    remove = pygame.sprite.Sprite()
                    create_sprite(remove, "remove.png", a + 125, b + 150, title_sprites)
                    n[remove] = title[0]

            text.extend([[title[1], (255, 255, 255), a + 150, b + 25, 50, 1],
                         [title[2], (192, 192, 192), a + 150, b + 100, 15, 2]])

            if a == 100:
                a = self.size[0] - 600
            else:
                a, b = 100, self.size[1] - 325
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if x.rect.collidepoint(event.pos):
                            s.play()
                            return
                        for button in p.keys():
                            if button.rect.collidepoint(event.pos):
                                s.play()
                                set_statistic(self.path_statistic, p[button], key="title",
                                              add=False)
                                return "replay"
                        for button in n.keys():
                            if button.rect.collidepoint(event.pos):
                                s.play()
                                set_statistic(self.path_statistic, "not", key="title", add=False)
                                return "replay"
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    s.play()
                    return

            self.screen.blit(fon, (0, 0))

            menu_sprites.draw(self.screen)
            title_sprites.draw(self.screen)

            for j in text:
                self.screen.blit(
                    pygame.font.Font(custom_font(j[5]), j[4]).render(j[0], True, j[1]), (j[2], j[3]))

            pygame.display.flip()
            clock.tick(self.fps)
            await asyncio.sleep(0)
