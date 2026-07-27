import asyncio

import pygame as pg
# В wasm-сборке pygame подмодули не привязаны к пакету автоматически, а этот
# модуль создаёт спрайт-группы прямо при импорте — импортируем их явно.
import pygame.sprite
import pygame.transform
import os

from .main_functions import create_sprite, get_values, terminate

#: На сколько пикселей можно увести палец, чтобы касание всё ещё считалось
#: нажатием, а не перетаскиванием.
TAP_SLOP = 12

display_width = 0
display_height = 0

all_sprites_cell = pg.sprite.Group()
all_sprites = pg.sprite.Group()

pos_all = []

if_yes_rect_map = []  # позиция корабля на поле

list_pos_if_yes = []  # позиции которые попадают в клетки

if_downloads = False  # можно ли ставить корабль на данную позицию

test_007 = 0  # тест все ли корабли установлены

board = [[0] * 10 for _ in range(10)]  # игровое поле


def up_per():
    global if_downloads, if_yes_rect_map, list_pos_if_yes, board, test_007, pos_all
    if_yes_rect_map = []  # позиция корабля на поле

    list_pos_if_yes = []  # позиции которые попадают в клетки

    if_downloads = False  # можно ли ставить корабль на данную позицыю

    pos_all = []

    test_007 = 0

    for i in all_sprites:
        i.kill()

    for i in all_sprites_cell:
        i.kill()

    board = [[0] * 10 for _ in range(10)]  # игровое поле


def test_board(list_009, hh=0):
    opa = []
    if len(list_009) == 0:
        return

    for tt in list_009:
        i = tt[1]
        g = tt[0]

        if i == 0 and g == 0:
            spi = list(map(lambda x: x[g:g + 2], board[i:i + 2]))
        elif g == 0:
            spi = list(map(lambda x: x[g:g + 2], board[i - 1:i + 2]))
        elif i == 0:
            spi = list(map(lambda x: x[g - 1:g + 2], board[i:i + 2]))
        else:
            spi = list(map(lambda x: x[g - 1:g + 2], board[i - 1:i + 2]))

        for h in spi:
            opa.extend(h)

    if 1 not in opa and hh == 1:
        return True

    return False


def downloads_tic_tac(list_008):
    for i in list_008:
        board[i[1]][i[0]] = 1


def flip_image(image):
    return pg.transform.rotate(image, 90)


class Cell(pg.sprite.Sprite):
    def __init__(self, rect, size, x, y, theme, *op):
        super().__init__(*op)
        self.pos = rect
        self.t = theme
        self.image = pg.Surface((size - 1, size - 1))
        self.image.fill(theme)
        self.rect = self.image.get_rect()
        self.rect.x = x + 1
        self.rect.y = y + 1

    def update(self, event, list_007=(), hh=0):
        if hh == 1:
            global if_downloads, if_yes_rect_map, list_pos_if_yes
            n = 0
            for i in list_007:
                if self.rect.collidepoint(i):
                    list_pos_if_yes.append(self.pos)
                    if n == 0:
                        if_yes_rect_map = (self.rect.x + 5, self.rect.y + 5)

                n += 1
                if n == len(list_007):
                    break

            if len(list_pos_if_yes) == len(list_007) and test_board(list_pos_if_yes, hh):
                if_downloads = True
                pos_all.append(list_pos_if_yes.copy())
                downloads_tic_tac(list_pos_if_yes)
                del list_pos_if_yes[:]

        self.image.fill(self.t)

        try:
            for i in list_007:
                if self.rect.collidepoint(i):
                    self.image.fill((255, 0, 0))

        except AttributeError:
            pass


class Ship(pg.sprite.Sprite):
    def __init__(self, size, n, x, y, *op):
        super().__init__(*op)
        self.n = n
        self.size = size
        self.image = pg.Surface((size * n + ((n * 10) - 10), size))
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

        self.old_x = x
        self.old_y = y

        self.hover_x = 0
        self.hover_y = 0

        self.hover = False
        self.flip = False

        # состояние касания: где нажали и как корабль был повёрнут в тот момент
        self.press_pos = None
        self.flip_at_press = False

        self.installed_map = False

    def rotate(self):
        """Повернуть корабль на 90°"""
        self.image = flip_image(self.image)
        x_00 = self.rect.x
        y_00 = self.rect.y
        self.rect = self.image.get_rect()
        self.rect.x = x_00
        self.rect.y = y_00
        self.flip = not self.flip

    def update(self, screen, event):
        if self.installed_map:
            pass
        else:
            if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
                self.hover = True
                self.hover_x = self.rect.x - event.pos[0]
                self.hover_y = self.rect.y - event.pos[1]
                self.press_pos = event.pos
                self.flip_at_press = self.flip

            if event.type == pg.MOUSEBUTTONUP and self.hover:
                all_sprites_cell.update(0, self.return_pos(), 1)
                del list_pos_if_yes[:]

                global if_downloads, test_007
                if if_downloads:
                    if_downloads = False
                    test_007 += 1

                    self.installed_map = True
                    self.rect.x = if_yes_rect_map[0]
                    self.rect.y = if_yes_rect_map[1]

                else:
                    # Касание без перетаскивания — это поворот. На телефоне
                    # клавиши "пробел" нет, поэтому иначе корабль не развернуть.
                    if self.press_pos is not None and abs(
                            event.pos[0] - self.press_pos[0]) <= TAP_SLOP and abs(
                            event.pos[1] - self.press_pos[1]) <= TAP_SLOP:
                        target_flip = not self.flip_at_press
                    else:
                        target_flip = self.flip_at_press

                    if self.flip != target_flip:
                        self.rotate()

                    self.rect.x = self.old_x
                    self.rect.y = self.old_y

                self.hover = False
                self.press_pos = None

            if self.hover and event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                self.rotate()

            try:
                if self.hover:
                    all_sprites_cell.update(0, self.return_pos())
                    self.rect.x = self.hover_x + event.pos[0]
                    self.rect.y = self.hover_y + event.pos[1]

            except AttributeError:
                pass

    def return_pos(self):
        if self.hover:
            list_008 = []
            for i in range(self.n):
                if self.flip:
                    list_008.append(
                        (
                            int(self.rect.x + self.size * 0.5),
                            int(self.rect.y + self.size * 0.5 + self.size * i + i * 10)
                        )
                    )
                else:
                    list_008.append((int(self.rect.x + self.size * 0.5 + self.size * i + i * 10),
                                     int(self.rect.y + self.size * 0.5)))
            return list_008


class Customization:
    click = os.path.join("data", os.path.join("sound", "click.ogg"))
    enter = os.path.join("data", os.path.join("sound", "enter.ogg"))
    font_2 = os.path.join("data", os.path.join("fonts", "font_2.ttf"))

    def __init__(self, screen, fps, path, theme):
        global display_width, display_height

        self.sc = screen
        self.fps = fps
        self.path = path

        if theme:
            self.t = (255, 255, 255), (0, 0, 0)
        else:
            self.t = (0, 0, 0), (255, 255, 255)

        self.all_sprite_gg = pg.sprite.Group()

        sur = pg.display.get_surface()
        display_width = sur.get_width()
        display_height = sur.get_height()
        for i in all_sprites:
            i.kill()
        up_per()
        self.clock = pg.time.Clock()
        self.size = int(display_width * 0.035)
        self.screensize = tuple(
            map(int, (get_values(os.path.join(path, "config.json"), "screensize")[0].split("x"))))
        self.co = int(display_width * 0.02)
        self.font = pg.font.Font(self.font_2, int(self.size * 0.8))

        self.map_indent_top = 50
        self.map_indent_left = 50

        self.x_ship = int(display_width * 0.6)
        self.y_ship = int(display_height * 0.25)

        self.add_cells()
        self.add_ship()

    def map_draw(self, x, y):

        slo = list("АБВГДЕЖЗИК")

        for i in range(10):
            text = self.font.render(str(i), True, self.t[1])
            self.sc.blit(text, (i * self.size + x + 15 + self.co, 3 + y))

        for i, pp in enumerate(slo):
            text = self.font.render(pp, True, self.t[1])
            self.sc.blit(text, (x, i * self.size + y + 10 + self.co))

        for i in range(1, 10):
            pg.draw.line(self.sc, self.t[1], (x + self.co + self.size * i, y + self.co),
                         (x + self.co + self.size * i, y + self.co + self.size * 10))
        for i in range(1, 10):
            pg.draw.line(self.sc, self.t[1], (x + self.co, y + self.co + self.size * i),
                         (x + self.co + self.size * 10, y + self.co + self.size * i))

        pg.draw.rect(self.sc, self.t[1], (x + self.co, y + self.co, self.size * 10, self.size * 10),
                     4)

        pg.draw.rect(self.sc, self.t[1], (self.x_ship - 30, self.y_ship - 10,
                                          (int(display_width * 0.035)) * 7,
                                          (int(display_width * 0.035)) * 6), 4)
        text = self.font.render("Корабли:", True, self.t[1])
        self.sc.blit(text, (self.x_ship, self.y_ship))

        font = pg.font.Font(self.font_2, int(self.size * 0.4))
        text = font.render("Нажмите на корабль (или пробел), чтобы повернуть", True, self.t[1])
        self.sc.blit(text, (self.x_ship - 30, int(display_height * 0.69)))

        text = font.render("Если корабль не ставиться значит там его нельзя поставить!!!!", True,
                           self.t[1])  # логично
        self.sc.blit(text, (self.x_ship - 30, int(display_height * 0.4 + 240)))

    async def map_customization(self):
        running = True

        x = pg.sprite.Sprite()
        create_sprite(x, "x" + ("_black" if self.t[0] == (255, 255, 255) else "") + ".png",
                      display_width - 75, 30, self.all_sprite_gg)

        reset = pg.sprite.Sprite()
        create_sprite(reset, "reset" + ("_black" if self.t[0] == (255, 255, 255) else "") + ".png",
                      display_width - 300, display_height - 100, self.all_sprite_gg)

        go = pg.sprite.Sprite()
        create_sprite(go, "go.png", display_width - 600, display_height - 100, self.all_sprite_gg)

        while running:
            self.sc.fill(self.t[0])
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    terminate()

                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        pg.mixer.Sound(self.click).play()
                        raise SystemExit

                    elif event.key == pg.K_r:
                        pg.mixer.Sound(self.click).play()
                        up_per()
                        self.add_ship()
                        self.add_cells()

                    elif event.key == pg.K_RETURN and test_007 == 10:
                        pg.mixer.Sound(self.enter).play()
                        return

                if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    if x.rect.collidepoint(event.pos):
                        pg.mixer.Sound(self.click).play()
                        raise SystemExit

                    elif reset.rect.collidepoint(event.pos):
                        pg.mixer.Sound(self.click).play()
                        up_per()
                        self.add_ship()
                        self.add_cells()

                    elif go.rect.collidepoint(event.pos) and test_007 == 10:
                        pg.mixer.Sound(self.enter).play()
                        return

                all_sprites_cell.update(event)
                all_sprites.update(self.sc, event)

            self.map_draw(self.map_indent_left, self.map_indent_top)
            all_sprites_cell.draw(self.sc)
            all_sprites.draw(self.sc)
            self.all_sprite_gg.draw(self.sc)
            self.clock.tick(self.fps)
            pg.display.flip()
            await asyncio.sleep(0)

    def add_ship(self):
        x = int(display_width * 0.6)
        y = int(display_height * 0.25)
        indent_bottom = 10
        indent_right = 10
        size = int(display_width * 0.035) - 10

        for i in range(1, 5):
            for g in range(i):
                Ship(size, 5 - i,
                     x + (((size * (5 - i)) + indent_right + (((5 - i) * 10) - 10)) * g),
                     y + ((size + indent_bottom) * i), all_sprites)

    def add_cells(self):

        for i in range(10):
            for g in range(10):
                Cell((i, g), self.size, self.size * i + self.co + self.map_indent_left,
                     self.size * g + self.co + self.map_indent_top, self.t[0], all_sprites_cell)

    def bir(self):
        return board, all_sprites, pos_all
