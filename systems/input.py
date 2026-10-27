"""Keyboard input mapping."""
import pygame

class InputController:
    def __init__(self):
        self.emergency = False

    def handle_event(self, event, train):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.emergency = True
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            self.emergency = False

    def update(self, train, dt):
        keys = pygame.key.get_pressed()
        train.throttle = 1.0 if keys[pygame.K_w] or keys[pygame.K_UP] else 0.0
        train.brake = 1.0 if keys[pygame.K_s] or keys[pygame.K_DOWN] else 0.0
        train.emergency_brake_active = self.emergency
        if self.emergency:
            train.brake = 1.0
            train.throttle = 0.0
