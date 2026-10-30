"""Vector-style surface view of the provisional Vladykino depot yard."""
import pygame


def draw_depot(surface, train, route_set, elapsed):
    width, height = surface.get_size()
    surface.fill((137, 169, 184))
    pygame.draw.rect(surface, (177, 204, 211), (0, 0, width, int(height * .48)))
    pygame.draw.circle(surface, (238, 222, 166), (int(width * .82), int(height * .13)), 42)
    for i in range(18):
        x = i * width // 17
        pygame.draw.circle(surface, (64, 105, 83), (x, int(height * .43)), 48)
        pygame.draw.rect(surface, (75, 111, 83), (x - 7, int(height * .43), 14, 70))
    ground_y = int(height * .62)
    pygame.draw.rect(surface, (113, 124, 105), (0, ground_y, width, height-ground_y))
    building = pygame.Rect(int(width*.12), int(height*.25), int(width*.48), int(height*.36))
    pygame.draw.rect(surface, (157, 164, 164), building)
    pygame.draw.polygon(surface, (82, 91, 98), [
        (building.left-15, building.top+10), (building.left+45, building.top-38),
        (building.right+18, building.top-38), (building.right, building.top+10)
    ])
    pygame.draw.rect(surface, (91, 104, 110), (building.left+20, building.top+55, building.width-40, building.height-55))
    for x in range(building.left+35, building.right-15, 70):
        pygame.draw.rect(surface, (178, 199, 198), (x, building.top+24, 42, 25))
    pygame.draw.rect(surface, (84, 91, 88), (0, ground_y+20, width, 9))
    for x in range(0, width, 28):
        pygame.draw.line(surface, (181, 185, 174), (x, ground_y+12), (x, ground_y+52), 2)
    pygame.draw.rect(surface, (67, 70, 67), (0, int(height*.83), width, int(height*.17)))
    pygame.draw.line(surface, (205, 205, 195), (0, int(height*.83)), (width, int(height*.83)), 3)
    track_ys = [int(height*.73), int(height*.81), int(height*.89)]
    for y in track_ys:
        for x in range(0, width, 28):
            pygame.draw.line(surface, (105, 82, 65), (x, y-8), (x+13, y+9), 4)
        pygame.draw.line(surface, (185, 190, 192), (0, y-5), (width, y-5), 4)
        pygame.draw.line(surface, (80, 87, 91), (0, y+5), (width, y+5), 4)
        pygame.draw.line(surface, (89, 94, 91), (int(width*.08), y-90), (int(width*.08), y+18), 4)
        pygame.draw.line(surface, (89, 94, 91), (int(width*.08), y-90), (int(width*.92), y-90), 3)
        pygame.draw.line(surface, (89, 94, 91), (int(width*.92), y-90), (int(width*.92), y+18), 4)
    pygame.draw.line(surface, (188, 192, 194), (int(width*.12), track_ys[0]), (int(width*.88), int(height*.53)), 5)
    pygame.draw.line(surface, (188, 192, 194), (int(width*.12), track_ys[0]+10), (int(width*.88), int(height*.53)+10), 4)
    train_x = int(width*.22 + min(1.0, train.position/720.0)*width*.56)
    train_y = track_ys[0]-50
    car_w = max(45, width//17)
    for i in range(8):
        x = train_x - i*car_w
        body = pygame.Rect(x, train_y, car_w-3, 42)
        pygame.draw.rect(surface, (202, 207, 211), body, border_radius=5)
        pygame.draw.rect(surface, (66, 77, 85), body, 2, border_radius=5)
        pygame.draw.rect(surface, (45, 68, 81), (x+7, train_y+7, car_w-18, 12))
        pygame.draw.line(surface, (105, 110, 113), (x+5, train_y+33), (x+car_w-9, train_y+33), 2)
        pygame.draw.circle(surface, (35, 38, 42), (x+12, train_y+44), 5)
        pygame.draw.circle(surface, (35, 38, 42), (x+car_w-17, train_y+44), 5)
    sig_x, sig_y = int(width*.88), int(height*.48)
    pygame.draw.line(surface, (52, 57, 62), (sig_x, sig_y), (sig_x, sig_y+115), 6)
    pygame.draw.rect(surface, (24, 28, 32), (sig_x-13, sig_y-8, 26, 42), border_radius=5)
    lamp = (235, 239, 242) if route_set else (55, 105, 255)
    pygame.draw.circle(surface, lamp, (sig_x, sig_y+13), 8)
    pygame.draw.circle(surface, (20, 22, 24), (sig_x, sig_y+31), 5)
    font, small = pygame.font.Font(None, 30), pygame.font.Font(None, 23)
    surface.blit(font.render("ТЧ-14 «Владыкино» — учебная схема депо", True, (25, 34, 39)), (28, 24))
    status = "МАНЕВРОВЫЙ МАРШРУТ ОТКРЫТ" if route_set else "МАНЕВРОВЫЙ МАРШРУТ ЗАКРЫТ"
    color = (245, 245, 245) if route_set else (65, 125, 255)
    surface.blit(font.render(status, True, color), (28, 62))
    surface.blit(small.render("R — установить/отменить маршрут   D/→ тяга   A/← тормоз", True, (25, 34, 39)), (28, height-42))
    surface.blit(small.render(f"Скорость: {train.speed*3.6:04.1f} км/ч   Путь: {train.position:05.0f} / 720 м", True, (25, 34, 39)), (28, height-70))
