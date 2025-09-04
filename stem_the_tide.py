''' CAVEAT
This is a prototype/proof of concept for the game Stem The Tide
The code is far from complete, and several bugs exist. 
It is just meant to show how the game could look and function.
'''

''' GAME MECHANICS
Mechanic 1: Rising Tide
- Concept: Starting from 1 end of the screen, a wave sweeps row by row through the screen when the space bar is pressed.
- Visual: The side of the screen that the flood comes from is blue pixels, and when the wave spreads, the empty pixels turn blue row by row.
- Learning: The player must learn that the flood comes from the side(s) of the screen with blue pixels, which will affect how they play out their strategy.
- Progression: 
  - Easy: The blue only comes from 1 side
  - Medium: The blue comes from 2 sides at once
  - Hard: the blue comes from 3-4 sides at once

Mechanic 2: Barriers
- Concept: Barriers help "stem the tide" by temporarily diverting water flow. Some barriers are weak (divert water poorly), while others are strong (divert water more effectively).
- Visual: When the tide hits a barrier, it does not fill in the pixels in the "shadow" of the barrier (area behind the barrier that decreases as the rows progress). Weak barriers cause water to close in on the shadow more quickly than strong barriers.
- Learning: Barriers must be clicked in order to be moved. Use the arrow keys after clicking a barrier to move it. Barriers that are strong have much longer shadows, and must be placed accordingly.
- Progression:
  - Easy: Large, strong barrier that can be placed right in front of priority dry zone.
  - Medium: Must strategically place multiple barriers in order to stem the tide from multiple directions.
  - Hard: Must take into account the differences between strong and weak barriers in order to keep all the priority zones dry as the tide comes in from multiple directions.

Mechanic 3: Splash Pads
- Concept: Splash Pads will "bounce" water off of them, which can add or change the angle of the tide.
- Visual: When the tide reaches a Splash Pad, it spreads from it perpedicular to the original flood direction.
- Learning: Must account for this diversion of the flood when placing barriers.
- Progression:
  - Easy: No Splash Pads
  - Medium: Splash Pad is easy to counteract with a small, weak barrier.
  - Hard: Multiple Splash Pads make the flood come in from every direction, even when previously diverted.
'''

''' LEVELS
- Level 1: Basic diversion. Put the strong barrier right in front of the dry zone so that it will divert the water.
- Level 2: Weak vs Strong Barriers. Must place the correct barrier in front of the correct zone in order to effectively protect. Tide comes in from a different side.
- Level 3: Splash pad. Tide comes in from one side, but gets redirected by a splash pad, requiring the use of 2 barriers.
- Level 4: Tide comes in from 2 directions. Must place few barriers in creative ways in order to keep multiple dry zones safe.
- Level 5: Tide comes in from 3 directions. 2 Splash Pads make it difficult to track where the water will come from when it nears the dray zones. Must place barriers to block both incoming tides and splashed water.
'''

import sys
import pygame

# ---------- Config ----------
GRID_W, GRID_H = 64, 64      # 64x64 "pixels"
PIXEL_SIZE = 10               # how large each pixel appears on screen
WIN_W, WIN_H = GRID_W * PIXEL_SIZE, GRID_H * PIXEL_SIZE

# State definitions
STATES = {
    0: (20, 20, 20),      # Empty (black)
    1: (255, 255, 255),   # Priority (white)
    2: (0, 100, 255),     # Tide (blue)
    3: (128, 128, 128),   # Barrier (grey) - inactive
    4: (0, 255, 0),       # Barrier (green) - active/movable
    5: (20, 20, 20),      # Barrier Shadow (black) - blocks flood but fills from edges
    6: (40, 40, 40),      # Metadata Zone (dark grey) - edge pixels
    7: (0, 255, 0),       # Passed Level (green)
    8: (255, 255, 0),     # Current Level (yellow)
    9: (255, 0, 0),       # Future Level (red)
    10: (255, 0, 0),      # Wet Priority (red) - game over state
    11: (139, 69, 19),    # Weak Barrier (brown) - inactive
    12: (0, 255, 0),      # Weak Barrier (green) - active/movable
    # Future states can be added here:
    # 13-15: Available for future features
}

# Flood direction system (for future levels)
FLOOD_DIRECTIONS = {
    'top': (0, 1),      # Down
    'bottom': (0, -1),  # Up  
    'left': (1, 0),     # Right
    'right': (-1, 0),   # Left
    'multi': [(0, 1), (1, 0)]  # Multiple directions
}

GRID_COLOR = (40, 40, 40)
DRAW_GRID = False  # set True to see grid lines (slower)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def get_color_for_state(state):
    """Get the color for a given state number"""
    return STATES.get(state, (255, 0, 255))  # Magenta for unknown states

def is_valid_position(grid, x, y, width, height):
    """Check if a position is valid (within bounds and not overlapping priority areas)"""
    if x < 0 or y < 0 or x + width > GRID_W or y + height > GRID_H:
        return False
    
    # Check if the area is empty or contains the barrier itself
    for dy in range(height):
        for dx in range(width):
            if grid[y + dy][x + dx] not in [0, 3, 4]:  # Only allow empty and barriers
                return False
    return True

def place_barrier(grid, x, y, width, height, state):
    """Place a barrier at the given position"""
    for dy in range(height):
        for dx in range(width):
            grid[y + dy][x + dx] = state

def remove_barrier(grid, x, y, width, height):
    """Remove a barrier from the given position (set to empty)"""
    for dy in range(height):
        for dx in range(width):
            grid[y + dy][x + dx] = 0

def create_flood_shadow_mask(barriers):
    """Create a mask of cells that should be excluded from flooding (shadow areas)"""
    shadow_mask = set()
    
    for barrier in barriers:
        barrier_x, barrier_y, barrier_width, barrier_height = barrier
        
        # For each row below the barrier
        for row in range(barrier_y + barrier_height, GRID_H):
            # Calculate distance from barrier
            distance_from_barrier = row - barrier_y
            
            # Calculate shadow width - starts at barrier width, shrinks by 2 pixels every 2 rows
            # Every 2 rows, the shadow gets 1 pixel smaller on each side
            shadow_shrink = max(0, (distance_from_barrier - 1) // 2)
            shadow_width = max(0, barrier_width - (shadow_shrink * 2))
            
            if shadow_width > 0:
                # Calculate shadow position (centered behind barrier)
                shadow_start = barrier_x + (barrier_width - shadow_width) // 2
                shadow_end = shadow_start + shadow_width
                
                # Add shadow cells to mask
                for col in range(shadow_start, shadow_end):
                    if 0 <= col < GRID_W:
                        shadow_mask.add((col, row))
    
    return shadow_mask

def create_flood_shadow_mask_with_weak_barriers(barriers):
    """Create a mask of cells that should be excluded from flooding (shadow areas)"""
    shadow_mask = set()
    
    for barrier in barriers:
        barrier_x, barrier_y, barrier_width, barrier_height, is_weak, is_active = barrier
        
        # For each row below the barrier
        for row in range(barrier_y + barrier_height, GRID_H):
            # Calculate distance from barrier
            distance_from_barrier = row - barrier_y
            
            # Calculate shadow width based on barrier type
            if is_weak:
                # Weak barriers: shadow shrinks by 2 pixels every row (1 pixel per side)
                # First row: full width, second row: width-2, third row: width-4, etc.
                shadow_shrink = max(0, distance_from_barrier - 1)  # Start shrinking from second row
                shadow_width = max(0, barrier_width - (shadow_shrink * 2))
            else:
                # Strong barriers: shadow shrinks by 2 pixels every 2 rows
                shadow_shrink = max(0, (distance_from_barrier - 1) // 2)
                shadow_width = max(0, barrier_width - (shadow_shrink * 2))
            
            if shadow_width > 0:
                # Calculate shadow position (centered behind barrier)
                shadow_start = barrier_x + (barrier_width - shadow_width) // 2
                shadow_end = shadow_start + shadow_width
                
                # Add shadow cells to mask
                for col in range(shadow_start, shadow_end):
                    if 0 <= col < GRID_W:
                        shadow_mask.add((col, row))
    
    return shadow_mask

def setup_metadata_edges(grid, current_level, total_levels=8):
    """Setup the metadata edges with level progression indicators"""
    # Clear all edge pixels first
    for x in range(GRID_W):
        for y in range(GRID_H):
            if (x < 3 or x >= GRID_W - 3 or y < 3 or y >= GRID_H - 3):
                grid[y][x] = 6  # Metadata zone
    
    # Add level progression indicators (top edge, centered)
    level_start_x = GRID_W // 2 - total_levels // 2
    for i in range(total_levels):
        x = level_start_x + i
        if x >= 3 and x < GRID_W - 3:  # Within metadata zone
            if i < current_level - 1:
                grid[1][x] = 7  # Passed level (green)
            elif i == current_level - 1:
                grid[1][x] = 8  # Current level (yellow)
            else:
                grid[1][x] = 9  # Future level (red)
    
    # Add empty metadata blocks between level indicators
    for i in range(total_levels - 1):
        x = level_start_x + i + 0.5  # Between levels
        if int(x) >= 3 and int(x) < GRID_W - 3:
            grid[1][int(x)] = 6  # Empty metadata

def check_priority_wet(grid, priority_zones):
    """Check if any priority zone has been touched by the tide"""
    for zone in priority_zones:
        zone_x, zone_y, zone_size = zone
        for dy in range(zone_size):
            for dx in range(zone_size):
                if grid[zone_y + dy][zone_x + dx] == 2:  # Tide
                    return True
    return False

def mark_priority_wet(grid, priority_zones):
    """Mark all priority zones as wet (game over state)"""
    for zone in priority_zones:
        zone_x, zone_y, zone_size = zone
        for dy in range(zone_size):
            for dx in range(zone_size):
                grid[zone_y + dy][zone_x + dx] = 10  # Wet priority (red)

def is_level_complete(grid, flood_active=False):
    """Check if the current level is complete (flood ended and priority stayed dry)"""
    if flood_active:
        return False
    
    # Check if flood has reached the bottom
    for x in range(GRID_W):
        if grid[GRID_H - 1][x] == 2:  # Tide at bottom
            return True
    
    return False

def setup_level_1(grid):
    """Setup Level 1: Single priority zone, one strong barrier"""
    # Clear grid
    for y in range(GRID_H):
        for x in range(GRID_W):
            grid[y][x] = 0
    
    # Setup metadata edges
    setup_metadata_edges(grid, 1, 8)
    
    # Make top row tide initially (but not in metadata zone)
    for x in range(3, GRID_W - 3):
        grid[0][x] = 2  # State 2 = tide (blue)
    
    # Position for the 4x4 priority box (near bottom, but not in metadata zone)
    box_x = GRID_W // 2 - 2  # Center the box
    box_y = GRID_H - 13      # Near bottom but above metadata zone
    
    # Place the priority box (state 1 = white)
    for dy in range(4):
        for dx in range(4):
            grid[box_y + dy][box_x + dx] = 1
    
    return [(box_x, box_y, 4)]  # Return priority zones

def reset_level(grid, current_level, barriers, priority_zones):
    """Reset the current level to its initial state"""
    # Clear grid
    for y in range(GRID_H):
        for x in range(GRID_W):
            grid[y][x] = 0
    
    # Setup level based on current level
    if current_level == 1:
        priority_zones = setup_level_1(grid)
        
        # Reset barriers for level 1
        barriers.clear()
        barrier_x, barrier_y = 10, 20
        barrier_width, barrier_height = 16, 3
        barriers.append((barrier_x, barrier_y, barrier_width, barrier_height, False, False))  # Strong, inactive
        place_barrier(grid, barrier_x, barrier_y, barrier_width, barrier_height, 3)
        
    elif current_level == 2:
        priority_zones = setup_level_2(grid)
        
        # Reset barriers for level 2
        barriers.clear()
        
        # Add strong barrier (12 pixels)
        strong_barrier_x, strong_barrier_y = 15, 25
        barriers.append((strong_barrier_x, strong_barrier_y, 12, 3, False, False))
        place_barrier(grid, strong_barrier_x, strong_barrier_y, 12, 3, 3)
        
        # Add weak barrier (12 pixels)
        weak_barrier_x, weak_barrier_y = 45, 25
        barriers.append((weak_barrier_x, weak_barrier_y, 12, 3, True, False))
        place_barrier(grid, weak_barrier_x, weak_barrier_y, 12, 3, 11)
    
    return priority_zones

def setup_level_2(grid):
    """Setup Level 2: Two priority zones, one strong barrier, one weak barrier"""
    # Clear grid
    for y in range(GRID_H):
        for x in range(GRID_W):
            grid[y][x] = 0
    
    # Setup metadata edges
    setup_metadata_edges(grid, 2, 8)
    
    # Make top row tide initially (but not in metadata zone)
    for x in range(3, GRID_W - 3):
        grid[0][x] = 2  # State 2 = tide (blue)
    
    # Position for the 4x4 priority box (larger zone)
    large_box_x = GRID_W // 2 - 2  # Center the box
    large_box_y = GRID_H - 13      # Near bottom but above metadata zone
    
    # Position for the 2x2 priority box (smaller zone)
    small_box_x = GRID_W // 4 - 1  # Left side
    small_box_y = GRID_H - 13      # Same height as large box
    
    # Place the priority boxes (state 1 = white)
    for dy in range(4):
        for dx in range(4):
            grid[large_box_y + dy][large_box_x + dx] = 1
    
    for dy in range(2):
        for dx in range(2):
            grid[small_box_y + dy][small_box_x + dx] = 1
    
    return [(large_box_x, large_box_y, 4), (small_box_x, small_box_y, 2)]  # Return priority zones

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Stem the Tide — Level 1: Press SPACE to start the flood!")
    clock = pygame.time.Clock()

    # Game state
    current_level = 1
    total_levels = 8
    flood_active = False
    flood_row = 0
    flood_speed = 0.1  # seconds per row
    flood_timer = 0
    flood_shadow_mask = set()  # Cells to exclude from flooding
    game_over = False
    level_complete = False
    
    # Barrier state
    barriers = []  # List of (x, y, width, height, is_weak, is_active)
    selected_barrier = None  # Index of currently selected barrier
    
    # Create a 2D grid to track states
    grid = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
    
    # Setup initial level
    priority_zones = setup_level_1(grid)
    
    # Add initial barrier for level 1
    barrier_x, barrier_y = 10, 20
    barrier_width, barrier_height = 16, 3
    barriers.append((barrier_x, barrier_y, barrier_width, barrier_height, False, False))  # Strong, inactive
    
    # Place the initial barrier
    place_barrier(grid, barrier_x, barrier_y, barrier_width, barrier_height, 3)
    
    # Create initial flood shadow mask
    flood_shadow_mask = create_flood_shadow_mask_with_weak_barriers(barriers)
    
    # Enable key repeat for smooth movement
    pygame.key.set_repeat(100, 50)  # 100ms delay, 50ms interval

    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        
        # ---- Input ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_g:
                    # Toggle grid lines
                    global DRAW_GRID
                    DRAW_GRID = not DRAW_GRID
                elif event.key == pygame.K_r and not flood_active:
                    # Reset current level
                    priority_zones = reset_level(grid, current_level, barriers, priority_zones)
                    selected_barrier = None
                    game_over = False
                    level_complete = False
                    flood_shadow_mask = create_flood_shadow_mask_with_weak_barriers(barriers)
                    pygame.display.set_caption(f"Stem the Tide — Level {current_level}: Press SPACE to start the flood!")
                elif event.key == pygame.K_SPACE and not flood_active and not game_over:
                    # Start the flood!
                    flood_active = True
                    flood_row = 1  # Start from second row (first is already tide)
                    flood_timer = 0
                    # Update shadow mask for current barrier positions
                    flood_shadow_mask = create_flood_shadow_mask_with_weak_barriers(barriers)
                elif selected_barrier is not None and not game_over:
                    # Move barrier with arrow keys when active
                    barrier_x, barrier_y, barrier_width, barrier_height, is_weak, is_active = barriers[selected_barrier]
                    new_x, new_y = barrier_x, barrier_y
                    
                    if event.key == pygame.K_UP:
                        new_y -= 1
                    elif event.key == pygame.K_DOWN:
                        new_y += 1
                    elif event.key == pygame.K_LEFT:
                        new_x -= 1
                    elif event.key == pygame.K_RIGHT:
                        new_x += 1
                    
                    # Check if new position is valid
                    if is_valid_position(grid, new_x, new_y, barrier_width, barrier_height):
                        # Remove barrier from old position
                        remove_barrier(grid, barrier_x, barrier_y, barrier_width, barrier_height)
                        # Place barrier at new position
                        barrier_x, barrier_y = new_x, new_y
                        active_state = 12 if is_weak else 4  # Green for active
                        place_barrier(grid, barrier_x, barrier_y, barrier_width, barrier_height, active_state)
                        # Update barriers list
                        barriers[selected_barrier] = (barrier_x, barrier_y, barrier_width, barrier_height, is_weak, True)
                        # Recreate shadow mask
                        flood_shadow_mask = create_flood_shadow_mask_with_weak_barriers(barriers)

            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:  # Left click
                    # Get mouse position in grid coordinates
                    mouse_x, mouse_y = event.pos
                    grid_x = mouse_x // PIXEL_SIZE
                    grid_y = mouse_y // PIXEL_SIZE
                    
                    # Check if clicked on any barrier
                    for i, barrier in enumerate(barriers):
                        barrier_x, barrier_y, barrier_width, barrier_height, is_weak, is_active = barrier
                        if (barrier_x <= grid_x < barrier_x + barrier_width and 
                            barrier_y <= grid_y < barrier_y + barrier_height):
                            
                            if selected_barrier == i:
                                # Deactivate barrier
                                selected_barrier = None
                                inactive_state = 11 if is_weak else 3  # Brown/grey for inactive
                                place_barrier(grid, barrier_x, barrier_y, barrier_width, barrier_height, inactive_state)
                                barriers[i] = (barrier_x, barrier_y, barrier_width, barrier_height, is_weak, False)
                            else:
                                # Activate this barrier, deactivate others
                                for j, other_barrier in enumerate(barriers):
                                    other_x, other_y, other_w, other_h, other_weak, other_active = other_barrier
                                    if other_active:
                                        other_inactive_state = 11 if other_weak else 3
                                        place_barrier(grid, other_x, other_y, other_w, other_h, other_inactive_state)
                                        barriers[j] = (other_x, other_y, other_w, other_h, other_weak, False)
                                
                                # Activate clicked barrier
                                selected_barrier = i
                                active_state = 12 if is_weak else 4  # Green for active
                                place_barrier(grid, barrier_x, barrier_y, barrier_width, barrier_height, active_state)
                                barriers[i] = (barrier_x, barrier_y, barrier_width, barrier_height, is_weak, True)
                            break

        # ---- Update ----
        if flood_active and not game_over:
            # Check if priority zone got wet
            if check_priority_wet(grid, priority_zones):
                game_over = True
                mark_priority_wet(grid, priority_zones)
                flood_active = False
            
            flood_timer += dt
            if flood_timer >= flood_speed:
                flood_timer = 0
                # Flood the next row
                if flood_row < GRID_H - 3:  # Don't flood metadata zone
                    # Flood normally, but exclude shadow areas
                    for x in range(3, GRID_W - 3):  # Don't flood metadata zone
                        # Only flood if the cell is empty and not in shadow mask
                        if grid[flood_row][x] == 0 and (x, flood_row) not in flood_shadow_mask:
                            grid[flood_row][x] = 2  # State 2 = tide
                    flood_row += 1
                else:
                    # Flood complete
                    flood_active = False
                    # Check if level is complete
                    if not game_over:
                        level_complete = True
                        current_level += 1
                        
                        if current_level == 2:
                            # Setup Level 2
                            priority_zones = setup_level_2(grid)
                            
                            # Clear old barriers and add new ones
                            barriers.clear()
                            selected_barrier = None
                            
                            # Add strong barrier (12 pixels)
                            strong_barrier_x, strong_barrier_y = 15, 25
                            barriers.append((strong_barrier_x, strong_barrier_y, 12, 3, False, False))
                            place_barrier(grid, strong_barrier_x, strong_barrier_y, 12, 3, 3)
                            
                            # Add weak barrier (12 pixels)
                            weak_barrier_x, weak_barrier_y = 45, 25
                            barriers.append((weak_barrier_x, weak_barrier_y, 12, 3, True, False))
                            place_barrier(grid, weak_barrier_x, weak_barrier_y, 12, 3, 11)
                            
                            pygame.display.set_caption("Stem the Tide — Level 2: Two priority zones! Press SPACE to start the flood!")
                        else:
                            pygame.display.set_caption(f"Stem the Tide — Level {current_level} Complete! Press ESC to exit.")

        # ---- Draw ----
        screen.fill(STATES[0])  # Fill with empty state color

        if DRAW_GRID:
            # draw faint grid lines (optional)
            for cx in range(0, WIN_W, PIXEL_SIZE):
                pygame.draw.line(screen, GRID_COLOR, (cx, 0), (cx, WIN_H), 1)
            for cy in range(0, WIN_H, PIXEL_SIZE):
                pygame.draw.line(screen, GRID_COLOR, (0, cy), (WIN_W, cy), 1)

        # Draw all grid cells based on their state
        for y in range(GRID_H):
            for x in range(GRID_W):
                state = grid[y][x]
                if state != 0:  # Don't draw empty cells (they're already the background)
                    color = get_color_for_state(state)
                    rect = pygame.Rect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE)
                    pygame.draw.rect(screen, color, rect)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
