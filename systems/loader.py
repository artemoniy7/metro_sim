"""Load JSON data and optional images safely."""
import json
from pathlib import Path
import pygame

def load_json(path, default=None):
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default

def load_image(path, size=None):
    try:
        image = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.smoothscale(image, size) if size else image
    except (pygame.error, OSError):
        return None
