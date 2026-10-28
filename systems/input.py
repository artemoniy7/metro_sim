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
            elif event.key == pygame.K_b:
                # Reset the overspeed trip only after stopping, selecting T3,
                # and acknowledging vigilance with B.
                if abs(train.speed) < 0.05 and train.controller_notch == -3:
                    train.overspeed_emergency_active = False
                    train.overspeed_timer = 0.0
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            self.emergency = False

    def update(self, train, dt):
        train.manual_emergency_brake_active = self.emergency
