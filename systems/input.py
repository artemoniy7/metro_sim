"""Keyboard input for train controls and camera navigation."""
import pygame


class InputController:
    def __init__(self):
        self.emergency = False

    def handle_event(self, event, train):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.emergency = True
            elif event.key == pygame.K_a:
                train.controller_notch = max(-3, train.controller_notch - 1)
            elif event.key == pygame.K_d:
                train.controller_notch = min(4, train.controller_notch + 1)
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            self.emergency = False

    def update(self, train, dt):
        train.emergency_brake_active = self.emergency
