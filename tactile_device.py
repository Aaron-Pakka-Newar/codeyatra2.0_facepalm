import pygame
import random
import math
import time

# Initialize pygame
pygame.init()

WIDTH = 1400
HEIGHT = 700
SCENE_W = WIDTH // 2

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Directional Tactile Navigation Device - 3×3 Grid Simulation")
clock = pygame.time.Clock()

# Fonts
pygame.font.init()
title_font = pygame.font.Font(None, 32)
label_font = pygame.font.Font(None, 24)
small_font = pygame.font.Font(None, 20)

UPDATE_RATE = 5  # Hz (200ms cycle)
MAX_RANGE = 3.0  # meters (scaled to pixels: 100px = 1m)
SCALE = 100  # pixels per meter
FOV = math.radians(120)  # 120° field of view

# Distance layers (rows)
DISTANCE_LAYERS = {
    0: {"name": "Immediate", "range": (0, 1), "weight": 1.0},
    1: {"name": "Near", "range": (1, 2), "weight": 0.7},
    2: {"name": "Far", "range": (2, 3), "weight": 0.4}
}

# Direction layers (columns)
DIRECTION_LAYERS = {
    0: {"name": "Left", "angle": (-60, -20)},
    1: {"name": "Center", "angle": (-20, 20)},
    2: {"name": "Right", "angle": (20, 60)}
}

# Elevation categories
ELEVATION_TYPES = {
    "ground": {"height": 0, "color": (60, 60, 60), "label": "Ground"},
    "pothole": {"height": -1, "color": (80, 40, 120), "label": "Pothole"},
    "step": {"height": 1, "color": (100, 200, 100), "label": "Step"},
    "mid": {"height": 2, "color": (220, 180, 60), "label": "Mid"},
    "top": {"height": 3, "color": (255, 80, 80), "label": "Top/Head"}
}

WORLD_SIZE = 1000  # pixels (10m x 10m world)
NUM_OBSTACLES = 20

player_x = WORLD_SIZE // 2
player_y = WORLD_SIZE // 2
player_angle = -math.pi / 2  # Facing up initially (0° = right, -90° = up)

speed = 5
rot_speed = 0.06

# Obstacle structure
obstacles = []

# Previous distance tracking for motion detection
previous_dist = [[None]*3 for _ in range(3)]

# Simulation time
last_update = time.time()
timestep = 0

def generate_obstacles():
    global obstacles
    obstacles = []
    elevation_choices = ["step", "mid", "top", "pothole"]
    weights = [0.3, 0.35, 0.2, 0.15]
    
    # Generate obstacles in a ring around the player (within detectable range)
    for _ in range(NUM_OBSTACLES):
        # Random distance between 0.5m and 4m (some outside range)
        dist = random.uniform(50, 400)  # 0.5m to 4m in pixels
        angle = random.uniform(0, 2 * math.pi)
        
        x = player_x + dist * math.cos(angle)
        y = player_y + dist * math.sin(angle)
        
        # Keep within world bounds
        x = max(50, min(WORLD_SIZE - 50, x))
        y = max(50, min(WORLD_SIZE - 50, y))
        
        elev = random.choices(elevation_choices, weights)[0]
        is_moving = random.random() < 0.15  # 15% chance of moving
        vx = random.uniform(-0.8, 0.8) if is_moving else 0
        vy = random.uniform(-0.8, 0.8) if is_moving else 0
        
        obstacles.append({
            "x": x, "y": y,
            "elevation": elev,
            "moving": is_moving,
            "vx": vx, "vy": vy
        })

generate_obstacles()
def draw_top_down_view():
    """Draw the top-down world view on the left side"""
    # Calculate camera offset to center on player
    cam_x = player_x - SCENE_W // 2
    cam_y = player_y - HEIGHT // 2
    
    # Draw obstacles
    for obs in obstacles:
        screen_x = obs["x"] - cam_x
        screen_y = obs["y"] - cam_y
        
        # Only draw if on screen (left panel)
        if 0 <= screen_x < SCENE_W and 0 <= screen_y < HEIGHT:
            color = ELEVATION_TYPES[obs["elevation"]]["color"]
            pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), 15)
            
            # Draw movement indicator for moving obstacles
            if obs["moving"]:
                pygame.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), 18, 2)
    
    # Draw player
    player_screen_x = player_x - cam_x
    player_screen_y = player_y - cam_y
    pygame.draw.circle(screen, (0, 200, 255), (int(player_screen_x), int(player_screen_y)), 12)
    
    # Draw player direction indicator
    dir_len = 30
    dir_x = player_screen_x + dir_len * math.cos(player_angle)
    dir_y = player_screen_y + dir_len * math.sin(player_angle)
    pygame.draw.line(screen, (0, 255, 255), 
                     (int(player_screen_x), int(player_screen_y)), 
                     (int(dir_x), int(dir_y)), 3)
    
    # Draw FOV cone
    left_angle = player_angle - FOV / 2
    right_angle = player_angle + FOV / 2
    fov_len = MAX_RANGE * SCALE
    
    left_x = player_screen_x + fov_len * math.cos(left_angle)
    left_y = player_screen_y + fov_len * math.sin(left_angle)
    right_x = player_screen_x + fov_len * math.cos(right_angle)
    right_y = player_screen_y + fov_len * math.sin(right_angle)
    
    pygame.draw.line(screen, (100, 100, 100), 
                     (int(player_screen_x), int(player_screen_y)), 
                     (int(left_x), int(left_y)), 1)
    pygame.draw.line(screen, (100, 100, 100), 
                     (int(player_screen_x), int(player_screen_y)), 
                     (int(right_x), int(right_y)), 1)
    
    # Draw divider line
    pygame.draw.line(screen, (80, 80, 80), (SCENE_W, 0), (SCENE_W, HEIGHT), 2)

def draw_grid_panel():
    """Draw the 3x3 tactile grid on the right side"""
    panel_x = SCENE_W + 50
    panel_y = 100
    cell_size = 120
    
    # Title
    title = title_font.render("Tactile 3x3 Grid", True, (255, 255, 255))
    screen.blit(title, (panel_x + 80, 50))
    
    # Draw 3x3 grid
    for row in range(3):
        for col in range(3):
            x = panel_x + col * cell_size
            y = panel_y + row * cell_size
            
            # Check for obstacles in this cell
            cell_color = (40, 40, 40)
            cell_label = ""
            
            # Get distance and direction ranges for this cell
            dist_layer = DISTANCE_LAYERS[row]
            dir_layer = DIRECTION_LAYERS[col]
            
            for obs in obstacles:
                dx = obs["x"] - player_x
                dy = obs["y"] - player_y
                dist = math.sqrt(dx*dx + dy*dy) / SCALE  # Convert to meters
                
                # Calculate angle relative to player facing direction
                obs_angle = math.atan2(dy, dx)
                rel_angle = math.degrees(obs_angle - player_angle)
                
                # Normalize angle to -180 to 180
                while rel_angle > 180:
                    rel_angle -= 360
                while rel_angle < -180:
                    rel_angle += 360
                
                # Check if obstacle is in this cell
                if (dist_layer["range"][0] <= dist < dist_layer["range"][1] and
                    dir_layer["angle"][0] <= rel_angle < dir_layer["angle"][1]):
                    cell_color = ELEVATION_TYPES[obs["elevation"]]["color"]
                    cell_label = ELEVATION_TYPES[obs["elevation"]]["label"]
                    break
            
            # Draw cell
            pygame.draw.rect(screen, cell_color, (x, y, cell_size - 5, cell_size - 5))
            pygame.draw.rect(screen, (100, 100, 100), (x, y, cell_size - 5, cell_size - 5), 2)
            
            # Draw cell label
            if cell_label:
                label = small_font.render(cell_label, True, (255, 255, 255))
                screen.blit(label, (x + 10, y + cell_size - 30))
    
    # Draw row/column labels
    for i, layer in DISTANCE_LAYERS.items():
        label = small_font.render(layer["name"], True, (180, 180, 180))
        screen.blit(label, (panel_x - 70, panel_y + i * cell_size + 50))
    
    for i, layer in DIRECTION_LAYERS.items():
        label = small_font.render(layer["name"], True, (180, 180, 180))
        screen.blit(label, (panel_x + i * cell_size + 40, panel_y - 25))
    
    # Draw legend
    legend_y = panel_y + 400
    legend_label = label_font.render("Legend:", True, (255, 255, 255))
    screen.blit(legend_label, (panel_x, legend_y))
    
    for i, (key, elev) in enumerate(ELEVATION_TYPES.items()):
        if key != "ground":
            pygame.draw.rect(screen, elev["color"], (panel_x, legend_y + 30 + i * 25, 20, 20))
            text = small_font.render(elev["label"], True, (200, 200, 200))
            screen.blit(text, (panel_x + 30, legend_y + 32 + i * 25))

def update_obstacles():
    """Update moving obstacles"""
    for obs in obstacles:
        if obs["moving"]:
            obs["x"] += obs["vx"]
            obs["y"] += obs["vy"]
            
            # Bounce off world boundaries
            if obs["x"] < 50 or obs["x"] > WORLD_SIZE - 50:
                obs["vx"] *= -1
            if obs["y"] < 50 or obs["y"] > WORLD_SIZE - 50:
                obs["vy"] *= -1
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_r:
                generate_obstacles()
    
    # Handle continuous key input for movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        player_x += speed * math.cos(player_angle)
        player_y += speed * math.sin(player_angle)
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        player_x -= speed * math.cos(player_angle)
        player_y -= speed * math.sin(player_angle)
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        player_angle -= rot_speed
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        player_angle += rot_speed
    
    # Keep player in bounds
    player_x = max(50, min(WORLD_SIZE - 50, player_x))
    player_y = max(50, min(WORLD_SIZE - 50, player_y))
    
    # Update moving obstacles
    update_obstacles()
    
    # Clear screen
    screen.fill((30, 30, 30))
    
    # Draw everything
    draw_top_down_view()
    draw_grid_panel()
    
    # Update display
    pygame.display.flip()
    clock.tick(60)

pygame.quit()