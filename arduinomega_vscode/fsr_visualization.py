# File: fsr_visualization.py
# Defines the class for the standalone FSR monitoring window.

import pygame

class FSRVisualizer:
    """
    Manages the Pygame window for displaying detailed FSR data.
    It does NOT run its own loop. It is updated by an external main script.
    """
    def __init__(self):
        # --- Window Settings ---
        self.width, self.height = 800, 450
        # Create a second, separate display surface.
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Robotic Gripper Force Monitor")

        # --- Fonts and Colors ---
        self.title_font = pygame.font.Font(None, 40)
        self.label_font = pygame.font.Font(None, 28)
        self.value_font = pygame.font.Font(None, 22)
        self.BG_COLOR = (15, 20, 30)
        self.JAW_COLOR = (40, 50, 65)
        self.TEXT_COLOR = (220, 220, 240)
        self.COF_COLOR = (255, 255, 0)
        
        # --- Gripper Layout ---
        jaw_width, jaw_height = 150, 360
        self.left_jaw_rect = pygame.Rect(100, 80, jaw_width, jaw_height)
        self.right_jaw_rect = pygame.Rect(self.width - 100 - jaw_width, 80, jaw_width, jaw_height)
        pad_positions = [(jaw_width / 2, 60 + i * 80) for i in range(4)]
        self.left_pad_coords = [(self.left_jaw_rect.x + x, self.left_jaw_rect.y + y) for x, y in pad_positions]
        self.right_pad_coords = [(self.right_jaw_rect.x + x, self.right_jaw_rect.y + y) for x, y in pad_positions]

    def _get_glow_color(self, value, max_value=1023):
        ratio = min(value / max_value, 1.0)
        if ratio < 0.5: r, g, b = 0, int(510 * ratio), 255
        else: r, g, b = int(510 * (ratio - 0.5)), int(255 * (1 - (ratio - 0.5) * 2)), 0
        return (r, g, b)

    def _calculate_cof(self, pad_coords, fsr_values):
        total_force = sum(fsr_values)
        if total_force == 0: return None
        weighted_x = sum(coord[0] * force for coord, force in zip(pad_coords, fsr_values))
        weighted_y = sum(coord[1] * force for coord, force in zip(pad_coords, fsr_values))
        return (weighted_x / total_force, weighted_y / total_force)

    def update(self, fsr_values):
        """Redraws this window's content."""
        self.screen.fill(self.BG_COLOR)
        title_surf = self.title_font.render("Gripper Force Distribution", True, self.TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(self.width / 2, 40)))

        # If fsr_values is empty, we can't draw details.
        if not fsr_values:
            return

        jaws_data = [
            ("Left Gripper", self.left_jaw_rect, self.left_pad_coords, fsr_values[0:4]),
            ("Right Gripper", self.right_jaw_rect, self.right_pad_coords, fsr_values[4:8])
        ]

        for name, jaw_rect, pad_coords, values in jaws_data:
            pygame.draw.rect(self.screen, self.JAW_COLOR, jaw_rect, border_radius=15)
            label_surf = self.label_font.render(name, True, self.TEXT_COLOR)
            self.screen.blit(label_surf, label_surf.get_rect(center=(jaw_rect.centerx, jaw_rect.top - 20)))

            for i, value in enumerate(values):
                pos = pad_coords[i]
                base_radius = 20
                dynamic_radius = int((value / 1023) * 30)
                if dynamic_radius > 1:
                    glow_color = self._get_glow_color(value)
                    s = pygame.Surface((dynamic_radius*2, dynamic_radius*2), pygame.SRCALPHA)
                    alpha = 150 - (i / dynamic_radius) * 150 if dynamic_radius > 0 else 150
                    pygame.draw.circle(s, (*glow_color, int(alpha)), (dynamic_radius, dynamic_radius), dynamic_radius)
                    self.screen.blit(s, (pos[0]-dynamic_radius, pos[1]-dynamic_radius))

                pygame.draw.circle(self.screen, (200, 200, 220), pos, base_radius)
                value_surf = self.value_font.render(str(value), True, self.BG_COLOR)
                self.screen.blit(value_surf, value_surf.get_rect(center=pos))

            cof = self._calculate_cof(pad_coords, values)
            if cof:
                cof_x, cof_y = int(cof[0]), int(cof[1])
                pygame.draw.line(self.screen, self.COF_COLOR, (cof_x-12, cof_y), (cof_x+12, cof_y), 2)
                pygame.draw.line(self.screen, self.COF_COLOR, (cof_x, cof_y-12), (cof_x, cof_y+12), 2)
