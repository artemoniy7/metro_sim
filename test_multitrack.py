"""Isolated multi-track / switchyard prototype. Run: python test_multitrack.py"""
import math
import pygame

WIDTH, HEIGHT = 1280, 720
FPS = 60
BG = (18, 22, 29)
RAIL = (105, 116, 128)
SLEEPER = (67, 76, 87)
TEXT = (230, 235, 242)
ACCENT = (90, 190, 255)
TRAIN = (224, 229, 232)
WINDOW = (40, 57, 72)


def bezier(p0, p1, p2, p3, steps=80):
    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]
        points.append((x, y))
    return points


def path_lengths(points):
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.dist(a, b))
    return lengths


def point_at(points, lengths, distance):
    distance = max(0.0, min(distance, lengths[-1]))
    for i in range(1, len(lengths)):
        if distance <= lengths[i]:
            span = lengths[i] - lengths[i - 1]
            t = 0 if span == 0 else (distance - lengths[i - 1]) / span
            a, b = points[i - 1], points[i]
            return (a[0] + (b[0] - a[0]) * t,
                    a[1] + (b[1] - a[1]) * t)
    return points[-1]


def draw_track(surface, points, color=RAIL, width=3):
    # Two rails and sleepers, following the same centre line.
    for i in range(0, len(points), 5):
        x, y = points[i]
        pygame.draw.line(surface, SLEEPER, (x, y - 11), (x, y + 11), 3)
    pygame.draw.lines(surface, color, False,
                      [(int(x), int(y - 6)) for x, y in points], width)
    pygame.draw.lines(surface, color, False,
                      [(int(x), int(y + 6)) for x, y in points], width)


def draw_train(surface, points, lengths, front_distance, cars=4, color=TRAIN):
    # Each car is placed behind the previous one along the route, so it follows curves.
    for index in reversed(range(cars)):
        d = front_distance - index * 47
        if d < 0:
            continue
        x, y = point_at(points, lengths, d)
        before = point_at(points, lengths, max(0, d - 2))
        after = point_at(points, lengths, min(lengths[-1], d + 2))
        angle = math.atan2(after[1] - before[1], after[0] - before[0])
        body = pygame.Surface((62, 27), pygame.SRCALPHA)
        pygame.draw.rect(body, color, (1, 2, 60, 23), border_radius=5)
        pygame.draw.rect(body, WINDOW, (9, 5, 10, 7), border_radius=2)
        pygame.draw.rect(body, WINDOW, (23, 5, 10, 7), border_radius=2)
        pygame.draw.rect(body, WINDOW, (37, 5, 10, 7), border_radius=2)
        pygame.draw.rect(body, (80, 94, 106), (1, 19, 60, 4), border_radius=2)
        rotated = pygame.transform.rotate(body, -math.degrees(angle))
        surface.blit(rotated, rotated.get_rect(center=(int(x), int(y))))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Metro Sim — тест нескольких путей")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22)
    small = pygame.font.SysFont("arial", 16)

    # Main line and two selectable branch connectors.
    main_track = [(40, 360), (1240, 360)]
    left_branch = bezier((650, 360), (760, 360), (760, 270), (900, 270))
    right_branch = bezier((650, 360), (760, 360), (760, 450), (900, 450))
    left_route = [(40, 360)] + left_branch[1:] + [(1240, 270)]
    right_route = [(40, 360)] + right_branch[1:] + [(1240, 450)]
    routes = [left_route, right_route]
    route_lengths = [path_lengths(p) for p in routes]
    active_route = 0
    distance = 90.0
    speed = 145.0
    paused = False
    show_help = True

    # Yard: parallel sidings with a few parked trains to demonstrate many trains.
    yard_tracks = []
    for y in (95, 145, 195):
        yard_tracks.append([(690, y), (1190, y)])
    parked = [(yard_tracks[0], 300), (yard_tracks[1], 390), (yard_tracks[2], 220)]

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_a and distance < 610:
                    active_route = 0
                elif event.key == pygame.K_d and distance < 610:
                    active_route = 1
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    distance = 90.0

        if not paused:
            distance += speed * dt
            if distance > route_lengths[active_route][-1]:
                distance = 0.0

        screen.fill(BG)

        # Three long parallel tracks in the background.
        for y in (310, 360, 410):
            draw_track(screen, [(35, y), (1245, y)], (68, 78, 91), 2)

        # Depot / yard tracks.
        for points in yard_tracks:
            draw_track(screen, points, (110, 122, 135), 2)
            pygame.draw.line(screen, (150, 91, 75), points[-1], (points[-1][0], points[-1][1] + 12), 4)
        for points, pos in parked:
            lengths = path_lengths(points)
            draw_train(screen, points, lengths, pos, cars=3, color=(150, 163, 174))

        # Highlight both switch paths; selected one is brighter.
        draw_track(screen, left_branch, ACCENT if active_route == 0 else (87, 102, 116), 3)
        draw_track(screen, right_branch, ACCENT if active_route == 1 else (87, 102, 116), 3)
        pygame.draw.circle(screen, (242, 190, 90), (650, 360), 7)
        pygame.draw.circle(screen, (242, 190, 90), (900, 270 if active_route == 0 else 450), 5)

        draw_train(screen, routes[active_route], route_lengths[active_route], distance)

        title = font.render("ТЕСТОВАЯ СХЕМА: ПАРАЛЛЕЛЬНЫЕ ПУТИ И СТРЕЛКА", True, TEXT)
        screen.blit(title, (32, 24))
        screen.blit(small.render("Депо: несколько отдельных составов на соседних путях", True, (166, 180, 194)), (690, 58))
        screen.blit(small.render("Путь A — верхняя ветка" + ("  [ВЫБРАН]" if active_route == 0 else ""), True,
                                 ACCENT if active_route == 0 else TEXT), (930, 235))
        screen.blit(small.render("Путь D — нижняя ветка" + ("  [ВЫБРАН]" if active_route == 1 else ""), True,
                                 ACCENT if active_route == 1 else TEXT), (930, 465))

        status = "ПАУЗА" if paused else "ДВИЖЕНИЕ"
        screen.blit(font.render(f"{status}   Скорость: {speed:.0f} условных ед./с", True, TEXT), (32, 610))
        screen.blit(small.render(f"Маршрут: {'верхний' if active_route == 0 else 'нижний'}   |   Позиция: {distance:.0f}", True,
                                 (166, 180, 194)), (32, 642))
        if show_help:
            help_lines = ["A — выбрать левую/верхнюю ветку", "D — выбрать правую/нижнюю ветку",
                          "SPACE — пауза   R — вернуть поезд в начало   ESC — выход"]
            for i, line in enumerate(help_lines):
                screen.blit(small.render(line, True, TEXT), (32, 76 + i * 23))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
