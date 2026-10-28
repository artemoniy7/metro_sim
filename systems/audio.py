"""Randomized 81-760 rail-joint sounds and train audio."""
import math
import random
import re
import struct

import pygame

from settings import ASSETS_DIR


class AudioSystem:
    MIN_JOINT_SPACING_M = 25.0
    MAX_JOINT_SPACING_M = 100.0
    REFERENCE_SPEED_MPS = 12.0
    SOUND_FULL_VOLUME_DISTANCE_M = 12.0
    SOUND_CUTOFF_DISTANCE_M = 85.0
    ROLLING_MAX_VOLUME = 0.38
    ENGINE_MAX_VOLUME = 0.48
    BRAKE_VOLUME = 0.62
    BRAKE_NEAR_STOP_SPEED_KMH = 8.0
    BRAKE_SOUND_MIN_SPEED_KMH = 2.0
    BRAKE_REPEAT_INTERVAL_S = 1.25
    BRAKE_VOLUME_SMOOTHING = 2.5

    # Source-image x coordinates for the two points in each wheel pair.
    LOCO_PAIRS = ((345, 621), (1763, 2003))
    CAR_PAIRS = ((193, 464), (1761, 2016))

    def __init__(self):
        self.sounds = {}
        self._group_speeds = {}
        self._last_position = None
        # Joint 0 is at world coordinate 0; other joints are spaced randomly.
        self._joint_positions = {0: 0.0}
        self._next_positive_joint = 1
        self._next_negative_joint = -1
        self._pair_sequences = {}
        self._joint_group_bags = {}
        self._last_joint_group = None
        self._groups = []
        self._loco_image_width = 2048
        self._car_image_width = 2048
        self.rolling_sounds = []
        self.rolling_channels = []
        self.door_channel = None
        self.joint_channels = []
        self.engine_sounds = []
        self.engine_channels = []
        self._engine_volumes = [0.0, 0.0, 0.0]
        self.brake_sounds = {}
        self.door_sound = None
        self.door_ring_sound = None
        self.door_ring_channel = None
        self.brake_release_sound = None
        self.brake_release_channel = None
        self.overspeed_ring_sound = None
        self.overspeed_ring_channel = None
        self.overspeed_ring_active = False
        self.door_ring_active = False
        self._door_ring_timer = 0.0
        self._door_ring_beeping = False
        self._door_ring_volume = 1.0
        self.station_announcements = []
        self.station_announcement_index = 0
        self.station_announcer_enabled = False
        self.station_announcer_pending_start = False
        self.station_announcement_channel = None
        self.brake_channel = None
        self.brake_channel_alt = None
        self._active_brake_channel = 0
        self._brake_target_volume = 0.0
        self._brake_stop_fade_done = False
        self._was_braking = False
        self._played_near_stop = False
        self._last_brake_notch = 0
        self._brake_repeat_timer = 0.0

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()

            rolling_dir = ASSETS_DIR / "sounds" / "train" / "81-760"
            try:
                self.door_sound = pygame.mixer.Sound(str(rolling_dir / "doors" / "door_close.wav"))
            except (pygame.error, OSError):
                self.door_sound = None
            try:
                self.door_ring_sound = pygame.mixer.Sound(
                    str(rolling_dir / "doors" / "ring_doors_temp.wav")
                )
            except (pygame.error, OSError):
                self.door_ring_sound = None
            for filename in ("rolling_low.wav", "rolling_50.wav", "rolling_70.wav"):
                try:
                    self.rolling_sounds.append(pygame.mixer.Sound(str(rolling_dir / filename)))
                except (pygame.error, OSError):
                    self.rolling_sounds.append(None)

            # Rusich and async play together at low speed. Async fades out
            # between 25 and 40 km/h; the next motor layer comes in at higher speed.
            engine_dir = rolling_dir / "engine"
            self.engine_sounds = [
                self._load_engine_sound(engine_dir, "engine_rusich.wav", (72.0, 2.4, 0.35)),
                self._load_engine_sound(engine_dir, "async.wav", (95.0, 3.1, 0.65)),
                self._load_engine_sound(engine_dir, "engine_loud_new.wav", (145.0, 4.0, 0.8)),
            ]

            # Give each sound category its own channels. Track-joint sounds
            # must never steal a channel from the motor, brakes, or announcements.
            pygame.mixer.set_num_channels(max(32, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(13)
            self.rolling_channels = [pygame.mixer.Channel(i) for i in range(3)]
            self.engine_channels = [pygame.mixer.Channel(i) for i in range(3, 6)]
            # Keep both brake channels reserved from automatic joint-sound playback.
            self.brake_channel = pygame.mixer.Channel(6)
            self.brake_channel_alt = pygame.mixer.Channel(7)
            self.station_announcement_channel = pygame.mixer.Channel(8)
            self.door_ring_channel = pygame.mixer.Channel(9)
            self.brake_release_channel = pygame.mixer.Channel(10)
            self.overspeed_ring_channel = pygame.mixer.Channel(11)
            self.door_channel = pygame.mixer.Channel(12)
            self.joint_channels = [pygame.mixer.Channel(i) for i in range(13, 32)]

            # Short squeals are used when braking starts; the longer recordings
            # are reserved for the final few km/h before the train stops.
            brake_dir = rolling_dir / "brake"
            try:
                self.brake_release_sound = pygame.mixer.Sound(
                    str(brake_dir / "013_release.wav")
                )
            except (pygame.error, OSError):
                self.brake_release_sound = None
            try:
                self.overspeed_ring_sound = pygame.mixer.Sound(
                    str(brake_dir / "ring_ao.wav")
                )
            except (pygame.error, OSError):
                self.overspeed_ring_sound = None

            for key, filename in (
                ("gentle", "brake_squeal1.wav"),
                ("medium", "brake_squeal3.wav"),
                ("strong", "brake_squeal1_03.wav"),
                ("near_stop_a", "brake_squeal1_02v2.wav"),
                ("near_stop_b", "brake_squeal1_03.wav"),
            ):
                try:
                    self.brake_sounds[key] = pygame.mixer.Sound(str(brake_dir / filename))
                except (pygame.error, OSError):
                    self.brake_sounds[key] = None

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
                    # Set volume on the playback channel in _play(); setting the
                    # Sound object's volume to zero here mutes it permanently.
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

    @staticmethod
    def _make_motor_fallback(base_hz, modulation_hz, brightness=0.5):
        """Synthesize a quiet loopable electric-motor bed if an asset is missing."""
        mixer_format = pygame.mixer.get_init()
        sample_rate = mixer_format[0] if mixer_format else 22050
        duration_s = 2.0
        sample_count = int(sample_rate * duration_s)
        frames = bytearray()
        for i in range(sample_count):
            t = i / sample_rate
            wobble = math.sin(2.0 * math.pi * modulation_hz * t) * 0.08
            phase = 2.0 * math.pi * base_hz * t + wobble
            value = (
                math.sin(phase)
                + brightness * 0.45 * math.sin(phase * 2.0)
                + brightness * 0.22 * math.sin(phase * 3.0)
                + 0.12 * math.sin(2.0 * math.pi * (base_hz * 0.5) * t)
            ) * 0.18
            # Slightly soften the loop edges to avoid a click at the seam.
            edge = min(1.0, i / (sample_rate * 0.04),
                       (sample_count - i - 1) / (sample_rate * 0.04))
            sample = int(max(-1.0, min(1.0, value * edge)) * 32767)
            frames.extend(struct.pack("<hh", sample, sample))
        return pygame.mixer.Sound(buffer=bytes(frames))

    def _load_engine_sound(self, engine_dir, filename, fallback):
        try:
            return pygame.mixer.Sound(str(engine_dir / filename))
        except (pygame.error, OSError):
            # A missing/empty motor file should not prevent joint sounds loading.
            # Keep async.wav as the real middle-speed layer when it exists.
            try:
                return self._make_motor_fallback(*fallback)
            except (pygame.error, OSError, ValueError, struct.error):
                # Audio fallback is optional; rail-joint audio must still initialize.
                return None

    def play_door_sound(self, volume=1.0):
        """Play a door sound with distance-based volume attenuation."""
        if self.door_sound is not None and self.door_channel is not None and volume > 0.01:
            self.door_channel.stop()
            self.door_channel.set_volume(max(0.0, min(1.0, volume)))
            self.door_channel.play(self.door_sound)

    def configure_station_announcements(self, station_count):
        """Load the ordered next/current announcements for stations 2 onward."""
        self.station_announcements = []
        if pygame.mixer.get_init() is None:
            return

        station_dir = ASSETS_DIR / "stations" / "line_9"
        for station_number in range(2, int(station_count) + 1):
            names = []
            if station_number < int(station_count):
                names.append(f"st_{station_number:02d}_next.mp3")
            names.append(f"st_{station_number:02d}_cur.mp3")
            for filename in names:
                path = station_dir / filename
                if not path.is_file():
                    continue
                try:
                    self.station_announcements.append(
                        (pygame.mixer.Sound(str(path)), filename.endswith("_next.mp3"))
                    )
                except (pygame.error, OSError):
                    continue
        self.station_announcement_index = 0

    def toggle_station_announcer(self, train=None, volume=1.0):
        """Play exactly one next announcement each time I is pressed."""
        channel = self.station_announcement_channel
        if channel is None or not self.station_announcements:
            return

        # If a clip is already playing, I stops it and advances to the next one.
        if channel.get_busy():
            channel.stop()

        if self.station_announcement_index >= len(self.station_announcements):
            self.station_announcement_index = 0

        sound, is_next_station = self.station_announcements[self.station_announcement_index]
        self.station_announcement_index += 1
        volume = max(0.0, min(1.0, volume))
        if volume <= 0.01:
            return
        channel.set_volume(volume)
        channel.play(sound)
        if is_next_station:
            self.start_door_ring(volume=volume)

    def start_door_ring(self, volume=1.0):
        """Start repeating the door-closing beep with distance attenuation."""
        if self.door_ring_sound is None or self.door_ring_channel is None:
            return
        self.door_ring_active = True
        self._door_ring_volume = max(0.0, min(1.0, volume))
        if self._door_ring_volume <= 0.01:
            self.door_ring_active = False
            return
        self._door_ring_timer = 0.0
        self._door_ring_beeping = True
        self.door_ring_channel.stop()
        self.door_ring_channel.set_volume(self._door_ring_volume)
        self.door_ring_channel.play(self.door_ring_sound)

    def stop_door_ring(self):
        self.door_ring_active = False
        self._door_ring_timer = 0.0
        self._door_ring_beeping = False
        if self.door_ring_channel is not None:
            self.door_ring_channel.stop()

    def update_station_announcer(self, train, dt=0.0):
        """Keep the warning beep in a half-second-on / half-second-off rhythm."""
        if not self.door_ring_active:
            return
        self._door_ring_timer += max(0.0, dt)
        if self._door_ring_timer < 0.5:
            return
        self._door_ring_timer -= 0.5
        self._door_ring_beeping = not self._door_ring_beeping
        if self.door_ring_channel is None:
            return
        if self._door_ring_beeping:
            self.door_ring_channel.set_volume(self._door_ring_volume)
            self.door_ring_channel.play(self.door_ring_sound)
        else:
            self.door_ring_channel.stop()

    def _update_overspeed_warning(self, train):
        """Repeat the overspeed alarm until speed is legal or the trip is reset."""
        limit = getattr(train, "current_speed_limit_mps", train.max_speed)
        overspeed = abs(train.speed) > limit
        # Once an overspeed trip triggers, keep the alarm sounding through the
        # full stop. It is silenced only after the driver completes the reset
        # procedure (stop + T3 + B), not merely because speed has fallen.
        should_beep = (
            overspeed
            or getattr(train, "overspeed_timer", 0.0) > 0.0
            or getattr(train, "overspeed_emergency_active", False)
        )
        if should_beep and not self.overspeed_ring_active:
            if self.overspeed_ring_sound is not None and self.overspeed_ring_channel is not None:
                self.overspeed_ring_channel.set_volume(1.0)
                self.overspeed_ring_channel.play(self.overspeed_ring_sound, loops=-1)
            self.overspeed_ring_active = True
        elif not should_beep and self.overspeed_ring_active:
            if self.overspeed_ring_channel is not None:
                self.overspeed_ring_channel.stop()
            self.overspeed_ring_active = False

    def _update_brakes(self, train, dt):
        """Play brake sounds only while the train is actually applying the brakes."""
        speed_kmh = abs(train.speed) * 3.6
        # Brake audio follows the driver command, not brake_applied: the train's
        # physical brakes intentionally react after a delay, but the sound should
        # begin as soon as the driver selects a brake notch.
        braking = bool(
            getattr(train, "emergency_brake_active", False)
            or getattr(train, "controller_notch", 0) < 0
        )
        brake_notch = 4 if train.emergency_brake_active else abs(min(0, train.controller_notch))

        if not braking:
            # Brake-release air sound is only used when releasing brakes at a stop.
            # If the train was already moving, simply stop the brake squeal.
            if self._was_braking:
                for channel in (self.brake_channel, self.brake_channel_alt):
                    if channel is not None and channel.get_busy():
                        channel.fadeout(250)
                if (speed_kmh < 0.2
                        and self.brake_release_sound is not None
                        and self.brake_release_channel is not None):
                    self.brake_release_channel.stop()
                    self.brake_release_channel.set_volume(0.85)
                    self.brake_release_channel.play(self.brake_release_sound)
            self._brake_stop_fade_done = False
            self._was_braking = False
            self._played_near_stop = False
            self._last_brake_notch = 0
            self._brake_repeat_timer = 0.0
            self._brake_target_volume = 0.0
            return

        sound_key = {1: "gentle", 2: "medium", 3: "strong"}.get(brake_notch, "strong")
        target_volume = self.BRAKE_VOLUME * (0.65 + 0.12 * min(brake_notch, 3))
        self._brake_target_volume = target_volume

        if not self._was_braking or brake_notch != self._last_brake_notch:
            self._brake_stop_fade_done = False
            sound = self.brake_sounds.get(sound_key)
            if sound is not None and speed_kmh > self.BRAKE_SOUND_MIN_SPEED_KMH:
                # Alternate channels so a new brake notch can blend in smoothly.
                channels = (self.brake_channel, self.brake_channel_alt)
                next_index = 1 - self._active_brake_channel
                next_channel = channels[next_index]
                current_channel = channels[self._active_brake_channel]
                next_channel.stop()
                next_channel.set_volume(target_volume)
                next_channel.play(sound, fade_ms=350)
                if current_channel.get_busy():
                    current_channel.fadeout(350)
                self._active_brake_channel = next_index
            self._brake_repeat_timer = 0.0
            self._last_brake_notch = brake_notch
        else:
            self._brake_repeat_timer += max(0.0, dt)
            if self._brake_repeat_timer >= self.BRAKE_REPEAT_INTERVAL_S:
                sound = self.brake_sounds.get(sound_key)
                if sound is not None and speed_kmh > self.BRAKE_NEAR_STOP_SPEED_KMH:
                    channels = (self.brake_channel, self.brake_channel_alt)
                    channel = channels[self._active_brake_channel]
                    channel.set_volume(target_volume)
                    channel.play(sound)
                self._brake_repeat_timer = 0.0

        self._was_braking = True

        # Silence brake squeal once the train is effectively stopped.
        if speed_kmh <= self.BRAKE_SOUND_MIN_SPEED_KMH:
            if not self._brake_stop_fade_done:
                for channel in (self.brake_channel, self.brake_channel_alt):
                    if channel is not None and channel.get_busy():
                        channel.fadeout(250)
                self._brake_stop_fade_done = True
            self._played_near_stop = True
            return

        # Play the longer squeal near the stop, but only once per braking event.
        if (not self._played_near_stop
                and self.BRAKE_SOUND_MIN_SPEED_KMH < speed_kmh <= self.BRAKE_NEAR_STOP_SPEED_KMH):
            key = random.choice(("near_stop_a", "near_stop_b"))
            sound = self.brake_sounds.get(key)
            if sound is not None:
                channels = (self.brake_channel, self.brake_channel_alt)
                next_index = 1 - self._active_brake_channel
                next_channel = channels[next_index]
                current_channel = channels[self._active_brake_channel]
                next_channel.stop()
                next_channel.set_volume(min(1.0, self.BRAKE_VOLUME * 1.45))
                next_channel.play(sound, fade_ms=350)
                if current_channel.get_busy():
                    current_channel.fadeout(350)
                self._active_brake_channel = next_index
            self._played_near_stop = True

    def _play(self, group, hit, speed, distance_m):
        sound = self.sounds.get((group, hit))
        if sound is None or speed < 0.5 or distance_m >= self.SOUND_CUTOFF_DISTANCE_M:
            return
        speed_volume = max(0.08, min(0.65, 0.55 * speed / self.REFERENCE_SPEED_MPS))
        distance_volume = 1.0 - max(0.0, distance_m - self.SOUND_FULL_VOLUME_DISTANCE_M) / (
            self.SOUND_CUTOFF_DISTANCE_M - self.SOUND_FULL_VOLUME_DISTANCE_M
        )
        volume = max(0.0, min(0.65, speed_volume * distance_volume))
        # Use a dedicated pool instead of Sound.play(), which can interrupt
        # unrelated sounds when pygame runs out of automatic mixer channels.
        channel = next(
            (candidate for candidate in self.joint_channels if not candidate.get_busy()),
            None,
        )
        if channel is None:
            # Preserve sounds already playing rather than cutting one off.
            return
        channel.set_volume(volume)
        channel.play(sound)

    def _ensure_joint_positions(self, low, high):
        """Generate random track-joint locations covering the requested range."""
        while max(
            coordinate for index, coordinate in self._joint_positions.items() if index >= 0
        ) < high:
            previous = self._joint_positions[self._next_positive_joint - 1]
            spacing = random.uniform(self.MIN_JOINT_SPACING_M, self.MAX_JOINT_SPACING_M)
            self._joint_positions[self._next_positive_joint] = previous + spacing
            self._next_positive_joint += 1

        while min(
            coordinate for index, coordinate in self._joint_positions.items() if index <= 0
        ) > low:
            previous = self._joint_positions[self._next_negative_joint + 1]
            spacing = random.uniform(self.MIN_JOINT_SPACING_M, self.MAX_JOINT_SPACING_M)
            self._joint_positions[self._next_negative_joint] = previous - spacing
            self._next_negative_joint -= 1

    def _crossed_joints(self, previous_world, current_world):
        """Yield random-layout joint indices crossed between two updates."""
        if current_world <= previous_world:
            return
        self._ensure_joint_positions(previous_world, current_world)
        crossed = (
            (joint_index, coordinate)
            for joint_index, coordinate in self._joint_positions.items()
            if previous_world < coordinate <= current_world
        )
        for joint_index, _ in sorted(crossed, key=lambda item: item[1]):
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
            speed_kmh = speed * 3.6
            closest_difference = min(
                abs(self._group_speeds[group] - speed_kmh)
                for group in self._groups
            )
            candidates = [
                group for group in self._groups
                if abs(self._group_speeds[group] - speed_kmh) <= closest_difference + 5.0
            ]

            # Draw from a shuffled bag instead of choosing freely on every hit.
            # This prevents the same few recordings from repeating in a pattern
            # while still keeping recordings close to the train's current speed.
            bag_key = tuple(candidates)
            bag = self._joint_group_bags.get(bag_key)
            if not bag:
                bag = list(candidates)
                random.shuffle(bag)
                # Avoid an identical recording at the boundary between bags.
                if len(bag) > 1 and bag[-1] == self._last_joint_group:
                    bag[0], bag[-1] = bag[-1], bag[0]
                self._joint_group_bags[bag_key] = bag
            group = bag.pop()
            self._last_joint_group = group
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
        traction = 0.0
        traction_allowed = (
            train.controller_notch > 0
            and not train.emergency_brake_active
            and not train.brake_applied
            and getattr(train, "brake_release_timer", 0.0) <= 0.0
            and not getattr(train, "doors_open", False)
        )
        if traction_allowed:
            traction = min(1.0, 0.70 + (train.controller_notch - 1) * 0.10)
        speed_weights = (
            max(0.0, 1.0 - speed_kmh / 22.0),
            1.0 - self._fade_in(speed_kmh, 25.0, 40.0),
            self._fade_in(speed_kmh, 30.0, 48.0),
        )
        smoothing = min(1.0, max(0.0, dt) * 3.5)
        for index, (sound, channel, weight) in enumerate(zip(
            self.engine_sounds, self.engine_channels, speed_weights
        )):
            if sound is None:
                continue
            target = weight * traction
            self._engine_volumes[index] += (target - self._engine_volumes[index]) * smoothing
            channel.set_volume(self.ENGINE_MAX_VOLUME * self._engine_volumes[index])
            if target > 0.01 and not channel.get_busy():
                channel.play(sound, loops=-1)
            elif target <= 0.01 and self._engine_volumes[index] < 0.015:
                if channel.get_busy():
                    channel.stop()
                self._engine_volumes[index] = 0.0

    def update(self, train, dt, camera=None):
        speed = abs(train.speed)
        self._update_overspeed_warning(train)
        self._update_rolling(speed)
        self._update_engine(train, dt)
        self._update_brakes(train, dt)
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
            oldest_position = position - train.consist_length_m - self.MAX_JOINT_SPACING_M
            self._pair_sequences = {
                key: group for key, group in self._pair_sequences.items()
                if self._joint_positions.get(key[1], float("-inf")) >= oldest_position
            }
