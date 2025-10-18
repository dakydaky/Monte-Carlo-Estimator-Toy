import pygame
import random
import sys
import math
import time

pygame.init()

# Window setup
WIDTH, HEIGHT = 800, 800
WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Monte Carlo Shape Area Estimation with Confidence")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_BLUE = (180, 200, 255)
GREEN = (0, 200, 0)
RED = (220, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 120, 255)
DARK_GRAY = (100, 100, 100)

font = pygame.font.SysFont(None, 28)

# Simulation state
drawing = True
shape_points = []
square_rect = None
points = []  # (x, y, inside)
inside_count = 0
total_count = 0
last_point_time = 0
space_held = False


def point_in_polygon(x, y, poly):
    """Ray casting algorithm for inside/outside test."""
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


def draw_confidence_bar(confidence_percent, pos, width=300, height=20):
    """Draw visual confidence bar."""
    x, y = pos
    pygame.draw.rect(WINDOW, DARK_GRAY, (x, y, width, height), 2)
    fill_width = width * (confidence_percent / 100)
    pygame.draw.rect(WINDOW, BLUE, (x, y, fill_width, height))
    draw_text(f"{confidence_percent:.1f}%", (x + width + 10, y - 2))


def normalize_shape_to_bottom_center(points, margin=60, bottom_padding=50, target_height_ratio=0.35):
    """
    Moves and scales shape to bottom-center of screen,
    ensuring it fits fully above the bottom margin with a bit of padding.
    """
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width, height = max_x - min_x, max_y - min_y

    # Scale shape to target height ratio of window
    target_height = HEIGHT * target_height_ratio
    scale = target_height / height
    new_width = width * scale
    new_height = height * scale

    # Compute scaled bounding box
    scaled_min_y = min_y * scale
    scaled_max_y = max_y * scale

    # Center horizontally, and add bottom padding
    horizontal_offset = WIDTH / 2 - (min_x + width / 2) * scale
    vertical_offset = HEIGHT - margin - scaled_max_y - bottom_padding

    # Apply transformation
    transformed = [
        (x * scale + horizontal_offset, y * scale + vertical_offset)
        for x, y in points
    ]
    return transformed

# Main loop
clock = pygame.time.Clock()
running = True

while running:
    WINDOW.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Draw shape
        if drawing and pygame.mouse.get_pressed()[0]:
            shape_points.append(pygame.mouse.get_pos())

        # Key events
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and len(shape_points) > 2:
                drawing = False
                # Move and scale shape to bottom-center
                shape_points = normalize_shape_to_bottom_center(shape_points)
                # Define bounding square
                xs = [p[0] for p in shape_points]
                ys = [p[1] for p in shape_points]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                side = max(max_x - min_x, max_y - min_y)
                square_rect = pygame.Rect(min_x, min_y, side, side)

            elif event.key == pygame.K_SPACE and not drawing and square_rect:
                space_held = True

            elif event.key == pygame.K_r:
                # Reset simulation
                drawing = True
                shape_points.clear()
                square_rect = None
                points.clear()
                inside_count = total_count = 0
                space_held = False

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                space_held = False

    # Automatic point addition when space is held
    current_time = time.time()
    if (
        space_held
        and not drawing
        and square_rect
        and current_time - last_point_time > 0.2
    ):
        rx = random.uniform(square_rect.left, square_rect.right)
        ry = random.uniform(square_rect.top, square_rect.bottom)
        inside = point_in_polygon(rx, ry, shape_points)
        points.append((rx, ry, inside))
        total_count += 1
        if inside:
            inside_count += 1
        last_point_time = current_time

    # Draw shape
    if len(shape_points) > 1:
        pygame.draw.lines(WINDOW, BLACK, False, shape_points, 2)

    # Draw bounding square
    if not drawing and square_rect:
        pygame.draw.rect(WINDOW, GRAY, square_rect, 2)
        pygame.draw.polygon(WINDOW, LIGHT_BLUE, shape_points, 0)
        pygame.draw.polygon(WINDOW, BLACK, shape_points, 2)

    # Draw dots
    for x, y, inside in points:
        color = GREEN if inside else RED
        pygame.draw.circle(WINDOW, color, (int(x), int(y)), 4)

    # Display info text
    draw_text("Draw a shape with mouse. Press ENTER when done.", (10, 10))
    draw_text("Hold SPACE to add random dots. Press R to reset.", (10, 40))

    if square_rect:
        square_area = square_rect.width ** 2
        draw_text(f"Bounding Square Area = {square_area:.0f} px²", (10, 70))

    if total_count > 0 and square_rect:
        p = inside_count / total_count
        estimated_area = p * square_area

        # 95% confidence interval
        se = math.sqrt(p * (1 - p) / total_count) if total_count > 0 else 0
        ci_low = max(0, (p - 1.96 * se) * square_area)
        ci_high = min(square_area, (p + 1.96 * se) * square_area)

        # Confidence based on number of samples
        k = 0.01
        confidence_score = 1 - math.exp(-k * total_count)
        confidence_percent = confidence_score * 100

        draw_text(f"Samples: {total_count} | Inside: {inside_count}", (10, 110))
        draw_text(f"Estimated Shape Area = {estimated_area:.2f} px²", (10, 140))
        draw_text(f"95% Confidence Interval = [{ci_low:.2f}, {ci_high:.2f}] px²", (10, 170))

        draw_text("Confidence Level:", (10, 210))
        draw_confidence_bar(confidence_percent, (180, 208))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
