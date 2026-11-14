import pygame
import math
import sys

pygame.init()

# ==================== НАСТРОЙКИ ====================
WIDTH, HEIGHT = 1000, 650
FPS = 60
GRAVITY = 1200
POWER = -7.5
MAX_DRAG = 140

# ==================== ЦВЕТА ====================
SKY = (135, 206, 235)
GROUND = (80, 160, 60)
DIRT = (110, 80, 50)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
YELLOW = (250, 210, 60)
GREEN = (80, 180, 60)
BROWN = (140, 90, 50)
GRAY = (100, 100, 100)
DARK_GRAY = (60, 60, 60)
ORANGE = (255, 140, 0)

# ==================== СПРАЙТЫ ====================
SPRITES = {
    "bird_red": None, 
    "bird_yellow": None, 
    "bird_black": None,
    "pig": None,
    "pig_hit": None, 
    "block": None, 
    "slingshot": None,
    "background1": None, 
    "background2": None,
}
loaded_sprites = {}

def load_sprites():
    for name, path in SPRITES.items():
        if path:
            try:
                loaded_sprites[name] = pygame.image.load(path).convert_alpha()
            except Exception as e:
                print(f"Ошибка {path}: {e}")

def get_sprite(name, size=None):
    img = loaded_sprites.get(name)
    if img and size:
        return pygame.transform.scale(img, size)
    return img

def draw_text(surf, text, size, x, y, color=BLACK, bold=False):
    font = pygame.font.SysFont("Arial", size, bold=bold)
    t = font.render(text, True, color)
    surf.blit(t, t.get_rect(center=(x, y)))
    return t.get_rect()

def draw_button(surf, text, x, y, w, h, mouse_pos, size=32):
    rect = pygame.Rect(x, y, w, h)
    hover = rect.collidepoint(mouse_pos)
    color = (240, 200, 120) if hover else (200, 160, 90)
    pygame.draw.rect(surf, color, rect, border_radius=12)
    pygame.draw.rect(surf, BLACK, rect, 3, border_radius=12)
    draw_text(surf, text, size, x + w // 2, y + h // 2, BLACK, bold=True)
    return rect


# ==================== ТИПЫ ПТИЦ ====================
BIRD_TYPES = {
    "red":    {"sprite": "bird_red",    "color": RED,    "r": 18, "dmg": 2, "ability": None},
    "yellow": {"sprite": "bird_yellow", "color": YELLOW, "r": 16, "dmg": 2, "ability": "speed"},
    "black":  {"sprite": "bird_black",  "color": DARK_GRAY,"r": 20, "dmg": 3, "ability": "bomb"},
}


# ==================== ПТИЦА ====================
class Bird:
    def __init__(self, x, y, btype="red"):
        self.start_x, self.start_y = x, y
        self.x, self.y = x, y
        self.btype = btype
        cfg = BIRD_TYPES[btype]
        self.radius = cfg["r"]
        self.color = cfg["color"]
        self.ability = cfg["ability"]
        self.dmg = cfg["dmg"]
        self.sprite = cfg["sprite"]
        self.vx = self.vy = 0
        self.flying = False
        self.launched = False
        self.stopped = False
        self.ability_used = False
        self.anim_t = 0
        self.hit_cooldown = 0.5       # кулдаун удара по блоку/свинке
        self.slow_timer = 0         # сколько времени скорость мала

    def launch(self, px, py):
        self.vx, self.vy = px, py
        self.flying = True
        self.launched = True

    def use_ability(self):
        if not self.flying or self.ability_used:
            return
        if self.ability == "speed":
            self.vx *= 1.7
            self.vy *= 0.6
        elif self.ability == "bomb":
            return "explode"
        self.ability_used = True

    def stop(self):
        """Останавливает птицу — запустит следующую."""
        self.flying = False
        self.stopped = True
        self.vx = self.vy = 0

    def update(self, dt, ground_y):
        if self.hit_cooldown > 0:
            self.hit_cooldown -= dt

        if not self.flying:
            return

        self.vy += GRAVITY * dt    #dt - delta time - время 
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.anim_t += dt

        # земля
        if self.y + self.radius >= ground_y:
            self.y = ground_y - self.radius
            self.vy *= -0.3
            self.vx *= 0.5
            if abs(self.vy) < 100:
                self.vy = 0
            if abs(self.vx) < 60:
                self.stop()
                return

        # стены
        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx *= -0.5
        if self.x + self.radius > WIDTH:
            self.x = WIDTH - self.radius
            self.vx *= -0.5

        # защита от застревания: если долго медленно — стоп
        speed = math.hypot(self.vx, self.vy)
        if speed < 120:
            self.slow_timer += dt
            if self.slow_timer > 1.0:
                self.stop()
        else:
            self.slow_timer = 0

    def draw(self, surf):
        img = get_sprite(self.sprite, (self.radius * 2, self.radius * 2))
        if img:
            surf.blit(img, (self.x - self.radius, self.y - self.radius))
        else:
            bob = math.sin(self.anim_t * 12) * 2 if self.flying else 0
            cx, cy = int(self.x), int(self.y + bob)
            pygame.draw.circle(surf, self.color, (cx, cy), self.radius)
            pygame.draw.circle(surf, WHITE, (cx + 6, cy - 4), 5)
            pygame.draw.circle(surf, BLACK, (cx + 7, cy - 4), 2)
            pygame.draw.polygon(surf, ORANGE, [
                (cx + self.radius - 2, cy),
                (cx + self.radius + 10, cy + 3),
                (cx + self.radius - 2, cy + 8)
            ])


# ==================== СВИНКА ====================
class Pig:
    def __init__(self, x, y, hp=2):
        self.x, self.y = float(x), float(y)
        self.r = 22
        self.hp = hp
        self.alive = True
        self.hit_timer = 0
        # для гравитации (если стоит на блоке)
        self.vy = 0
        self.on_ground = False

    def hit(self, dmg=1):
        self.hp -= dmg
        self.hit_timer = 0.15
        if self.hp <= 0:
            self.alive = False

    def update(self, dt, blocks):
        if self.hit_timer > 0: self.hit_timer -= dt
        if not self.alive: return
        # гравитация — свинка падает, если под ней нет опоры
        support = self.find_support(blocks)
        if support is None:
            self.vy += GRAVITY * dt
            self.y += self.vy * dt
            # падение об землю — урон
            ground_y = HEIGHT - 60
            if self.y + self.r >= ground_y:
                self.y = ground_y - self.r
                if self.vy > 400:
                    self.hit(1)
                self.vy = 0
        else:
            # стоит на блоке — проверяем, не упал ли блок
            self.vy = 0
            self.y = support.top - self.r

    def find_support(self, blocks):
        """Ищет блок под свинкой."""
        for b in blocks:
            if not b.alive: continue
            if abs(b.rect.top - (self.y + self.r)) < 6 \
                    and b.rect.left < self.x < b.rect.right:
                return b.rect
        return None

    def draw(self, surf):
        if not self.alive: return
        name = "pig_hit" if self.hit_timer > 0 else "pig"
        img = get_sprite(name, (self.r * 2, self.r * 2))
        if img:
            surf.blit(img, (self.x - self.r, self.y - self.r))
        else:
            color = GREEN if self.hit_timer <= 0 else (200, 250, 120)
            pygame.draw.circle(surf, color, (int(self.x), int(self.y)), self.r)
            pygame.draw.circle(surf, WHITE, (int(self.x - 7), int(self.y - 5)), 5)
            pygame.draw.circle(surf, WHITE, (int(self.x + 7), int(self.y - 5)), 5)
            pygame.draw.circle(surf, BLACK, (int(self.x - 6), int(self.y - 5)), 2)
            pygame.draw.circle(surf, BLACK, (int(self.x + 8), int(self.y - 5)), 2)
            pygame.draw.circle(surf, (40, 140, 40), (int(self.x), int(self.y + 4)), 7)


# ==================== БЛОК ====================
class Block:
    def __init__(self, x, y, w, h, hp=3):
        self.rect = pygame.Rect(x, y, w, h)
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.hit_timer = 0
        # физика падения
        self.vy = 0
        self.falling = False
        self.landed = False

    def hit(self, dmg=1):
        self.hp -= dmg
        self.hit_timer = 0.12
        if self.hp <= 0 and self.alive:
            self.alive = False
            self.falling = True   # сломанный блок — падает

    def update(self, dt, all_blocks, pigs):
        if self.hit_timer > 0: self.hit_timer -= dt
        if not self.alive and not self.falling: return

        ground_y = HEIGHT - 60

        # падение
        if self.falling:
            self.vy += GRAVITY * dt
            self.rect.y += int(self.vy * dt)

            # столкновение с землёй — исчезает
            if self.rect.bottom >= ground_y:
                self.rect.bottom = ground_y
                self.falling = False
                self.alive = False
                return

            # столкновение с другими блоками — наносит им урон
            for b in all_blocks:
                if b is self or not b.alive: continue
                if self.rect.colliderect(b.rect):
                    if self.vy > 300:
                        b.hit(1)
                    self.rect.bottom = b.rect.top
                    self.falling = False
                    self.alive = False
                    return

            # столкновение со свинками — урон
            for p in pigs:
                if not p.alive: continue
                if math.hypot(p.x - (self.rect.centerx), p.y - (self.rect.centery)) \
                        < p.r + max(self.rect.w, self.rect.h) / 2:
                    if self.vy > 250:
                        p.hit(2)
                    return

    def draw(self, surf):
        if not self.alive and not self.falling: return
        img = get_sprite("block", (self.rect.w, self.rect.h))
        if img:
            surf.blit(img, self.rect.topleft)
        else:
            # трещины при низком HP
            base = BROWN if self.hit_timer <= 0 else (220, 160, 90)
            if self.hp < self.max_hp:
                base = (180, 120, 70)
            pygame.draw.rect(surf, base, self.rect, border_radius=4)
            pygame.draw.rect(surf, DARK_GRAY, self.rect, 3, border_radius=4)


# ==================== УРОВНИ ====================
def build_level(n):
    pigs, blocks = [], []
    if n == 1:
        blocks += [Block(780, 450, 30, 150, hp=2), Block(850, 450, 30, 150, hp=2),
                   Block(760, 420, 140, 30, hp=2)]
        pigs += [Pig(815, 390, hp=2), Pig(700, 590, hp=2)]
        birds = ["red", "yellow", "red"]
    else:
        blocks += [Block(700, 470, 30, 130, hp=2), Block(770, 470, 30, 130, hp=2),
                   Block(840, 470, 30, 130, hp=2), Block(680, 440, 200, 30, hp=2),
                   Block(745, 340, 30, 100, hp=2), Block(715, 320, 90, 25, hp=2)]
        pigs += [Pig(735, 410, hp=2), Pig(805, 410, hp=2),
                 Pig(760, 295, hp=2), Pig(900, 590, hp=2)]
        birds = ["red", "yellow", "black", "red", "black"]
    return pigs, blocks, birds


# ==================== ИГРА ====================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Angry Birds")
        self.clock = pygame.time.Clock()
        self.state = "menu"
        self.level = 1
        self.slingshot_x, self.slingshot_y = 180, 450
        self.ground_y = HEIGHT - 60
        self.dragging = False
        self.drag_pos = (self.slingshot_x, self.slingshot_y)
        self.score = 0
        self.best_score = 0
        self.reset_level()

    def reset_level(self):
        self.pigs, self.blocks, self.bird_queue = build_level(self.level)
        self.total_pigs = len(self.pigs)
        self.birds_left = list(self.bird_queue)
        self.current_bird = None
        self.spawn_bird()
        self.win = self.lose = False
        self.win_timer = 0

    def spawn_bird(self):
        if self.birds_left:
            btype = self.birds_left.pop(0)
            self.current_bird = Bird(self.slingshot_x, self.slingshot_y - 40, btype)
        else:
            self.current_bird = None

    def start_level(self, level):
        self.level = level
        self.reset_level()
        self.state = "play"

    # -------------------- ЛОГИКА --------------------
    def update(self, dt):
        if self.state != "play": return

        if self.current_bird:
            self.current_bird.update(dt, self.ground_y)

        for b in self.blocks:
            b.update(dt, self.blocks, self.pigs)
        for p in self.pigs:
            p.update(dt, self.blocks)

        bird = self.current_bird
        if bird and (bird.flying or bird.stopped):
            self.check_collisions()

        # проверка победы
        if not self.win and not self.lose:
            if not any(p.alive for p in self.pigs):
                self.win = True
                self.win_timer = 0
            elif bird and bird.stopped:
                self.win_timer += dt
                if self.win_timer > 1.2:
                    if self.birds_left:
                        self.spawn_bird()
                        self.win_timer = 0
                    else:
                        self.lose = True

    def check_collisions(self):
        bird = self.current_bird
        if not bird: return
        bx, by, br = bird.x, bird.y, bird.radius
        speed = math.hypot(bird.vx, bird.vy)

        # птица → свинки
        for p in self.pigs:
            if not p.alive: continue
            dist = math.hypot(p.x - bx, p.y - by)
            if dist < p.r + br and speed > 150:
                p.hit(bird.dmg)
                if not p.alive: self.score += 500
                bird.vx *= 0.5
                bird.vy *= 0.5

        # птица → блоки
        for b in self.blocks:
            if not b.alive: continue
            cx = max(b.rect.left, min(bx, b.rect.right))
            cy = max(b.rect.top, min(by, b.rect.bottom))
            dx, dy = bx - cx, by - cy
            dist = math.hypot(dx, dy)
            if dist < br:
                if speed > 250:
                    b.hit(1 if speed < 500 else 2)
                    if not b.alive: self.score += 100
                if dist > 0:
                    nx, ny = dx / dist, dy / dist
                    bird.x = cx + nx * br
                    bird.y = cy + ny * br
                    dot = bird.vx * nx + bird.vy * ny
                    bird.vx = (bird.vx - 2 * dot * nx) * 0.5
                    bird.vy = (bird.vy - 2 * dot * ny) * 0.5

    def explode(self, x, y):
        radius = 130
        for p in self.pigs:
            if p.alive and math.hypot(p.x - x, p.y - y) < radius + p.r:
                p.hit(3)
                if not p.alive: self.score += 500
        for b in self.blocks:
            if b.alive:
                cx = max(b.rect.left, min(x, b.rect.right))
                cy = max(b.rect.top, min(y, b.rect.bottom))
                if math.hypot(cx - x, cy - y) < radius:
                    b.hit(3)
                    if not b.alive: self.score += 100
        if self.current_bird:
            self.current_bird.flying = False
            self.current_bird.stopped = True

    # -------------------- ОТРИСОВКА --------------------
    def draw_background(self):
        bg = get_sprite(f"background{self.level}")
        if bg:
            self.screen.blit(pygame.transform.scale(bg, (WIDTH, HEIGHT)), (0, 0))
        else:
            self.screen.fill(SKY)
            for cx, cy in [(150, 100), (500, 80), (800, 130)]:
                pygame.draw.circle(self.screen, WHITE, (cx, cy), 35)
                pygame.draw.circle(self.screen, WHITE, (cx + 40, cy + 10), 30)
                pygame.draw.circle(self.screen, WHITE, (cx - 40, cy + 10), 28)
        pygame.draw.rect(self.screen, GROUND, (0, self.ground_y, WIDTH, HEIGHT))
        pygame.draw.rect(self.screen, DIRT, (0, self.ground_y + 20, WIDTH, HEIGHT))

    def draw_slingshot(self):
        img = get_sprite("slingshot", (80, 160))
        if img:
            self.screen.blit(img, (self.slingshot_x - 40, self.slingshot_y - 80))
        else:
            pygame.draw.rect(self.screen, BROWN,
                             (self.slingshot_x - 8, self.slingshot_y - 30, 16, 100))
            pygame.draw.circle(self.screen, DARK_GRAY,
                               (self.slingshot_x, self.slingshot_y - 30), 18)

    def draw_trajectory(self):
        if not self.dragging or not self.current_bird: return
        sx, sy = self.slingshot_x, self.slingshot_y - 40
        dx, dy = self.drag_pos[0] - sx, self.drag_pos[1] - sy
        vx, vy = dx * POWER, dy * POWER
        x, y = sx, sy
        for _ in range(55):
            vy += GRAVITY * 0.03
            x += vx * 0.03
            y += vy * 0.03
            if y > self.ground_y: break
            pygame.draw.circle(self.screen, WHITE, (int(x), int(y)), 3)

    def draw_play(self):
        self.draw_background()
        for b in self.blocks: b.draw(self.screen)
        for p in self.pigs: p.draw(self.screen)

        if self.dragging and self.current_bird and not self.current_bird.launched:
            pygame.draw.line(self.screen, DARK_GRAY,
                             (self.slingshot_x, self.slingshot_y - 30),
                             self.drag_pos, 4)

        self.draw_slingshot()
        if self.current_bird:
            self.current_bird.draw(self.screen)
        self.draw_trajectory()

        # HUD
        draw_text(self.screen, f"Уровень {self.level}", 28, 100, 30, WHITE, True)
        draw_text(self.screen, f"Счёт: {self.score}", 26, 100, 65, YELLOW, True)
        alive = sum(1 for p in self.pigs if p.alive)
        draw_text(self.screen, f"Свинки: {alive}/{self.total_pigs}",
                  22, 130, 100, WHITE, True)

        draw_text(self.screen, "Очередь:", 18, 60, 130, WHITE, True)
        for i, bt in enumerate(self.birds_left):
            c = BIRD_TYPES[bt]["color"]
            pygame.draw.circle(self.screen, c, (110 + i * 30, 135), 10)
            pygame.draw.circle(self.screen, BLACK, (110 + i * 30, 135), 10, 2)

        if self.current_bird and self.current_bird.flying \
                and self.current_bird.ability and not self.current_bird.ability_used:
            draw_text(self.screen, "ЛКМ — способность!", 22,
                      WIDTH // 2, HEIGHT - 90, WHITE, True)

        if self.win:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            bonus = len(self.birds_left) * 1000
            draw_text(self.screen, "ПОБЕДА!", 72, WIDTH // 2, 200, YELLOW, True)
            draw_text(self.screen, f"Бонус за птиц: +{bonus}", 28,
                      WIDTH // 2, 280, WHITE)
            draw_text(self.screen, f"Итог: {self.score + bonus}", 34,
                      WIDTH // 2, 320, YELLOW, True)
            txt = "Enter — следующий" if self.level < 2 else "Enter — меню"
            draw_text(self.screen, txt, 28, WIDTH // 2, 380, WHITE)
            draw_text(self.screen, "R — заново", 24, WIDTH // 2, 420, WHITE)

        if self.lose:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            draw_text(self.screen, "Птички закончились :(", 56,
                      WIDTH // 2, 250, RED, True)
            draw_text(self.screen, "R — заново", 30, WIDTH // 2, 330, WHITE)
            draw_text(self.screen, "Esc — в меню", 26, WIDTH // 2, 380, WHITE)

    def draw_menu(self):
        self.screen.fill(SKY)
        pygame.draw.rect(self.screen, GROUND, (0, HEIGHT - 80, WIDTH, HEIGHT))
        draw_text(self.screen, "ANGRY BIRDS", 84, WIDTH // 2, 100, RED, True)
        draw_text(self.screen, "Python Edition", 32, WIDTH // 2, 165, BLACK, True)
        draw_text(self.screen, f"Рекорд: {self.best_score}", 28,
                  WIDTH // 2, 215, DARK_GRAY, True)

        m = pygame.mouse.get_pos()
        b1 = draw_button(self.screen, "Уровень 1", WIDTH // 2 - 150, 280, 300, 70, m)
        b2 = draw_button(self.screen, "Уровень 2", WIDTH // 2 - 150, 380, 300, 70, m)
        b3 = draw_button(self.screen, "Выход", WIDTH // 2 - 150, 480, 300, 60, m, 26)
        draw_text(self.screen, "Тяни от рогатки. ЛКМ в полёте — способность",
                  22, WIDTH // 2, HEIGHT - 40, WHITE)
        return b1, b2, b3

    # -------------------- СОБЫТИЯ --------------------
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if self.state == "menu":
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                b1, b2, b3 = self.draw_menu()
                if b1.collidepoint(e.pos): self.start_level(1)
                elif b2.collidepoint(e.pos): self.start_level(2)
                elif b3.collidepoint(e.pos):
                    pygame.quit(); sys.exit()

        elif self.state == "play":
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.best_score = max(self.best_score, self.score)
                    self.state = "menu"
                elif e.key == pygame.K_r:
                    self.reset_level()
                elif e.key == pygame.K_RETURN and self.win:
                    self.best_score = max(self.best_score, self.score)
                    if self.level < 2: self.start_level(2)
                    else: self.state = "menu"

            bird = self.current_bird

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 \
                    and bird and bird.flying and not bird.ability_used \
                    and bird.ability:
                res = bird.use_ability()
                if res == "explode":
                    self.explode(bird.x, bird.y)

            if bird and not bird.launched:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if math.hypot(mx - bird.x, my - bird.y) < 80:
                        self.dragging = True
                        self.drag_pos = (mx, my)
                elif e.type == pygame.MOUSEMOTION and self.dragging:
                    sx, sy = self.slingshot_x, self.slingshot_y - 40
                    dx, dy = e.pos[0] - sx, e.pos[1] - sy
                    dist = math.hypot(dx, dy)
                    if dist > MAX_DRAG:
                        dx = dx / dist * MAX_DRAG
                        dy = dy / dist * MAX_DRAG
                    self.drag_pos = (sx + dx, sy + dy)
                    bird.x, bird.y = sx + dx, sy + dy
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.dragging:
                    self.dragging = False
                    sx, sy = self.slingshot_x, self.slingshot_y - 40
                    dx, dy = self.drag_pos[0] - sx, self.drag_pos[1] - sy
                    if math.hypot(dx, dy) > 10:
                        bird.launch(dx * POWER, dy * POWER)
                    else:
                        bird.x, bird.y = sx, sy

    def check_collisions(self):
        bird = self.current_bird
        if not bird or not bird.flying:
            return

        bx, by, br = bird.x, bird.y, bird.radius
        speed = math.hypot(bird.vx, bird.vy)

        # птица → свинки
        for p in self.pigs:
            if not p.alive:
                continue
            dist = math.hypot(p.x - bx, p.y - by)
            if dist < p.r + br:
                if speed > 150 and bird.hit_cooldown <= 0:
                    p.hit(bird.dmg)
                    if not p.alive:
                        self.score += 500
                    bird.hit_cooldown = 0.3
                    # гасим скорость после удара
                    bird.vx *= 0.4
                    bird.vy *= 0.4
                elif dist > 0:
                    # мягкое выталкивание без отскока
                    nx, ny = (bx - p.x) / dist, (by - p.y) / dist
                    bird.x = p.x + nx * (p.r + br)
                    bird.y = p.y + ny * (p.r + br)

        # птица → блоки
        for b in self.blocks:
            if not b.alive:
                continue
            cx = max(b.rect.left, min(bx, b.rect.right))
            cy = max(b.rect.top, min(by, b.rect.bottom))
            dx, dy = bx - cx, by - cy
            dist = math.hypot(dx, dy)

            if dist < br:
                # урон — только с кулдауном
                if speed > 250 and bird.hit_cooldown <= 0:
                    b.hit(2 if speed > 500 else 1)
                    if not b.alive:
                        self.score += 100
                    bird.hit_cooldown = 0.25

                # выталкивание + единственный отскок
                if dist > 0.001:
                    nx, ny = dx / dist, dy / dist
                else:
                    nx, ny = 0, -1
                bird.x = cx + nx * (br + 0.5)
                bird.y = cy + ny * (br + 0.5)

                # отражаем скорость только если летим «в» блок
                dot = bird.vx * nx + bird.vy * ny
                if dot < 0:
                    bird.vx = (bird.vx - 2 * dot * nx) * 0.4
                    bird.vy = (bird.vy - 2 * dot * ny) * 0.4

                # если после отскока почти стоим — стоп
                if math.hypot(bird.vx, bird.vy) < 150:
                    bird.stop()
                    return

    # -------------------- ЦИКЛ --------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            if self.state == "menu":
                self.draw_menu()
            else:
                self.draw_play()
            pygame.display.flip()


if __name__ == "__main__":
    load_sprites()
    Game().run()