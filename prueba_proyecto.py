import pygame, sys, math, random
from random import randint

# --- Clases de elementos ---

class Bubble(pygame.sprite.Sprite):
    def __init__(self, image, pos, speed, accel=1.05, bounce_thresh=5):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=pos)
        self.speed = pygame.math.Vector2(speed)
        self.accel, self.bounce_thresh, self.bounce_count = accel, bounce_thresh, 0

    def update(self, bounds):
        self.rect.x += int(self.speed.x)
        self.rect.y += int(self.speed.y)
        if self.rect.left < bounds.left or self.rect.right > bounds.right:
            self.speed.x *= -1; self.register_bounce()
        if self.rect.top < bounds.top:
            self.speed.y *= -1; self.register_bounce()
        if abs(self.speed.y) < 3:
            self.speed.y = -3 if self.speed.y < 0 else 3

    def register_bounce(self):
        self.bounce_count += 1
        if self.bounce_count % self.bounce_thresh == 0:
            self.speed *= self.accel

    def bounce_off_submarine(self, sub):
        offset = (self.rect.centerx - sub.rect.centerx) / (sub.rect.width / 2)
        angle = offset * math.radians(60)
        mag = self.speed.length()
        self.speed.x = mag * math.sin(angle)
        self.speed.y = -abs(mag * math.cos(angle))
        if abs(self.speed.y) < 3: self.speed.y = -3
        self.register_bounce()

    def clamp_speed(self, max_speed):
        if self.speed.length() > max_speed:
            self.speed.scale_to_length(max_speed)

class Submarine(pygame.sprite.Sprite):
    def __init__(self, image, pos):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(midbottom=pos)
        self.speed = 7
    def update(self, bounds, keys):
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if self.rect.left < bounds.left: self.rect.left = bounds.left
        if self.rect.right > bounds.right: self.rect.right = bounds.right

class Brick(pygame.sprite.Sprite):
    def __init__(self, image, pos, hits=1):
        super().__init__()
        self.image = image.copy()
        self.rect = self.image.get_rect(topleft=pos)
        self.hits = hits
    def hit(self):
        self.hits -= 1
        if self.hits <= 0:
            self.kill()
            return True
        return False

class SpecialBrick(Brick):
    def __init__(self, image, pos, hits=2):
        super().__init__(image, pos, hits)
    def hit(self):
        res = super().hit()
        if res: print("Special brick hit!")
        return res

class UnbreakableBrick(Brick):
    def __init__(self, image, pos):
        super().__init__(image, pos, hits=9999)
    def hit(self):
        print("Unbreakable brick hit, not broken.")
        return False

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, image, pos, ptype, fall_speed=3):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=pos)
        self.ptype = ptype  # "extra_life", "increase_sub_speed" o "duplicate_ball"
        self.fall_speed = fall_speed
    def update(self, bounds):
        self.rect.y += self.fall_speed
        if self.rect.top > bounds.height: self.kill()

# --- Clase principal del juego ---

class Game:
    def __init__(self):
        pygame.init(); pygame.mixer.init()
        self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        pygame.display.set_caption("Mundo Submarino")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None,36)
        self.max_ball_speed = 15

        # Cargar imágenes
        self.background = pygame.image.load("ocean_background.png").convert()
        self.bubble_img = pygame.image.load("bubble.png").convert_alpha()
        self.submarine_img = pygame.image.load("submarine.png").convert_alpha()
        self.brick_img = pygame.image.load("brick.png").convert_alpha()
        self.special_brick_img = pygame.image.load("special_brick.png").convert_alpha()
        self.powerup_speed_img = pygame.image.load("powerup_speed.png").convert_alpha()
        self.powerup_ball_img = pygame.image.load("powerup_ball.png").convert_alpha()
        self.powerup_life_img = pygame.image.load("powerup_life.png").convert_alpha()
        self.heart_img = pygame.transform.scale(pygame.image.load("heart.png").convert_alpha(), (30,30))

        # Cargar sonidos
        self.break_sound = pygame.mixer.Sound("break.wav")
        self.powerup_extra_life_sound = pygame.mixer.Sound("powerup_extra_life.wav")
        self.powerup_speed_sound = pygame.mixer.Sound("powerup_speed.wav")
        self.powerup_duplicate_sound = pygame.mixer.Sound("powerup_duplicate.wav")
        self.life_lost_sound = pygame.mixer.Sound("life_lost.wav")
        self.game_over_sound = pygame.mixer.Sound("game_over.wav")
        pygame.mixer.music.load("background_music.mp3")
        pygame.mixer.music.play(-1)

        self.all_sprites = pygame.sprite.Group()
        self.bubbles = pygame.sprite.Group()
        self.bricks = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()

        self.lives, self.level, self.paused = 3, 1, False
        bounds = self.screen.get_rect()
        self.submarine = Submarine(self.submarine_img, (bounds.centerx, bounds.bottom-20))
        self.all_sprites.add(self.submarine)
        self.new_ball(initial=True)
        self.load_level()
        self.running = True

    def new_ball(self, initial=False):
        # Velocidad base incrementada (multiplicador 1.60)
        base_speed = randint(3,6) * 1.60 * (1+(self.level-1)*0.1)
        horz = random.uniform(-0.5, 0.5)
        speed = (base_speed*(1+horz), -abs(base_speed))
        pos = self.submarine.rect.midtop if initial else self.screen.get_rect().center
        ball = Bubble(self.bubble_img, pos, speed)
        ball.clamp_speed(self.max_ball_speed)
        self.all_sprites.add(ball)
        self.bubbles.add(ball)
        if initial:
            self.submarine.rect.midbottom = (self.screen.get_rect().centerx, self.screen.get_rect().bottom-20)

    def load_level(self):
        for brick in list(self.bricks): brick.kill()
        columns, rows = 8, 3 if self.level==1 else self.level+2
        bw, bh = self.brick_img.get_width(), self.brick_img.get_height()
        gap = 10; sw = self.screen.get_rect().width
        total = columns * bw + (columns-1)*gap
        offset_x = (sw - total) / 2; offset_y = 50
        for r in range(rows):
            for c in range(columns):
                x = offset_x + c*(bw+gap)
                y = offset_y + r*(bh+gap)
                if self.level>=3 and random.random() < 0.15:
                    brick = UnbreakableBrick(self.special_brick_img, (x,y))
                elif random.random() < 0.2:
                    brick = SpecialBrick(self.special_brick_img, (x,y))
                else:
                    brick = Brick(self.brick_img, (x,y))
                self.all_sprites.add(brick)
                self.bricks.add(brick)

    def run(self):
        while self.running:
            self.handle_events()
            if not self.paused: self.update()
            self.draw()
            self.clock.tick(60)
        self.game_over(); pygame.quit(); sys.exit()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT: self.running = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE: self.paused = not self.paused

    def update(self):
        bounds = self.screen.get_rect()
        keys = pygame.key.get_pressed()
        self.submarine.update(bounds, keys)
        for ball in list(self.bubbles):
            ball.update(bounds); ball.clamp_speed(self.max_ball_speed)
            if ball.rect.colliderect(self.submarine.rect) and ball.speed.y > 0:
                ball.bounce_off_submarine(self.submarine); ball.clamp_speed(self.max_ball_speed)
            coll = None
            for brick in self.bricks:
                if ball.rect.colliderect(brick.rect.inflate(-5,-5)):
                    coll = brick; break
            if coll:
                ball.speed.y *= -1
                if coll.hit():
                    self.break_sound.play()
                    if randint(0,19)==0:
                        power_type = "extra_life" if randint(0,9)==0 else random.choice(["increase_sub_speed","duplicate_ball"])
                        img = self.powerup_life_img if power_type=="extra_life" else self.powerup_speed_img if power_type=="increase_sub_speed" else self.powerup_ball_img
                        pu = PowerUp(img, coll.rect.center, power_type)
                        self.all_sprites.add(pu); self.powerups.add(pu)
            if ball.rect.top > bounds.height: ball.kill()
        if len(self.bubbles)==0:
            self.life_lost_sound.play(); self.lives -= 1
            if self.lives > 0: self.new_ball()
            else: self.running = False
        for pu in list(self.powerups): pu.update(bounds)
        for pu in pygame.sprite.spritecollide(self.submarine, self.powerups, True):
            self.apply_powerup(pu.ptype)
        if len(self.bricks)==0:
            self.level += 1
            for ball in list(self.bubbles):
                ball.speed *= 1.05; ball.clamp_speed(self.max_ball_speed)
            self.load_level()

    def apply_powerup(self, ptype):
        if ptype=="increase_sub_speed":
            self.submarine.speed += 2; self.powerup_speed_sound.play()
        elif ptype=="duplicate_ball":
            for ball in list(self.bubbles):
                nb = Bubble(self.bubble_img, ball.rect.center, ball.speed)
                nb.clamp_speed(self.max_ball_speed)
                self.all_sprites.add(nb); self.bubbles.add(nb)
            self.powerup_duplicate_sound.play()
        elif ptype=="extra_life":
            if self.lives < 3:
                self.lives += 1; self.powerup_extra_life_sound.play()
            else:
                print("Max lives reached!")
    def draw(self):
        self.screen.blit(self.background, (0,0))
        self.all_sprites.draw(self.screen)
        self.screen.blit(self.font.render("Vidas:", True, (255,255,255)), (10,10))
        for i in range(self.lives):
            self.screen.blit(self.heart_img, (120+i*(self.heart_img.get_width()+5), 10))
        self.screen.blit(self.font.render(f"Nivel: {self.level}", True, (255,255,255)), (10,50))
        if self.paused:
            self.screen.blit(self.font.render("Pausado", True, (255,0,0)), self.font.render("Pausado", True, (255,0,0)).get_rect(center=self.screen.get_rect().center))
        pygame.display.flip()
    def game_over(self):
        self.game_over_sound.play()
        self.screen.fill((0,0,0))
        self.screen.blit(self.font.render("Game Over", True, (255,0,0)), self.font.render("Game Over", True, (255,0,0)).get_rect(center=self.screen.get_rect().center))
        pygame.display.flip()
        pygame.time.delay(3000)

if __name__ == "__main__":
    Game().run()
    