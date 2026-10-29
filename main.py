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
                line_meta, line_path, line_data = menu.selected_line
                train_path, train_data = menu.selected_train
                stations = line_data.get("stations", [])
                end_index = min(menu.end_index, len(stations) - 1)
                end_position = float(stations[end_index].get("position", line_data.get("total_length_m", 0)))
                game = Game(
                    line_file=line_path.name,
                    train_file=train_path.name,
                    start_position=menu.selected_start_position,
                    end_position=end_position,
                )
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
