from pathlib import Path
import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def p(*parts):
    return PROJECT_ROOT.joinpath(*parts)

def import_image(*path, format='png', alpha=True):
    full_path = p(*path).with_suffix('.' + format)
    surf = pygame.image.load(full_path)
    return surf.convert_alpha() if alpha else surf.convert()

def import_folder(*path):
    frames, folder = [], p(*path)
    for name in sorted(folder.iterdir(), key=lambda p: int(p.stem)):
        if name.is_file():
            frames.append(pygame.image.load(name).convert_alpha())
    return frames

def audio_importer(*path):
    audio, folder = {}, p(*path)
    for f in folder.iterdir():
        if f.is_file():
            try:
                audio[f.stem] = pygame.mixer.Sound(str(f))
            except Exception:
                pass
    return audio