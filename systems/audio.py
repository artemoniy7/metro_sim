"""Randomized 81-760 rail-joint sounds triggered by individual wheel points."""
import random
import re

import pygame

from settings import ASSETS_DIR


class AudioSystem:
    JOINT_SPACING_M = 50.0
    REFERENCE_SPEED_MPS = 12.0
    SOUND_FULL_VOLUME_DISTANCE_M = 12.0
    SOUND_CUTOFF_DISTANCE_M = 85.0
    ROLLING_MAX_VOLUME = 0.38
    ENGINE_MAX_VOLUME = 0.48

    # Source-image x coordinates for the two points in each wheel pair.
    LOCO_PAIRS = ((345, 621), (1763, 2003))
    CAR_PAIRS = ((193, 464), (1761, 2016))

    def __init__(self):
        self.sounds = {}
        self._group_speeds = {}
        self._last_position = None
        self._pair_sequences = {}
        self._groups = []
        self._loco_image_width = 2048
        self._car_image_width = 2048
        self.rolling_sounds = []
        self.rolling_channels = []
        self.engine_sounds = []
        self.engine_channels = []
        self._engine_volumes = [0.0, 0.0, 0.0, 0.0]

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()

            rolling_dir = ASSETS_DIR / "sounds" / "train" / "81-760"
            for filename in ("rolling_low.wav", "rolling_50.wav", "rolling_70.wav"):
                try:
                    self.rolling_sounds.append(pygame.mixer.Sound(str(rolling_dir / filename)))
                except (pygame.error, OSError):
                    self.rolling_sounds.append(None)

            # Layer the Rusich sound and async.wav at launch, then blend into
            # the louder 81-760 motor recordings as speed increases.
            engine_dir = rolling_dir / "engine"
            for filename in (
                "engine_rusich.wav",
                "async.wav",
                "engine_loud_new2_clean.wav",
                "engine_loud_new2_clean_high.wav",
            ):
                try:
                    self.engine_sounds.append(pygame.mixer.Sound(str(engine_dir / filename)))
                except (pygame.error, OSError):
                    self.engine_sounds.append(None)

            # Dedicated channels keep rolling and engine loops separate from joint effects.
            pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(6)
            self.rolling_channels = [pygame.mixer.Channel(i) for i in range(3)]
            self.engine_channels = [pygame.mixer.Channel(i) for i in range(3, 6)]

            sound_dir = rolling_dir / "joint"
            # New exterior recordings encode the recording speed in the filename:
            # joint_stl760_<group>_<hit>_<speed>.wav
            pattern = re.compile(
                r"joint_stl760_(\d+)_([12])_(\d+)\.(?:wav|mp3)$",
                re.IGNORECASE,
            )
            for path in sorted(sound_dir.iterdir()):
                match = pattern.fullmatch(path.name)
                if not match:
                    continue
                group, hit, recorded_speed = map(int, match.groups())
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(0.0)
                    self.sounds[(group, hit)] = sound
                    self._group_speeds[group] = recorded_speed
                except (pygame.error, OSError):
                    continue

            self._groups = sorted({
                group for group, hit in self.sounds
                if hit == 1 and (group, 2) in self.sounds
            })

            loco_path = ASSETS_DIR / "trains" / "81-760" / "81-760-loco.png"
            car_path = ASSETS_DIR / "trains" / "81-760" / "81-760-car.png"
            try:
                self._loco_image_width = pygame.image.load(str(loco_path)).get_width()
            except (pygame.error, OSError):
                pass
            try:
                self._car_image_width = pygame.image.load(str(car_path)).get_width()
            except (pygame.error, OSError):
                pass
        except (pygame.error, OSError):
            # Sound is optional; the simulation should still start without it.
            self.sounds = {}

    def _play(self, group, hit, speed, distance_m):
        sound = self.sounds.get((group, hit))
        if sound is None or speed < 0.5 or distance_m >= self.SOUND_CUTOFF_DISTANCE_M:
            return
        speed_volume = max(0.08, min(0.65, 0.55 * speed / self.REFERENCE_SPEED_MPS))
        distance_volume = 1.0 - max(0.0, distance_m - self.SOUND_FULL_VOLUME_DISTANCE_M) / (
            self.SOUND_CUTOFF_DISTANCE_M - self.SOUND_FULL_VOLUME_DISTANCE_M
        )
        sound.set_volume(max(0.0, min(0.65, speed_volume * distance_volume)))
        sound.play()

    @staticmethod
    def _crossed_joints(previous_world, current_world):
        """Yield track-joint indices crossed between two updates."""
        if current_world <= previous_world:
            return
        first = int(previous_world // AudioSystem.JOINT_SPACING_M) + 1
        last = int(current_world // AudioSystem.JOINT_SPACING_M)
        for joint_index in range(first, last + 1):
            yield joint_index

    def _process_pair(self, pair_key, offsets, previous_position, position,
                      speed, distance_m):
        ordered_offsets = sorted(offsets)
        first_offset, second_offset = ordered_offsets
        previous_first = previous_position + first_offset
        current_first = position + first_offset
        previous_second = previous_position + second_offset
        current_second = position + second_offset

        for joint_index in self._crossed_joints(previous_first, current_first):
            if not self._groups:
                return
            # Prefer samples recorded near the train's current speed, while
            # retaining variation between recordings at that speed.
            speed_kmh = speed * 3.6
            closest_difference = min(
                abs(self._group_speeds[group] - speed_kmh)
                for group in self._groups
            )
            candidates = [
                group for group in self._groups
                if abs(self._group_speeds[group] - speed_kmh) <= closest_difference + 5.0
            ]
            group = random.choice(candidates)
            self._pair_sequences[(pair_key, joint_index)] = group
            self._play(group, 1, speed, distance_m)

        for joint_index in self._crossed_joints(previous_second, current_second):
            group = self._pair_sequences.pop((pair_key, joint_index), None)
            if group is not None:
                self._play(group, 2, speed, distance_m)

    @staticmethod
    def _fade_in(speed_kmh, start, end):
        return max(0.0, min(1.0, (speed_kmh - start) / (end - start)))

    def _update_rolling(self, speed_mps):
        speed_kmh = speed_mps * 3.6
        # Start each layer 10 km/h before its nominal range, then crossfade
        # gradually so the next sound is already present before the threshold.
        volumes = (
            self._fade_in(speed_kmh, 20.0, 30.0)
            * (1.0 - self._fade_in(speed_kmh, 40.0, 50.0)),
            self._fade_in(speed_kmh, 40.0, 50.0)
            * (1.0 - self._fade_in(speed_kmh, 60.0, 70.0)),
            self._fade_in(speed_kmh, 60.0, 70.0),
        )
        for sound, channel, weight in zip(
            self.rolling_sounds, self.rolling_channels, volumes
        ):
            if sound is None:
                continue
            if weight <= 0.0:
                if channel.get_busy():
                    channel.stop()
                continue
            channel.set_volume(self.ROLLING_MAX_VOLUME * weight)
            if not channel.get_busy():
                channel.play(sound, loops=-1)

    def _update_engine(self, train, dt):
        speed_kmh = abs(train.speed) * 3.6
        # The motor is audible under traction; easing the volume down on coast/braking
        # avoids an abrupt cut when the controller returns to zero.
        traction = 0.0
        if train.controller_notch > 0 and not train.emergency_brake_active:
            traction = min(1.0, 0.70 + (train.controller_notch - 1) * 0.10)

        # Both launch sounds begin immediately. Rusich gives the initial
        # low-speed motor character; async starts fading out at about 25 km/h and fades away gradually by 45 km/h.
        # The louder 81-760 layers then crossfade in as speed rises.
        speed_weights = (
            max(0.0, 1.0 - speed_kmh / 22.0),
            max(0.0, min(1.0, (45.0 - speed_kmh) / (45.0 - 25.0))),
            self._fade_in(speed_kmh, 10.0, 25.0)
            * (1.0 - self._fade_in(speed_kmh, 45.0, 58.0)),
            self._fade_in(speed_kmh, 35.0, 55.0),
        )
        smoothing = min(1.0, max(0.0, dt) * 3.5)

        for index, (sound, channel, weight) in enumerate(zip(
            self.engine_sounds, self.engine_channels, speed_weights
        )):
            if sound is None:
                continue
            target = weight * traction
            self._engine_volumes[index] += (target - self._engine_volumes[index]) * smoothing
            volume = self.ENGINE_MAX_VOLUME * self._engine_volumes[index]
            channel.set_volume(volume)
            if target > 0.01 and not channel.get_busy():
                channel.play(sound, loops=-1)
            elif target <= 0.01 and self._engine_volumes[index] < 0.015:
                if channel.get_busy():
                    channel.stop()
                self._engine_volumes[index] = 0.0

    def update(self, train, dt, camera=None):
        speed = abs(train.speed)
        self._update_rolling(speed)
        self._update_engine(train, dt)
        if not self.sounds:
            return

        position = train.position
        if self._last_position is None:
            self._last_position = position
            return

        previous_position = self._last_position
        self._last_position = position
        if position <= previous_position:
            return

        camera_offset = getattr(camera, "consist_offset_m", 0.0)
        loco_distance = abs(camera_offset)
        for pair_index, pair in enumerate(self.LOCO_PAIRS):
            offsets = tuple(
                (self._loco_image_width - x) / self._loco_image_width * train.loco_length_m
                for x in pair
            )
            self._process_pair(("loco", pair_index), offsets,
                               previous_position, position, speed, loco_distance)

        for wagon in train.wagons:
            if wagon.is_loco:
                continue
            for pair_index, pair in enumerate(self.CAR_PAIRS):
                offsets = tuple(
                    -((wagon.index - 1) * train.car_length_m)
                    - (x / self._car_image_width) * train.car_length_m
                    for x in pair
                )
                wagon_center = wagon.index * train.car_length_m
                distance = abs(wagon_center - camera_offset)
                self._process_pair((f"wagon_{wagon.index}", pair_index), offsets,
                                   previous_position, position, speed, distance)

        if len(self._pair_sequences) > 512:
            cutoff = int((position - train.consist_length_m) // self.JOINT_SPACING_M) - 4
            self._pair_sequences = {
                key: group for key, group in self._pair_sequences.items()
                if key[1] >= cutoff
            }
