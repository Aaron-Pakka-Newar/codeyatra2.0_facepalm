import pygame
import random
import math
import time

# Initialize pygame
pygame.init()

# -----------------------
# WINDOW SETUP
# -----------------------
WIDTH = 1600
HEIGHT = 1000
SCENE_W = WIDTH // 2

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Directional Tactile Navigation Device - 3×3 Grid Simulation")
clock = pygame.time.Clock()

# Fonts with proper scaling
pygame.font.init()
title_font = pygame.font.Font(None, 40)
label_font = pygame.font.Font(None, 30)
small_font = pygame.font.Font(None, 24)
info_font = pygame.font.Font(None, 22)

# -----------------------
# SYSTEM CONSTANTS (from spec)
# -----------------------
UPDATE_RATE = 5  # Hz (200ms cycle)
MAX_RANGE = 3.0  # meters (scaled to pixels: 100px = 1m)
SCALE = 100  # pixels per meter
VIEW_SCALE = 0.55  # Scale factor to fit the full 3m circle in the viewport
FOV = math.radians(120)  # 120° field of view
CAMERA_HEIGHT = 1.6  # Camera/eye height in meters

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

# -----------------------
# WORLD SETTINGS
# -----------------------
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


# OBSTACLE GENERATION

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
        
        # Random cuboid dimensions (in meters)
        height_ranges = {
            "step": (0.2, 0.5),
            "mid": (0.6, 1.2),
            "top": (1.5, 2.0),
            "pothole": (0.15, 0.4)
        }
        hmin, hmax = height_ranges.get(elev, (0.3, 0.5))
        
        obstacles.append({
            "x": x, "y": y,
            "elevation": elev,
            "moving": is_moving,
            "vx": vx, "vy": vy,
            "cube_w": random.uniform(0.15, 0.55),  # half-width in meters
            "cube_d": random.uniform(0.15, 0.55),  # half-depth in meters
            "cube_h": random.uniform(hmin, hmax)    # height in meters
        })

generate_obstacles()


# HELPERS

def normalize_angle(a):
    while a < -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a

def world_to_screen(wx, wy):
    """Convert world coords to screen coords - scaled to fit viewport"""
    sx = SCENE_W / 2 + (wx - player_x) * VIEW_SCALE
    sy = HEIGHT / 2 + (wy - player_y) * VIEW_SCALE
    return sx, sy

def get_distance_meters(dist_pixels):
    return dist_pixels / SCALE

def get_elevation_height(elev_type):
    return ELEVATION_TYPES.get(elev_type, ELEVATION_TYPES["ground"])["height"]

# -----------------------
# GRID COMPUTATION (Core Algorithm)
# -----------------------
def compute_tactile_grid():
    
    global previous_dist, timestep
    
    # Grid state: height and vibration per cell
    heights = [[0.0] * 3 for _ in range(3)]
    vibration = [["static"] * 3 for _ in range(3)]
    cell_obstacles = [[None] * 3 for _ in range(3)]  # Store obstacle info
    
    for r in range(3):
        for c in range(3):
            best_dist = None
            best_obstacle = None
            
            for obs in obstacles:
                dx = obs["x"] - player_x
                dy = obs["y"] - player_y
                dist_px = math.hypot(dx, dy)
                dist_m = get_distance_meters(dist_px)
                
                # Check range (0-3m)
                if dist_m > MAX_RANGE:
                    continue
                
                # Calculate angle relative to player heading
                angle_rad = normalize_angle(math.atan2(dy, dx) - player_angle)
                angle_deg = math.degrees(angle_rad)
                
                # Check FOV (-60° to +60°)
                if abs(angle_deg) > 60:
                    continue
                
                # Determine column (direction)
                if angle_deg < -20:
                    col = 0  # Left
                elif angle_deg < 20:
                    col = 1  # Center
                else:
                    col = 2  # Right
                
                # Determine row (distance)
                if dist_m < 1:
                    row = 0  # Immediate
                elif dist_m < 2:
                    row = 1  # Near
                else:
                    row = 2  # Far
                
                # Check if this obstacle belongs to current cell
                if row == r and col == c:
                    if best_dist is None or dist_m < best_dist:
                        best_dist = dist_m
                        best_obstacle = obs
            
            if best_dist is not None and best_obstacle is not None:
                # Get elevation height
                elev_height = get_elevation_height(best_obstacle["elevation"])
                
                # Apply distance attenuation
                weight = DISTANCE_LAYERS[r]["weight"]
                final_height = elev_height * weight
                
                heights[r][c] = final_height
                cell_obstacles[r][c] = best_obstacle
                
                # Motion detection
                prev = previous_dist[r][c]
                if prev is not None:
                    velocity = abs(prev - best_dist) / 0.2  # m/s (200ms cycle)
                    if velocity > 0.8:
                        vibration[r][c] = "fast"
                    elif velocity > 0.2:
                        vibration[r][c] = "slow"
                
                previous_dist[r][c] = best_dist
            else:
                previous_dist[r][c] = None
    
    # Priority suppression: If Row 0 has level 3 obstacle, suppress Row 2
    for c in range(3):
        if heights[0][c] >= 3 * DISTANCE_LAYERS[0]["weight"]:
            heights[2][c] *= 0.3  # Suppress far
            heights[1][c] *= 0.7  # Reduce near
    
    timestep += 1
    return heights, vibration, cell_obstacles

# -----------------------
# DIRECTION SUGGESTION
# -----------------------
def compute_safe_direction(heights):
    """Calculate risk per column and suggest safest direction"""
    risks = [0, 0, 0]
    for c in range(3):
        for r in range(3):
            h = abs(heights[r][c])
            weight = DISTANCE_LAYERS[r]["weight"]
            if h > 0:
                risks[c] += h / weight  # Higher risk for closer obstacles
    
    min_risk = min(risks)
    if min_risk == 0:
        return None  # All clear
    safe_col = risks.index(min_risk)
    return safe_col

# -----------------------
# UPDATE OBSTACLES
# -----------------------
def update_obstacles():
    for obs in obstacles:
        if obs["moving"]:
            obs["x"] += obs["vx"]
            obs["y"] += obs["vy"]
            
            # Bounce off walls
            if obs["x"] < 20 or obs["x"] > WORLD_SIZE - 20:
                obs["vx"] *= -1
            if obs["y"] < 20 or obs["y"] > WORLD_SIZE - 20:
                obs["vy"] *= -1

# -----------------------
# DRAW SCENE (Top-down view)
# -----------------------
def draw_scene():
    # Background
    pygame.draw.rect(screen, (25, 25, 35), (0, 0, SCENE_W, HEIGHT))
    
    # Top border accent
    pygame.draw.line(screen, (100, 200, 255), (0, 0), (SCENE_W, 0), 3)
    
    # Title with background box
    title = title_font.render("Environment View (Top-Down)", True, (200, 200, 200))
    title_box_height = 45
    pygame.draw.rect(screen, (30, 30, 50), (0, 5, SCENE_W, title_box_height))
    pygame.draw.rect(screen, (100, 200, 255), (0, 5, SCENE_W, title_box_height), 2)
    screen.blit(title, (SCENE_W//2 - title.get_width()//2, 12))
    center = (SCENE_W//2, HEIGHT//2)
    fov_len = MAX_RANGE * SCALE * VIEW_SCALE
    
    # Draw FOV cone (120 degree field of view)
    left_angle = player_angle - FOV/2
    right_angle = player_angle + FOV/2
    
    # Create FOV arc points for filled polygon
    fov_points = [center]
    num_arc_points = 20
    for i in range(num_arc_points + 1):
        angle = left_angle + (right_angle - left_angle) * i / num_arc_points
        px = center[0] + fov_len * math.cos(angle)
        py = center[1] + fov_len * math.sin(angle)
        fov_points.append((px, py))
    
    # FOV fill
    pygame.draw.polygon(screen, (40, 50, 70), fov_points)
    pygame.draw.polygon(screen, (80, 100, 140), fov_points, 2)
    
    # Distance rings (1m, 2m, 3m) with improved labels
    ring_colors = [(80, 200, 80), (200, 200, 80), (200, 80, 80)]
    for i, (row, info) in enumerate(DISTANCE_LAYERS.items()):
        radius = int(info["range"][1] * SCALE * VIEW_SCALE)
        pygame.draw.circle(screen, ring_colors[i], center, radius, 2)
        # Label positioning - along a fixed angle for consistency
        label = label_font.render(f'{info["range"][1]}m', True, ring_colors[i])
        label_angle = player_angle + math.radians(75)
        lx = center[0] + (radius + 5) * math.cos(label_angle)
        ly = center[1] + (radius + 5) * math.sin(label_angle)
        screen.blit(label, (lx - label.get_width()//2, ly - label.get_height()//2))
    
    # Direction dividers (Left/Center/Right zones at -20° and +20°)
    for angle_offset in [-20, 20]:
        angle = player_angle + math.radians(angle_offset)
        end = (center[0] + fov_len * math.cos(angle),
               center[1] + fov_len * math.sin(angle))
        pygame.draw.line(screen, (100, 100, 150), center, end, 1)
    
    # Draw outer boundary circle (slightly beyond 3m) for visual clarity
    outer_radius = int(MAX_RANGE * SCALE * VIEW_SCALE) + 8
    pygame.draw.circle(screen, (50, 50, 65), center, outer_radius, 1)
    
    # Draw obstacles
    for obs in obstacles:
        sx, sy = world_to_screen(obs["x"], obs["y"])
        if 10 < sx < SCENE_W - 10 and 10 < sy < HEIGHT - 10:
            elev = obs["elevation"]
            color = ELEVATION_TYPES[elev]["color"]
            base_size = 8 + abs(ELEVATION_TYPES[elev]["height"]) * 3
            size = max(4, int(base_size * VIEW_SCALE))
            
            # Check if in FOV for highlighting
            dx = obs["x"] - player_x
            dy = obs["y"] - player_y
            dist = math.hypot(dx, dy) / SCALE
            angle = normalize_angle(math.atan2(dy, dx) - player_angle)
            in_fov = abs(math.degrees(angle)) <= 60 and dist <= 3
            
            if in_fov:
                # Highlight obstacles in FOV
                pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), max(5, size) + 4, 2)
            
            if obs["moving"]:
                pulse = int(abs(math.sin(time.time() * 5)) * 3)
                pygame.draw.circle(screen, (255, 255, 100), (int(sx), int(sy)), size + pulse + 3, 2)
            
            # Draw 3D obstacle representation
            draw_3d_obstacle(sx, sy, obs["elevation"], size)
    
    # Draw player with clear ARROW for direction
    pygame.draw.circle(screen, (255, 255, 255), center, 10)
    pygame.draw.circle(screen, (50, 150, 255), center, 8)
    
    # Direction arrow (prominent)
    arrow_len = 28
    arrow_tip = (center[0] + arrow_len * math.cos(player_angle),
                 center[1] + arrow_len * math.sin(player_angle))
    
    # Arrow shaft
    pygame.draw.line(screen, (255, 255, 255), center, arrow_tip, 3)
    
    # Arrow head
    head_len = 12
    head_angle = math.radians(25)
    left_head = (arrow_tip[0] - head_len * math.cos(player_angle - head_angle),
                 arrow_tip[1] - head_len * math.sin(player_angle - head_angle))
    right_head = (arrow_tip[0] - head_len * math.cos(player_angle + head_angle),
                  arrow_tip[1] - head_len * math.sin(player_angle + head_angle))
    pygame.draw.polygon(screen, (255, 255, 255), [arrow_tip, left_head, right_head])
    
    # Facing angle - positioned below the circle for clear visibility
    angle_deg = math.degrees(player_angle) % 360
    
    # Compute cardinal direction
    cardinals = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    cardinal_idx = int(((angle_deg + 22.5) % 360) / 45)
    # Remap: pygame 0°=right, 90°=down, so adjust
    cardinal = cardinals[cardinal_idx]
    
    angle_str = f"Facing: {angle_deg:.0f}°  ({cardinal})"
    angle_text = label_font.render(angle_str, True, (200, 255, 200))
    
    angle_box_w = angle_text.get_width() + 30
    angle_box_h = 40
    angle_box_x = SCENE_W//2 - angle_box_w//2
    angle_box_y = center[1] + int(MAX_RANGE * SCALE * VIEW_SCALE) + 20
    
    pygame.draw.rect(screen, (20, 40, 30), (angle_box_x, angle_box_y, angle_box_w, angle_box_h))
    pygame.draw.rect(screen, (100, 255, 100), (angle_box_x, angle_box_y, angle_box_w, angle_box_h), 2)
    screen.blit(angle_text, (angle_box_x + 15, angle_box_y + 8))
    
    # Legend with background - positioned bottom-left
    y_off = HEIGHT - 135
    legend_bg_height = 130
    pygame.draw.rect(screen, (20, 20, 30), (10, y_off - 5, 180, legend_bg_height))
    pygame.draw.rect(screen, (80, 120, 160), (10, y_off - 5, 180, legend_bg_height), 2)
    
    legend_title = label_font.render("Obstacles:", True, (100, 200, 255))
    screen.blit(legend_title, (20, y_off))
    y_off += 30
    for name, info in ELEVATION_TYPES.items():
        if name != "ground":
            pygame.draw.rect(screen, info["color"], (25, y_off, 14, 14))
            label = small_font.render(info["label"], True, (200, 200, 200))
            screen.blit(label, (48, y_off - 2))
            y_off += 25
    
    # Controls hint with background - bottom
    ctrl_y = HEIGHT - 45
    ctrl_bg_height = 40
    pygame.draw.rect(screen, (20, 20, 30), (10, ctrl_y - 5, SCENE_W - 20, ctrl_bg_height))
    pygame.draw.rect(screen, (100, 150, 200), (10, ctrl_y - 5, SCENE_W - 20, ctrl_bg_height), 1)
    
    ctrl = info_font.render("A/D: Rotate | W/S: Move | R: Reset | ESC: Quit", True, (150, 200, 255))
    screen.blit(ctrl, (20, ctrl_y))

def draw_3d_obstacle(sx, sy, elevation, size):
    """Draw a 3D cuboid obstacle in environment view"""
    elev_info = ELEVATION_TYPES.get(elevation, ELEVATION_TYPES["step"])
    color = elev_info["color"]
    height = abs(elev_info["height"])
    
    # 3D parameters
    cube_w = size * 1.5
    cube_h = height * 15 + 10
    iso_offset = 8  # Isometric offset
    
    if elev_info["height"] < 0:  # Pothole - draw as depression
        pygame.draw.ellipse(screen, (40, 20, 60), (sx - cube_w, sy - cube_w//2, cube_w*2, cube_w))
        pygame.draw.ellipse(screen, color, (sx - cube_w, sy - cube_w//2, cube_w*2, cube_w), 2)
        return
    
    # Bottom face (shadow)
    pygame.draw.polygon(screen, (20, 20, 30), [
        (sx - cube_w//2, sy + 5),
        (sx + cube_w//2, sy + 5),
        (sx + cube_w//2 + iso_offset, sy + 5 - iso_offset//2),
        (sx - cube_w//2 + iso_offset, sy + 5 - iso_offset//2),
    ])
    
    # Right face (darker)
    dark_color = tuple(max(0, c - 60) for c in color)
    pygame.draw.polygon(screen, dark_color, [
        (sx + cube_w//2, sy),
        (sx + cube_w//2, sy - cube_h),
        (sx + cube_w//2 + iso_offset, sy - cube_h - iso_offset//2),
        (sx + cube_w//2 + iso_offset, sy - iso_offset//2),
    ])
    
    # Front face
    pygame.draw.rect(screen, color, (sx - cube_w//2, sy - cube_h, cube_w, cube_h))
    
    # Top face (lighter)
    light_color = tuple(min(255, c + 40) for c in color)
    pygame.draw.polygon(screen, light_color, [
        (sx - cube_w//2, sy - cube_h),
        (sx + cube_w//2, sy - cube_h),
        (sx + cube_w//2 + iso_offset, sy - cube_h - iso_offset//2),
        (sx - cube_w//2 + iso_offset, sy - cube_h - iso_offset//2),
    ])
    
    # Edges
    pygame.draw.rect(screen, (255, 255, 255), (sx - cube_w//2, sy - cube_h, cube_w, cube_h), 1)

# -----------------------
# FIRST-PERSON PERSPECTIVE VIEW (Blind Navigation)
# -----------------------
def draw_first_person_view():
    """Draw first-person 3D perspective view showing ground plane with cuboid obstacles"""
    
    horizon_y = int(HEIGHT * 0.42)
    focal = (SCENE_W / 2) / math.tan(FOV / 2)
    
    def project(x, y, z):
        """Project 3D point to screen. x=right, y=up, z=forward in meters."""
        if z <= 0.05:
            return None
        sx = SCENE_W / 2 + (x / z) * focal
        sy = horizon_y - ((y - CAMERA_HEIGHT) / z) * focal
        return (sx, sy)
    
    def apply_fade(col, f):
        return tuple(max(0, min(255, int(comp * f))) for comp in col)
    
    # --- Sky ---
    pygame.draw.rect(screen, (12, 15, 35), (0, 0, SCENE_W, horizon_y))
    # Horizon glow
    for i in range(40):
        y = horizon_y - i
        if y >= 0:
            a = int(40 - i)
            pygame.draw.line(screen, (12 + a // 2, 18 + a // 2, 40 + a), (0, y), (SCENE_W, y))
    
    # --- Ground ---
    pygame.draw.rect(screen, (25, 35, 25), (0, horizon_y, SCENE_W, HEIGHT - horizon_y))
    # Slight gradient near bottom
    for i in range(25):
        y = HEIGHT - i
        if y > horizon_y:
            c = 30 + i
            pygame.draw.line(screen, (c - 8, c + 3, c - 8), (0, y), (SCENE_W, y))
    
    # --- Horizon line ---
    pygame.draw.line(screen, (60, 70, 90), (0, horizon_y), (SCENE_W, horizon_y), 2)
    
    # --- Ground grid lines for depth perception ---
    for d in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]:
        gy = horizon_y + (CAMERA_HEIGHT / d) * focal
        if horizon_y < gy < HEIGHT:
            intensity = max(18, int(50 - d * 4))
            pygame.draw.line(screen, (intensity, intensity + 6, intensity),
                             (0, int(gy)), (SCENE_W, int(gy)), 1)
    
    # Vertical perspective grid lines
    for lateral in [-3, -2, -1, 0, 1, 2, 3]:
        pts = []
        for d in [0.8, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]:
            p = project(lateral, 0, d)
            if p and 0 <= p[0] <= SCENE_W and horizon_y <= p[1] <= HEIGHT:
                pts.append((int(p[0]), int(p[1])))
        if len(pts) >= 2:
            pygame.draw.lines(screen, (30, 38, 30), False, pts, 1)
    
    # --- Distance zone markers (1m, 2m, 3m) ---
    zone_colors = [(200, 80, 80), (200, 200, 80), (100, 200, 100)]
    zone_labels = ["1m - IMMEDIATE", "2m - NEAR", "3m - FAR"]
    for i, d in enumerate([1.0, 2.0, 3.0]):
        gy = horizon_y + (CAMERA_HEIGHT / d) * focal
        if horizon_y < gy < HEIGHT:
            pygame.draw.line(screen, zone_colors[i], (0, int(gy)), (SCENE_W, int(gy)), 2)
            label = small_font.render(zone_labels[i], True, zone_colors[i])
            screen.blit(label, (SCENE_W - label.get_width() - 10, int(gy) - 18))
    
    # --- Direction zone dividers (-20 deg and +20 deg) ---
    for angle_off_deg in [-20, 20]:
        tan_a = math.tan(math.radians(angle_off_deg))
        sx = SCENE_W / 2 + tan_a * focal
        if 0 <= sx <= SCENE_W:
            pygame.draw.line(screen, (60, 60, 100), (int(sx), horizon_y), (int(sx), HEIGHT), 1)
    
    # Direction zone labels
    for label_text, angle_deg in [("LEFT", -40), ("CENTER", 0), ("RIGHT", 40)]:
        tan_a = math.tan(math.radians(angle_deg))
        sx = SCENE_W / 2 + tan_a * focal
        lbl = small_font.render(label_text, True, (90, 90, 130))
        screen.blit(lbl, (int(sx) - lbl.get_width() // 2, horizon_y + 8))
    
    # --- Collect visible obstacles ---
    cos_a = math.cos(player_angle)
    sin_a = math.sin(player_angle)
    
    visible = []
    for obs in obstacles:
        dx = obs["x"] - player_x
        dy = obs["y"] - player_y
        
        # Transform to camera space
        forward = dx * cos_a + dy * sin_a       # along player facing
        right = -dx * sin_a + dy * cos_a        # perpendicular (+ is right)
        
        forward_m = forward / SCALE
        right_m = right / SCALE
        
        if forward_m < 0.15:
            continue
        if forward_m > MAX_RANGE + 2:
            continue
        
        hw = obs.get("cube_w", 0.3)
        ang = math.atan2(abs(right_m), forward_m)
        margin = math.atan2(hw, forward_m) if forward_m > 0.1 else 0
        if ang > FOV / 2 + margin:
            continue
        
        visible.append({
            "obs": obs,
            "forward_m": forward_m,
            "right_m": right_m,
        })
    
    # Sort far-to-near (painter's algorithm)
    visible.sort(key=lambda v: -v["forward_m"])
    
    # --- Draw obstacles as 3D cuboids ---
    for v in visible:
        obs = v["obs"]
        fm = v["forward_m"]
        rm = v["right_m"]
        
        elev = obs["elevation"]
        elev_info = ELEVATION_TYPES[elev]
        color = elev_info["color"]
        
        hw = obs.get("cube_w", 0.3)
        hd = obs.get("cube_d", 0.3)
        ch = obs.get("cube_h", 0.5)
        is_pothole = elev_info["height"] < 0
        
        # Distance fade
        fade = max(0.35, 1.0 - (fm / (MAX_RANGE + 1)) * 0.5)
        
        if is_pothole:
            # Draw pothole as a dark depression on the ground plane
            corners = [
                project(rm - hw, 0, fm - hd),
                project(rm + hw, 0, fm - hd),
                project(rm + hw, 0, fm + hd),
                project(rm - hw, 0, fm + hd),
            ]
            if all(c is not None for c in corners):
                pygame.draw.polygon(screen, apply_fade((40, 20, 60), fade), corners)
                pygame.draw.polygon(screen, apply_fade(color, fade), corners, 2)
                # Depth lines inward
                inner = [
                    project(rm - hw * 0.5, -ch, fm - hd * 0.5),
                    project(rm + hw * 0.5, -ch, fm - hd * 0.5),
                    project(rm + hw * 0.5, -ch, fm + hd * 0.5),
                    project(rm - hw * 0.5, -ch, fm + hd * 0.5),
                ]
                if all(c is not None for c in inner):
                    pygame.draw.polygon(screen, apply_fade((20, 10, 30), fade), inner)
                    for j in range(4):
                        pygame.draw.line(screen, apply_fade((60, 30, 80), fade),
                                         corners[j], inner[j], 1)
        else:
            # --- Draw cuboid ---
            # 8 corners: ground (y=0) and top (y=ch)
            gfl = project(rm - hw, 0, fm - hd)
            gfr = project(rm + hw, 0, fm - hd)
            gbr = project(rm + hw, 0, fm + hd)
            gbl = project(rm - hw, 0, fm + hd)
            tfl = project(rm - hw, ch, fm - hd)
            tfr = project(rm + hw, ch, fm - hd)
            tbr = project(rm + hw, ch, fm + hd)
            tbl = project(rm - hw, ch, fm + hd)
            
            all_corners = [gfl, gfr, gbr, gbl, tfl, tfr, tbr, tbl]
            if any(c is None for c in all_corners):
                continue
            
            front_color = apply_fade(color, fade)
            dark_color = apply_fade(tuple(max(0, c - 60) for c in color), fade)
            light_color = apply_fade(tuple(min(255, c + 40) for c in color), fade)
            edge_color = apply_fade((200, 200, 200), fade)
            
            # Side face (draw first so front overlaps it)
            if rm > 0.02:  # Obstacle to our right → we see its LEFT face
                face = [gfl, gbl, tbl, tfl]
                pygame.draw.polygon(screen, dark_color, face)
                pygame.draw.polygon(screen, edge_color, face, 1)
            elif rm < -0.02:  # Obstacle to our left → we see its RIGHT face
                face = [gfr, gbr, tbr, tfr]
                pygame.draw.polygon(screen, dark_color, face)
                pygame.draw.polygon(screen, edge_color, face, 1)
            
            # Front face
            front = [gfl, gfr, tfr, tfl]
            pygame.draw.polygon(screen, front_color, front)
            pygame.draw.polygon(screen, edge_color, front, 1)
            
            # Top face (visible when cuboid is shorter than camera height)
            if ch < CAMERA_HEIGHT:
                top = [tfl, tfr, tbr, tbl]
                pygame.draw.polygon(screen, light_color, top)
                pygame.draw.polygon(screen, edge_color, top, 1)
            
            # Proximity warning glow for immediate zone (< 1m)
            if fm < 1.0:
                pulse = (math.sin(time.time() * 6) + 1) / 2
                glow_r = int(255 * pulse)
                glow_g = int(50 * pulse)
                pygame.draw.polygon(screen, (glow_r, glow_g, glow_g), front, 3)
            
            # Moving indicator
            if obs.get("moving"):
                pulse = (math.sin(time.time() * 8) + 1) / 2
                mov_color = (255, int(255 * pulse), 50)
                pygame.draw.polygon(screen, mov_color, front, 2)
    
    # --- Title ---
    title = title_font.render("Player View (Blind Navigation)", True, (200, 200, 200))
    title_box_h = 45
    pygame.draw.rect(screen, (30, 30, 50), (0, 5, SCENE_W, title_box_h))
    pygame.draw.rect(screen, (100, 200, 255), (0, 5, SCENE_W, title_box_h), 2)
    screen.blit(title, (SCENE_W // 2 - title.get_width() // 2, 12))
    
    # --- Facing direction ---
    angle_deg = math.degrees(player_angle) % 360
    cardinals = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    cardinal_idx = int(((angle_deg + 22.5) % 360) / 45)
    cardinal = cardinals[cardinal_idx]
    angle_str = f"Facing: {angle_deg:.0f}\u00b0 ({cardinal})"
    angle_text = label_font.render(angle_str, True, (200, 255, 200))
    angle_box_w = angle_text.get_width() + 30
    angle_box_h = 40
    angle_box_x = SCENE_W // 2 - angle_box_w // 2
    angle_box_y = HEIGHT - 90
    pygame.draw.rect(screen, (20, 40, 30), (angle_box_x, angle_box_y, angle_box_w, angle_box_h))
    pygame.draw.rect(screen, (100, 255, 100), (angle_box_x, angle_box_y, angle_box_w, angle_box_h), 2)
    screen.blit(angle_text, (angle_box_x + 15, angle_box_y + 8))
    
    # --- Legend ---
    y_off = 60
    legend_bg_h = 130
    pygame.draw.rect(screen, (20, 20, 30), (10, y_off - 5, 180, legend_bg_h))
    pygame.draw.rect(screen, (80, 120, 160), (10, y_off - 5, 180, legend_bg_h), 2)
    legend_title = label_font.render("Obstacles:", True, (100, 200, 255))
    screen.blit(legend_title, (20, y_off))
    y_off += 30
    for name, einfo in ELEVATION_TYPES.items():
        if name != "ground":
            pygame.draw.rect(screen, einfo["color"], (25, y_off, 14, 14))
            lbl = small_font.render(einfo["label"], True, (200, 200, 200))
            screen.blit(lbl, (48, y_off - 2))
            y_off += 25
    
    # --- Controls ---
    ctrl_y = HEIGHT - 45
    pygame.draw.rect(screen, (20, 20, 30), (10, ctrl_y - 5, SCENE_W - 20, 40))
    pygame.draw.rect(screen, (100, 150, 200), (10, ctrl_y - 5, SCENE_W - 20, 40), 1)
    ctrl = info_font.render("A/D: Rotate | W/S: Move | R: Reset | ESC: Quit", True, (150, 200, 255))
    screen.blit(ctrl, (20, ctrl_y))

# -----------------------
# 3D ISOMETRIC TACTILE GRID
# -----------------------
def draw_isometric_grid(heights, vibration, cell_obstacles):
    """Draw isometric 3D tactile grid like the reference image"""
    panel_x = SCENE_W
    panel_w = WIDTH - SCENE_W
    
    # Background with gradient
    for y in range(HEIGHT):
        gray = int(40 + (y / HEIGHT) * 30)
        pygame.draw.line(screen, (gray, gray, gray + 5), (panel_x, y), (WIDTH, y))
    
    # Draw top border with accent color
    pygame.draw.line(screen, (100, 150, 200), (panel_x, 0), (WIDTH, 0), 3)
    
    # Title with background box
    title = title_font.render("3×3 Tactile Grid Device", True, (220, 220, 220))
    title_box_height = 45
    pygame.draw.rect(screen, (30, 30, 50), (panel_x, 5, panel_w, title_box_height))
    pygame.draw.rect(screen, (100, 150, 200), (panel_x, 5, panel_w, title_box_height), 2)
    screen.blit(title, (panel_x + panel_w//2 - title.get_width()//2, 12))
    
    # Isometric grid parameters - optimized for new window size
    grid_center_x = panel_x + panel_w // 2
    grid_center_y = HEIGHT // 2 + 60
    
    cell_w = 120  # Cell width in isometric view
    cell_h = 80   # Cell depth in isometric view
    
    # Isometric transformation
    iso_angle = math.radians(30)
    
    def iso_transform(col, row):
        """Transform grid position to isometric screen coordinates"""
        # Center the grid
        gc = col - 1  # -1, 0, 1
        gr = 1 - row   # Flipped: row 0 (IMM) at front/bottom-left, row 2 (FAR) at back/top-right
        
        ix = grid_center_x + (gc - gr) * cell_w * 0.6
        iy = grid_center_y + (gc + gr) * cell_h * 0.5
        return ix, iy
    
    # Draw grid from back to front for proper overlap
    t = time.time()
    
    # Draw row labels (Distance) - positioned on separate left panel
    row_label_panel_x = panel_x + 15
    row_label_panel_y = grid_center_y - 160
    row_box_width = 140
    row_boxes = []  # Store box positions for later reference
    
    # Distance header
    row_header = label_font.render("DISTANCE", True, (100, 200, 255))
    screen.blit(row_header, (row_label_panel_x, grid_center_y - 200))
    
    # Draw each distance category as a separate labeled box
    row_names = ["IMMEDIATE", "NEAR", "FAR"]
    row_ranges = ["0-1m", "1-2m", "2-3m"]
    row_colors = [(200, 80, 80), (200, 200, 80), (100, 200, 100)]
    
    for r, (name, range_text, color) in enumerate(zip(row_names, row_ranges, row_colors)):
        box_y = row_label_panel_y + r * 70
        row_boxes.append((row_label_panel_x, box_y, row_box_width, 65))
        
        # Draw background box
        pygame.draw.rect(screen, (25, 25, 40), (row_label_panel_x, box_y, row_box_width, 65))
        pygame.draw.rect(screen, color, (row_label_panel_x, box_y, row_box_width, 65), 2)
        
        # Draw colored indicator bar on left
        pygame.draw.rect(screen, color, (row_label_panel_x - 8, box_y, 8, 65))
        
        # Draw text
        distance_label = label_font.render(name, True, (220, 220, 220))
        range_label = small_font.render(range_text, True, color)
        screen.blit(distance_label, (row_label_panel_x + 8, box_y + 12))
        screen.blit(range_label, (row_label_panel_x + 8, box_y + 38))
    
    # Draw column labels at bottom with better spacing
    col_header_y = HEIGHT - 110
    col_header = label_font.render("DIRECTION", True, (100, 200, 255))
    screen.blit(col_header, (grid_center_x - col_header.get_width()//2, col_header_y))
    
    for c in range(3):
        ix, _ = iso_transform(c, 3.5)
        col_y = HEIGHT - 65
        
        # Draw background box
        col_width = 130
        col_height = 50
        col_colors_list = [(255, 100, 100), (100, 255, 100), (100, 100, 255)]
        col_color = col_colors_list[c]
        
        pygame.draw.rect(screen, (25, 25, 40), (ix - col_width//2, col_y, col_width, col_height))
        pygame.draw.rect(screen, col_color, (ix - col_width//2, col_y, col_width, col_height), 2)
        
        # Draw colored bar on top
        pygame.draw.rect(screen, col_color, (ix - col_width//2, col_y - 5, col_width, 5))
        
        # Draw label
        col_labels_list = ["LEFT", "CENTER", "RIGHT"]
        label = label_font.render(col_labels_list[c], True, col_color)
        screen.blit(label, (ix - label.get_width()//2, col_y + 10))
    
    # Add visual separator line between left panel and grid
    pygame.draw.line(screen, (80, 100, 130), (row_label_panel_x + row_box_width + 15, grid_center_y - 220), 
                     (row_label_panel_x + row_box_width + 15, grid_center_y + 180), 2)
    
    # Draw grid cells and cuboids (back to front: FAR first, then NEAR, then IMM)
    for row in range(2, -1, -1):  # Distance: 2=far(back) drawn first, 0=immediate(front) last
        for col in range(3):  # Direction: 0=left, 1=center, 2=right
            ix, iy = iso_transform(col, row)
            h = heights[row][col]
            vib = vibration[row][col]
            # Draw base plate
            draw_iso_base_plate(ix, iy, cell_w * 0.55, cell_h * 0.5)
            # Draw cuboid if there's an obstacle
            if h != 0:
                vib_offset = 0
                if vib == "fast":
                    vib_offset = math.sin(t * 25) * 4
                elif vib == "slow":
                    vib_offset = math.sin(t * 10) * 2
                draw_iso_cuboid(ix + vib_offset, iy, h, vib, t)
    
    # Info panel at bottom with background
    info_y = HEIGHT - 32
    safe_dir = compute_safe_direction(heights)
    
    # Draw info panel background
    pygame.draw.rect(screen, (25, 25, 40), (panel_x, info_y - 5, panel_w, 35))
    pygame.draw.line(screen, (100, 120, 150), (panel_x, info_y - 5), (WIDTH, info_y - 5), 1)
    
    # Info panel with corrected direction
    safe_dir_label = ['Left', 'Center', 'Right']
    safe_dir_color = (100, 200, 100) if safe_dir is None else (200, 200, 100)
    safe_text = safe_dir_label[safe_dir] if safe_dir is not None else 'All Clear'
    
    info_parts = [
        f"t={timestep}",
        "5Hz",
        "0-3m",
        "120°",
        f"Safe: {safe_text}"
    ]
    info_labels = ["Timestep:", "Rate:", "Range:", "FOV:", "Direction:"]
    
    x_pos = panel_x + 15
    for label, value in zip(info_labels, info_parts):
        label_surf = small_font.render(label, True, (150, 150, 180))
        value_color = safe_dir_color if "Safe" in label else (200, 200, 200)
        value_surf = small_font.render(value, True, value_color)
        screen.blit(label_surf, (x_pos, info_y))
        screen.blit(value_surf, (x_pos + label_surf.get_width() + 5, info_y))
        x_pos += label_surf.get_width() + value_surf.get_width() + 50

def draw_iso_base_plate(cx, cy, w, h):
    """Draw isometric base plate (black platform)"""
    # Isometric diamond shape
    points = [
        (cx, cy - h),      # Top
        (cx + w, cy),      # Right
        (cx, cy + h),      # Bottom
        (cx - w, cy),      # Left
    ]
    
    # Shadow
    shadow_points = [(p[0] + 3, p[1] + 3) for p in points]
    pygame.draw.polygon(screen, (15, 15, 20), shadow_points)
    
    # Base plate
    pygame.draw.polygon(screen, (25, 25, 30), points)
    pygame.draw.polygon(screen, (60, 60, 70), points, 2)
    
    # Side faces for 3D effect
    depth = 8
    # Right side
    pygame.draw.polygon(screen, (20, 20, 25), [
        points[1], points[2],
        (points[2][0], points[2][1] + depth),
        (points[1][0], points[1][1] + depth),
    ])
    # Bottom side
    pygame.draw.polygon(screen, (15, 15, 20), [
        points[2], points[3],
        (points[3][0], points[3][1] + depth),
        (points[2][0], points[2][1] + depth),
    ])

def draw_iso_cuboid(cx, cy, height_val, vibration, t):
    """Draw isometric 3D cuboid based on height value"""
    # Cuboid dimensions
    w = 35  # Half-width
    d = 20  # Half-depth (isometric)
    
    # Height calculation - taller for higher obstacles
    max_h = 150
    h = abs(height_val) / 3.0 * max_h
    h = max(20, h)  # Minimum height
    
    # Color based on elevation type and distance attenuation
    if height_val < 0:  # Pothole
        base_color = (120, 60, 180)  # Purple
    elif abs(height_val) < 0.8:
        base_color = (80, 220, 80)   # Green - step
    elif abs(height_val) < 1.5:
        base_color = (80, 200, 80)   # Green - mid  
    else:
        base_color = (60, 230, 60)   # Bright green - top
    
    # Vibration color effect
    pulse = (math.sin(t * 8) + 1) / 2
    if vibration == "fast":
        base_color = (255, int(80 + 80 * pulse), int(80 + 80 * pulse))
    elif vibration == "slow":
        base_color = (int(80 + 80 * pulse), int(80 + 80 * pulse), 255)
    
    # Calculate face colors
    front_color = base_color
    right_color = tuple(max(0, c - 50) for c in base_color)
    top_color = tuple(min(255, c + 30) for c in base_color)
    
    if height_val < 0:  # Pothole - draw as depression
        # Draw hole
        hole_points = [
            (cx, cy - d),
            (cx + w, cy),
            (cx, cy + d),
            (cx - w, cy),
        ]
        pygame.draw.polygon(screen, (30, 15, 45), hole_points)
        pygame.draw.polygon(screen, base_color, hole_points, 2)
        
        # Depth lines
        inner_scale = 0.6
        inner_points = [(cx + (p[0]-cx)*inner_scale, cy + (p[1]-cy)*inner_scale + 15) for p in hole_points]
        for i in range(4):
            pygame.draw.line(screen, (80, 40, 100), hole_points[i], inner_points[i], 1)
        pygame.draw.polygon(screen, (20, 10, 30), inner_points)
        return
    
    # Top face (diamond)
    top_y = cy - h
    top_points = [
        (cx, top_y - d),      # Top
        (cx + w, top_y),      # Right
        (cx, top_y + d),      # Bottom
        (cx - w, top_y),      # Left
    ]
    
    # Right face
    right_points = [
        (cx + w, top_y),
        (cx, top_y + d),
        (cx, cy + d),
        (cx + w, cy),
    ]
    
    # Left/front face
    front_points = [
        (cx - w, top_y),
        (cx, top_y + d),
        (cx, cy + d),
        (cx - w, cy),
    ]
    
    # Draw faces (back to front)
    pygame.draw.polygon(screen, right_color, right_points)
    pygame.draw.polygon(screen, (255, 255, 255), right_points, 1)
    
    pygame.draw.polygon(screen, front_color, front_points)
    pygame.draw.polygon(screen, (255, 255, 255), front_points, 1)
    
    pygame.draw.polygon(screen, top_color, top_points)
    pygame.draw.polygon(screen, (255, 255, 255), top_points, 1)
    
    # Edge highlights
    pygame.draw.line(screen, (255, 255, 255), (cx - w, top_y), (cx - w, cy), 1)
    pygame.draw.line(screen, (255, 255, 255), (cx, top_y + d), (cx, cy + d), 1)

# -----------------------
# DRAW TACTILE DEVICE (wrapper)
# -----------------------
def draw_tactile_device(heights, vibration, cell_obstacles):
    draw_isometric_grid(heights, vibration, cell_obstacles)

# -----------------------
# MAIN LOOP
# -----------------------
def main():
    global player_x, player_y, player_angle, last_update
    
    running = True
    
    print("=" * 60)
    print("Directional Tactile Navigation Device Simulation")
    print("3×3 Tactile Grid Model")
    print("=" * 60)
    print("\nControls:")
    print("  W/S - Move forward/backward")
    print("  A/D - Rotate left/right")
    print("  R   - Reset obstacles")
    print("  ESC - Quit")
    print("\nTactile Encoding:")
    print("  Green  = Step (can step over)")
    print("  Yellow = Mid (deflect/redirect)")
    print("  Red    = Top (avoid - head level)")
    print("  Purple = Pothole (drop below surface)")
    print("  Vibration = Moving obstacle")
    print("=" * 60)
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    generate_obstacles()
                    print("Obstacles reset!")
        
        # Input handling
        pressed = pygame.key.get_pressed()
        
        # WASD and Arrow keys
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            new_x = player_x + math.cos(player_angle) * speed
            new_y = player_y + math.sin(player_angle) * speed
            if 50 < new_x < WORLD_SIZE - 50 and 50 < new_y < WORLD_SIZE - 50:
                player_x = new_x
                player_y = new_y
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            new_x = player_x - math.cos(player_angle) * speed
            new_y = player_y - math.sin(player_angle) * speed
            if 50 < new_x < WORLD_SIZE - 50 and 50 < new_y < WORLD_SIZE - 50:
                player_x = new_x
                player_y = new_y
        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            player_angle -= rot_speed
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            player_angle += rot_speed
        
        # Update at 5 Hz
        current_time = time.time()
        if current_time - last_update >= 1.0 / UPDATE_RATE:
            update_obstacles()
            last_update = current_time
        
        # Compute tactile grid
        heights, vibration, cell_obstacles = compute_tactile_grid()
        
        # Draw
        screen.fill((0, 0, 0))
        draw_first_person_view()
        draw_tactile_device(heights, vibration, cell_obstacles)
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()
