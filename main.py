import pygame
import random
import sys
import math
import time

pygame.init()

# Window setup
WIDTH, HEIGHT = 800, 800
WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Monte Carlo Shape Area Estimation")

convergence_points = []

GRAPH_WIDTH, GRAPH_HEIGHT = 200, 150
GRAPH_MARGIN = 10

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_BLUE = (180, 200, 255)
GREEN = (0, 200, 0)
RED = (220, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
YELLOW = (240, 200, 0)
BLUE = (0, 120, 255)

font = pygame.font.SysFont(None, 26)

# State
drawing = True
shape_points = []
square_rect = None
points = []
inside_count = 0
total_count = 0
last_point_time = 0
space_held = False
preset_selected = None  # Tracks which preset shape was chosen

# Speedup tracker
space_held_time = 0  # tracks how long space has been held
initial_delay = 0.2  # starting delay between points
min_delay = 0.01     # fastest speed
acceleration = 0.95  # multiplier per step


# ---------- Utility functions ----------

def point_in_polygon(x, y, poly):
    inside = False
    n = len(poly)
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def draw_text(text, pos, color=BLACK):
    label = font.render(text, True, color)
    WINDOW.blit(label, pos)


def draw_confidence_bar(confidence_percent, pos, width=200, height=20):
    x, y = pos
    pygame.draw.rect(WINDOW, DARK_GRAY, (x, y, width, height), 2)
    fill_width = width * (confidence_percent / 100)
    pygame.draw.rect(WINDOW, BLUE, (x, y, fill_width, height))
    draw_text(f"{confidence_percent:.1f}%", (x + width + 10, y - 2))


def normalize_shape_to_bottom_center(points, margin=60, bottom_padding=10, target_height_ratio=0.35, preserve_aspect=False):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width, height = max_x - min_x, max_y - min_y

    target_height = HEIGHT * target_height_ratio
    scale = target_height / height

    if preserve_aspect:
        # Make square scaling to ensure bounding square is exact
        scale = target_height / max(width, height)

    scaled_max_y = max_y * scale
    horizontal_offset = WIDTH / 2 - (min_x + width / 2) * scale
    vertical_offset = HEIGHT - margin - scaled_max_y - bottom_padding

    return [(x * scale + horizontal_offset, y * scale + vertical_offset) for x, y in points]



# ---------- Preset Shapes ----------

def make_circle(n=100, r=100):
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]

def make_triangle():
    return [(0, 0), (200, 0), (100, -173)]

def make_star(points=5, r1=100, r2=40):
    verts = []
    for i in range(points*2):
        r = r1 if i%2==0 else r2
        angle = math.pi / points * i
        verts.append((r*math.cos(angle), r*math.sin(angle)))
    return verts

def make_blob(n=8):
    verts = []
    for i in range(n):
        angle = 2*math.pi*i/n
        radius = 100 + random.uniform(-40, 40)
        verts.append((radius*math.cos(angle), radius*math.sin(angle)))
    return verts

def make_heart(n=100):
    verts = []
    for i in range(n):
        t = math.pi - 2*math.pi*i/n
        x = 16*math.sin(t)**3
        y = 13*math.cos(t) -5*math.cos(2*t) -2*math.cos(3*t) - math.cos(4*t)
        verts.append((x*10, -y*10))
    return verts


# ---------- Buttons ----------

def draw_button(text, rect, hover=False):
    color = YELLOW if hover else GRAY
    pygame.draw.rect(WINDOW, color, rect, border_radius=5)
    pygame.draw.rect(WINDOW, BLACK, rect, 2, border_radius=5)
    label = font.render(text, True, BLACK)
    WINDOW.blit(label, (rect.x + 10, rect.y + 5))


button_labels = ["Circle", "Triangle", "Star", "Blob", "Heart"]
button_rects = []
for i, label in enumerate(button_labels):
    rect = pygame.Rect(60 + i*140, HEIGHT-60, 120, 35)
    button_rects.append((label, rect))


# ---------- Main Loop ----------

clock = pygame.time.Clock()
running = True

while running:
    WINDOW.fill(WHITE)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if drawing and pygame.mouse.get_pressed()[0]:
            shape_points.append(pygame.mouse.get_pos())

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and len(shape_points) > 2:
                drawing = False
                shape_points = normalize_shape_to_bottom_center(shape_points)
                xs = [p[0] for p in shape_points]
                ys = [p[1] for p in shape_points]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                side = max(max_x - min_x, max_y - min_y)
                square_rect = pygame.Rect(min_x, min_y, side, side)

            elif event.key == pygame.K_SPACE and not drawing and square_rect:
                space_held = True

            elif event.key == pygame.K_r:
                drawing = True
                shape_points.clear()
                square_rect = None
                points.clear()
                inside_count = total_count = 0
                space_held = False

        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            space_held = False

        # Preset shape clicks
        if drawing and event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
            for label, rect in button_rects:
                if rect.collidepoint(mouse_pos):
                    preset_selected=label
                    if label=="Circle": 
                        shape_points = make_circle()
                        drawing = False
                        # Normalize but preserve aspect to keep square bounding correct
                        shape_points = normalize_shape_to_bottom_center(shape_points, preserve_aspect=True)
                    elif label=="Triangle": shape_points=make_triangle()
                    elif label=="Star": shape_points=make_star()
                    elif label=="Blob": shape_points=make_blob()
                    elif label=="Heart": shape_points=make_heart()
                    drawing=False
                    shape_points=normalize_shape_to_bottom_center(shape_points)
                    xs=[p[0] for p in shape_points]
                    ys=[p[1] for p in shape_points]
                    min_x, max_x=min(xs), max(xs)
                    min_y, max_y=min(ys), max(ys)
                    side=max(max_x - min_x, max_y - min_y)
                    square_rect=pygame.Rect(min_x, min_y, side, side)

        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            space_held = False
            space_held_time = 0


    # Continuous sampling
    current_time = time.time()
    if space_held and not drawing and square_rect:
        if last_point_time == 0:
            last_point_time = current_time
        # compute dynamic delay
        elapsed = current_time - last_point_time
        dynamic_delay = max(min_delay, initial_delay * (acceleration ** space_held_time))
        if elapsed > dynamic_delay:
            rx = random.uniform(square_rect.left, square_rect.right)
            ry = random.uniform(square_rect.top, square_rect.bottom)
            inside = point_in_polygon(rx, ry, shape_points)
            points.append((rx, ry, inside))
            total_count += 1
            if inside: inside_count += 1
            last_point_time = current_time
            space_held_time += 1

    # Draw shape
    if len(shape_points) > 1:
        pygame.draw.lines(WINDOW, BLACK, False, shape_points, 2)

    # Bounding square
    if square_rect:
        pygame.draw.rect(WINDOW, GRAY, square_rect, 2)
        pygame.draw.polygon(WINDOW, LIGHT_BLUE, shape_points, 0)
        pygame.draw.polygon(WINDOW, BLACK, shape_points, 2)

    # Draw dots
    for x,y,inside in points:
        color = GREEN if inside else RED
        pygame.draw.circle(WINDOW, color, (int(x), int(y)), 4)

    # ---------- UI Info Panel ----------
    draw_text("Draw shape or choose preset below", (10,10))
    draw_text("Hold SPACE to add dots | R to reset", (10,40))

    if drawing:
        for label, rect in button_rects:
            hover = rect.collidepoint(mouse_pos)
            draw_button(label, rect, hover)

    if square_rect and total_count>0:
        p = inside_count / total_count
        estimated_area = p * square_rect.width**2
        fractional = estimated_area / square_rect.width**2
        se = math.sqrt(p*(1-p)/total_count)
        ci_low = max(0, (p - 1.96*se)*square_rect.width**2)
        ci_high = min(square_rect.width**2, (p + 1.96*se)*square_rect.width**2)
        k=0.01
        confidence_score = 1 - math.exp(-k*total_count)
        confidence_percent = confidence_score*100

        convergence_points.append(estimated_area)

        info_y = 70

        draw_text(f"Samples: {total_count} | Inside: {inside_count}", (10,info_y))
        draw_text(f"Estimated Area = {estimated_area:.2f} px²", (10, info_y+30))
        draw_text(f"Fractional Size = {fractional:.4f}", (10, info_y+60))
        draw_text(f"95% Confidence Interval = [{ci_low:.2f}, {ci_high:.2f}] px²", (10, info_y+90))
        draw_text("Confidence Level:", (10, info_y+120))
        draw_confidence_bar(confidence_percent, (180, info_y+118))
        if preset_selected == "Circle":
            pi_estimate = 4 * (inside_count / total_count)  # fraction matches π/4 exactly
            draw_text(f"π estimate = {pi_estimate:.5f}", (10, 250))
            draw_text("Hint: π = 4 × Fractional Size", (10, 280))

        # ---------- Draw Convergence Graph ----------
        graph_x = WIDTH - GRAPH_WIDTH - GRAPH_MARGIN
        graph_y = GRAPH_MARGIN
        pygame.draw.rect(WINDOW, DARK_GRAY, (graph_x, graph_y, GRAPH_WIDTH, GRAPH_HEIGHT), 2)

        if convergence_points:
            max_area = square_rect.width**2
            n_points = len(convergence_points)
            step = max(1, n_points // GRAPH_WIDTH)
            last_x, last_y = graph_x, graph_y + GRAPH_HEIGHT
            for i in range(0, n_points, step):
                x = graph_x + (i / n_points) * GRAPH_WIDTH
                y = graph_y + GRAPH_HEIGHT - (convergence_points[i] / max_area) * GRAPH_HEIGHT
                pygame.draw.line(WINDOW, BLUE, (last_x, last_y), (x, y), 2)
                last_x, last_y = x, y
            draw_text("Convergence", (graph_x, graph_y + GRAPH_HEIGHT + 5), BLACK)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
