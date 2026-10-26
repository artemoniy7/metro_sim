"""Entry point for Metro Sim."""
import pygame
from settings import WINDOW_SIZE, WINDOW_TITLE, FPS
from core.game import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    game = Game()
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            game.handle_event(event)
        game.update(dt)
        game.render(screen)
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()
