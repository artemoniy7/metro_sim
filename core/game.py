"""Main game state and scene manager."""
import pygame
from settings import BACKGROUND_COLOR, WINDOW_SIZE, DATA_DIR
from core.train import Train
from core.bot import BotTrain
from core.camera import Camera
from core.line import Line
from core.station_simulation import StationSimulation
from systems.loader import load_json
from systems.renderer import Renderer
from systems.input import InputController
from systems.audio import AudioSystem


class Game:
    def __init__(self, line_file=None, train_file=None, start_position=0.0, end_position=None):
        self.renderer = Renderer()
        self.controls = InputController()
        self.audio = AudioSystem()
        line_path = DATA_DIR / "lines" / (line_file or "line_9.json")
        self.line_data = load_json(line_path, default={})
        self.line = Line(self.line_data)
        configure_station_joints = getattr(self.audio, "configure_station_joint_sounds", None)
        if callable(configure_station_joints):
            configure_station_joints(self.line.stations)
        self.station_simulation = StationSimulation(self.line.stations)
        configure_announcements = getattr(self.audio, "configure_station_announcements", None)
        if callable(configure_announcements):
            configure_announcements(len(self.line.stations))
        train_path = DATA_DIR / "trains" / (train_file or "81-760.json")
        train_data = load_json(train_path, default={})
        self.train = Train(train_data)
        self.train.position = max(0.0, float(start_position))
        self.end_position = float(end_position) if end_position is not None else self.line.path.total_length
        # Close view of the locomotive, with mouse-wheel zoom and consist panning.
        self.camera = Camera(WINDOW_SIZE, zoom=2.8)
        self.elapsed = 0.0
        self.doors_open = False
        # The player's initial position is reserved; AI trains enter every
        # two minutes and are recycled to the line start after the terminus.
        self.bot_trains = []
        self.bot_dispatch_interval = 120.0
        self.bots_enabled = self.train.position <= 0.01
        self.bot_dispatch_timer = 0.0
        self.bot_number = 0
        # Put the first AI train into service immediately; subsequent trains
        # are dispatched every two minutes.
        # AI traffic is enabled only when starting from the line origin.
        if self.train.position <= 0.01:
            self._dispatch_bot()

    def _dispatch_bot(self):
        train_data = load_json(DATA_DIR / "trains" / "81-760.json", default={})
        self.bot_number += 1
        # Keep one bot farther down the line. All other bots queue just beyond
        # Altufyevo's platform, spaced by roughly one train length so they do
        # not spawn inside the player or inside one another.
        first_station = self.line.stations[0]
        station_position = float(first_station.get("position", 0.0))
        if self.bot_number == 1:
            start_position = min(2000.0, self.line.path.total_length - 2500.0)
        else:
            start_position = station_position + 175.0 + (self.bot_number - 2) * 180.0
        bot = BotTrain(train_data, start_position=start_position)
        bot.train.display_name = f"Состав {self.bot_number}"
        self.bot_trains.append(bot)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_v:
            # Doors may only be operated while the train is completely stopped.
            if abs(self.train.speed) < 0.05:
                self.doors_open = not self.doors_open
                self.train.doors_open = self.doors_open
                play_door_sound = getattr(self.audio, "play_door_sound", None)
                if callable(play_door_sound):
                    play_door_sound()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_i:
            toggle_announcer = getattr(self.audio, "toggle_station_announcer", None)
            if callable(toggle_announcer):
                toggle_announcer(self.train, self.line)
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
        # Do not retain a traction command while the doors are open.
        if self.doors_open and self.train.controller_notch > 0:
            self.train.controller_notch = 0
        self.train.doors_open = self.doors_open

        self.bot_dispatch_timer += dt
        if self.bots_enabled and self.bot_dispatch_timer >= self.bot_dispatch_interval:
            self.bot_dispatch_timer -= self.bot_dispatch_interval
            self._dispatch_bot()

        # ALS-ARS sees every train, including the player, before any train
        # updates this frame. This keeps following trains from driving through.
        self.line.traffic_trains = [self.train] + [bot.train for bot in self.bot_trains]
        self.train.update(dt, self.line)
        if self.train.position >= self.end_position:
            self.train.position = self.end_position
            self.train.speed = 0.0
            self.train.controller_notch = 0
        for bot in list(self.bot_trains):
            bot.update(dt, self.line, self.audio,
                       seconds_to_dispatch=self.bot_dispatch_interval - self.bot_dispatch_timer)
            if (bot.state != "dwelling"
                    and bot.train.position >= self.line.path.total_length - 0.5):
                # Remove the train from the terminus and put it at the back of
                # the service queue. The player's own train is never recycled.
                slot_index = self.bot_trains.index(bot)
                self.bot_trains.remove(bot)
                # Recycle into the same staggered queue beyond Altufyevo.
                bot.train.position = (
                    min(2000.0, self.line.path.total_length - 2500.0)
                    if slot_index == 0
                    else float(self.line.stations[0].get("position", 0.0))
                    + 175.0 + slot_index * 180.0
                )
                bot.train.speed = 0.0
                bot.train.acceleration_state = 0.0
                bot.train.controller_notch = 0
                bot.state = "running"
                bot.target_station = None
                bot.dwell_timer = 0.0
                bot.informer_started = False
                bot.informer_timer = 0.0
                bot.closed_for_departure = False
                self.bot_trains.append(bot)
        self.line.traffic_trains = [self.train] + [bot.train for bot in self.bot_trains]
        self.line.update_signals(self.line.traffic_trains)
        self.camera.follow(self.train, self.line.path.total_length)
        self.audio.update(self.train, dt, self.camera)
        self.station_simulation.update(dt, self.train, self.doors_open)
        update_station_ambience = getattr(self.audio, "update_station_ambience", None)
        if callable(update_station_ambience):
            update_station_ambience(self.station_simulation, self.train)
        update_announcer = getattr(self.audio, "update_station_announcer", None)
        if callable(update_announcer):
            update_announcer(self.train, dt)

    def render(self, surface):
        surface.fill(BACKGROUND_COLOR)
        self.renderer.draw_scene(
            surface, self.line, self.train, self.camera, self.elapsed,
            doors_open=self.doors_open,
            door_closing=getattr(self.audio, "door_ring_active", False),
            other_trains=[bot.train for bot in self.bot_trains],
            station_simulation=self.station_simulation,
        )
        if not self.doors_open and self.renderer.door_open_amount <= 0.0:
            stop_door_ring = getattr(self.audio, "stop_door_ring", None)
            if callable(stop_door_ring):
                stop_door_ring()
