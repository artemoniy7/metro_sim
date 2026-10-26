"""Shared configuration and paths."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"
SAVES_DIR = ROOT_DIR / "saves"
WINDOW_SIZE = (1280, 720)
WINDOW_TITLE = "Metro Sim"
FPS = 60
PIXELS_PER_METER = 4
BACKGROUND_COLOR = (18, 22, 29)
