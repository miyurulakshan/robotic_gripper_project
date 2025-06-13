# File: fsr_visualization.py
# A creative, intuitive visualization that mimics the gripper jaws.
# MODIFIED for a vertical 4-sensor-per-jaw arrangement.

import pygame
import math

class FSRVisualizer:
    """
    Creates a Pygame window to visualize FSR pressure data as a top-down
    view of the robotic gripper, including a Center of Force calculation.
    """
    def __init__(self, num_sensors=8):
        """
        Initializes the Pygame window and sets up parameters for the gripper view.
        """
        if num_sensors != 8:
            raise ValueError("This visualization is designed for exactly 8 sensors.")
            
        pygame.init()
        self.num_sensors = num_sensors
        
        # --- Window Settings ---
        self.width, self.height = 800, 450
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Robotic Gripper Force Monitor")

        # --- Fonts ---
        self.title_font = pygame.font.Font(None, 40)
        self.label_font = pygame.font.Font(None, 28)
        self.value_font = pygame.font.Font(None, 22)

        # --- Colors ---
        self.BG_COLOR = (15, 20, 30)      # Very dark blue
        self.JAW_COLOR = (40, 50, 65)     # Dark grey-blue
        self.TEXT_COLOR = (220, 220, 240) # Light grey-blue
        self.COF_COLOR = (255, 255, 0)    # Yellow for Center of Force

        # --- Gripper Layout (MODIFIED FOR VERTICAL SENSORS) ---
        # Jaws are now narrower and taller to better suit the vertical layout.
        jaw_width = 150
        jaw_height = 360
        self.left_jaw_rect = pygame.Rect(100, 80, jaw_width, jaw_height)
        self.right_jaw_rect = pygame.Rect(self.width - 100 - jaw_width, 80, jaw_width, jaw_height)
        
        # Positions for the 4 sensor pads on each jaw (relative to the jaw's top-left)
        # These are now in a single column, centered horizontally.
        pad_positions = [
            (jaw_width / 2, 60),  # Sensor 1 (Top)
            (jaw_width / 2, 140), # Sensor 2
            (jaw_width / 2, 220), # Sensor 3
            (jaw_width / 2, 300)  # Sensor 4 (Bottom)
        ]

        # Store the absolute screen coordinates for each sensor pad
        self.left_pad_coords = [(self.left_jaw_rect.x + x, self.left_jaw_rect.y + y) for x, y in pad_positions]
        self.right_pad_coords = [(self.right_jaw_rect.x + x, self.right_jaw_rect.y + y) for x, y in pad_positions]

    def _get_glow_color(self, value, max_value=1023):
        """Calculates a color from blue (low) to red (high) for a glowing effect."""
        ratio = min(value / max_value, 1.0)
        # Transition from blue (0,0,255) -> cyan (0,255,255) -> red (255,0,0)
        if ratio < 0.5:
            # Blue to Cyan
            r = 0
            g = int(255 * (ratio * 2))
            b = 255
        else:
            # Cyan to Red
            r = int(255 * ((ratio - 0.5) * 2))
            g = int(255 * (1 - ((ratio - 0.5) * 2)))
            b = 0
        return (r, g, b)

    def _calculate_cof(self, pad_coords, fsr_values):
        """Calculates the Center of Force for one jaw."""
        total_force = sum(fsr_values)
        if total_force == 0:
            return None # No force, no center

        weighted_x = sum(coord[0] * force for coord, force in zip(pad_coords, fsr_values))
        weighted_y = sum(coord[1] * force for coord, force in zip(pad_coords, fsr_values))
        
        return (weighted_x / total_force, weighted_y / total_force)

    def update(self, fsr_values):
        """Redraws the screen with the updated gripper view."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False

        # --- Drawing Background ---
        self.screen.fill(self.BG_COLOR)
        title_surf = self.title_font.render("Gripper Force Distribution", True, self.TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(self.width / 2, 40)))

        # --- Split sensor data for each jaw ---
        left_values = fsr_values[0:4]
        right_values = fsr_values[4:8]

        # --- Process and Draw Each Jaw ---
        jaws_data = [
            ("Left Gripper", self.left_jaw_rect, self.left_pad_coords, left_values),
            ("Right Gripper", self.right_jaw_rect, self.right_pad_coords, right_values)
        ]

        for name, jaw_rect, pad_coords, values in jaws_data:
            # Draw the main jaw rectangle
            pygame.draw.rect(self.screen, self.JAW_COLOR, jaw_rect, border_radius=15)
            
            # Draw the label
            label_surf = self.label_font.render(name, True, self.TEXT_COLOR)
            self.screen.blit(label_surf, label_surf.get_rect(center=(jaw_rect.centerx, jaw_rect.top - 20)))

            # Draw each sensor pad
            for i, value in enumerate(values):
                pos = pad_coords[i]
                
                # Base radius and pressure-based radius
                base_radius = 20
                dynamic_radius = int((value / 1023) * 40)
                
                # Draw glowing effect
                if dynamic_radius > 2:
                    glow_color = self._get_glow_color(value)
                    # Draw multiple circles with decreasing alpha for a glow
                    for j in range(dynamic_radius, 0, -2):
                        s = pygame.Surface((j*2, j*2), pygame.SRCALPHA)
                        alpha = 150 - (j / dynamic_radius) * 150
                        pygame.draw.circle(s, (glow_color[0], glow_color[1], glow_color[2], alpha), (j, j), j)
                        self.screen.blit(s, (pos[0]-j, pos[1]-j))

                # Draw the solid center circle
                pygame.draw.circle(self.screen, (200, 200, 220), pos, base_radius)
                
                # Draw the pressure value text
                value_surf = self.value_font.render(str(value), True, self.BG_COLOR)
                self.screen.blit(value_surf, value_surf.get_rect(center=pos))

            # Calculate and draw Center of Force
            cof = self._calculate_cof(pad_coords, values)
            if cof:
                cof_x, cof_y = int(cof[0]), int(cof[1])
                pygame.draw.line(self.screen, self.COF_COLOR, (cof_x - 12, cof_y), (cof_x + 12, cof_y), 2)
                pygame.draw.line(self.screen, self.COF_COLOR, (cof_x, cof_y - 12), (cof_x, cof_y + 12), 2)

        pygame.display.flip()
        return True

    def close(self):
        pygame.quit()