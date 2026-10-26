"""Simple placeholder renderer for track, train and HUD."""
import pygame

class Renderer:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 20)

    def draw_scene(self, surface, line, train, camera, elapsed):
        width, height = surface.get_size()
        # Tunnel walls and track bed
        pygame.draw.rect(surface, (28, 33, 42), (0, 180, width, 300))
        pygame.draw.rect(surface, (48, 51, 58), (0, 330, width, 85))
        points = [(int(x-camera.x), int(y)) for x, y in line.path.sample(24)]
        if len(points) > 1:
            pygame.draw.lines(surface, (135, 139, 145), False, points, 5)
            pygame.draw.lines(surface, (70, 74, 82), False, [(x, y+12) for x,y in points], 3)
        for station in line.stations:
            x = int(float(station.get("position", 0))-camera.x)
            if -100 < x < width+100:
                pygame.draw.rect(surface, (75, 125, 145), (x-45, 260, 90, 14), border_radius=3)
                label = self.small_font.render(station.get("name", "Station"), True, (225, 230, 235))
                surface.blit(label, (x-label.get_width()//2, 235))
        for signal in line.signals:
            x = int(signal.position-camera.x)
            if -20 < x < width+20:
                pygame.draw.rect(surface, (85, 88, 94), (x-3, 280, 6, 52))
                pygame.draw.circle(surface, signal.ASPECTS[signal.aspect], (x, 280), 7)
        # Train consist
        wagon_width = 68
        total_width = wagon_width * len(train.wagons)
        train_x = int(train.position-camera.x)
        start_x = train_x
        for i, wagon in enumerate(train.wagons):
            x = start_x - total_width + i*wagon_width
            rect = pygame.Rect(x, 292, wagon_width-3, 38)
            pygame.draw.rect(surface, (190, 194, 198), rect, border_radius=5)
            pygame.draw.rect(surface, (45, 95, 135), (x+5, 299, wagon_width-15, 10), border_radius=2)
            pygame.draw.rect(surface, (80, 83, 88), (x+4, 328, 10, 5))
            pygame.draw.rect(surface, (80, 83, 88), (x+50, 328, 10, 5))
        # HUD
        pygame.draw.rect(surface, (12, 15, 20), (16, 16, 300, 104), border_radius=8)
        surface.blit(self.font.render(line.name, True, (240, 240, 240)), (30, 26))
        surface.blit(self.font.render(f"Speed: {train.speed*3.6:05.1f} km/h", True, (110, 220, 160)), (30, 55))
        surface.blit(self.small_font.render("W/UP: traction  S/DOWN: brake  SPACE: emergency", True, (205, 210, 218)), (30, 88))
