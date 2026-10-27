"""Randomized 81-760 rail-joint sounds triggered by individual wheel points."""
import random
import re

import pygame

from settings import ASSETS_DIR


class AudioSystem:
    JOINT_SPACING_M = 25.0
    REFERENCE_SPEED_MPS = 12.0

    # Source-image x coordinates for the two points in each wheel pair.
    LOCO_PAIRS = ((345, 621), (1763, 2003))
    CAR_PAIRS = ((193, 464), (1761, 2016))

    def __init__(self):
        self.sounds = {}
        self._last_position = None
        self._pair_sequences = {}
        self._groups = []
        self._loco_image_width = 2048
        self._car_image_width = 2048

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()

            sound_dir = ASSETS_DIR / "sounds" / "train" / "81-760" / "joint"
            pattern = re.compile(r"joint_st_(\d{2})_([12])\.(?:wav|mp3)$", re.IGNORECASE)
            for path in sorted(sound_dir.iterdir()):
                match = pattern.fullmatch(path.name)
                if not match:
                    continue
                group, hit = int(match.group(1)), int(match.group(2))
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(0.0)
                    self.sounds[(group, hit)] = sound
                except (pygame.error, OSError):
                    continue

            self._groups = sorted({group for group, hit in self.sounds if hit == 1 and (group, 2) in self.sounds})

            # Use the actual sprite dimensions so the wheel coordinates match
            # the points drawn by Renderer, even if the source image changes.
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

    def _play(self, group, hit, speed):
        sound = self.sounds.get((group, hit))
        if sound is None or speed < 0.5:
            return
        sound.set_volume(max(0.08, min(0.65, 0.55 * speed / self.REFERENCE_SPEED_MPS)))
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

    def _process_pair(self, pair_key, offsets, previous_position, position, speed):
        # The smaller offset reaches a track joint first as the train moves.
        ordered_offsets = sorted(offsets)
        first_offset, second_offset = ordered_offsets
        previous_first = previous_position + first_offset
        current_first = position + first_offset
        previous_second = previous_position + second_offset
        current_second = position + second_offset

        for joint_index in self._crossed_joints(previous_first, current_first):
            if not self._groups:
                return
            group = random.choice(self._groups)
            self._pair_sequences[(pair_key, joint_index)] = group
            self._play(group, 1, speed)

        for joint_index in self._crossed_joints(previous_second, current_second):
            group = self._pair_sequences.pop((pair_key, joint_index), None)
            if group is not None:
                self._play(group, 2, speed)

    def update(self, train, dt):
        if not self.sounds:
            return

        position = train.position
        if self._last_position is None:
            self._last_position = position
            return

        previous_position = self._last_position
        self._last_position = position
        speed = abs(train.speed)
        if position <= previous_position:
            return

        # Locomotive: position is referenced to its right/front edge in the
        # renderer; convert source-image x points into distances behind it.
        for pair_index, pair in enumerate(self.LOCO_PAIRS):
            offsets = tuple(
                (self._loco_image_width - x) / self._loco_image_width * train.loco_length_m
                for x in pair
            )
            self._process_pair(("loco", pair_index), offsets,
                               previous_position, position, speed)

        # Wagons are laid out to the right of the locomotive in the side view.
        # Their world-position offsets therefore continue in the negative direction.
        for wagon in train.wagons:
            if wagon.is_loco:
                continue
            for pair_index, pair in enumerate(self.CAR_PAIRS):
                offsets = tuple(
                    -((wagon.index - 1) * train.car_length_m)
                    - (x / self._car_image_width) * train.car_length_m
                    for x in pair
                )
                self._process_pair((f"wagon_{wagon.index}", pair_index), offsets,
                                   previous_position, position, speed)

        # Avoid keeping stale pair IDs if an audio file is missing or the train
        # has already passed a long section of track.
        if len(self._pair_sequences) > 512:
            cutoff = int((position - train.consist_length_m) // self.JOINT_SPACING_M) - 4
            self._pair_sequences = {
                key: group for key, group in self._pair_sequences.items()
                if key[1] >= cutoff
            }
