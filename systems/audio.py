"""Train wheel sounds tied to movement along the track."""
from pathlib import Path
import math

import pygame
import numpy as np

from settings import ASSETS_DIR


class AudioSystem:
    # Approximate rail-joint spacing and the distance between the two axle hits.
    JOINT_SPACING_M = 25.0
    AXLE_SPACING_M = 2.5
    REFERENCE_SPEED_MPS = 12.0

    def __init__(self):
        self.joint_sound = None
        self._source_samples = None
        self._variants = {}
        self._next_joint = None
        self._pending_hits = []

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            path = ASSETS_DIR / "sounds" / "train" / "joint.mp3"
            self.joint_sound = pygame.mixer.Sound(str(path))
            self.joint_sound.set_volume(0.55)
            self._source_samples = pygame.sndarray.array(self.joint_sound)
        except (pygame.error, OSError, ImportError, ValueError):
            # The simulation can still run if audio or NumPy is unavailable.
            self.joint_sound = None
            self._source_samples = None

    def _sound_for_speed(self, speed):
        if self.joint_sound is None:
            return None

        # Cache pitch/speed variants in 0.1x increments to avoid rebuilding
        # the audio buffer on every wheel hit.
        rate = max(0.5, min(2.0, speed / self.REFERENCE_SPEED_MPS))
        rate = round(rate * 10) / 10
        if rate not in self._variants:
            if self._source_samples is None or rate == 1.0:
                self._variants[rate] = self.joint_sound
            else:
                source = self._source_samples
                new_length = max(1, round(len(source) / rate))
                indices = np.linspace(0, len(source) - 1, new_length).astype(np.int64)
                samples = source[indices].copy()
                self._variants[rate] = pygame.sndarray.make_sound(samples)
        return self._variants[rate]

    def _play_joint(self, speed):
        if self.joint_sound is None or speed < 0.5:
            return
        sound = self._sound_for_speed(speed)
        if sound is not None:
            # Faster movement raises the pitch and shortens the sound.
            sound.set_volume(max(0.12, min(0.65, 0.55 * speed / self.REFERENCE_SPEED_MPS)))
            sound.play()

    def update(self, train, dt):
        if self.joint_sound is None:
            return

        position = train.position
        if self._next_joint is None:
            self._next_joint = (
                math.floor(position / self.JOINT_SPACING_M) + 1
            ) * self.JOINT_SPACING_M

        # Each joint produces two wheel/axle passes, separated by 2.5 m.
        while self._next_joint <= position:
            self._play_joint(abs(train.speed))
            self._pending_hits.append(self._next_joint + self.AXLE_SPACING_M)
            self._next_joint += self.JOINT_SPACING_M

        while self._pending_hits and self._pending_hits[0] <= position:
            self._pending_hits.pop(0)
            self._play_joint(abs(train.speed))
