from settings import *
from timer import Timer
from math import sin, pi
from random import uniform, random, randint


class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=pos)
        self.mask = pygame.mask.from_surface(self.image)


class CollisionTile(pygame.sprite.Sprite):

    def __init__(self, world_pos, surf, groups):
        super().__init__(groups)

        mask = pygame.mask.from_surface(surf)
        rects = mask.get_bounding_rects()

        if rects:
            r = rects[0]
            self.rect = pygame.Rect(world_pos[0] + r.x, world_pos[1] + r.y, r.w, r.h)
        else:

            self.rect = pygame.Rect(world_pos[0], world_pos[1], 0, 0)

        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)


class Goal(pygame.sprite.Sprite):
    def __init__(self, rect, groups):
        super().__init__(groups)
        self.image = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)  # 透明
        self.rect = rect


class Bullet(Sprite):
    def __init__(self, surf, pos, direction, groups, enemy_group=None, on_hit=None):
        super().__init__(pos, surf, groups)

        self.image = pygame.transform.flip(self.image, direction == -1, False)
        self.rect = self.image.get_rect(topleft=self.rect.topleft)
        self.mask = pygame.mask.from_surface(self.image)

        self.direction = direction
        self.speed = 850

        self.enemy_group = enemy_group
        self.on_hit = on_hit

    def update(self, dt):
        dx_total = self.direction * self.speed * dt

        max_step = 4
        steps = max(1, int(abs(dx_total) // max_step) + 1)
        step_dx = dx_total / steps

        for _ in range(steps):
            self.rect.x += step_dx

            if self.enemy_group:
                candidates = pygame.sprite.spritecollide(self, self.enemy_group, False)
                for s in candidates:
                    if pygame.sprite.collide_mask(self, s):
                        if self.on_hit:
                            self.on_hit(self, [s])
                        return


class Fire(Sprite):
    def __init__(self, surf, pos, groups, player):
        super().__init__(pos, surf, groups)
        self.player = player
        self.flip = player.flip
        self.timer = Timer(100, autostart=True, func=self.kill)
        self.y_offset = pygame.Vector2(0, 8)
        if self.player.flip:
            self.rect.midright = self.player.rect.midleft + self.y_offset
            self.image = pygame.transform.flip(self.image, True, False)
        else:
            self.rect.midleft = self.player.rect.midright + self.y_offset

    def update(self, _):
        self.timer.update()

        if self.player.flip:
            self.rect.midright = self.player.rect.midleft + self.y_offset
        else:
            self.rect.midleft = self.player.rect.midright + self.y_offset

        if self.flip != self.player.flip:
            self.kill()


class AnimatedSprite(Sprite):
    def __init__(self, frames, pos, groups):
        self.frames, self.frame_index, self.animation_speed = frames, 0, 10
        super().__init__(pos, self.frames[self.frame_index], groups)

    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]


class Enemy(AnimatedSprite):
    def __init__(self, frames, pos, groups):
        super().__init__(frames, pos, groups)
        self.death_timer = Timer(200, func=self.kill)

    def destroy(self):
        self.death_timer.activate()
        self.animation_speed = 0
        self.image = pygame.mask.from_surface(self.image).to_surface()
        self.image.set_colorkey('black')

    def update(self, dt):
        self.death_timer.update()
        if not self.death_timer:
            self.move(dt)
            self.animate(dt)
        self.constraint()


class Bee(Enemy):
    def __init__(self, frames, pos, groups, speed):
        super().__init__(frames, pos, groups)
        self.speed = speed

        self.base_y = self.rect.y
        self.amplitude = uniform(30, 80)
        self.period = uniform(1.5, 3.0)
        self.phase0 = random() * 2 * pi

    def move(self, dt):
        self.rect.x -= self.speed * dt

        t = pygame.time.get_ticks() / 1000.0
        self.rect.y = self.base_y + sin(2 * pi * t / self.period + self.phase0) * self.amplitude

    def constraint(self):
        if self.rect.right <= 0:
            self.kill()


class Snake(Enemy):
    def __init__(self, frames, rect, groups):
        super().__init__(frames, rect.topleft, groups)
        self.rect.bottomleft = rect.bottomleft
        self.main_rect = rect
        self.speed = randint(50, 60)
        self.direction = 1

    def move(self, dt):
        self.rect.x += self.direction * self.speed * dt

    def constraint(self):
        if not self.main_rect.contains(self.rect):
            self.direction *= -1
            self.frames = [pygame.transform.flip(surf, True, False) for surf in self.frames]


class Player(AnimatedSprite):
    def __init__(self, pos, groups, collision_sprites, anims, create_bullet):
        self.anims = anims
        self.state = 'idle'
        self.frames = self.anims[self.state]
        self.frame_index = 0
        self.animation_speed = 8

        super().__init__(self.frames, pos, groups)

        self.flip = False
        self.facing = 1
        self.create_bullet = create_bullet

        # movement & collision
        self.direction = pygame.Vector2()
        self.collision_sprites = collision_sprites
        self.speed = 120
        self.gravity = 30
        self.on_floor = False

        # timer
        self.shoot_timer = Timer(500)

    def input(self):
        keys = pygame.key.get_pressed()

        self.direction.x = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_floor:
            self.direction.y = -15
        if keys[pygame.K_s] and not self.shoot_timer:
            self.create_bullet(self.rect.center, -1 if self.flip else 1)
            self.shoot_timer.activate()

    def move(self, dt):
        self.rect.x += self.direction.x * self.speed * dt
        self.collision('horizontal')

        self.direction.y += self.gravity * dt
        self.rect.y += self.direction.y
        self.collision('vertical')

    def collision(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.rect):
                if direction == 'horizontal':
                    if self.direction.x > 0:
                        self.rect.right = sprite.rect.left
                    elif self.direction.x < 0:
                        self.rect.left = sprite.rect.right
                elif direction == 'vertical':
                    if self.direction.y > 0:
                        self.rect.bottom = sprite.rect.top
                    elif self.direction.y < 0:
                        self.rect.top = sprite.rect.bottom
                    self.direction.y = 0

    def check_floor(self):
        bottom_rect = pygame.Rect(0, 0, self.rect.width, 2)
        bottom_rect.midtop = self.rect.midbottom
        self.on_floor = bottom_rect.collidelist([sprite.rect for sprite in self.collision_sprites]) >= 0

    def animate(self, dt):
        if not self.on_floor:
            self.state = 'jump'
        elif self.direction.x:
            self.state = 'run'
        else:
            self.state = 'idle'

        if self.direction.x != 0:
            self.facing = -1 if self.direction.x < 0 else 1
        self.flip = (self.facing == -1)

        self.frames = self.anims[self.state]

        if self.state in ('run', 'idle'):
            self.frame_index += self.animation_speed * dt
            frame = int(self.frame_index) % len(self.frames)
        else:
            self.frame_index = min(self.frame_index + self.animation_speed * dt, len(self.frames) - 1)
            frame = int(self.frame_index)

        self.image = self.frames[frame]
        self.image = pygame.transform.flip(self.image, self.flip, False)

    def update(self, dt):
        self.shoot_timer.update()
        self.check_floor()
        self.input()
        self.move(dt)
        self.animate(dt)
