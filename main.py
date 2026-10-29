"""Entry point for Metro Sim."""
import pygame
from settings import WINDOW_SIZE, WINDOW_TITLE, FPS
from systems.menu import MainMenu


def main():
    pygame.init()
    # Borderless desktop-sized window avoids exclusive fullscreen flicker on Windows.
    desktop = pygame.display.Info()
    screen = pygame.display.set_mode((desktop.current_w, desktop.current_h), pygame.NOFRAME)
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    menu = MainMenu(WINDOW_SIZE)
    game = None
    scene = "menu"
    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if scene == "menu":
                action = menu.handle_event(event)
                if action == "quit":
                    running = False
            elif game is not None:
                game.handle_event(event)

        if scene == "menu":
            action = menu.update(dt)
            if action == "start":
                from core.game import Game
                game = Game()
                scene = "game"
            elif action == "quit":
                running = False
            menu.render(screen)
        elif game is not None:
            game.update(dt)
            game.render(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
