import pygame
import math
import random
import os
import json

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
WIDTH, HEIGHT = 1200, 800
FPS = 60
GRAVITY = 0.2  # Reduced for space-like feel
THRUST_POWER = 0.8
SIDE_THRUST = 0.3
EMERGENCY_BOOST = 3.0
MAX_FUEL = 2000
LANDING_VELOCITY_THRESHOLD = 3
LANDING_ANGLE_THRESHOLD = 10  # degrees

# SpaceX Starship dimensions (scaled for game)
BOOSTER_HEIGHT = 70
BOOSTER_WIDTH = 9
STARSHIP_HEIGHT = 50
STARSHIP_WIDTH = 9
FULL_STACK_HEIGHT = BOOSTER_HEIGHT + STARSHIP_HEIGHT
TOWER_HEIGHT = 143
CHOPSTICKS_LENGTH = 25

# Game phases
PHASE_LAUNCH = "launch"
PHASE_SEPARATION = "separation"
PHASE_RETURN = "return"
PHASE_CATCH = "catch"

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self, screen):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            # Create a surface for alpha blending
            particle_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(particle_surface, (*self.color[:3], alpha), (2, 2), 2)
            screen.blit(particle_surface, (int(self.x) - 2, int(self.y) - 2))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_particle(self, x, y, vx, vy, color, lifetime):
        self.particles.append(Particle(x, y, vx, vy, color, lifetime))

    def update(self):
        self.particles = [p for p in self.particles if p.lifetime > 0]
        for particle in self.particles:
            particle.update()

    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)

class Booster:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.angle = 0
        self.fuel = MAX_FUEL
        self.thrusting = False
        self.left_thrust = False
        self.right_thrust = False
        self.width = BOOSTER_WIDTH
        self.height = BOOSTER_HEIGHT
        self.engine_count = 33
        self.mass = 200000  # kg (empty booster mass)
        self.phase = PHASE_LAUNCH

    def update(self, keys, gravity, wind_force, thrust_sound=None):
        # Apply gravity
        self.vy += gravity

        # Apply wind
        self.vx += wind_force

        # Launch phase - automatic full thrust upward
        if self.phase == PHASE_LAUNCH:
            if self.fuel > 0:
                thrust_y = -THRUST_POWER * 2  # Strong upward thrust
                self.vy += thrust_y
                self.fuel -= 2
                if thrust_sound and not self.thrusting:
                    thrust_sound.play(-1)
                self.thrusting = True
            else:
                self.thrusting = False
                if thrust_sound:
                    thrust_sound.stop()

        # Return phase - player controlled
        elif self.phase == PHASE_RETURN:
            self.thrusting = keys[pygame.K_UP] or keys[pygame.K_w]
            self.left_thrust = keys[pygame.K_LEFT] or keys[pygame.K_a]
            self.right_thrust = keys[pygame.K_RIGHT] or keys[pygame.K_d]

            if self.thrusting and self.fuel > 0:
                thrust_x = math.sin(math.radians(self.angle)) * THRUST_POWER
                thrust_y = -math.cos(math.radians(self.angle)) * THRUST_POWER
                self.vx += thrust_x
                self.vy += thrust_y
                self.fuel -= 1
                if thrust_sound and not hasattr(self, 'was_thrusting'):
                    thrust_sound.play(-1)
                self.was_thrusting = True
            elif thrust_sound and hasattr(self, 'was_thrusting') and self.was_thrusting:
                thrust_sound.stop()
                self.was_thrusting = False

            # Side thrust for rotation
            if self.left_thrust and self.fuel > 0:
                self.angle -= 1.5
                self.fuel -= 0.3
            if self.right_thrust and self.fuel > 0:
                self.angle += 1.5
                self.fuel -= 0.3

        # Update position
        self.x += self.vx
        self.y += self.vy

    def draw(self, screen, particle_system):
        # Draw booster as rectangular body with engines
        body_color = (169, 169, 169)  # Stainless steel color
        pygame.draw.rect(screen, body_color, (self.x - self.width/2, self.y - self.height/2, self.width, self.height))

        # Draw grid fins (simplified)
        fin_color = (105, 105, 105)
        fin_size = 8
        pygame.draw.rect(screen, fin_color, (self.x - self.width/2 - fin_size, self.y - self.height/4, fin_size, fin_size))
        pygame.draw.rect(screen, fin_color, (self.x + self.width/2, self.y - self.height/4, fin_size, fin_size))

        # Draw engines at bottom
        engine_color = (255, 100, 0)
        engine_y = self.y + self.height/2
        for i in range(self.engine_count // 11):  # 3 rows
            for j in range(11):  # 11 engines per row (approximate)
                if i * 11 + j < self.engine_count:
                    engine_x = self.x - self.width/2 + (j + 0.5) * (self.width / 11)
                    pygame.draw.circle(screen, engine_color, (int(engine_x), int(engine_y + i * 3)), 2)

        # Add thrust particles during thrusting
        if self.thrusting:
            for _ in range(10):
                particle_system.add_particle(
                    self.x + random.uniform(-self.width/2, self.width/2),
                    self.y + self.height/2,
                    random.uniform(-0.5, 0.5), random.uniform(2, 5),
                    (255, 150, 0), 30
                )

class Starship:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.angle = 0
        self.width = STARSHIP_WIDTH
        self.height = STARSHIP_HEIGHT
        self.attached = True

    def update(self, gravity):
        if not self.attached:
            self.vy += gravity
            self.x += self.vx
            self.y += self.vy

    def draw(self, screen):
        # Draw Starship as cylindrical body
        body_color = (192, 192, 192)  # Stainless steel
        pygame.draw.rect(screen, body_color, (self.x - self.width/2, self.y - self.height/2, self.width, self.height))

        # Draw nose cone
        nose_points = [
            (self.x, self.y - self.height/2),
            (self.x - self.width/4, self.y - self.height/2 - 5),
            (self.x + self.width/4, self.y - self.height/2 - 5)
        ]
        pygame.draw.polygon(screen, body_color, nose_points)

class MechazillaTower:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.height = TOWER_HEIGHT
        self.chopsticks_length = CHOPSTICKS_LENGTH
        self.left_arm_angle = 0
        self.right_arm_angle = 0
        self.arms_extended = False
        self.catch_zone_x = x
        self.catch_zone_y = y - 20  # Catch point above ground
        self.catch_zone_width = 15
        self.catch_zone_height = 10

    def update(self, booster):
        # Check if booster is in catch zone
        if (abs(booster.x - self.catch_zone_x) < self.catch_zone_width and
            abs(booster.y - self.catch_zone_y) < self.catch_zone_height and
            abs(booster.vy) < 2 and abs(booster.angle) < 5):
            self.arms_extended = True
            self.left_arm_angle = -30
            self.right_arm_angle = 30
        else:
            self.arms_extended = False
            self.left_arm_angle = 0
            self.right_arm_angle = 0

    def draw(self, screen):
        # Draw tower structure
        tower_color = (100, 100, 100)
        pygame.draw.rect(screen, tower_color, (self.x - 5, self.y - self.height, 10, self.height))

        # Draw platform at top
        pygame.draw.rect(screen, tower_color, (self.x - 20, self.y - self.height, 40, 10))

        # Draw chopsticks arms
        arm_color = (80, 80, 80)

        # Left arm
        left_arm_end_x = self.x - self.chopsticks_length * math.cos(math.radians(self.left_arm_angle))
        left_arm_end_y = (self.y - self.height + 5) + self.chopsticks_length * math.sin(math.radians(self.left_arm_angle))
        pygame.draw.line(screen, arm_color, (self.x - 15, self.y - self.height + 5),
                        (left_arm_end_x, left_arm_end_y), 3)

        # Right arm
        right_arm_end_x = self.x + self.chopsticks_length * math.cos(math.radians(self.right_arm_angle))
        right_arm_end_y = (self.y - self.height + 5) + self.chopsticks_length * math.sin(math.radians(self.right_arm_angle))
        pygame.draw.line(screen, arm_color, (self.x + 15, self.y - self.height + 5),
                        (right_arm_end_x, right_arm_end_y), 3)

        # Draw catch zone (semi-transparent)
        catch_surface = pygame.Surface((self.catch_zone_width * 2, self.catch_zone_height * 2), pygame.SRCALPHA)
        pygame.draw.rect(catch_surface, (0, 255, 0, 100), (0, 0, self.catch_zone_width * 2, self.catch_zone_height * 2))
        screen.blit(catch_surface, (self.catch_zone_x - self.catch_zone_width, self.catch_zone_y - self.catch_zone_height))

class Ship:  # Legacy ship class for compatibility
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 2  # Initial downward velocity
        self.angle = 0  # Rotation angle in degrees
        self.fuel = MAX_FUEL
        self.thrusting = False
        self.left_thrust = False
        self.right_thrust = False
        self.emergency_boost = False
        self.width = 20
        self.height = 40
        self.was_thrusting = False  # Track previous thrust state

    def update(self, keys, gravity, wind_force, thrust_sound=None):
        # Handle input
        self.thrusting = keys[pygame.K_UP] or keys[pygame.K_w]
        self.left_thrust = keys[pygame.K_LEFT] or keys[pygame.K_a]
        self.right_thrust = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        self.emergency_boost = keys[pygame.K_SPACE]

        # Apply gravity
        self.vy += gravity

        # Apply wind
        self.vx += wind_force

        # Apply thrust
        if self.thrusting and self.fuel > 0:
            thrust_x = math.sin(math.radians(self.angle)) * THRUST_POWER
            thrust_y = -math.cos(math.radians(self.angle)) * THRUST_POWER
            self.vx += thrust_x
            self.vy += thrust_y
            self.fuel -= 1
            # Play thrust sound only when starting to thrust
            if thrust_sound and not self.was_thrusting:
                thrust_sound.play(-1)  # Loop the sound
        elif thrust_sound and self.was_thrusting:
            thrust_sound.stop()  # Stop when not thrusting

        self.was_thrusting = self.thrusting

        # Apply side thrust for rotation
        if self.left_thrust and self.fuel > 0:
            self.angle -= 2
            self.fuel -= 0.5
        if self.right_thrust and self.fuel > 0:
            self.angle += 2
            self.fuel -= 0.5

        # Emergency boost
        if self.emergency_boost and self.fuel > 50:
            thrust_x = math.sin(math.radians(self.angle)) * EMERGENCY_BOOST
            thrust_y = -math.cos(math.radians(self.angle)) * EMERGENCY_BOOST
            self.vx += thrust_x
            self.vy += thrust_y
            self.fuel -= 50

        # Update position
        self.x += self.vx
        self.y += self.vy

        # Keep ship on screen (wrap around)
        if self.x < 0:
            self.x = WIDTH
        elif self.x > WIDTH:
            self.x = 0

    def draw(self, screen, particle_system):
        # Draw ship as a simple rocket shape
        points = [
            (self.x, self.y - self.height/2),
            (self.x - self.width/2, self.y + self.height/2),
            (self.x + self.width/2, self.y + self.height/2)
        ]

        # Rotate points
        rotated_points = []
        for px, py in points:
            dx = px - self.x
            dy = py - self.y
            rotated_x = dx * math.cos(math.radians(self.angle)) - dy * math.sin(math.radians(self.angle))
            rotated_y = dx * math.sin(math.radians(self.angle)) + dy * math.cos(math.radians(self.angle))
            rotated_points.append((self.x + rotated_x, self.y + rotated_y))

        pygame.draw.polygon(screen, WHITE, rotated_points)

        # Add thrust particles
        if self.thrusting:
            for _ in range(5):
                particle_system.add_particle(
                    self.x, self.y + self.height/2,
                    random.uniform(-1, 1), random.uniform(1, 3),
                    ORANGE, 20
                )

class Terrain:
    def __init__(self):
        self.points = []
        self.generate_terrain()

    def generate_terrain(self):
        self.points = []
        for x in range(0, WIDTH + 50, 50):
            y = HEIGHT - 100 + random.randint(-20, 20)
            self.points.append((x, y))
        self.points.append((WIDTH, HEIGHT))
        self.points.append((0, HEIGHT))

    def draw(self, screen):
        pygame.draw.polygon(screen, GREEN, self.points)

class LandingPad:
    def __init__(self, x, y, width=100):
        self.x = x
        self.y = y
        self.width = width
        self.height = 10

    def draw(self, screen):
        pygame.draw.rect(screen, YELLOW, (self.x - self.width/2, self.y - self.height, self.width, self.height))

    def check_landing(self, ship):
        ship_bottom = ship.y + ship.height/2
        ship_left = ship.x - ship.width/2
        ship_right = ship.x + ship.width/2

        if (ship_bottom >= self.y - self.height and
            ship_bottom <= self.y and
            ship_left >= self.x - self.width/2 and
            ship_right <= self.x + self.width/2):
            return True
        return False

class HUD:
    def __init__(self):
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen, ship, score, level, altitude):
        # Fuel bar
        fuel_percentage = ship.fuel / MAX_FUEL
        pygame.draw.rect(screen, RED, (10, 10, 200, 20))
        pygame.draw.rect(screen, GREEN, (10, 10, 200 * fuel_percentage, 20))

        # Text info
        texts = [
            f"Fuel: {int(ship.fuel)}",
            f"Altitude: {int(altitude)}m",
            f"Vertical Speed: {ship.vy:.1f} m/s",
            f"Horizontal Speed: {ship.vx:.1f} m/s",
            f"Angle: {int(ship.angle)}°",
            f"Score: {score}",
            f"Level: {level}"
        ]

        for i, text in enumerate(texts):
            text_surface = self.font.render(text, True, WHITE)
            screen.blit(text_surface, (10, 40 + i * 25))

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Starship Lander")
        self.clock = pygame.time.Clock()
        self.particle_system = ParticleSystem()
        self.hud = HUD()
        self.level = 1
        self.score = 0
        self.high_score = self.load_high_score()
        self.game_state = "menu"  # menu, playing, win, lose
        self.wind_force = 0
        self.level_gravity = GRAVITY
        self.load_sounds()
        self.reset_game()

    def load_sounds(self):
        # Audio placeholders - replace with actual sound files
        try:
            self.thrust_sound = pygame.mixer.Sound("thrust.wav")  # Engine thrust sound
            self.crash_sound = pygame.mixer.Sound("crash.wav")    # Crash/explosion sound
            self.success_sound = pygame.mixer.Sound("success.wav") # Successful landing sound
            self.thrust_sound.set_volume(0.3)
            self.crash_sound.set_volume(0.5)
            self.success_sound.set_volume(0.5)
        except:
            # If sound files don't exist, create silent placeholders
            self.thrust_sound = None
            self.crash_sound = None
            self.success_sound = None
            print("Sound files not found. Add thrust.wav, crash.wav, and success.wav to the game directory.")

    def reset_game(self):
        self.ship = Ship(WIDTH // 2, 50)
        self.terrain = Terrain()
        self.landing_pad = LandingPad(WIDTH // 2, HEIGHT - 120)
        self.score = 0
        self.set_level_difficulty()

    def set_level_difficulty(self):
        if self.level == 1:
            self.level_gravity = GRAVITY
            self.wind_force = 0
            self.ship.fuel = MAX_FUEL
        elif self.level == 2:
            self.level_gravity = GRAVITY * 1.2
            self.wind_force = 0.05
            self.ship.fuel = MAX_FUEL * 0.8
        elif self.level == 3:
            self.level_gravity = GRAVITY * 1.5
            self.wind_force = 0.1
            self.ship.fuel = MAX_FUEL * 0.6
        else:
            self.level_gravity = GRAVITY * 2.0
            self.wind_force = 0.15
            self.ship.fuel = MAX_FUEL * 0.4

    def add_explosion_particles(self):
        # Add explosion particles at ship's position
        for _ in range(50):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particle_system.add_particle(
                self.ship.x, self.ship.y,
                vx, vy,
                RED, 60
            )

    def load_high_score(self):
        try:
            with open("high_score.json", "r") as f:
                return json.load(f)
        except:
            return 0

    def save_high_score(self):
        with open("high_score.json", "w") as f:
            json.dump(self.high_score, f)

    def update(self):
        if self.game_state == "playing":
            keys = pygame.key.get_pressed()
            self.ship.update(keys, self.level_gravity, self.wind_force, self.thrust_sound)
            self.particle_system.update()

            # Check collisions
            altitude = HEIGHT - self.ship.y - self.ship.height/2
            if self.ship.y + self.ship.height/2 >= HEIGHT - 100:  # Ground collision
                if self.landing_pad.check_landing(self.ship):
                    if abs(self.ship.vy) < LANDING_VELOCITY_THRESHOLD and abs(self.ship.angle) < LANDING_ANGLE_THRESHOLD:
                        self.game_state = "win"
                        self.score += int(self.ship.fuel * 0.1) + 1000
                        self.level += 1
                        if self.level > 4:
                            self.level = 1  # Reset to level 1 after completing all levels
                        # Play success sound
                        if self.success_sound:
                            self.success_sound.play()
                    else:
                        self.game_state = "lose"
                        # Play crash sound
                        if self.crash_sound:
                            self.crash_sound.play()
                        # Add explosion particles
                        self.add_explosion_particles()
                else:
                    self.game_state = "lose"
                    # Play crash sound
                    if self.crash_sound:
                        self.crash_sound.play()
                    # Add explosion particles
                    self.add_explosion_particles()

            # Update score
            self.score += 1

    def draw(self):
        self.screen.fill(BLACK)

        if self.game_state == "menu":
            self.draw_menu()
        elif self.game_state == "playing":
            self.draw_game()
        elif self.game_state == "win":
            self.draw_win_screen()
        elif self.game_state == "lose":
            self.draw_lose_screen()

        pygame.display.flip()

    def draw_menu(self):
        font = pygame.font.Font(None, 48)
        title = font.render("Starship Lander", True, WHITE)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 100))

        font = pygame.font.Font(None, 24)
        instructions = [
            "Use UP/W to thrust, LEFT/RIGHT/A/D to rotate",
            "SPACE for emergency boost",
            "Land with low speed and minimal tilt",
            "Press SPACE to start"
        ]

        for i, instruction in enumerate(instructions):
            text = font.render(instruction, True, WHITE)
            self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 50 + i * 30))

        high_score_text = font.render(f"High Score: {self.high_score}", True, YELLOW)
        self.screen.blit(high_score_text, (WIDTH//2 - high_score_text.get_width()//2, HEIGHT//2 + 100))

    def draw_game(self):
        # Draw stars
        for _ in range(50):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT//2)
            pygame.draw.circle(self.screen, WHITE, (x, y), 1)

        self.terrain.draw(self.screen)
        self.landing_pad.draw(self.screen)
        self.ship.draw(self.screen, self.particle_system)
        self.particle_system.draw(self.screen)

        altitude = HEIGHT - self.ship.y - self.ship.height/2
        self.hud.draw(self.screen, self.ship, self.score, self.level, altitude)

    def draw_win_screen(self):
        font = pygame.font.Font(None, 48)
        win_text = font.render("Successful Landing!", True, GREEN)
        self.screen.blit(win_text, (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 50))

        font = pygame.font.Font(None, 24)
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2))

        restart_text = font.render("Press R to restart, Q to quit", True, WHITE)
        self.screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 50))

    def draw_lose_screen(self):
        font = pygame.font.Font(None, 48)
        lose_text = font.render("Crash!", True, RED)
        self.screen.blit(lose_text, (WIDTH//2 - lose_text.get_width()//2, HEIGHT//2 - 50))

        font = pygame.font.Font(None, 24)
        score_text = font.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2))

        restart_text = font.render("Press R to restart, Q to quit", True, WHITE)
        self.screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 50))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return False
                elif event.key == pygame.K_r and self.game_state in ["win", "lose"]:
                    self.reset_game()
                    self.game_state = "playing"
                elif event.key == pygame.K_SPACE and self.game_state == "menu":
                    self.game_state = "playing"
        return True

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()