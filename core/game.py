"""Main game state and scene manager."""
import pygame
from settings import BACKGROUND_COLOR, WINDOW_SIZE, DATA_DIR
from core.train import Train
from core.camera import Camera
from core.line import Line
from systems.loader import load_json
from systems.renderer import Renderer
from systems.input import InputController


class Game:
    def __init__(self):
        self.renderer = Renderer()
        self.controls = InputController()
        self.line_data = load_json(DATA_DIR / "lines" / "line_1.json", default={})
        self.line = Line(self.line_data)
        # 81-760 is the playable train; its sprites live in assets/trains/81-760/.
        train_data = load_json(DATA_DIR / "trains" / "81-760.json", default={})
        self.train = Train(train_data)
        self.camera = Camera(WINDOW_SIZE, zoom=0.5)
        self.elapsed = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.controls.handle_event(event, self.train)

    def update(self, dt):
        self.elapsed += dt
        self.controls.update(self.train, dt)
        self.train.update(dt, self.line)
        self.camera.follow(self.train, self.line.path.total_length)

    def render(self, surface):
        surface.fill(BACKGROUND_COLOR)
        self.renderer.draw_scene(surface, self.line, self.train, self.camera, self.elapsed)
