from settings import *

class AllSprites(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()

    def draw(self, target_pos, level_size):
        level_w, level_h = level_size

        self.offset.x = -(target_pos[0] - WINDOW_WIDTH  / 2)
        self.offset.y = -(target_pos[1] - WINDOW_HEIGHT / 2)

        if level_w > WINDOW_WIDTH:
            self.offset.x = max(WINDOW_WIDTH - level_w, min(0, self.offset.x))
        else:
            self.offset.x = (WINDOW_WIDTH - level_w) // 2

        if level_h > WINDOW_HEIGHT:
            self.offset.y = max(WINDOW_HEIGHT - level_h, min(0, self.offset.y))
        else:
            self.offset.y = (WINDOW_HEIGHT - level_h) // 2

        for sprite in self:
            self.display_surface.blit(sprite.image, sprite.rect.topleft + self.offset)