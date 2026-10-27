"""Main game state and scene manager."""
import pygame
from settings import BACKGROUND_COLOR, WINDOW_SIZE, DATA_DIR
from core.train import Train
from core.camera import Camera
from core.line import Line
from systems.loader import load_json
from systems.renderer import Renderer
from systems.input import InputController
from systems.audio import AudioSystem


class Game:
    def __init__(self):
        self.renderer = Renderer()
        self.controls = InputController()
        self.audio = AudioSystem()
        self.line_data = load_json(DATA_DIR / "lines" / "line_1.json", default={})
        self.line = Line(self.line_data)
        train_data = load_json(DATA_DIR / "trains" / "81-760.json", default={})
        self.train = Train(train_data)
        # Close view of the locomotive, with mouse-wheel zoom and consist panning.
        self.camera = Camera(WINDOW_SIZE, zoom=2.8)
        self.elapsed = 0.0
        self.doors_open = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_v:
            self.doors_open = not self.doors_open
        elif event.type == pygame.MOUSEWHEEL:
            self.camera.zoom_by(event.y * 0.15)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.camera.zoom_by(0.15)
            elif event.button == 5:
                self.camera.zoom_by(-0.15)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            self.camera.pan(-1, self.train)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            self.camera.pan(1, self.train)

        self.controls.handle_event(event, self.train)

    def update(self, dt):
        self.elapsed += dt
        self.controls.update(self.train, dt)
        self.train.update(dt, self.line)
        self.camera.follow(self.train, self.line.path.total_length)
        self.audio.update(self.train, dt, self.camera)

    def render(self, surface):
        surface.fill(BACKGROUND_COLOR)
        self.renderer.draw_scene(surface, self.line, self.train, self.camera, self.elapsed,
                                 doors_open=self.doors_open)
