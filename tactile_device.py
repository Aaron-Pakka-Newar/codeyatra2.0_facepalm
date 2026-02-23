import pygame
import random
import math
import time

# Initialize pygame
pygame.init()

# -----------------------
# WINDOW SETUP (Resolution Adaptive)
# -----------------------
# Get display resolution
_info = pygame.display.Info()
MONITOR_WIDTH = _info.current_w
MONITOR_HEIGHT = _info.current_h

# Base design resolution (all layout authored at this size)
BASE_WIDTH = 1600
BASE_HEIGHT = 1000

# Account for taskbar + title bar (~70 px on Windows)
USABLE_W = MONITOR_WIDTH
USABLE_H = MONITOR_HEIGHT - 70

# Fit within usable area while keeping 16:10 aspect
_target_w = min(USABLE_W, BASE_WIDTH)
_target_h = int(_target_w * BASE_HEIGHT / BASE_WIDTH)
if _target_h > USABLE_H:
    _target_h = USABLE_H
    _target_w = int(_target_h * BASE_WIDTH / BASE_HEIGHT)

WIDTH = _target_w
HEIGHT = _target_h
SCENE_W = WIDTH // 2
SCALE_FACTOR = WIDTH / BASE_WIDTH

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Directional Tactile Navigation Device - 3×3 Grid Simulation")
clock = pygame.time.Clock()

# Fonts (rebuilt on resize)
pygame.font.init()
title_font = label_font = small_font = info_font = None

def rebuild_fonts():
    global title_font, label_font, small_font, info_font
    title_font = pygame.font.Font(None, max(20, int(40 * SCALE_FACTOR)))
    label_font = pygame.font.Font(None, max(16, int(30 * SCALE_FACTOR)))
    small_font = pygame.font.Font(None, max(13, int(24 * SCALE_FACTOR)))
    info_font  = pygame.font.Font(None, max(12, int(22 * SCALE_FACTOR)))

def handle_resize(new_w, new_h):
    """Recalculate all layout globals after a window resize."""
    global WIDTH, HEIGHT, SCENE_W, SCALE_FACTOR, screen
    WIDTH = max(800, new_w)
    HEIGHT = max(500, new_h)
    SCENE_W = WIDTH // 2
    SCALE_FACTOR = WIDTH / BASE_WIDTH
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    rebuild_fonts()

rebuild_fonts()

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
    "shallow_pothole": {"height": -1, "color": (140, 90, 200), "label": "Shallow Pit"},
    "cliff_pothole": {"height": -3, "color": (180, 30, 30), "label": "Cliff (Danger)"},
    "step": {"height": 1, "color": (100, 200, 100), "label": "Step"},
    "mid": {"height": 2, "color": (220, 180, 60), "label": "Mid"},
    "top": {"height": 3, "color": (255, 80, 80), "label": "Top/Head"}
}

# -----------------------
# WORLD SETTINGS
# -----------------------
WORLD_SIZE = 1000  # pixels (10m x 10m world)
NUM_OBSTACLES = 14  # Reduced for more walking room
MIN_OBSTACLE_SPACING = 60  # Minimum pixels between obstacle centres
WALL_BOUNDARY = 50         # Wall outer edge in pixels
WALL_THICKNESS_PX = 30     # Wall thickness in pixels
WALL_INNER = WALL_BOUNDARY + WALL_THICKNESS_PX  # Inner edge of walls
WALL_HEIGHT_M = 3.5        # Wall height in metres (taller than top/red obstacles)

player_x = WORLD_SIZE // 2
player_y = WORLD_SIZE // 2
player_angle = -math.pi / 2  # Facing up initially (0° = right, -90° = up)

speed = 5
rot_speed = 0.06

# Player vertical state (for pothole falling & jumping)
player_y_offset = 0.0       # Current camera Y offset in meters (negative = below ground)
player_y_target = 0.0       # Target Y offset (smoothly interpolated)
player_in_pothole = False   # Whether player is currently in a shallow pothole
player_jumping = False      # Whether player is currently in a jump
player_jump_velocity = 0.0  # Current jump vertical velocity
JUMP_STRENGTH = 4.0         # Initial upward velocity (m/s)
GRAVITY = 12.0              # Gravity acceleration (m/s²)
FALL_SPEED = 3.0            # Speed of falling into pothole (m/s)
POTHOLE_DEPTH = -0.8        # How deep the camera drops in a shallow pothole (meters)

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
    elevation_choices = ["step", "mid", "top", "shallow_pothole", "cliff_pothole"]
    weights = [0.25, 0.3, 0.15, 0.15, 0.15]
    
    # Generate obstacles in a ring around the player (within detectable range)
    for _ in range(NUM_OBSTACLES):
        # Try several times to find a non-overlapping position
        for _attempt in range(30):
            # Random distance between 0.8m and 4m (some outside range)
            dist = random.uniform(80, 400)  # 0.8m to 4m in pixels
            ang = random.uniform(0, 2 * math.pi)
            
            x = player_x + dist * math.cos(ang)
            y = player_y + dist * math.sin(ang)
            
            # Keep within world bounds (with wall margin)
            x = max(80, min(WORLD_SIZE - 80, x))
            y = max(80, min(WORLD_SIZE - 80, y))
            
            # Check spacing against already-placed obstacles
            too_close = False
            for existing in obstacles:
                if math.hypot(x - existing["x"], y - existing["y"]) < MIN_OBSTACLE_SPACING:
                    too_close = True
                    break
            if not too_close:
                break
        
        elev = random.choices(elevation_choices, weights)[0]
        # Potholes are always static
        is_pothole = elev in ("shallow_pothole", "cliff_pothole")
        is_moving = False if is_pothole else (random.random() < 0.25)
        vx = random.uniform(-3.5, 3.5) if is_moving else 0
        vy = random.uniform(-3.5, 3.5) if is_moving else 0
        
        # Random cuboid dimensions (in meters)
        height_ranges = {
            "step": (0.2, 0.5),
            "mid": (0.6, 1.2),
            "top": (1.5, 2.0),
            "shallow_pothole": (0.15, 0.4),
            "cliff_pothole": (0.8, 1.5)
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
    sx = (SCENE_W / 2) + (wx - player_x) * VIEW_SCALE
    sy = (HEIGHT / 2) + (wy - player_y) * VIEW_SCALE
    return sx, sy

def scale_px(base_px):
    """Scale pixel value based on current resolution"""
    return int(base_px * SCALE_FACTOR)

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
# Player collision radius in pixels
PLAYER_RADIUS = 15  # ~0.15m

def check_collision(px, py):
    """Return True if position (px, py) collides with any obstacle or wall."""
    # --- Wall collision ---
    if (px <= WALL_INNER or px >= WORLD_SIZE - WALL_INNER or
        py <= WALL_INNER or py >= WORLD_SIZE - WALL_INNER):
        return True
    # --- Obstacle collision ---
    for obs in obstacles:
        hw_px = obs["cube_w"] * SCALE  # half-width in pixels
        hd_px = obs["cube_d"] * SCALE  # half-depth in pixels
        # Expand obstacle bounds by player radius for circle-vs-AABB collision
        if (obs["x"] - hw_px - PLAYER_RADIUS < px < obs["x"] + hw_px + PLAYER_RADIUS and
            obs["y"] - hd_px - PLAYER_RADIUS < py < obs["y"] + hd_px + PLAYER_RADIUS):
            elev = obs["elevation"]
            # Cliff potholes ALWAYS block movement
            if elev == "cliff_pothole":
                return True
            # Mid and top obstacles block (unless jumping over step)
            if elev in ("mid", "top"):
                return True
            # Step obstacles block UNLESS player is jumping
            if elev == "step" and not player_jumping:
                return True
            # shallow_pothole: never blocks, player falls in
    return False


def get_pothole_at_player():
    """Check if player is standing inside a shallow pothole. Returns the obstacle or None."""
    for obs in obstacles:
        if obs["elevation"] != "shallow_pothole":
            continue
        hw_px = obs["cube_w"] * SCALE
        hd_px = obs["cube_d"] * SCALE
        if (obs["x"] - hw_px - PLAYER_RADIUS < player_x < obs["x"] + hw_px + PLAYER_RADIUS and
            obs["y"] - hd_px - PLAYER_RADIUS < player_y < obs["y"] + hd_px + PLAYER_RADIUS):
            return obs
    return None


def update_player_vertical(dt):
    """Update player vertical position (pothole falling / jumping)."""
    global player_y_offset, player_y_target, player_in_pothole
    global player_jumping, player_jump_velocity

    # --- Jumping logic ---
    if player_jumping:
        player_jump_velocity -= GRAVITY * dt
        player_y_offset += player_jump_velocity * dt
        # Landed
        if player_y_offset <= 0.0 and player_jump_velocity < 0:
            player_y_offset = 0.0
            player_jumping = False
            player_jump_velocity = 0.0
            player_in_pothole = False  # Jump fully exits any pothole
        return  # Skip pothole logic while airborne

    # --- Pothole falling logic ---
    pothole = get_pothole_at_player()
    if pothole is not None and not player_in_pothole:
        # Just entered a shallow pothole - start falling
        player_in_pothole = True
        player_y_target = POTHOLE_DEPTH
    elif pothole is None and player_in_pothole and not player_jumping:
        # Walked out without jumping (shouldn't normally happen since
        # we require jump, but handle gracefully)
        player_in_pothole = False
        player_y_target = 0.0

    # Smooth interpolation toward target
    if player_in_pothole:
        player_y_target = POTHOLE_DEPTH
    diff = player_y_target - player_y_offset
    if abs(diff) > 0.005:
        player_y_offset += diff * min(1.0, FALL_SPEED * dt * 5)
    else:
        player_y_offset = player_y_target


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
    pygame.draw.line(screen, (100, 200, 255), (0, 0), (SCENE_W, 0), scale_px(3))
    
    # Title with background box
    title = title_font.render("Environment View (Top-Down)", True, (200, 200, 200))
    title_box_height = scale_px(45)
    pygame.draw.rect(screen, (30, 30, 50), (0, scale_px(5), SCENE_W, title_box_height))
    pygame.draw.rect(screen, (100, 200, 255), (0, scale_px(5), SCENE_W, title_box_height), scale_px(2))
    screen.blit(title, (SCENE_W//2 - title.get_width()//2, scale_px(12)))
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
    pygame.draw.polygon(screen, (80, 100, 140), fov_points, scale_px(2))
    
    # Distance rings (1m, 2m, 3m) with improved labels
    ring_colors = [(80, 200, 80), (200, 200, 80), (200, 80, 80)]
    for i, (row, info) in enumerate(DISTANCE_LAYERS.items()):
        radius = int(info["range"][1] * SCALE * VIEW_SCALE)
        pygame.draw.circle(screen, ring_colors[i], center, radius, scale_px(2))
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
        pygame.draw.line(screen, (100, 100, 150), center, end, scale_px(1))
    
    # Draw outer boundary circle (slightly beyond 3m) for visual clarity
    outer_radius = int(MAX_RANGE * SCALE * VIEW_SCALE) + scale_px(8)
    pygame.draw.circle(screen, (50, 50, 65), center, outer_radius, scale_px(1))
    
    # Draw thick white boundary walls in top-down view
    wall_corners = [
        (WALL_BOUNDARY, WALL_BOUNDARY),
        (WORLD_SIZE - WALL_BOUNDARY, WALL_BOUNDARY),
        (WORLD_SIZE - WALL_BOUNDARY, WORLD_SIZE - WALL_BOUNDARY),
        (WALL_BOUNDARY, WORLD_SIZE - WALL_BOUNDARY),
    ]
    inner_corners = [
        (WALL_INNER, WALL_INNER),
        (WORLD_SIZE - WALL_INNER, WALL_INNER),
        (WORLD_SIZE - WALL_INNER, WORLD_SIZE - WALL_INNER),
        (WALL_INNER, WORLD_SIZE - WALL_INNER),
    ]
    for i in range(4):
        j = (i + 1) % 4
        o1 = world_to_screen(*wall_corners[i])
        o2 = world_to_screen(*wall_corners[j])
        i1 = world_to_screen(*inner_corners[i])
        i2 = world_to_screen(*inner_corners[j])
        pts = [(int(o1[0]), int(o1[1])), (int(o2[0]), int(o2[1])),
               (int(i2[0]), int(i2[1])), (int(i1[0]), int(i1[1]))]
        pygame.draw.polygon(screen, (200, 200, 200), pts)
        pygame.draw.polygon(screen, (160, 160, 160), pts, 1)
    
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
                pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), max(5, size) + scale_px(4), scale_px(2))
            
            if obs["moving"]:
                pulse = int(abs(math.sin(time.time() * 5)) * 3)
                pygame.draw.circle(screen, (255, 255, 100), (int(sx), int(sy)), size + pulse + scale_px(3), scale_px(2))
            
            # Draw 3D obstacle representation
            draw_3d_obstacle(sx, sy, obs["elevation"], size)
    
    # Draw player with clear ARROW for direction
    pygame.draw.circle(screen, (255, 255, 255), center, scale_px(10))
    pygame.draw.circle(screen, (50, 150, 255), center, scale_px(8))
    
    # Direction arrow (prominent)
    arrow_len = scale_px(28)
    arrow_tip = (center[0] + arrow_len * math.cos(player_angle),
                 center[1] + arrow_len * math.sin(player_angle))
    
    # Arrow shaft
    pygame.draw.line(screen, (255, 255, 255), center, arrow_tip, scale_px(3))
    
    # Arrow head
    head_len = scale_px(12)
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
    
    angle_box_w = angle_text.get_width() + scale_px(30)
    angle_box_h = scale_px(40)
    angle_box_x = SCENE_W//2 - angle_box_w//2
    angle_box_y = center[1] + int(MAX_RANGE * SCALE * VIEW_SCALE) + scale_px(20)
    
    pygame.draw.rect(screen, (20, 40, 30), (angle_box_x, angle_box_y, angle_box_w, angle_box_h))
    pygame.draw.rect(screen, (100, 255, 100), (angle_box_x, angle_box_y, angle_box_w, angle_box_h), scale_px(2))
    screen.blit(angle_text, (angle_box_x + scale_px(15), angle_box_y + scale_px(8)))
    
    # Legend with background - positioned bottom-left
    y_off = HEIGHT - scale_px(135)
    legend_bg_height = scale_px(130)
    pygame.draw.rect(screen, (20, 20, 30), (scale_px(10), y_off - scale_px(5), scale_px(180), legend_bg_height))
    pygame.draw.rect(screen, (80, 120, 160), (scale_px(10), y_off - scale_px(5), scale_px(180), legend_bg_height), scale_px(2))
    
    legend_title = label_font.render("Obstacles:", True, (100, 200, 255))
    screen.blit(legend_title, (scale_px(20), y_off))
    y_off += scale_px(30)
    for name, info in ELEVATION_TYPES.items():
        if name != "ground":
            pygame.draw.rect(screen, info["color"], (scale_px(25), y_off, scale_px(14), scale_px(14)))
            label = small_font.render(info["label"], True, (200, 200, 200))
            screen.blit(label, (scale_px(48), y_off - scale_px(2)))
            y_off += scale_px(25)
    
    # Controls hint with background - bottom
    ctrl_y = HEIGHT - scale_px(45)
    ctrl_bg_height = scale_px(40)
    pygame.draw.rect(screen, (20, 20, 30), (scale_px(10), ctrl_y - scale_px(5), SCENE_W - scale_px(20), ctrl_bg_height))
    pygame.draw.rect(screen, (100, 150, 200), (scale_px(10), ctrl_y - scale_px(5), SCENE_W - scale_px(20), ctrl_bg_height), scale_px(1))
    
    ctrl = info_font.render("A/D: Rotate | W/S: Move | SPACE: Jump | R: Reset | ESC: Quit", True, (150, 200, 255))
    screen.blit(ctrl, (scale_px(20), ctrl_y))

def draw_3d_obstacle(sx, sy, elevation, size):
    """Draw a 3D cuboid obstacle in environment view"""
    elev_info = ELEVATION_TYPES.get(elevation, ELEVATION_TYPES["step"])
    color = elev_info["color"]
    height = abs(elev_info["height"])
    
    # 3D parameters (scaled)
    cube_w = size * 1.5
    cube_h = height * (15 * SCALE_FACTOR) + scale_px(10)
    iso_offset = scale_px(8)  # Isometric offset
    
    if elev_info["height"] < 0:  # Pothole - flat coloured ellipse (no depth)
        if elevation == "cliff_pothole":
            pygame.draw.ellipse(screen, (180, 30, 30), (sx - cube_w, sy - cube_w//2, cube_w*2, cube_w))
            pygame.draw.ellipse(screen, (220, 50, 50), (sx - cube_w, sy - cube_w//2, cube_w*2, cube_w), 2)
        else:
            pygame.draw.ellipse(screen, (140, 90, 200), (sx - cube_w, sy - cube_w//2, cube_w*2, cube_w))
            pygame.draw.ellipse(screen, (170, 120, 230), (sx - cube_w, sy - cube_w//2, cube_w*2, cube_w), 2)
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
    
    # Clip all drawing to the left panel
    screen.set_clip(pygame.Rect(0, 0, SCENE_W, HEIGHT))
    
    horizon_y = int(HEIGHT * 0.42)
    # Shift horizon based on player vertical offset (falling into pothole / jumping)
    effective_camera_height = CAMERA_HEIGHT + player_y_offset
    horizon_shift = int(player_y_offset * 120 * SCALE_FACTOR)  # Positive = up, negative = down
    horizon_y = horizon_y - horizon_shift
    focal = (SCENE_W / 2) / math.tan(FOV / 2)
    
    def project(x, y, z):
        """Project 3D point to screen. x=right, y=up, z=forward in meters."""
        if z <= 0.05:
            return None
        sx = SCENE_W / 2 + (x / z) * focal
        sy = horizon_y - ((y - effective_camera_height) / z) * focal
        return (sx, sy)
    
    def apply_fade(col, f):
        return tuple(max(0, min(255, int(comp * f))) for comp in col)
    
    # --- Sky ---
    pygame.draw.rect(screen, (12, 15, 35), (0, 0, SCENE_W, horizon_y))
    # Horizon glow (optimized: fewer lines, step by 3)
    for i in range(0, 30, 3):
        y = horizon_y - i
        if y >= 0:
            a = int(30 - i)
            pygame.draw.line(screen, (12 + a // 2, 18 + a // 2, 40 + a), (0, y), (SCENE_W, y))
    
    # --- Ground ---
    pygame.draw.rect(screen, (25, 35, 25), (0, horizon_y, SCENE_W, HEIGHT - horizon_y))
    
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
    
    # --- White boundary walls (4 thick walls of the world) ---
    WALL_THICK_M = WALL_THICKNESS_PX / SCALE  # Thickness in metres
    cos_a = math.cos(player_angle)
    sin_a = math.sin(player_angle)
    
    def world_to_camera(wx_px, wy_px):
        """Convert world pixel coords to camera-space (right, forward) in metres."""
        dx = wx_px - player_x
        dy = wy_px - player_y
        fwd = (dx * cos_a + dy * sin_a) / SCALE
        rgt = (-dx * sin_a + dy * cos_a) / SCALE
        return rgt, fwd
    
    # Outer and inner corners of wall boundary
    wo = WALL_BOUNDARY           # outer edge px
    wi = WALL_INNER              # inner edge px
    wmax_o = WORLD_SIZE - wo
    wmax_i = WORLD_SIZE - wi
    
    # Each wall is a quad: 4 corners (outer_start, outer_end, inner_end, inner_start)
    # We draw outer face, inner face, and top face for thickness
    wall_quads = [
        # Top wall  (y = small)
        [(wo, wo), (wmax_o, wo), (wmax_i, wi), (wi, wi)],
        # Right wall (x = large)
        [(wmax_o, wo), (wmax_o, wmax_o), (wmax_i, wmax_i), (wmax_i, wi)],
        # Bottom wall (y = large)
        [(wmax_o, wmax_o), (wo, wmax_o), (wi, wmax_i), (wmax_i, wmax_i)],
        # Left wall (x = small)
        [(wo, wmax_o), (wo, wo), (wi, wi), (wi, wmax_i)],
    ]
    
    wall_color_front = (220, 220, 220)
    wall_color_side = (190, 190, 190)
    wall_color_top = (245, 245, 245)
    wall_edge = (160, 160, 160)
    
    # Collect wall faces with depth for painter's sort
    wall_faces = []
    
    for quad in wall_quads:
        # Outer face (quad[0] -> quad[1]), Inner face (quad[2] -> quad[3])
        outer_pairs = [(quad[0], quad[1]), (quad[3], quad[2])]  # outer edge, inner edge
        
        for idx, (p1_px, p2_px) in enumerate(outer_pairs):
            r1, f1 = world_to_camera(p1_px[0], p1_px[1])
            r2, f2 = world_to_camera(p2_px[0], p2_px[1])
            
            if f1 <= 0.1 and f2 <= 0.1:
                continue
            
            # Clip to near plane
            if f1 <= 0.1:
                t_val = (0.15 - f1) / (f2 - f1) if f2 != f1 else 0
                r1 = r1 + t_val * (r2 - r1)
                f1 = 0.15
            elif f2 <= 0.1:
                t_val = (0.15 - f2) / (f1 - f2) if f1 != f2 else 0
                r2 = r2 + t_val * (r1 - r2)
                f2 = 0.15
            
            bl = project(r1, 0, f1)
            br = project(r2, 0, f2)
            tl = project(r1, WALL_HEIGHT_M, f1)
            tr = project(r2, WALL_HEIGHT_M, f2)
            
            if bl and br and tl and tr:
                avg_dist = (f1 + f2) / 2
                fc = wall_color_front if idx == 0 else wall_color_side
                wall_faces.append((avg_dist, [bl, br, tr, tl], fc))
        
        # Top face (connects outer top edge to inner top edge)
        corners_px = [quad[0], quad[1], quad[2], quad[3]]
        cam_pts = [world_to_camera(p[0], p[1]) for p in corners_px]
        
        # Check if any point is in front
        if any(f > 0.1 for _, f in cam_pts):
            top_projs = []
            for r, f in cam_pts:
                if f <= 0.1:
                    f = 0.15
                p = project(r, WALL_HEIGHT_M, f)
                if p:
                    top_projs.append(p)
            if len(top_projs) >= 3:
                avg_d = sum(max(0.15, f) for _, f in cam_pts) / 4
                wall_faces.append((avg_d, top_projs, wall_color_top))
    
    # Sort far-to-near and draw
    wall_faces.sort(key=lambda x: -x[0])
    for _, pts, col in wall_faces:
        fade = max(0.25, 1.0 - _ / 14.0)
        fc = tuple(max(0, min(255, int(c * fade))) for c in col)
        ec = tuple(max(0, min(255, int(c * fade))) for c in wall_edge)
        pygame.draw.polygon(screen, fc, pts)
        pygame.draw.polygon(screen, ec, pts, 1)
    
    # --- Collect visible obstacles ---
    
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
            is_cliff = (elev == "cliff_pothole")
            if is_cliff:
                fill_color = (180, 30, 30)   # Solid red
                border_color = (220, 50, 50)
            else:
                fill_color = (140, 90, 200)  # Solid purple
                border_color = (170, 120, 230)
            
            # Draw pothole as a flat coloured patch on the ground (no depth)
            corners = [
                project(rm - hw, 0, fm - hd),
                project(rm + hw, 0, fm - hd),
                project(rm + hw, 0, fm + hd),
                project(rm - hw, 0, fm + hd),
            ]
            if all(c is not None for c in corners):
                pygame.draw.polygon(screen, apply_fade(fill_color, fade), corners)
                pygame.draw.polygon(screen, apply_fade(border_color, fade), corners, 2)
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
    
    # --- Circular Minimap (Top Left, below title) ---
    minimap_radius = max(40, int(HEIGHT * 0.09))
    minimap_x = scale_px(10) + minimap_radius
    minimap_y = scale_px(55) + minimap_radius
    minimap_scale = minimap_radius / MAX_RANGE
    
    # Background circle
    pygame.draw.circle(screen, (20, 20, 30), (minimap_x, minimap_y), minimap_radius)
    pygame.draw.circle(screen, (80, 100, 140), (minimap_x, minimap_y), minimap_radius, max(1, scale_px(2)))
    
    # Distance rings
    ring_colors = [(80, 200, 80), (200, 200, 80), (200, 80, 80)]
    for i, d in enumerate([1.0, 2.0, 3.0]):
        r = int(d * minimap_scale)
        pygame.draw.circle(screen, ring_colors[i], (minimap_x, minimap_y), r, max(1, scale_px(1)))
    
    # FOV cone in minimap
    fov_len = minimap_radius
    left_angle = player_angle - FOV / 2
    right_angle = player_angle + FOV / 2
    fov_pts = [(minimap_x, minimap_y)]
    num_arc = 12
    for i in range(num_arc + 1):
        angle = left_angle + (right_angle - left_angle) * i / num_arc
        px = minimap_x + fov_len * math.cos(angle)
        py = minimap_y + fov_len * math.sin(angle)
        fov_pts.append((px, py))
    pygame.draw.polygon(screen, (40, 50, 80), fov_pts)
    pygame.draw.polygon(screen, (80, 120, 160), fov_pts, max(1, scale_px(1)))
    
    # Draw obstacles on minimap
    for obs in obstacles:
        dx = obs["x"] - player_x
        dy = obs["y"] - player_y
        dist = math.hypot(dx, dy)
        if dist > MAX_RANGE * SCALE:
            continue
        angle = math.atan2(dy, dx)
        dist_m = dist / SCALE
        obs_x = minimap_x + (dist_m * math.cos(angle)) * minimap_scale
        obs_y = minimap_y + (dist_m * math.sin(angle)) * minimap_scale
        # Only draw if within minimap circle
        if math.hypot(obs_x - minimap_x, obs_y - minimap_y) <= minimap_radius:
            elev = obs["elevation"]
            color = ELEVATION_TYPES[elev]["color"]
            obs_size = max(2, scale_px(3))
            if obs.get("moving"):
                pulse = int(abs(math.sin(time.time() * 5)) * 2)
                pygame.draw.circle(screen, (255, 255, 100), (int(obs_x), int(obs_y)), obs_size + pulse + 1, 1)
            pygame.draw.circle(screen, color, (int(obs_x), int(obs_y)), obs_size)
    
    # Player marker (center)
    pygame.draw.circle(screen, (255, 255, 255), (minimap_x, minimap_y), max(3, scale_px(4)))
    pygame.draw.circle(screen, (50, 150, 255), (minimap_x, minimap_y), max(2, scale_px(3)))
    
    # Player heading arrow
    arrow_len = max(10, scale_px(16))
    arrow_tip_x = minimap_x + arrow_len * math.cos(player_angle)
    arrow_tip_y = minimap_y + arrow_len * math.sin(player_angle)
    pygame.draw.line(screen, (255, 255, 255), (minimap_x, minimap_y), (int(arrow_tip_x), int(arrow_tip_y)), max(1, scale_px(2)))
    
    # Minimap label
    mm_label = info_font.render("Minimap", True, (100, 200, 255))
    screen.blit(mm_label, (minimap_x - mm_label.get_width() // 2, minimap_y + minimap_radius + scale_px(4)))
    
    # --- Title ---
    title = title_font.render("Player View (Blind Navigation)", True, (200, 200, 200))
    title_box_h = scale_px(35)
    pygame.draw.rect(screen, (30, 30, 50), (0, 0, SCENE_W, title_box_h))
    pygame.draw.rect(screen, (100, 200, 255), (0, 0, SCENE_W, title_box_h), max(1, scale_px(2)))
    screen.blit(title, (SCENE_W // 2 - title.get_width() // 2, scale_px(6)))
    
    # --- Legend (Top Right of left panel) ---
    legend_item_h = max(14, scale_px(18))
    num_legend = sum(1 for n in ELEVATION_TYPES if n != "ground")
    legend_h = scale_px(22) + num_legend * legend_item_h + scale_px(4)
    legend_w = max(90, scale_px(120))
    legend_x = SCENE_W - legend_w - scale_px(8)
    legend_y = scale_px(40)
    
    pygame.draw.rect(screen, (15, 15, 25), (legend_x, legend_y, legend_w, legend_h))
    pygame.draw.rect(screen, (80, 120, 160), (legend_x, legend_y, legend_w, legend_h), max(1, scale_px(1)))
    lt = info_font.render("Obstacles:", True, (100, 200, 255))
    screen.blit(lt, (legend_x + scale_px(6), legend_y + scale_px(3)))
    ly = legend_y + scale_px(20)
    for name, einfo in ELEVATION_TYPES.items():
        if name != "ground":
            sz = max(8, scale_px(10))
            pygame.draw.rect(screen, einfo["color"], (legend_x + scale_px(6), ly, sz, sz))
            lbl = info_font.render(einfo["label"], True, (200, 200, 200))
            screen.blit(lbl, (legend_x + scale_px(6) + sz + scale_px(4), ly))
            ly += legend_item_h
    
    # --- Facing direction ---
    angle_deg = math.degrees(player_angle) % 360
    cardinals = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    cardinal_idx = int(((angle_deg + 22.5) % 360) / 45)
    cardinal = cardinals[cardinal_idx]
    angle_str = f"Facing: {angle_deg:.0f}\u00b0 ({cardinal})"
    angle_text = label_font.render(angle_str, True, (200, 255, 200))
    angle_box_w = angle_text.get_width() + scale_px(16)
    angle_box_h = scale_px(28)
    angle_box_x = SCENE_W // 2 - angle_box_w // 2
    angle_box_y = HEIGHT - scale_px(58)
    pygame.draw.rect(screen, (20, 40, 30), (angle_box_x, angle_box_y, angle_box_w, angle_box_h))
    pygame.draw.rect(screen, (100, 255, 100), (angle_box_x, angle_box_y, angle_box_w, angle_box_h), max(1, scale_px(2)))
    screen.blit(angle_text, (angle_box_x + scale_px(8), angle_box_y + scale_px(4)))
    
    # --- Controls ---
    ctrl_box_h = scale_px(24)
    ctrl_y = HEIGHT - ctrl_box_h - scale_px(4)
    pygame.draw.rect(screen, (20, 20, 30), (scale_px(6), ctrl_y, SCENE_W - scale_px(12), ctrl_box_h))
    pygame.draw.rect(screen, (100, 150, 200), (scale_px(6), ctrl_y, SCENE_W - scale_px(12), ctrl_box_h), max(1, scale_px(1)))
    ctrl = info_font.render("A/D: Rotate | W/S: Move | SPACE: Jump | R: Reset | ESC: Quit", True, (150, 200, 255))
    screen.blit(ctrl, (scale_px(12), ctrl_y + scale_px(4)))
    
    # --- Pothole falling overlay ---
    if player_in_pothole and not player_jumping:
        # Dark vignette effect when in pothole
        overlay = pygame.Surface((SCENE_W, HEIGHT), pygame.SRCALPHA)
        # Darkness proportional to depth
        depth_ratio = min(1.0, abs(player_y_offset) / abs(POTHOLE_DEPTH))
        alpha = int(120 * depth_ratio)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
        
        # "IN POTHOLE" warning text
        warn_pulse = (math.sin(time.time() * 4) + 1) / 2
        warn_alpha = int(150 + 105 * warn_pulse)
        warn_text = label_font.render("IN POTHOLE - Press SPACE to jump out!", True,
                                       (255, warn_alpha, int(80 * warn_pulse)))
        screen.blit(warn_text, (SCENE_W // 2 - warn_text.get_width() // 2, HEIGHT // 2 - scale_px(20)))
        
        # Draw rising ground walls on sides to simulate being in a pit
        wall_height = int(HEIGHT * 0.3 * depth_ratio)
        wall_color = (30, 20, 15)
        # Left wall
        pygame.draw.rect(screen, wall_color, (0, HEIGHT - wall_height, scale_px(30), wall_height))
        # Right wall
        pygame.draw.rect(screen, wall_color, (SCENE_W - scale_px(30), HEIGHT - wall_height, scale_px(30), wall_height))
    
    # --- Jump arc indicator ---
    if player_jumping:
        jump_text = info_font.render(f"JUMPING  Y: {player_y_offset:+.2f}m", True, (100, 255, 100))
        screen.blit(jump_text, (SCENE_W // 2 - jump_text.get_width() // 2, scale_px(42)))
    
    # Release clip
    screen.set_clip(None)

# -----------------------
# 3D ISOMETRIC TACTILE GRID
# -----------------------
def draw_isometric_grid(heights, vibration, cell_obstacles):
    """Draw isometric 3D tactile grid like the reference image"""
    panel_x = SCENE_W
    panel_w = WIDTH - SCENE_W
    
    # Clip to right panel bounds
    screen.set_clip(pygame.Rect(panel_x, 0, panel_w, HEIGHT))
    
    # Background (solid - optimized from per-line gradient)
    pygame.draw.rect(screen, (48, 48, 55), (panel_x, 0, panel_w, HEIGHT))
    
    # Draw top border with accent color
    pygame.draw.line(screen, (100, 150, 200), (panel_x, 0), (WIDTH, 0), 3)
    
    # Title with background box
    title = title_font.render("3×3 Tactile Grid Device", True, (220, 220, 220))
    title_box_height = scale_px(45)
    pygame.draw.rect(screen, (30, 30, 50), (panel_x, scale_px(5), panel_w, title_box_height))
    pygame.draw.rect(screen, (100, 150, 200), (panel_x, scale_px(5), panel_w, title_box_height), scale_px(2))
    screen.blit(title, (panel_x + panel_w//2 - title.get_width()//2, scale_px(12)))
    
    # Isometric grid parameters - centered in available space
    grid_center_x = panel_x + panel_w // 2 + scale_px(20)
    grid_center_y = HEIGHT // 2 + scale_px(20)
    
    cell_w = scale_px(100)  # Cell width in isometric view
    cell_h = scale_px(65)   # Cell depth in isometric view
    
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
    row_label_panel_x = panel_x + scale_px(8)
    row_label_panel_y = grid_center_y - scale_px(120)
    row_box_width = scale_px(110)
    row_boxes = []  # Store box positions for later reference
    
    # Distance header
    row_header = label_font.render("DISTANCE", True, (100, 200, 255))
    screen.blit(row_header, (row_label_panel_x, row_label_panel_y - scale_px(28)))
    
    # Draw each distance category as a separate labeled box
    row_names = ["IMMEDIATE", "NEAR", "FAR"]
    row_ranges = ["0-1m", "1-2m", "2-3m"]
    row_colors = [(200, 80, 80), (200, 200, 80), (100, 200, 100)]
    
    row_box_h = scale_px(48)
    row_box_gap = scale_px(55)
    for r, (name, range_text, color) in enumerate(zip(row_names, row_ranges, row_colors)):
        box_y = row_label_panel_y + r * row_box_gap
        row_boxes.append((row_label_panel_x, box_y, row_box_width, row_box_h))
        
        # Draw background box
        pygame.draw.rect(screen, (25, 25, 40), (row_label_panel_x, box_y, row_box_width, row_box_h))
        pygame.draw.rect(screen, color, (row_label_panel_x, box_y, row_box_width, row_box_h), scale_px(2))
        
        # Draw colored indicator bar on left
        pygame.draw.rect(screen, color, (row_label_panel_x - scale_px(6), box_y, scale_px(6), row_box_h))
        
        # Draw text
        distance_label = small_font.render(name, True, (220, 220, 220))
        range_label = info_font.render(range_text, True, color)
        screen.blit(distance_label, (row_label_panel_x + scale_px(6), box_y + scale_px(6)))
        screen.blit(range_label, (row_label_panel_x + scale_px(6), box_y + scale_px(26)))
    
    # Draw column labels at bottom with better spacing
    col_header_y = HEIGHT - scale_px(80)
    col_header = label_font.render("DIRECTION", True, (100, 200, 255))
    screen.blit(col_header, (grid_center_x - col_header.get_width()//2, col_header_y))
    
    for c in range(3):
        ix, _ = iso_transform(c, 3.5)
        col_y = HEIGHT - scale_px(55)
        
        # Draw background box
        col_width = scale_px(90)
        col_height = scale_px(35)
        col_colors_list = [(255, 100, 100), (100, 255, 100), (100, 100, 255)]
        col_color = col_colors_list[c]
        
        pygame.draw.rect(screen, (25, 25, 40), (ix - col_width//2, col_y, col_width, col_height))
        pygame.draw.rect(screen, col_color, (ix - col_width//2, col_y, col_width, col_height), scale_px(2))
        
        # Draw colored bar on top
        pygame.draw.rect(screen, col_color, (ix - col_width//2, col_y - scale_px(3), col_width, scale_px(3)))
        
        # Draw label
        col_labels_list = ["LEFT", "CENTER", "RIGHT"]
        label = small_font.render(col_labels_list[c], True, col_color)
        screen.blit(label, (ix - label.get_width()//2, col_y + scale_px(6)))
    
    # Add visual separator line between left panel and grid
    sep_x = row_label_panel_x + row_box_width + scale_px(10)
    pygame.draw.line(screen, (80, 100, 130), (sep_x, row_label_panel_y - scale_px(28)), 
                     (sep_x, row_label_panel_y + 3 * row_box_gap), scale_px(1))
    
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
                obs_info = cell_obstacles[row][col]
                elev_type = obs_info["elevation"] if obs_info else None
                # Cliff potholes always vibrate on the tactile grid
                if elev_type == "cliff_pothole":
                    vib_offset = math.sin(t * 18) * 5
                draw_iso_cuboid(ix + vib_offset, iy, h, vib, t, elev_type)
    
    # Info panel at bottom with background
    info_y = HEIGHT - scale_px(18)
    safe_dir = compute_safe_direction(heights)
    
    # Draw info panel background
    pygame.draw.rect(screen, (25, 25, 40), (panel_x, info_y - scale_px(8), panel_w, scale_px(26)))
    pygame.draw.line(screen, (100, 120, 150), (panel_x, info_y - scale_px(8)), (WIDTH, info_y - scale_px(8)), scale_px(1))
    
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
    
    x_pos = panel_x + scale_px(10)
    for label, value in zip(info_labels, info_parts):
        label_surf = info_font.render(label, True, (150, 150, 180))
        value_color = safe_dir_color if "Safe" in label else (200, 200, 200)
        value_surf = info_font.render(value, True, value_color)
        screen.blit(label_surf, (x_pos, info_y))
        screen.blit(value_surf, (x_pos + label_surf.get_width() + scale_px(3), info_y))
        x_pos += label_surf.get_width() + value_surf.get_width() + scale_px(20)

    # Release clip
    screen.set_clip(None)

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
    shadow_off = scale_px(3)
    shadow_points = [(p[0] + shadow_off, p[1] + shadow_off) for p in points]
    pygame.draw.polygon(screen, (15, 15, 20), shadow_points)
    
    # Base plate
    pygame.draw.polygon(screen, (25, 25, 30), points)
    pygame.draw.polygon(screen, (60, 60, 70), points, scale_px(2))
    
    # Side faces for 3D effect
    depth = scale_px(6)
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

def draw_iso_cuboid(cx, cy, height_val, vibration, t, elev_type=None):
    """Draw isometric 3D cuboid based on height value"""
    # Cuboid dimensions (scaled)
    w = scale_px(30)  # Half-width
    d = scale_px(18)  # Half-depth (isometric)
    
    # Height calculation - taller for higher obstacles
    max_h = scale_px(120)
    h = abs(height_val) / 3.0 * max_h
    h = max(scale_px(18), h)  # Minimum height
    
    # Color based on elevation type and distance attenuation
    if elev_type == "cliff_pothole":
        base_color = (180, 30, 30)   # Dark red for cliff
    elif height_val < 0:  # Shallow pothole
        base_color = (140, 90, 200)  # Light purple
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
    
    if height_val < 0:  # Pothole - flat coloured diamond (no depth)
        is_cliff = (elev_type == "cliff_pothole")
        hole_points = [
            (cx, cy - d),
            (cx + w, cy),
            (cx, cy + d),
            (cx - w, cy),
        ]
        if is_cliff:
            # Pulsating vibration for cliff on tactile grid
            pulse = (math.sin(t * 8) + 1) / 2
            vib_r = int(140 + 115 * pulse)
            fill = (vib_r, int(20 * pulse), int(20 * pulse))
            border = (min(255, vib_r + 40), 50, 50)
            # Vibration shake offset
            shake = int(math.sin(t * 20) * 3)
            hole_points = [(p[0] + shake, p[1]) for p in hole_points]
        else:
            fill = (140, 90, 200)
            border = (170, 120, 230)
        
        pygame.draw.polygon(screen, fill, hole_points)
        pygame.draw.polygon(screen, border, hole_points, 2)
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
    global player_y_offset, player_y_target, player_in_pothole, player_jumping, player_jump_velocity
    
    running = True
    
    # Initialize keyboard - pump events and clear queue to ensure controls work on first run
    pygame.event.pump()
    pygame.event.clear()
    pygame.key.set_repeat(100, 50)  # Enable key repeat for smoother movement
    
    # Force initial display update to ensure window is ready
    screen.fill((0, 0, 0))
    pygame.display.flip()
    
    print("=" * 60)
    print("Directional Tactile Navigation Device Simulation")
    print("3×3 Tactile Grid Model")
    print("=" * 60)
    print("\nControls:")
    print("  W/S   - Move forward/backward")
    print("  A/D   - Rotate left/right")
    print("  SPACE - Jump (over steps / out of potholes)")
    print("  R     - Reset obstacles")
    print("  ESC   - Quit")
    print("\nTactile Encoding:")
    print("  Green       = Step (jump over with SPACE)")
    print("  Yellow      = Mid (deflect/redirect)")
    print("  Red         = Top (avoid - head level)")
    print("  Lt. Purple  = Shallow Pothole (fall in, SPACE to escape)")
    print("  Dark Red    = Cliff Pothole (DANGER - impassable!)")
    print("  Vibration   = Moving obstacle")
    print("=" * 60)
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                handle_resize(event.w, event.h)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    generate_obstacles()
                    player_y_offset = 0.0
                    player_y_target = 0.0
                    player_in_pothole = False
                    player_jumping = False
                    player_jump_velocity = 0.0
                    print("Obstacles reset!")
                elif event.key == pygame.K_SPACE:
                    # Jump: works when on ground OR in pothole
                    if not player_jumping:
                        player_jumping = True
                        player_jump_velocity = JUMP_STRENGTH
                        if player_in_pothole:
                            # Extra boost to escape pothole
                            player_jump_velocity = JUMP_STRENGTH * 1.2
        
        # Input handling
        pressed = pygame.key.get_pressed()
        
        # WASD and Arrow keys (with collision detection)
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            new_x = player_x + math.cos(player_angle) * speed
            new_y = player_y + math.sin(player_angle) * speed
            if (50 < new_x < WORLD_SIZE - 50 and 50 < new_y < WORLD_SIZE - 50
                    and not check_collision(new_x, new_y)):
                player_x = new_x
                player_y = new_y
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            new_x = player_x - math.cos(player_angle) * speed
            new_y = player_y - math.sin(player_angle) * speed
            if (50 < new_x < WORLD_SIZE - 50 and 50 < new_y < WORLD_SIZE - 50
                    and not check_collision(new_x, new_y)):
                player_x = new_x
                player_y = new_y
        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            player_angle -= rot_speed
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            player_angle += rot_speed
        
        # Update player vertical state (jumping / falling)
        dt = 1.0 / 60.0  # Frame delta time
        update_player_vertical(dt)
        
        # Slow movement when in pothole
        if player_in_pothole and not player_jumping:
            pass  # Movement is already handled above, could add slowdown here
        
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