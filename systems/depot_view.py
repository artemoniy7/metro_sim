"""Side-on surface depot and tunnel entrance view."""
import pygame

SKY = (116, 174, 205)
GROUND = (92, 112, 77)
EARTH = (76, 68, 57)
BALLAST = (48, 51, 58)
RAIL_TOP = (155, 160, 167)
RAIL_SIDE = (85, 90, 98)
SLEEPER = (95, 89, 80)


def _draw_track(surface, y, x1=0, x2=None, scale=1.0):
    """Draw the same simple side-on sleepers and rail profile as the tunnel scene."""
    x2 = surface.get_width() if x2 is None else x2
    pygame.draw.rect(surface, BALLAST, (x1, y + 8, x2 - x1, surface.get_height() - y - 8))
    spacing = max(12, round(25 * scale))
    for x in range(x1, x2 + spacing, spacing):
        pygame.draw.line(surface, SLEEPER, (x, y - 1), (x, y + 14), max(2, round(3 * scale)))
    pygame.draw.line(surface, RAIL_TOP, (x1, y + 1), (x2, y + 1), max(3, round(4 * scale)))
    pygame.draw.line(surface, RAIL_SIDE, (x1, y + 7), (x2, y + 7), max(2, round(2 * scale)))


def _draw_train(surface, train, renderer, x, rail_y):
    """Use the actual 81-760 assets and consist configuration from the game."""
    if renderer is None:
        return
    loco_image = renderer.loco_image
    car_image = renderer.car_image
    scale = 0.34
    loco_width = max(1, round(train.loco_length_m * 10 * scale))
    car_width = max(1, round(train.car_length_m * 10 * scale))
    reference = loco_image or car_image
    train_height = max(34, round(reference.get_height() * loco_width / reference.get_width())) if reference else 52
    vehicle_x = x
    for wagon in train.wagons:
        vehicle_width = loco_width if wagon.is_loco else car_width
        image = loco_image if wagon.is_loco else car_image
        if wagon.is_loco and wagon.index == len(train.wagons) - 1 and image is not None:
            image = pygame.transform.flip(image, True, False)
        if image is not None:
            sprite = pygame.transform.smoothscale(image, (vehicle_width, train_height))
            surface.blit(sprite, (round(vehicle_x), round(rail_y - train_height + 4)))
        else:
            body = pygame.Rect(round(vehicle_x), round(rail_y - 48), vehicle_width, 44)
            pygame.draw.rect(surface, (198, 205, 210), body, border_radius=4)
            pygame.draw.rect(surface, (55, 68, 77), body, 2, border_radius=4)
        vehicle_x += vehicle_width


def draw_depot(surface, train, route_set, elapsed, renderer=None):
    width, height = surface.get_size()
    ground_y = int(height * 0.64)
    rail_y = int(height * 0.82)
    surface.fill(SKY)

    # Open-air background: simple distant tree line, kept behind the ground.
    pygame.draw.circle(surface, (239, 218, 153), (int(width * .86), int(height * .14)), max(24, height // 22))
    for i in range(13):
        x = i * width // 12
        crown_y = ground_y - 8
        pygame.draw.circle(surface, (67, 105, 75), (x, crown_y - 23), 35)
        pygame.draw.rect(surface, (87, 78, 58), (x - 4, crown_y - 4, 8, 28))

    # The ground surface is a strict horizontal boundary. Nothing from the
    # tunnel is drawn above it, so the portal cannot cover the sky or land.
    pygame.draw.rect(surface, GROUND, (0, ground_y - 9, width, 9))
    pygame.draw.rect(surface, EARTH, (0, ground_y, width, height - ground_y))
    for y in range(ground_y + 22, height, 34):
        pygame.draw.line(surface, (86, 77, 65), (0, y), (width, y), 1)

    # Depot shed, drawn in strict profile rather than perspective.
    shed = pygame.Rect(int(width * .08), ground_y - int(height * .32), int(width * .34), int(height * .32))
    pygame.draw.rect(surface, (160, 169, 173), shed)
    pygame.draw.rect(surface, (83, 96, 105), shed, 3)
    pygame.draw.rect(surface, (54, 65, 72), (shed.left + 18, shed.bottom - int(height * .22), shed.width - 36, int(height * .22)))
    for wx in range(shed.left + 28, shed.right - 20, 55):
        pygame.draw.rect(surface, (120, 164, 179), (wx, shed.top + 18, 34, 22))

    # Surface track: same side-on rail/sleeper treatment as the tunnel renderer.
    _draw_track(surface, rail_y, 0, width)

    # Tunnel mouth is cut only into the earth, beginning exactly at ground_y.
    portal_x = int(width * .36)
    portal_w = int(width * .23)
    portal_top = ground_y + 12
    portal_rect = pygame.Rect(portal_x, portal_top, portal_w, height - portal_top)
    pygame.draw.rect(surface, (37, 42, 48), portal_rect)
    pygame.draw.rect(surface, (118, 124, 126), (portal_x - 9, portal_top, 18, height - portal_top))
    pygame.draw.rect(surface, (118, 124, 126), (portal_x, portal_top, portal_w, 15))
    pygame.draw.rect(surface, (22, 26, 31), (portal_x + 16, portal_top + 18, portal_w - 16, height - portal_top - 18))
    # Re-draw the rails over the portal so the track continues visibly inside.
    _draw_track(surface, rail_y, portal_x, width)

    progress = max(0.0, min(1.0, train.position / 720.0))
    train_front_x = int(width * .10 + progress * width * .26)
    _draw_train(surface, train, renderer, train_front_x, rail_y)

    # Blue/white shunting signal at the portal approach.
    sig_x, sig_y = portal_x - 30, rail_y - 108
    pygame.draw.line(surface, (55, 61, 66), (sig_x, sig_y + 30), (sig_x, rail_y + 4), 5)
    pygame.draw.rect(surface, (24, 28, 32), (sig_x - 12, sig_y, 24, 38), border_radius=4)
    lamp = (240, 243, 246) if route_set else (45, 105, 255)
    pygame.draw.circle(surface, lamp, (sig_x, sig_y + 12), 7)
    pygame.draw.circle(surface, (35, 39, 43), (sig_x, sig_y + 28), 5)

    font = pygame.font.Font(None, 30)
    small = pygame.font.Font(None, 23)
    surface.blit(font.render('ТЧ-14 «Владыкино»', True, (22, 31, 37)), (24, 20))
    status = 'МАНЕВРОВЫЙ МАРШРУТ ОТКРЫТ' if route_set else 'МАНЕВРОВЫЙ МАРШРУТ ЗАКРЫТ'
    surface.blit(font.render(status, True, (248, 248, 248) if route_set else (30, 78, 205)), (24, 54))
    surface.blit(small.render('R — маршрут   D/→ — тяга   A/← — тормоз', True, (22, 31, 37)), (24, height - 42))
    surface.blit(small.render(f'Скорость: {train.speed * 3.6:04.1f} км/ч   Маневровый путь: {train.position:05.0f} / 720 м', True, (22, 31, 37)), (24, height - 68))
