#required packages:pygame pytmx
import pygame
from random import randint
from settings import *
from sprites import *
from groups import AllSprites
from support import *
from timer import Timer
from pytmx.util_pygame import load_pygame

# =========================
# Main Game Class
# =========================

SCALE = 6  # Global scaling factor

class Game:
    def __init__(self):
        # --- Basic setup ---
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Jungle Adventure')
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 'play'  # can be 'play', 'dead', or 'win'

        # --- Sprite groups ---
        self.all_sprites = AllSprites()        # for rendering
        self.collision_sprites = pygame.sprite.Group()  # for ground
        self.bullet_sprites = pygame.sprite.Group()     # for bullets
        self.enemy_sprites = pygame.sprite.Group()      # for enemies
        self.goal_sprites = pygame.sprite.Group()       # for the win point

        # --- Score system ---
        self.score = 0
        self.high_score = self.load_high_score()  # load previous best score from file

        # --- Assets and map ---
        self.load_assets()
        self.setup()

        # --- Background music ---
        try:
            if 'music' in self.audio:
                self.audio['music'].play(loops=-1)
        except Exception as e:
            print("Your computer environment may not support this music file format.:(")
            print(f"Details: {e}")

        # --- Enemy spawn timer (spawns bees continuously) ---
        self.bee_timer = Timer(500, func=self.create_bee, autostart=True, repeat=True)

    # =========================
    # Score Management
    # =========================
    def load_high_score(self):
        """Load saved high score from file"""
        try:
            with open("score.txt", "r", encoding="utf-8") as f:
                return int(f.read().strip() or 0)
        except Exception:
            return 0

    def save_high_score(self):
        """Save the highest score achieved"""
        if self.score > self.high_score:
            try:
                with open("score.txt", "w", encoding="utf-8") as f:
                    f.write(str(self.score))
                self.high_score = self.score
            except Exception as e:
                print("WARN: save_high_score:", e)

    # =========================
    # Bullet and Enemy Handling
    # =========================
    def _bullet_hits(self, bullet, hit_sprites):
        """Handle bullet hitting enemies"""
        if 'impact' in self.audio:
            self.audio['impact'].play()
        bullet.kill()
        for s in hit_sprites:
            s.destroy()
            self.score += 1  # increase score per enemy defeated

    def create_bee(self):
        """Spawn a flying bee enemy"""
        Bee(
            frames=self.bee_frames,
            pos=((self.level_width + WINDOW_WIDTH), randint(0, self.level_height)),
            groups=(self.all_sprites, self.enemy_sprites),
            speed=randint(300, 500)
        )

    def create_bullet(self, pos, direction):
        """Create and shoot a bullet"""
        x = pos[0] + direction * 34 if direction == 1 else pos[0] + direction * 34 - self.bullet_surf.get_width()
        Bullet(self.bullet_surf, (x, pos[1]), direction,
               (self.all_sprites, self.bullet_sprites),
               enemy_group=self.enemy_sprites, on_hit=self._bullet_hits)
        Fire(self.fire_surf, pos, self.all_sprites, self.player)
        if 'shoot' in self.audio:
            self.audio['shoot'].play()

    # =========================
    # Asset Loading
    # =========================
    def load_assets(self):
        """Load images, sounds, and animations"""
        sf = SCALE

        # Player animations (scaled)
        self.player_anims = {
            state: [pygame.transform.scale(img, (img.get_width() * sf, img.get_height() * sf))
                    for img in import_folder('images', 'player', state)]
            for state in ['idle', 'run', 'jump']
        }

        # Bullets & fire (original size)
        self.bullet_surf = import_image('images', 'gun', 'bullet')
        self.fire_surf = import_image('images', 'gun', 'fire')

        # Enemies (scaled)
        self.bee_frames = [pygame.transform.scale(img, (img.get_width() * sf, img.get_height() * sf))
                           for img in import_folder('images', 'enemies', 'bee')]
        self.snake_frames = [pygame.transform.scale(img, (img.get_width() * sf, img.get_height() * sf))
                             for img in import_folder('images', 'enemies', 'snake')]

        # Load sound effects and music
        self.audio = audio_importer('audio')

    # =========================
    # Map Setup
    # =========================
    def setup(self):
        """Load and place all map tiles and objects"""
        sf = SCALE
        tmx_path = p('data', 'maps', 'world.tmx')
        if not tmx_path.exists():
            raise FileNotFoundError(f"TMX not found: {tmx_path}")
        tmx_map = load_pygame(str(tmx_path))

        # Calculate scaled map dimensions
        self.level_width = tmx_map.width * TILE_SIZE * sf
        self.level_height = tmx_map.height * TILE_SIZE * sf

        def scaled(img):
            return pygame.transform.scale(img, (img.get_width() * sf, img.get_height() * sf))

        # --- Layers ---
        # Background layer
        if 'background' in [l.name for l in tmx_map.layers]:
            for x, y, image in tmx_map.get_layer_by_name('background').tiles():
                Sprite((x * TILE_SIZE * sf, y * TILE_SIZE * sf), scaled(image), self.all_sprites)

        # Main (solid ground + walls)
        for x, y, image in tmx_map.get_layer_by_name('Main').tiles():
            wx, wy = x * TILE_SIZE * sf, y * TILE_SIZE * sf
            disp_img = scaled(image)
            Sprite((wx, wy), disp_img, self.all_sprites)
            CollisionTile((wx, wy), disp_img, self.collision_sprites)

        # Decoration layer
        if 'Decoration' in [l.name for l in tmx_map.layers]:
            for x, y, image in tmx_map.get_layer_by_name('Decoration').tiles():
                Sprite((x * TILE_SIZE * sf, y * TILE_SIZE * sf), scaled(image), self.all_sprites)

        # --- Objects ---
        for obj in tmx_map.get_layer_by_name('object'):
            if obj.name == 'Player':
                self.player = Player((obj.x * sf, obj.y * sf),
                                     self.all_sprites, self.collision_sprites,
                                     self.player_anims, self.create_bullet)
            elif obj.name == 'Snake':
                rect = pygame.Rect(int(obj.x * sf), int(obj.y * sf), int(obj.width * sf), int(obj.height * sf))
                Snake(self.snake_frames, rect, (self.all_sprites, self.enemy_sprites))
            elif obj.name == 'goal':
                goal_rect = pygame.Rect(int(obj.x * sf), int(obj.y * sf), int(obj.width * sf), int(obj.height * sf))
                Goal(goal_rect, (self.goal_sprites,))

    # =========================
    # Collision Logic
    # =========================
    def collision(self):
        """Handle all collision interactions"""
        # Bullets -> Enemies
        for bullet in self.bullet_sprites:
            hits = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
            if hits:
                if 'impact' in self.audio: self.audio['impact'].play()
                bullet.kill()
                for sprite in hits:
                    sprite.destroy()

        # Enemies -> Player (Death)
        if self.state == 'play' and pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.save_high_score()
            self.state = 'dead'

        # Player -> Goal (Win)
        if self.state == 'play' and pygame.sprite.spritecollide(self.player, self.goal_sprites, False):
            self.save_high_score()
            self.state = 'win'

    # =========================
    # Overlays (Game Over / Win)
    # =========================
    def draw_game_over(self):
        """Display death screen overlay"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.display_surface.blit(overlay, (0, 0))

        # Title
        title_font = pygame.font.Font(None, 120)
        title_surf = title_font.render("YOU DIED", True, (220, 60, 60))
        self.display_surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 - 70)))

        # Score info
        info_font = pygame.font.Font(None, 40)
        score_text = info_font.render(f"Score: {self.score}    High Score: {self.high_score}", True, (255, 255, 255))
        self.display_surface.blit(score_text, score_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2)))

        # Restart instructions
        hint_font = pygame.font.Font(None, 32)
        hint = hint_font.render("Press R to restart   /   Press ESC to exit", True, (240, 240, 240))
        self.display_surface.blit(hint, hint.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 50)))

    def draw_game_win(self):
        """Display victory screen overlay"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.display_surface.blit(overlay, (0, 0))

        title_font = pygame.font.Font(None, 120)
        title = title_font.render("YOU WIN!", True, (80, 220, 120))
        self.display_surface.blit(title, title.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 - 70)))

        info_font = pygame.font.Font(None, 40)
        score_text = info_font.render(f"Score: {self.score}    High Score: {self.high_score}", True, (255, 255, 255))
        self.display_surface.blit(score_text, score_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2)))

        hint_font = pygame.font.Font(None, 32)
        hint = hint_font.render("Press R to restart   /   Press ESC to exit", True, (240, 240, 240))
        self.display_surface.blit(hint, hint.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 50)))

    # =========================
    # Level Reset
    # =========================
    def reset_level(self):
        """Clear all sprites and reload the level"""
        self.save_high_score()
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        self.goal_sprites.empty()

        self.score = 0
        self.setup()
        self.bee_timer = Timer(500, func=self.create_bee, autostart=True, repeat=True)
        self.state = 'play'

    # =========================
    # Main Game Loop
    # =========================
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(FRAMERATE) / 1000  # time delta per frame

            # --- Handle events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_high_score()
                    self.running = False
                if self.state in ('dead', 'win') and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_level()
                    if event.key in (pygame.K_ESCAPE, pygame.K_e):
                        self.save_high_score()
                        self.running = False

            # --- Game logic per state ---
            if self.state == 'play':
                self.bee_timer.update()
                self.all_sprites.update(dt)
                self.collision()
                self.all_sprites.draw(self.player.rect.center, (self.level_width, self.level_height))

                # Draw current score
                ui_font = pygame.font.Font(None, 40)
                score_display = ui_font.render(f"Score: {self.score}", True, (255, 255, 255))
                self.display_surface.blit(score_display, (20, 20))

            elif self.state == 'dead':
                self.all_sprites.draw(self.player.rect.center, (self.level_width, self.level_height))
                self.draw_game_over()

            elif self.state == 'win':
                self.all_sprites.draw(self.player.rect.center, (self.level_width, self.level_height))
                self.draw_game_win()

            pygame.display.update()

        pygame.quit()


# =========================
# Entry Point
# =========================
if __name__ == '__main__':
    game = Game()
    game.run()