import json
import os
import random
import sys
import math
import hashlib
from array import array

import pygame

os.environ.setdefault("SDL_HINT_ORIENTATIONS", "LandscapeLeft LandscapeRight")

# Initialize Pygame
pygame.init()

# Initialize audio. The game remains playable if no audio device is available.
AUDIO_ENABLED = True
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except pygame.error as error:
    AUDIO_ENABLED = False
    print(f"Audio disabled: {error}")

# Procedural audio helpers: no external sound files are required.
def create_tone(frequency, duration, volume=0.3, wave_type="sine"):
    if not AUDIO_ENABLED:
        return None

    sample_rate = pygame.mixer.get_init()[0]
    sample_count = int(sample_rate * duration)
    samples = array("h")

    for index in range(sample_count):
        time = index / sample_rate
        fade = min(1.0, index / max(1, sample_rate * 0.01))
        fade *= min(1.0, (sample_count - index) / max(1, sample_rate * 0.03))
        phase = 2.0 * math.pi * frequency * time

        if wave_type == "square":
            value = 1.0 if math.sin(phase) >= 0 else -1.0
        else:
            value = math.sin(phase)

        sample = int(32767 * volume * fade * value)
        samples.append(sample)
        samples.append(sample)

    return pygame.mixer.Sound(buffer=samples.tobytes())


def create_melody(notes, note_duration=0.18, volume=0.12):
    if not AUDIO_ENABLED:
        return None

    sample_rate = pygame.mixer.get_init()[0]
    samples = array("h")

    for frequency in notes:
        sample_count = int(sample_rate * note_duration)
        for index in range(sample_count):
            time = index / sample_rate
            envelope = min(1.0, index / max(1, sample_rate * 0.02))
            envelope *= min(1.0, (sample_count - index) / max(1, sample_rate * 0.04))
            value = 0.0 if frequency == 0 else math.sin(2.0 * math.pi * frequency * time)
            sample = int(32767 * volume * envelope * value)
            samples.append(sample)
            samples.append(sample)

    return pygame.mixer.Sound(buffer=samples.tobytes())


def play_sound(sound):
    if AUDIO_ENABLED and sound is not None:
        sound.play()


# Sound effects and looping background melody
SOUND_JUMP = create_tone(620, 0.12, 0.22)
SOUND_COLLISION = create_tone(110, 0.35, 0.30, "square")
SOUND_BUTTON = create_tone(420, 0.07, 0.16)
SOUND_BULLET_HIT = create_tone(185, 0.11, 0.26, "square")
SOUND_BULLET_SPARK = create_tone(940, 0.06, 0.15)
SOUND_VICTORY = create_melody([523.25, 659.25, 783.99, 1046.50], 0.20, 0.22)
BOSS_AUDIO = {
    "ROBOT": create_melody([82,110,82,165,110,220,82,55],0.11,0.20),
    "GHOST": create_melody([523,0,392,0,311,233,174,0],0.19,0.15),
    "DRAGON": create_melody([65,82,98,131,98,82,65,49],0.15,0.23),
    "MONKEY": create_melody([196,196,262,196,330,262,196,147],0.10,0.20),
    "SNOW": create_melody([784,659,880,698,988,784,659,523],0.18,0.13),
    "ALIEN": create_melody([210,420,315,630,280,560,350,700],0.13,0.17),
    "SHADOW TARUN": create_melody([147,220,165,247,185,277,138,207],0.14,0.20),
}
BOSS_ATTACK_AUDIO = {
    "ROBOT": create_tone(145,0.18,0.28,"square"), "GHOST": create_tone(455,0.24,0.20),
    "DRAGON": create_tone(72,0.32,0.32,"square"), "MONKEY": create_tone(105,0.24,0.30,"square"),
    "SNOW": create_tone(880,0.20,0.18), "ALIEN": create_tone(325,0.20,0.24),
    "SHADOW TARUN": create_tone(205,0.28,0.27,"square"),
}
BOSS_DEFEAT_AUDIO = {
    "ROBOT": create_melody([220,165,110,55],0.13,0.24), "GHOST": create_melody([392,311,233,116],0.17,0.18),
    "DRAGON": create_melody([196,131,98,65],0.16,0.26), "MONKEY": create_melody([330,262,196,98],0.14,0.23),
    "SNOW": create_melody([988,784,659,392],0.16,0.17), "ALIEN": create_melody([700,350,175,87],0.14,0.22),
    "SHADOW TARUN": create_melody([277,220,165,110,55],0.15,0.24),
}
BOSS_MUSIC_CHANNEL=None
ACTIVE_BOSS_THEME=""

def start_boss_music(name):
    global BOSS_MUSIC_CHANNEL,ACTIVE_BOSS_THEME
    stop_boss_music(); sound=BOSS_AUDIO.get(name)
    if AUDIO_ENABLED and sound is not None:
        BOSS_MUSIC_CHANNEL=sound.play(loops=-1); BOSS_MUSIC_CHANNEL.set_volume(0.0 if SFX_MUTED else SFX_VOLUME*0.65)
        ACTIVE_BOSS_THEME=name
    if MUSIC_CHANNEL is not None: MUSIC_CHANNEL.set_volume((0.0 if MUSIC_MUTED else MUSIC_VOLUME)*0.25)

def stop_boss_music():
    global BOSS_MUSIC_CHANNEL,ACTIVE_BOSS_THEME
    if BOSS_MUSIC_CHANNEL is not None: BOSS_MUSIC_CHANNEL.stop()
    BOSS_MUSIC_CHANNEL=None; ACTIVE_BOSS_THEME=""
    if MUSIC_CHANNEL is not None: MUSIC_CHANNEL.set_volume(0.0 if MUSIC_MUTED else MUSIC_VOLUME)
BACKGROUND_MUSIC = create_melody(
    [261.63, 329.63, 392.00, 329.63, 293.66, 349.23, 440.00, 349.23],
    0.22,
    0.07,
)

# Runtime volume settings
# Music volume uses the mixer range directly: 0% to 100%.
MUSIC_VOLUME = 1.00  # Default and maximum: 100%
SFX_VOLUME = 0.75
MUSIC_MUTED = False
SFX_MUTED = False
MUSIC_CHANNEL = None


def apply_audio_volumes():
    music_level = 0.0 if MUSIC_MUTED else MUSIC_VOLUME
    effects_level = 0.0 if SFX_MUTED else SFX_VOLUME

    if MUSIC_CHANNEL is not None:
        MUSIC_CHANNEL.set_volume(music_level if not ACTIVE_BOSS_THEME else music_level*0.25)
    if BOSS_MUSIC_CHANNEL is not None:
        BOSS_MUSIC_CHANNEL.set_volume(effects_level*0.65)

    for sound in (
        SOUND_JUMP,
        SOUND_COLLISION,
        SOUND_BUTTON,
        SOUND_BULLET_HIT,
        SOUND_BULLET_SPARK,
        SOUND_VICTORY,
        *BOSS_AUDIO.values(),
        *BOSS_ATTACK_AUDIO.values(),
        *BOSS_DEFEAT_AUDIO.values(),
    ):
        if sound is not None:
            sound.set_volume(effects_level)


if AUDIO_ENABLED and BACKGROUND_MUSIC is not None:
    MUSIC_CHANNEL = BACKGROUND_MUSIC.play(loops=-1)
    apply_audio_volumes()


# Game Constants
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

# Fixed Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 177, 76)
GOLD = (255, 215, 0)
RED = (200, 50, 50)
LIGHT_GRAY = (240, 240, 240)
MOON_COLOR = (245, 245, 220)

# Day/Night Color Keyframes for Interpolation
COLOR_DAY_SKY = (135, 206, 235)
COLOR_SUNSET_SKY = (255, 140, 0)
COLOR_NIGHT_SKY = (20, 24, 43)

COLOR_DAY_GROUND = (24, 130, 54)
COLOR_SUNSET_GROUND = (120, 70, 20)
COLOR_NIGHT_GROUND = (10, 35, 15)

# Generate a natural-looking, repeatable star field. Each star has its own
# position, radius, brightness, colour temperature, and twinkle timing.
star_generator = random.Random(42)
stars = []
for _ in range(145):
    colour = star_generator.choice(
        [
            (255, 252, 235),  # warm white
            (235, 242, 255),  # cool white
            (255, 244, 205),  # pale gold
            (220, 232, 255),  # pale blue
        ]
    )
    stars.append(
        {
            "x": star_generator.randint(8, SCREEN_WIDTH - 8),
            "y": star_generator.randint(8, 390),
            "radius": star_generator.choices([1, 2, 3], weights=[72, 24, 4])[0],
            "brightness": star_generator.uniform(0.45, 1.0),
            "twinkle_speed": star_generator.uniform(1.2, 4.0),
            "twinkle_phase": star_generator.uniform(0, math.tau),
            "colour": colour,
        }
    )

# Optional special night event selected from the difficulty screen.
meteor_shower_mode = True  # Enabled by default
meteor_shower = []
next_shower_meteor_time = 0

alien_ship = {
    "active": False,
    "x": -180.0,
    "y": 105.0,
    "speed": 85.0,
    "direction": 1,
}
next_alien_ship_time = pygame.time.get_ticks() + star_generator.randint(5000, 9000)

# Shooting-star state. A new meteor appears after a random quiet interval.
shooting_star = {
    "active": False,
    "x": 0.0,
    "y": 0.0,
    "speed_x": 0.0,
    "speed_y": 0.0,
    "life": 0.0,
    "max_life": 0.0,
    "tail_length": 0,
}
next_shooting_star_time = pygame.time.get_ticks() + star_generator.randint(3500, 8500)


def update_and_draw_shooting_star(surface, night_strength):
    global next_shooting_star_time

    now = pygame.time.get_ticks()
    delta_time = clock.get_time() / 1000.0 if "clock" in globals() else 1.0 / FPS

    # Shooting stars only appear when the sky is sufficiently dark.
    if (
        not shooting_star["active"]
        and night_strength > 0.68
        and now >= next_shooting_star_time
    ):
        shooting_star["active"] = True
        shooting_star["x"] = float(star_generator.randint(220, SCREEN_WIDTH - 40))
        shooting_star["y"] = float(star_generator.randint(25, 160))
        shooting_star["speed_x"] = float(star_generator.randint(-440, -320))
        shooting_star["speed_y"] = float(star_generator.randint(150, 230))
        shooting_star["max_life"] = star_generator.uniform(0.65, 1.05)
        shooting_star["life"] = shooting_star["max_life"]
        shooting_star["tail_length"] = star_generator.randint(65, 105)

    if not shooting_star["active"]:
        return

    shooting_star["x"] += shooting_star["speed_x"] * delta_time
    shooting_star["y"] += shooting_star["speed_y"] * delta_time
    shooting_star["life"] -= delta_time

    speed_length = math.hypot(
        shooting_star["speed_x"],
        shooting_star["speed_y"],
    )
    direction_x = shooting_star["speed_x"] / speed_length
    direction_y = shooting_star["speed_y"] / speed_length
    fade = max(0.0, shooting_star["life"] / shooting_star["max_life"])
    alpha = int(255 * fade * night_strength)

    meteor_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    head_x = int(shooting_star["x"])
    head_y = int(shooting_star["y"])

    # Layered trail: a wide, faint outer tail and a narrow bright inner tail.
    for width, length_scale, opacity in ((7, 1.0, 0.16), (4, 0.72, 0.35), (2, 0.42, 0.75)):
        tail_length = shooting_star["tail_length"] * length_scale
        tail_x = int(head_x - direction_x * tail_length)
        tail_y = int(head_y - direction_y * tail_length)
        pygame.draw.line(
            meteor_layer,
            (220, 235, 255, int(alpha * opacity)),
            (tail_x, tail_y),
            (head_x, head_y),
            width,
        )

    pygame.draw.circle(meteor_layer, (255, 252, 235, alpha), (head_x, head_y), 3)
    pygame.draw.circle(
        meteor_layer,
        (210, 230, 255, alpha // 3),
        (head_x, head_y),
        8,
    )
    surface.blit(meteor_layer, (0, 0))

    if (
        shooting_star["life"] <= 0
        or shooting_star["x"] < -120
        or shooting_star["y"] > 430
    ):
        shooting_star["active"] = False
        next_shooting_star_time = now + star_generator.randint(4500, 11000)


def update_and_draw_meteor_shower(surface, night_strength):
    global next_shower_meteor_time

    if not meteor_shower_mode or night_strength <= 0.68:
        meteor_shower.clear()
        return

    now = pygame.time.get_ticks()
    delta_time = clock.get_time() / 1000.0 if "clock" in globals() else 1.0 / FPS

    if now >= next_shower_meteor_time:
        for _ in range(star_generator.randint(2, 4)):
            meteor_shower.append(
                {
                    "x": float(star_generator.randint(180, SCREEN_WIDTH + 120)),
                    "y": float(star_generator.randint(-30, 150)),
                    "vx": float(star_generator.randint(-520, -350)),
                    "vy": float(star_generator.randint(190, 290)),
                    "life": star_generator.uniform(0.60, 1.15),
                    "max_life": 1.15,
                    "length": star_generator.randint(55, 120),
                }
            )
        next_shower_meteor_time = now + star_generator.randint(500, 1300)

    layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for meteor in meteor_shower[:]:
        meteor["x"] += meteor["vx"] * delta_time
        meteor["y"] += meteor["vy"] * delta_time
        meteor["life"] -= delta_time
        fade = max(0.0, min(1.0, meteor["life"] / meteor["max_life"]))
        alpha = int(235 * fade * night_strength)
        speed = math.hypot(meteor["vx"], meteor["vy"])
        dx = meteor["vx"] / speed
        dy = meteor["vy"] / speed
        head = (int(meteor["x"]), int(meteor["y"]))
        tail = (
            int(meteor["x"] - dx * meteor["length"]),
            int(meteor["y"] - dy * meteor["length"]),
        )
        pygame.draw.line(layer, (205, 225, 255, alpha // 3), tail, head, 6)
        pygame.draw.line(layer, (245, 248, 255, alpha), tail, head, 2)
        pygame.draw.circle(layer, (255, 250, 225, alpha), head, 3)

        if meteor["life"] <= 0 or meteor["x"] < -150 or meteor["y"] > 450:
            meteor_shower.remove(meteor)
    surface.blit(layer, (0, 0))


def update_and_draw_alien_ship(surface, night_strength):
    global next_alien_ship_time

    if not meteor_shower_mode or night_strength <= 0.68:
        alien_ship["active"] = False
        return

    now = pygame.time.get_ticks()
    delta_time = clock.get_time() / 1000.0 if "clock" in globals() else 1.0 / FPS

    if not alien_ship["active"] and now >= next_alien_ship_time:
        alien_ship["active"] = True
        alien_ship["direction"] = star_generator.choice([-1, 1])
        alien_ship["x"] = -130.0 if alien_ship["direction"] == 1 else SCREEN_WIDTH + 130.0
        alien_ship["y"] = float(star_generator.randint(75, 185))
        alien_ship["speed"] = float(star_generator.randint(70, 115))

    if not alien_ship["active"]:
        return

    alien_ship["x"] += alien_ship["speed"] * alien_ship["direction"] * delta_time
    x = int(alien_ship["x"])
    y = int(alien_ship["y"] + math.sin(now / 350.0) * 5)
    layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    # Soft engine/tractor glow.
    pygame.draw.ellipse(layer, (90, 220, 255, 35), (x - 48, y + 16, 96, 32))
    pygame.draw.ellipse(layer, (160, 180, 195, 255), (x - 52, y, 104, 32))
    pygame.draw.ellipse(layer, (75, 90, 108, 255), (x - 42, y + 12, 84, 22))

    # Transparent cockpit dome.
    pygame.draw.ellipse(layer, (145, 225, 255, 150), (x - 29, y - 28, 58, 42))
    pygame.draw.arc(layer, (220, 250, 255, 230), (x - 29, y - 28, 58, 42), math.pi, math.tau, 2)

    # Alien visible inside the cockpit.
    pygame.draw.ellipse(layer, (105, 230, 110, 255), (x - 12, y - 20, 24, 28))
    pygame.draw.ellipse(layer, (10, 18, 28, 255), (x - 8, y - 12, 6, 9))
    pygame.draw.ellipse(layer, (10, 18, 28, 255), (x + 2, y - 12, 6, 9))
    pygame.draw.arc(layer, (35, 90, 45, 255), (x - 5, y - 4, 10, 7), 0, math.pi, 1)

    # Pulsing lights around the ship.
    light_on = (now // 180) % 2 == 0
    for offset, colour in ((-32, (255, 70, 70)), (0, (255, 230, 80)), (32, (80, 255, 160))):
        brightness = 255 if light_on else 130
        pygame.draw.circle(layer, (*colour, brightness), (x + offset, y + 20), 4)

    surface.blit(layer, (0, 0))

    if x < -150 or x > SCREEN_WIDTH + 150:
        alien_ship["active"] = False
        next_alien_ship_time = now + star_generator.randint(6500, 12000)


# Setup Screen
# Start in fullscreen while preserving the 800 x 600 logical game layout.
# Press F11 to switch between fullscreen and windowed mode.
FULLSCREEN_MODE = True
screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT),
    pygame.FULLSCREEN | pygame.SCALED,
)
pygame.display.set_caption("Dinosaur Adventure Game")
clock = pygame.time.Clock()

# Fonts
try:
    font_title = pygame.font.SysFont("Arial", 40, bold=True)
    font_sub = pygame.font.SysFont("Arial", 28)
    font_ui = pygame.font.SysFont("Arial", 24, bold=True)
except Exception:
    font_title = pygame.font.Font(None, 40)
    font_sub = pygame.font.Font(None, 28)
    font_ui = pygame.font.Font(None, 24)


class GameState:
    LOBBY = 0
    READY_SCREEN = 1
    PLAYING = 2
    PAUSE_FIRST_JUMP = 3
    VICTORY = 4
    ENTER_NAME = 5
    LEADERBOARD = 6
    LEVEL_SELECT = 7
    PAUSED = 8
    RESUME_COUNTDOWN = 9
    SKINS = 10
    ACCOUNT_NAME = 11
    ACCOUNT_PASSWORD = 12
    SKIN_MENU = 13
    GUN_SKINS = 14
    SKILLS = 15
    PETS = 16
    DINO_MANSION = 17
    ALL_MENU = 18
    ALL_BOSSES = 19
    BOSS_ARENA = 20
    COLLECTION = 21
    PET_COLLECTION = 22
    BOSS_POWERS = 23
    TROPHY_ROOM = 24
    ACHIEVEMENTS = 25
    BOSS_LOADING = 26
    TEAM_BATTLE = 27
    WORKSHOP = 28
    PET_FUSION = 29
    BOSS_RUSH = 30
    VICTORY_RESULTS = 31
    SECRET_EGG = 32
    BOSS_WEAPONS = 33
    TOURNAMENT = 34
    PET_ARMOUR = 35


class Button:
    def __init__(self, x, y, width, height, text, color, text_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=8)
        txt_surf = font_ui.render(self.text, True, self.text_color)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def is_clicked(self, pos, event):
        click_pos = None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            click_pos = pos
        elif event.type == pygame.FINGERDOWN:
            click_pos = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
        if click_pos is not None:
            clicked = self.rect.collidepoint(click_pos)
            if clicked:
                play_sound(SOUND_BUTTON)
            return clicked
        return False


# Volume control rectangles
VOLUME_RECTS = {
    "music_down": pygame.Rect(555, 10, 30, 28),
    "music_up": pygame.Rect(590, 10, 30, 28),
    "music_mute": pygame.Rect(625, 10, 65, 28),
    "sfx_down": pygame.Rect(555, 44, 30, 28),
    "sfx_up": pygame.Rect(590, 44, 30, 28),
    "sfx_mute": pygame.Rect(625, 44, 65, 28),
}


def change_volume(audio_type, amount):
    global MUSIC_VOLUME
    global SFX_VOLUME

    if audio_type == "music":
        MUSIC_VOLUME = max(0.0, min(1.0, MUSIC_VOLUME + amount))
    else:
        SFX_VOLUME = max(0.0, min(1.0, SFX_VOLUME + amount))
    apply_audio_volumes()


def toggle_mute(audio_type):
    global MUSIC_MUTED
    global SFX_MUTED

    if audio_type == "music":
        MUSIC_MUTED = not MUSIC_MUTED
    else:
        SFX_MUTED = not SFX_MUTED
    apply_audio_volumes()


def handle_volume_event(event):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_LEFTBRACKET:
            change_volume("music", -0.10)
        elif event.key == pygame.K_RIGHTBRACKET:
            change_volume("music", 0.10)
        elif event.key == pygame.K_MINUS:
            change_volume("sfx", -0.10)
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
            change_volume("sfx", 0.10)
        elif event.key == pygame.K_m:
            toggle_mute("music")
        elif event.key == pygame.K_s:
            toggle_mute("sfx")

    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if VOLUME_RECTS["music_down"].collidepoint(event.pos):
            change_volume("music", -0.10)
        elif VOLUME_RECTS["music_up"].collidepoint(event.pos):
            change_volume("music", 0.10)
        elif VOLUME_RECTS["music_mute"].collidepoint(event.pos):
            toggle_mute("music")
        elif VOLUME_RECTS["sfx_down"].collidepoint(event.pos):
            change_volume("sfx", -0.10)
        elif VOLUME_RECTS["sfx_up"].collidepoint(event.pos):
            change_volume("sfx", 0.10)
        elif VOLUME_RECTS["sfx_mute"].collidepoint(event.pos):
            toggle_mute("sfx")


def draw_volume_controls():
    panel = pygame.Surface((255, 72), pygame.SRCALPHA)
    panel.fill((255, 255, 255, 205))
    screen.blit(panel, (535, 5))

    music_status = "OFF" if MUSIC_MUTED else f"{round(MUSIC_VOLUME * 100)}%"
    sfx_status = "OFF" if SFX_MUTED else f"{round(SFX_VOLUME * 100)}%"
    labels = [
        font_ui.render(f"Music {music_status}", True, BLACK),
        font_ui.render(f"SFX {sfx_status}", True, BLACK),
    ]
    screen.blit(labels[0], (400, 12))
    screen.blit(labels[1], (430, 46))

    button_data = [
        ("music_down", "-"), ("music_up", "+"), ("music_mute", "MUTE"),
        ("sfx_down", "-"), ("sfx_up", "+"), ("sfx_mute", "MUTE"),
    ]
    for key, text in button_data:
        rect = VOLUME_RECTS[key]
        pygame.draw.rect(screen, BLACK, rect, border_radius=5)
        label = pygame.font.Font(None, 22).render(text, True, WHITE)
        screen.blit(label, label.get_rect(center=rect.center))


# Robust Leaderboard File Persistence
SCRIPT_DIR = (
    os.path.dirname(os.path.abspath(__file__))
    if "__file__" in locals()
    else os.getcwd()
)
# Stable, writable save location for desktop and Android.
# python-for-android exposes app_storage_path() as the app-private Android folder.
def get_save_root():
    android_private = os.environ.get("ANDROID_PRIVATE")

    if android_private:
        return os.path.join(android_private, "dinosaur_adventure")

    return os.path.join(
        os.path.expanduser("~"),
        ".dinosaur_adventure",
    )

SAVE_ROOT = get_save_root()
os.makedirs(SAVE_ROOT, exist_ok=True)
LOCAL_LEADERBOARD_FILE = os.path.join(SCRIPT_DIR, "leaderboard.json")
LOCAL_LEGACY_PROGRESS_FILE = os.path.join(SCRIPT_DIR, "player_progress.json")
LOCAL_ACCOUNT_PROGRESS_DIR = os.path.join(SCRIPT_DIR, "account_progress")
LOCAL_ACCOUNTS_FILE = os.path.join(SCRIPT_DIR, "accounts.json")
LEADERBOARD_FILE = os.path.join(SAVE_ROOT, "leaderboard.json")
LEGACY_PROGRESS_FILE = os.path.join(SAVE_ROOT, "player_progress.json")
ACCOUNT_PROGRESS_DIR = os.path.join(SAVE_ROOT, "account_progress")
PROGRESS_MIGRATION_FILE = os.path.join(ACCOUNT_PROGRESS_DIR, "legacy_progress_owner.json")
ACCOUNTS_FILE = os.path.join(SAVE_ROOT, "accounts.json")

def copy_json_if_missing(source, destination):
    if os.path.exists(destination) or not os.path.exists(source):
        return
    try:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(source, "r", encoding="utf-8") as source_file:
            data = json.load(source_file)
        with open(destination, "w", encoding="utf-8") as destination_file:
            json.dump(data, destination_file, indent=4)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

# Automatically recover existing saves located beside any earlier game version.
copy_json_if_missing(LOCAL_ACCOUNTS_FILE, ACCOUNTS_FILE)
copy_json_if_missing(LOCAL_LEADERBOARD_FILE, LEADERBOARD_FILE)
copy_json_if_missing(LOCAL_LEGACY_PROGRESS_FILE, LEGACY_PROGRESS_FILE)
os.makedirs(ACCOUNT_PROGRESS_DIR, exist_ok=True)
if os.path.isdir(LOCAL_ACCOUNT_PROGRESS_DIR):
    for old_save_name in os.listdir(LOCAL_ACCOUNT_PROGRESS_DIR):
        if old_save_name.endswith(".json"):
            copy_json_if_missing(
                os.path.join(LOCAL_ACCOUNT_PROGRESS_DIR, old_save_name),
                os.path.join(ACCOUNT_PROGRESS_DIR, old_save_name),
            )

def load_json_dict(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return {}

def save_json_dict(path, data):
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    except OSError as error:
        print(f"Error saving {path}: {error}")


def load_accounts():
    try:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return {}

def save_accounts():
    try:
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as file:
            json.dump(accounts, file, indent=4)
        with open(LOCAL_ACCOUNTS_FILE, "w", encoding="utf-8") as backup_file:
            json.dump(accounts, backup_file, indent=4)
    except OSError as error:
        print(f"Error saving accounts: {error}")



EXTRA_SKIN_NAMES = ['AQUA', 'MAGMA', 'FOREST', 'DESERT', 'OCEAN', 'CRYSTAL', 'GHOST', 'VAMPIRE', 'PIRATE', 'KNIGHT', 'SAMURAI', 'CYBER', 'NEON', 'GOLDEN', 'SILVER', 'BRONZE', 'DIAMOND', 'EMERALD', 'RUBY', 'SAPPHIRE', 'RAINBOW', 'CANDY', 'CHOCOLATE', 'SUN', 'MOON', 'STAR', 'COMET', 'METEOR', 'ALIEN', 'ASTRONAUT', 'ZOMBIE', 'SKELETON', 'MUMMY', 'PUMPKIN', 'SANTA', 'ELF', 'ANGEL', 'DEMON', 'DRAGON', 'PHOENIX', 'WATER', 'EARTH', 'WIND', 'LIGHT', 'DARK', 'PLASMA', 'LASER', 'STEAM', 'JUNGLE', 'ROYAL']
EXTRA_SKINS = []
for extra_index, extra_name in enumerate(EXTRA_SKIN_NAMES):
    skin_id = "extra_" + extra_name.lower()
    EXTRA_SKINS.append({
        "id": skin_id,
        "name": extra_name + " DINO",
        "cost": 55 + extra_index * 5,
        "owned_key": skin_id + "_owned",
    })

GUN_SKIN_NAMES = ["DEFAULT"] + [f"GUN SKIN {index:02d}" for index in range(1, 61)]
GUN_SKINS = []
for gun_index, gun_name in enumerate(GUN_SKIN_NAMES):
    gun_id = "gun_default" if gun_index == 0 else f"gun_{gun_index:02d}"
    GUN_SKINS.append({
        "id": gun_id,
        "name": gun_name,
        "cost": 0 if gun_index == 0 else 5 + gun_index * 3,
        "owned_key": gun_id + "_owned",
    })
GUN_SKINS.append({
    "id": "gun_cosmic",
    "name": "LEGENDARY COSMIC BLASTER",
    "cost": 500,
    "owned_key": "gun_cosmic_owned",
})

def default_progress():
    progress = {"cups": 0, "spider_owned": False, "iron_owned": False, "robot_owned": False, "ninja_owned": False, "fire_owned": False, "legendary_owned": False, "ice_owned": False, "thunder_owned": False, "shadow_owned": False, "toxic_owned": False, "galaxy_owned": False, "selected_skin": "default"}
    for extra_skin in EXTRA_SKINS:
        progress.setdefault(extra_skin["owned_key"], False)
    progress.setdefault("selected_gun_skin", "gun_default")
    progress.setdefault("heart_upgrade", 0)
    progress.setdefault("jump_upgrade", 0)
    progress.setdefault("shield_owned", False)
    progress.setdefault("double_cups_owned", False)
    progress.setdefault("owned_pets", [])
    progress.setdefault("selected_pet", "")
    progress.setdefault("secret_pet_unlocked", False)
    progress.setdefault("mansion_jump_boost", False)
    progress.setdefault("fusion_skin", "")
    progress.setdefault("boss_wins", [])
    progress.setdefault("boss_win_counts", {})
    progress.setdefault("selected_boss_companion", "")
    progress.setdefault("selected_boss_power", "")
    progress.setdefault("achievements", [])
    progress.setdefault("gun_damage_level", 1)
    progress.setdefault("rage_level", 1)
    progress.setdefault("selected_pet_fusion", "")
    progress.setdefault("owned_pet_fusions", [])
    progress.setdefault("boss_rush_best", 0)
    progress.setdefault("shadow_tarun_unlocked", False)
    progress.setdefault("nightmare_boss_wins", [])
    progress.setdefault("secret_egg_pets", [])
    progress.setdefault("selected_secret_pet", "")
    progress.setdefault("owned_boss_weapons", [])
    progress.setdefault("selected_boss_weapon", "")
    progress.setdefault("pet_armour", {})
    progress.setdefault("tournament_days", [])
    for gun_skin in GUN_SKINS:
        progress.setdefault(gun_skin["owned_key"], gun_skin["id"] == "gun_default")
    return progress

def safe_account_key(account_name):
    cleaned = "".join(character for character in account_name.lower() if character.isalnum() or character in ("_", "-"))
    return cleaned or "player"

def account_progress_path(account_name):
    return os.path.join(ACCOUNT_PROGRESS_DIR, safe_account_key(account_name) + ".json")

def load_progress(account_name=""):
    progress = default_progress()
    if not account_name:
        return progress
    os.makedirs(ACCOUNT_PROGRESS_DIR, exist_ok=True)
    path = account_progress_path(account_name)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                saved = json.load(file)
            if isinstance(saved, dict):
                progress.update(saved)
            return progress
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return progress

    # Preserve the original player's old shared progress once. Every other
    # account starts clean and receives its own independent save file.
    migration = load_json_dict(PROGRESS_MIGRATION_FILE)
    preferred_legacy_owner = next((item.get("name", "") for item in accounts.values() if item.get("name", "").strip().lower() == "tarun"), "")
    may_claim_legacy = not preferred_legacy_owner or account_name.strip().lower() == preferred_legacy_owner.strip().lower()
    if not migration.get("owner") and may_claim_legacy and os.path.exists(LEGACY_PROGRESS_FILE):
        try:
            with open(LEGACY_PROGRESS_FILE, "r", encoding="utf-8") as file:
                legacy = json.load(file)
            if isinstance(legacy, dict):
                progress.update(legacy)
                migration["owner"] = account_name
                save_json_dict(PROGRESS_MIGRATION_FILE, migration)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    save_progress_for_account(account_name, progress)
    return progress

def save_progress_for_account(account_name, progress_data):
    if not account_name:
        return
    try:
        os.makedirs(ACCOUNT_PROGRESS_DIR, exist_ok=True)
        with open(account_progress_path(account_name), "w", encoding="utf-8") as file:
            json.dump(progress_data, file, indent=4)
        os.makedirs(LOCAL_ACCOUNT_PROGRESS_DIR, exist_ok=True)
        with open(os.path.join(LOCAL_ACCOUNT_PROGRESS_DIR, safe_account_key(account_name) + ".json"), "w", encoding="utf-8") as backup_file:
            json.dump(progress_data, backup_file, indent=4)
    except OSError as error:
        print(f"Error saving account progress: {error}")

def save_progress():
    save_progress_for_account(active_account, player_progress)



def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list):
                    cleaned = []
                    for item in data:
                        if (
                            isinstance(item, dict)
                            and "name" in item
                            and "score" in item
                        ):
                            cleaned.append(
                                {
                                    "name": str(item["name"]),
                                    "score": int(item["score"]),
                                    "cups": int(item.get("cups", 0)),
                                }
                            )
                    return cleaned
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            print(f"Error loading leaderboard: {error}")

    empty_leaderboard = []
    save_leaderboard(empty_leaderboard)
    return empty_leaderboard


def save_leaderboard(lb):
    try:
        with open(LEADERBOARD_FILE, "w", encoding="utf-8") as file:
            json.dump(lb, file, indent=4)
            file.flush()
            os.fsync(file.fileno())
    except OSError as error:
        print(f"Error saving leaderboard: {error}")


# Global Game Variables and Leaderboard
current_state = GameState.ACCOUNT_NAME
jump_count = 0
has_paused_first_jump = False
safe_spawn_timer = 0
golden_obstacle = False
perfect_jump_message_until = 0
resume_countdown_start = 0
paused_game_frame = None
player_name = ""
leaderboard = load_leaderboard()
accounts = load_accounts()
account_name_input = ""
account_password_input = ""
active_account = ""
account_message = ""
player_progress = load_progress()
PET_RARITIES = [
 {"name":"COMMON","cost":10,"bonus":1,"pets":["DOG","CAT","RABBIT"],"colour":(70,190,100)},
 {"name":"RARE","cost":20,"bonus":5,"pets":["OCTOPUS","BUFFALO","COW"],"colour":(65,145,235)},
 {"name":"LEGENDARY","cost":30,"bonus":10,"pets":["VULTURE","EAGLE","OWL"],"colour":(195,100,255)},
 {"name":"MYTHIC","cost":50,"bonus":20,"pets":["TIGER","LION","CHEETAH"],"colour":(255,165,35)},
]
ALL_NORMAL_PETS=[p for r in PET_RARITIES for p in r["pets"]]
SECRET_EGG_PETS=["SHADOW DRAGON","ROBOT TIGER","COSMIC EAGLE","ICE LION"]
BOSS_WEAPON_DATA={"ROBOT":"ROBOT CANNON","GHOST":"REAPER BLASTER","DRAGON":"FLAME GUN","MONKEY":"JUNGLE LAUNCHER","SNOW":"ICE CANNON","ALIEN":"PLASMA RIFLE","SHADOW TARUN":"CREATOR BLASTER"}
PET_ARMOUR_LEVELS=[("NONE",0,0),("BRONZE",20,100),("SILVER",40,250),("GOLD",70,500),("COSMIC",120,1000)]
TOURNAMENT_ORDER=["ROBOT","GHOST","DRAGON","MONKEY","SNOW","ALIEN","SHADOW TARUN"]
SECRET_PET="RAINBOW TIGER"
pet_rarity_index=0
pet_message=""
pet_collection_page=0
BOSS_TYPES = [
    {"name":"ROBOT","health":4000,"reward":20,"theme":"FUTURISTIC"},
    {"name":"GHOST","health":4000,"reward":30,"theme":"CAVE"},
    {"name":"DRAGON","health":7000,"reward":40,"theme":"VOLCANO"},
    {"name":"MONKEY","health":10000,"reward":50,"theme":"JUNGLE"},
    {"name":"SNOW","health":13000,"reward":60,"theme":"SNOW"},
    {"name":"ALIEN","health":16000,"reward":70,"theme":"GALAXY"},
]
SHADOW_TARUN={"name":"SHADOW TARUN","health":40000,"reward":250,"theme":"GALAXY"}
BOSS_DIALOGUE={
    "ROBOT":("TARGET IDENTIFIED.","SYSTEM FAILURE..."),
    "GHOST":("YOUR JOURNEY ENDS HERE.","THE SHADOWS RELEASE ME..."),
    "DRAGON":("THE VOLCANO OBEYS ME.","MY FLAME... IS GONE..."),
    "MONKEY":("YOU ENTERED MY JUNGLE.","THE JUNGLE... REMEMBERS..."),
    "SNOW":("PREPARE TO FREEZE.","THE ICE... IS MELTING..."),
    "ALIEN":("EARTH CREATURE DETECTED.","RETURNING... TO THE STARS..."),
    "SHADOW TARUN":("FACE THE CREATOR'S SHADOW.","YOU DEFEATED... THE SHADOW..."),
}
BOSS_COMPANIONS={
    "ROBOT":"MINI ROBOT","GHOST":"MINI REAPER","DRAGON":"MINI DRAGON",
    "MONKEY":"MINI MONKEY","SNOW":"MINI SNOW TITAN","ALIEN":"MINI ALIEN",
    "SHADOW TARUN":"MINI SHADOW TARUN",
}
GUN_DAMAGE_LEVELS=[500,600,700,850,1000]
GUN_UPGRADE_COSTS=[0,25,40,60,90]
PET_FUSIONS=[
    ("SKY HOUND","DOG","EAGLE"),("NIGHT TIGER","TIGER","OWL"),
    ("COSMIC RABBIT","RABBIT","OCTOPUS"),("ICE BULL","COW","SNOW"),
]
BOSS_DIFFICULTIES={
    "NORMAL":{"health":1.0,"reward":1.0,"speed":1.0},
    "HARD":{"health":1.5,"reward":1.5,"speed":1.15},
    "NIGHTMARE":{"health":2.0,"reward":2.0,"speed":1.30},
}
BOSS_POWERS={
    "ROBOT":"LASER ARMOUR","GHOST":"SHADOW TELEPORT","DRAGON":"FIRE BREATH",
    "MONKEY":"GROUND SMASH","SNOW":"FREEZE TIME","ALIEN":"TRIPLE PLASMA",
}
ACHIEVEMENT_RULES=[
    ("BOSS HUNTER","Defeat all six bosses",lambda p: len(set(p.get("boss_wins",[])))>=6),
    ("PET MASTER","Unlock every normal pet",lambda p: all(pet in p.get("owned_pets",[]) for pet in ALL_NORMAL_PETS)),
    ("COLLECTOR","Own 25 dinosaur skins",lambda p: sum(1 for k,v in p.items() if k.endswith("_owned") and v)>=25),
    ("ALIEN DESTROYER","Defeat Alien 5 times",lambda p: int(p.get("boss_win_counts",{}).get("ALIEN",0))>=5),
]
boss_select_index=0
arena_boss=None
arena_health=0
arena_player_health=10
arena_shots=[]
arena_enemy_shots=[]
arena_next_attack=0
arena_message=""
arena_reward_given=False
arena_dino_y=390.0
arena_dino_velocity=0.0
arena_is_jumping=False
arena_intro_start=0
arena_attack_animation_start=0
arena_attack_kind=""
arena_death_start=0
arena_death_particles=[]
arena_combo=0
arena_finisher_ready=False
arena_power_used=False
boss_difficulty="NORMAL"
boss_loading_start=0
pet_next_attack=0
companion_next_attack=0
companion_projectiles=[]
pet_attack_projectiles=[]
pet_attack_message_until=0
boss_final_form=False
pet_attack_count=0
pet_ultimate_ready=False
arena_destruction_level=0
arena_debris=[]
boss_power_message=""
boss_power_message_until=0
team_first_index=0
team_second_index=1
team_message=""
rage_meter=0
rage_active_until=0
boss_rush_index=0
victory_stats={}
selected_skin = player_progress.get("selected_skin", "default")
selected_gun_skin = player_progress.get("selected_gun_skin", "gun_default")
shop_skin_index = 0
gun_skin_index = 0
skill_index = 0
cup_awarded_this_run = False

# Entities Physics Variables
dino_x = 150
dino_y = 400
dino_width = 40
dino_height = 50
dino_velocity_y = 0
is_jumping = False
GRAVITY = 0.6
JUMP_STRENGTH = -14
MAX_JUMP_LEVEL = 10

obstacle_x = 1400
single_spike_width = 45
obstacle_width = single_spike_width
obstacle_height = 50
obstacle_type = "spike"
# Difficulty speeds: Easy keeps the original speed.
DIFFICULTY_SPEEDS = {"EASY": 7, "MEDIUM": 10, "HARD": 14}
selected_difficulty = "EASY"
obstacle_speed = DIFFICULTY_SPEEDS[selected_difficulty]
spike_count = 1

# Extended gameplay systems
BASE_MAX_HEALTH = 3
MAX_HEARTS_LIMIT = 10
MAX_HEALTH = BASE_MAX_HEALTH
player_health = MAX_HEALTH
invincible_until = 0
shield_available = False
was_jumping = False
dust_particles = []
boss_projectiles = []
dino_projectiles = []
BOSS_MAX_HEALTH = 500
BOSS_BATTLE_TIME_MS = 60000
boss_health = BOSS_MAX_HEALTH
boss_defeated = False
boss_timer_remaining_ms = BOSS_BATTLE_TIME_MS
boss_timer_started = False
boss_entry_start = 0
boss_attack_count = 0
boss_defeat_start = 0
boss_defeat_particles = []
boss_defeat_debris = []
fireworks = []
firework_sparks = []
next_firework_launch = 0
next_boss_attack = 0
next_dino_shot = 0
muzzle_flash_until = 0
bullet_impact_particles = []
boss_hit_flash_until = 0
boss_damage_animation_start = 0
boss_damage_numbers = []
screen_shake_until = 0
parallax_offset = 0.0
weather_flash_until = 0
ENVIRONMENTS = ("DESERT", "JUNGLE", "SNOW", "VOLCANO")
current_environment = random.choice(ENVIRONMENTS)
next_environment = ""
environment_started_at = pygame.time.get_ticks()
ENVIRONMENT_DURATION_MS = 60000
ENVIRONMENT_WARNING_MS = 5000


def reset_game():
    global jump_count
    global has_paused_first_jump
    global dino_y
    global dino_velocity_y
    global is_jumping
    global obstacle_x
    global obstacle_type
    global spike_count
    global obstacle_width
    global safe_spawn_timer
    global golden_obstacle
    global perfect_jump_message_until
    global obstacle_speed
    global player_health
    global MAX_HEALTH
    global invincible_until
    global shield_available
    global was_jumping
    global dust_particles
    global boss_projectiles
    global dino_projectiles
    global boss_health
    global boss_defeated
    global boss_timer_remaining_ms
    global boss_timer_started
    global boss_entry_start
    global boss_attack_count
    global boss_defeat_start
    global boss_defeat_particles
    global boss_defeat_debris
    global fireworks
    global firework_sparks
    global next_firework_launch
    global next_boss_attack
    global next_dino_shot
    global muzzle_flash_until
    global bullet_impact_particles
    global boss_hit_flash_until
    global boss_damage_animation_start
    global boss_damage_numbers
    global screen_shake_until
    global parallax_offset
    global current_environment
    global next_environment
    global environment_started_at

    jump_count = 10 if player_progress.get("mansion_jump_boost", False) else 0
    if player_progress.get("mansion_jump_boost", False):
        player_progress["mansion_jump_boost"] = False
        save_progress()
    has_paused_first_jump = False
    dino_y = 400
    dino_velocity_y = 0
    is_jumping = False
    obstacle_x = 1400
    obstacle_type = "spike"
    spike_count = 1
    obstacle_width = single_spike_width
    obstacle_speed = DIFFICULTY_SPEEDS[selected_difficulty]
    safe_spawn_timer = 45
    golden_obstacle = False
    perfect_jump_message_until = 0
    MAX_HEALTH = min(MAX_HEARTS_LIMIT, BASE_MAX_HEALTH + int(player_progress.get("heart_upgrade", 0)))
    player_health = MAX_HEALTH
    invincible_until = 0
    shield_available = bool(player_progress.get("shield_owned", False))
    was_jumping = False
    dust_particles = []
    boss_projectiles = []
    dino_projectiles = []
    boss_health = BOSS_MAX_HEALTH
    boss_defeated = False
    boss_timer_remaining_ms = BOSS_BATTLE_TIME_MS
    boss_timer_started = False
    boss_entry_start = 0
    boss_attack_count = 0
    boss_defeat_start = 0
    boss_defeat_particles = []
    boss_defeat_debris = []
    fireworks = []
    firework_sparks = []
    next_firework_launch = 0
    next_boss_attack = 0
    next_dino_shot = 0
    muzzle_flash_until = 0
    bullet_impact_particles = []
    boss_hit_flash_until = 0
    boss_damage_animation_start = 0
    boss_damage_numbers = []
    screen_shake_until = 0
    parallax_offset = 0.0
    current_environment = random.choice(ENVIRONMENTS)
    next_environment = ""
    environment_started_at = pygame.time.get_ticks()


# Looping Day -> Night -> Sunny cycle every 250 jumps
def get_current_color(score, day_color, sunset_color, night_color):
    cycle_pos = score % 250
    if cycle_pos <= 125:
        progress = cycle_pos / 125.0
    else:
        progress = (250 - cycle_pos) / 125.0

    if progress < 0.5:
        t = progress / 0.5
        red = int(day_color[0] + (sunset_color[0] - day_color[0]) * t)
        green = int(day_color[1] + (sunset_color[1] - day_color[1]) * t)
        blue = int(day_color[2] + (sunset_color[2] - day_color[2]) * t)
    else:
        t = (progress - 0.5) / 0.5
        red = int(sunset_color[0] + (night_color[0] - sunset_color[0]) * t)
        green = int(sunset_color[1] + (night_color[1] - sunset_color[1]) * t)
        blue = int(sunset_color[2] + (night_color[2] - sunset_color[2]) * t)

    return (red, green, blue), progress


# Visual Asset Drawing Functions
def draw_lobby_background():
    # Layered sky gradient.
    for row in range(SCREEN_HEIGHT):
        ratio = row / SCREEN_HEIGHT
        colour = (
            int(105 + 120 * ratio),
            int(185 + 55 * ratio),
            int(235 + 15 * ratio),
        )
        pygame.draw.line(screen, colour, (0, row), (SCREEN_WIDTH, row))

    # Sun and soft halo.
    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for radius, alpha in ((70, 18), (55, 28), (42, 45)):
        pygame.draw.circle(glow, (255, 235, 145, alpha), (110, 95), radius)
    pygame.draw.circle(glow, (255, 225, 95, 255), (110, 95), 32)
    screen.blit(glow, (0, 0))

    # Rounded clouds.
    for cloud_x, cloud_y, scale in ((230, 80, 1.0), (585, 115, 0.8), (690, 55, 0.55)):
        cloud = pygame.Surface((150, 70), pygame.SRCALPHA)
        cloud_colour = (255, 255, 255, 210)
        pygame.draw.ellipse(cloud, cloud_colour, (10, 30, int(110 * scale), int(28 * scale)))
        pygame.draw.circle(cloud, cloud_colour, (45, 32), int(25 * scale))
        pygame.draw.circle(cloud, cloud_colour, (78, 25), int(31 * scale))
        pygame.draw.circle(cloud, cloud_colour, (105, 34), int(22 * scale))
        screen.blit(cloud, (cloud_x, cloud_y))

    # Distant mountains with snow caps.
    pygame.draw.polygon(screen, (90, 135, 145), [(0, 400), (150, 230), (310, 400)])
    pygame.draw.polygon(screen, (75, 120, 135), [(190, 400), (405, 190), (620, 400)])
    pygame.draw.polygon(screen, (82, 127, 140), [(480, 400), (670, 245), (800, 400)])
    pygame.draw.polygon(screen, (238, 245, 245), [(112, 273), (150, 230), (190, 275), (168, 267), (150, 282), (135, 267)])
    pygame.draw.polygon(screen, (238, 245, 245), [(354, 240), (405, 190), (458, 242), (430, 230), (405, 250), (382, 230)])

    # Layered hills and foreground grass.
    pygame.draw.ellipse(screen, (52, 145, 72), (-110, 340, 520, 220))
    pygame.draw.ellipse(screen, (40, 130, 65), (260, 330, 660, 245))
    pygame.draw.rect(screen, (29, 115, 52), (0, 440, SCREEN_WIDTH, 160))
    pygame.draw.rect(screen, (98, 68, 38), (0, 515, SCREEN_WIDTH, 85))

    # Small foreground plants and rocks.
    for plant_x in range(25, SCREEN_WIDTH, 70):
        pygame.draw.line(screen, (20, 90, 38), (plant_x, 520), (plant_x - 6, 500), 3)
        pygame.draw.line(screen, (20, 90, 38), (plant_x, 520), (plant_x + 8, 495), 3)
    for rock_x, rock_y, rock_w in ((55, 535, 30), (680, 548, 42), (755, 520, 24)):
        pygame.draw.ellipse(screen, (92, 88, 82), (rock_x, rock_y, rock_w, rock_w // 2))


def draw_dinosaur(x, y, jumping=False, animated=False):
    global selected_skin
    if jump_count >= 750:
        dino_colour = (145, 155, 170)
        robot_skin = True
    elif jump_count >= 300:
        dino_colour = (245, 135, 45)
        robot_skin = False
    elif jump_count >= 250:
        dino_colour = (50, 150, 235)
        robot_skin = False
    else:
        dino_colour = GREEN
        robot_skin = False

    spider_skin = selected_skin == "spider"
    iron_skin = selected_skin == "iron"
    shop_robot_skin = selected_skin == "robot"
    ninja_skin = selected_skin == "ninja"
    fire_skin = selected_skin == "fire"
    legendary_skin = selected_skin == "legendary"
    ice_skin = selected_skin == "ice"
    thunder_skin = selected_skin == "thunder"
    shadow_skin = selected_skin == "shadow"
    toxic_skin = selected_skin == "toxic"
    galaxy_skin = selected_skin == "galaxy"
    fusion_skin = player_progress.get("fusion_skin", "")
    extra_skin_index = next((i for i, item in enumerate(EXTRA_SKINS) if item["id"] == selected_skin), -1)
    if fusion_skin == "frostfire":
        dino_colour = (120, 205, 255) if (pygame.time.get_ticks() // 180) % 2 == 0 else (255, 85, 35)
        robot_skin = False
    elif fusion_skin == "galaxy_mech":
        dino_colour = (105, 55, 205)
        robot_skin = True
    elif fusion_skin == "storm_ninja":
        dino_colour = (35, 35, 70) if (pygame.time.get_ticks() // 120) % 2 == 0 else (245, 220, 60)
        robot_skin = False
    elif fusion_skin == "venom_crystal":
        dino_colour = (80, 235, 125) if (pygame.time.get_ticks() // 160) % 2 == 0 else (90, 235, 245)
        robot_skin = False
    elif spider_skin:
        dino_colour = (205, 35, 45)
        robot_skin = False
    elif iron_skin:
        dino_colour = (175, 25, 35)
        robot_skin = False
    elif shop_robot_skin:
        dino_colour = (125, 135, 150)
        robot_skin = False
    elif ninja_skin:
        dino_colour = (28, 32, 42)
        robot_skin = False
    elif fire_skin:
        dino_colour = (205, 45, 20)
        robot_skin = False
    elif legendary_skin:
        dino_colour = (65, 25, 120)
        robot_skin = False
    elif ice_skin:
        dino_colour = (110, 210, 245)
        robot_skin = False
    elif thunder_skin:
        dino_colour = (40, 55, 95)
        robot_skin = False
    elif shadow_skin:
        dino_colour = (22, 18, 35)
        robot_skin = False
    elif toxic_skin:
        dino_colour = (60, 165, 55)
        robot_skin = False
    elif galaxy_skin:
        dino_colour = (40, 20, 95)
        robot_skin = False
    elif extra_skin_index >= 0:
        hue_step = extra_skin_index
        dino_colour = (
            55 + (hue_step * 47) % 190,
            55 + (hue_step * 83) % 190,
            55 + (hue_step * 119) % 190,
        )
        robot_skin = False

    animation_time = pygame.time.get_ticks() / 1000.0
    run_phase = math.sin(animation_time * 12.0) if animated else 0.0
    bob = int(abs(run_phase) * 3) if animated and not jumping else 0
    draw_y = int(y - bob)

    # Tail swings while running and lifts while jumping.
    tail_lift = -10 if jumping else int(run_phase * 6)
    tail_points = [
        (x + 5, draw_y + 15),
        (x - 30, draw_y + 25 + tail_lift),
        (x + 5, draw_y + 35),
    ]
    pygame.draw.polygon(screen, dino_colour, tail_points)

    # Body and head.
    pygame.draw.rect(screen, dino_colour, (x, draw_y, dino_width, dino_height), border_radius=6)
    head_y = draw_y - 22 if jumping else draw_y - 20
    pygame.draw.rect(screen, dino_colour, (x + 20, head_y, 30, 25), border_radius=5)
    pygame.draw.rect(screen, BLACK, (x + 40, head_y + 5, 5, 5))

    if spider_skin:
        pygame.draw.rect(screen, (35, 80, 190), (x + 5, draw_y + 27, 30, 20), border_radius=4)
        pygame.draw.rect(screen, (35, 80, 190), (x + 20, head_y + 15, 30, 10), border_radius=3)
        pygame.draw.line(screen, WHITE, (x + 8, draw_y + 4), (x + 30, draw_y + 24), 1)
        pygame.draw.line(screen, WHITE, (x + 30, draw_y + 4), (x + 12, draw_y + 24), 1)
        pygame.draw.circle(screen, WHITE, (x + 40, head_y + 7), 3)
    elif iron_skin:
        gold = (245, 190, 35)
        pygame.draw.rect(screen, gold, (x + 7, draw_y + 7, 26, 12), border_radius=4)
        pygame.draw.rect(screen, gold, (x + 21, head_y + 3, 27, 9), border_radius=3)
        pygame.draw.rect(screen, gold, (x + 6, draw_y + 35, 29, 11), border_radius=3)
        pygame.draw.circle(screen, (90, 235, 255), (x + 20, draw_y + 24), 5)
        pygame.draw.circle(screen, WHITE, (x + 40, head_y + 7), 3)
    elif shop_robot_skin:
        dark_metal = (65, 75, 88)
        cyan = (70, 235, 255)
        pygame.draw.rect(screen, dark_metal, (x + 5, draw_y + 7, 30, 14), border_radius=2)
        pygame.draw.rect(screen, dark_metal, (x + 22, head_y + 3, 26, 17), border_radius=2)
        pygame.draw.line(screen, (40, 45, 55), (x + 20, draw_y), (x + 20, draw_y + 50), 2)
        pygame.draw.line(screen, (190, 200, 210), (x + 5, draw_y + 30), (x + 35, draw_y + 30), 2)
        pygame.draw.circle(screen, cyan, (x + 20, draw_y + 25), 5)
        pygame.draw.rect(screen, cyan, (x + 39, head_y + 6, 7, 4), border_radius=1)
        pygame.draw.line(screen, dark_metal, (x + 34, head_y + 2), (x + 34, head_y - 8), 2)
        pygame.draw.circle(screen, cyan, (x + 34, head_y - 9), 3)
    elif ninja_skin:
        ninja_red = (195, 35, 45)
        steel = (185, 195, 210)
        # Mask, headband, belt and crossed back blades.
        pygame.draw.rect(screen, (12, 15, 22), (x + 20, head_y + 2, 30, 16), border_radius=3)
        pygame.draw.rect(screen, ninja_red, (x + 19, head_y + 12, 32, 5))
        pygame.draw.line(screen, ninja_red, (x + 47, head_y + 14), (x + 62, head_y + 8), 4)
        pygame.draw.rect(screen, ninja_red, (x + 3, draw_y + 28, 34, 6), border_radius=2)
        pygame.draw.line(screen, steel, (x - 3, draw_y + 5), (x + 34, draw_y + 43), 4)
        pygame.draw.line(screen, steel, (x + 34, draw_y + 5), (x - 3, draw_y + 43), 4)
        pygame.draw.circle(screen, WHITE, (x + 40, head_y + 7), 3)
    elif fire_skin:
        flame_orange = (255, 120, 20)
        flame_yellow = (255, 225, 65)
        # Lava armour cracks and animated-looking flame spikes.
        pygame.draw.line(screen, flame_yellow, (x + 8, draw_y + 8), (x + 18, draw_y + 20), 3)
        pygame.draw.line(screen, flame_orange, (x + 30, draw_y + 5), (x + 20, draw_y + 25), 3)
        pygame.draw.line(screen, flame_yellow, (x + 7, draw_y + 34), (x + 30, draw_y + 28), 3)
        flame_points = [
            (x + 4, draw_y), (x + 9, draw_y - 17), (x + 14, draw_y - 4),
            (x + 20, draw_y - 23), (x + 25, draw_y - 3),
            (x + 31, draw_y - 15), (x + 36, draw_y),
        ]
        pygame.draw.polygon(screen, flame_orange, flame_points)
        pygame.draw.polygon(screen, flame_yellow, [(x + 13, draw_y), (x + 20, draw_y - 14), (x + 27, draw_y)])
        pygame.draw.circle(screen, flame_yellow, (x + 41, head_y + 7), 3)
    elif legendary_skin:
        legendary_gold = (255, 205, 45)
        cosmic_blue = (75, 220, 255)
        cosmic_pink = (235, 85, 255)
        # Gold armour with cosmic energy panels.
        pygame.draw.rect(screen, legendary_gold, (x + 4, draw_y + 5, 32, 9), border_radius=3)
        pygame.draw.rect(screen, legendary_gold, (x + 21, head_y + 2, 28, 7), border_radius=3)
        pygame.draw.rect(screen, cosmic_pink, (x + 7, draw_y + 20, 27, 19), border_radius=5)
        pygame.draw.circle(screen, cosmic_blue, (x + 20, draw_y + 28), 6)
        pygame.draw.circle(screen, WHITE, (x + 20, draw_y + 28), 2)
        # Dragon wings.
        left_wing = [(x + 4, draw_y + 18), (x - 28, draw_y - 12), (x - 18, draw_y + 18)]
        right_wing = [(x + 30, draw_y + 18), (x + 55, draw_y - 14), (x + 45, draw_y + 22)]
        pygame.draw.polygon(screen, (120, 55, 200), left_wing)
        pygame.draw.polygon(screen, (120, 55, 200), right_wing)
        pygame.draw.lines(screen, legendary_gold, True, left_wing, 2)
        pygame.draw.lines(screen, legendary_gold, True, right_wing, 2)
        # Legendary crown.
        crown = [(x + 24, head_y + 1), (x + 27, head_y - 11), (x + 33, head_y - 4),
                 (x + 38, head_y - 14), (x + 43, head_y - 4), (x + 48, head_y - 11),
                 (x + 49, head_y + 1)]
        pygame.draw.polygon(screen, legendary_gold, crown)
        pygame.draw.circle(screen, cosmic_blue, (x + 40, head_y + 7), 4)
        pygame.draw.circle(screen, WHITE, (x + 40, head_y + 7), 2)
        # Small orbiting energy spark.
        spark_phase = pygame.time.get_ticks() / 260.0
        spark_x = int(x + 20 + math.cos(spark_phase) * 31)
        spark_y = int(draw_y + 22 + math.sin(spark_phase) * 18)
        pygame.draw.circle(screen, cosmic_blue, (spark_x, spark_y), 4)
        pygame.draw.circle(screen, WHITE, (spark_x, spark_y), 2)

    elif ice_skin:
        ice_blue = (205, 250, 255)
        pygame.draw.polygon(screen, ice_blue, [(x + 3, draw_y), (x + 10, draw_y - 18), (x + 16, draw_y)])
        pygame.draw.polygon(screen, ice_blue, [(x + 16, draw_y), (x + 24, draw_y - 24), (x + 31, draw_y)])
        pygame.draw.line(screen, WHITE, (x + 8, draw_y + 10), (x + 30, draw_y + 35), 3)
        pygame.draw.circle(screen, WHITE, (x + 41, head_y + 7), 3)
    elif thunder_skin:
        electric = (255, 235, 55)
        pygame.draw.lines(screen, electric, False, [(x + 8, draw_y + 2), (x + 25, draw_y + 18), (x + 15, draw_y + 25), (x + 34, draw_y + 43)], 4)
        pygame.draw.polygon(screen, electric, [(x + 18, head_y), (x + 32, head_y - 18), (x + 29, head_y - 4), (x + 43, head_y - 12), (x + 34, head_y + 2)])
        pygame.draw.circle(screen, electric, (x + 41, head_y + 7), 4)
    elif shadow_skin:
        violet = (150, 65, 240)
        pygame.draw.ellipse(screen, (15, 10, 25), (x - 10, draw_y + 40, 65, 18))
        pygame.draw.line(screen, violet, (x + 4, draw_y + 8), (x + 34, draw_y + 35), 3)
        pygame.draw.circle(screen, violet, (x + 41, head_y + 7), 4)
        pygame.draw.circle(screen, (230, 210, 255), (x + 41, head_y + 7), 2)
    elif toxic_skin:
        acid = (165, 255, 55)
        for ox, oy, radius in ((8, 10, 4), (27, 18, 5), (16, 36, 4), (43, -8, 3)):
            pygame.draw.circle(screen, acid, (x + ox, draw_y + oy), radius)
        pygame.draw.line(screen, (225, 255, 120), (x + 6, draw_y + 5), (x + 33, draw_y + 42), 3)
        pygame.draw.circle(screen, acid, (x + 41, head_y + 7), 4)
    elif galaxy_skin:
        star_colours = ((255,255,255),(100,220,255),(245,100,255),(255,220,90))
        for index, (ox, oy) in enumerate(((7,8),(18,20),(31,10),(12,37),(29,34),(42,-8))):
            pygame.draw.circle(screen, star_colours[index % len(star_colours)], (x + ox, draw_y + oy), 2)
        pygame.draw.arc(screen, (110, 225, 255), (x - 5, draw_y + 3, 48, 38), 0, math.pi, 2)
        pygame.draw.circle(screen, (255, 120, 255), (x + 41, head_y + 7), 4)
    elif extra_skin_index >= 0:
        accent = (
            80 + (extra_skin_index * 97) % 176,
            80 + (extra_skin_index * 53) % 176,
            80 + (extra_skin_index * 29) % 176,
        )
        pattern = extra_skin_index % 5
        if pattern == 0:
            pygame.draw.line(screen, accent, (x + 4, draw_y + 6), (x + 34, draw_y + 42), 4)
            pygame.draw.line(screen, accent, (x + 34, draw_y + 6), (x + 4, draw_y + 42), 4)
        elif pattern == 1:
            for px, py in ((8, 10), (25, 18), (14, 35), (32, 39)):
                pygame.draw.circle(screen, accent, (x + px, draw_y + py), 4)
        elif pattern == 2:
            pygame.draw.rect(screen, accent, (x + 5, draw_y + 12, 30, 8), border_radius=3)
            pygame.draw.rect(screen, accent, (x + 5, draw_y + 31, 30, 8), border_radius=3)
        elif pattern == 3:
            pygame.draw.polygon(screen, accent, [(x + 4, draw_y), (x + 11, draw_y - 15), (x + 18, draw_y)])
            pygame.draw.polygon(screen, accent, [(x + 18, draw_y), (x + 26, draw_y - 20), (x + 34, draw_y)])
        else:
            pygame.draw.arc(screen, accent, (x - 3, draw_y + 4, 46, 38), 0, math.pi, 3)
            pygame.draw.circle(screen, accent, (x + 20, draw_y + 25), 5)
        pygame.draw.circle(screen, accent, (x + 41, head_y + 7), 4)
        pygame.draw.circle(screen, WHITE, (x + 41, head_y + 7), 2)

    # Small arm moves opposite to the legs.
    arm_offset = -4 if jumping else int(run_phase * 5)
    pygame.draw.line(
        screen,
        BLACK,
        (x + 25, draw_y + 18),
        (x + 36, draw_y + 25 + arm_offset),
        4,
    )

    # Fictional arcade gun carried by the dinosaur.
    gun_y = draw_y + 23
    gun_match = next((i for i, item in enumerate(GUN_SKINS) if item["id"] == selected_gun_skin), 0)
    cosmic_gun = selected_gun_skin == "gun_cosmic"
    if cosmic_gun:
        cosmic_time = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(cosmic_time / 130.0)
        aura = pygame.Surface((90, 46), pygame.SRCALPHA)
        for radius, alpha in ((18, 18), (12, 32), (7, 60)):
            pygame.draw.circle(aura, (135, 65, 255, alpha), (66, 17), radius)
        screen.blit(aura, (x + 12, gun_y - 14))
        # Deep-space body with a bright nebula core.
        pygame.draw.rect(screen, (21, 12, 48), (x + 29, gun_y - 2, 34, 12), border_radius=5)
        pygame.draw.rect(screen, (75, 25, 145), (x + 33, gun_y, 27, 8), border_radius=4)
        pygame.draw.rect(screen, (14, 8, 30), (x + 58, gun_y, 17, 7), border_radius=3)
        pygame.draw.polygon(screen, (42, 18, 82), [(x + 37, gun_y + 8), (x + 47, gun_y + 8), (x + 44, gun_y + 20), (x + 37, gun_y + 17)])
        pygame.draw.line(screen, (80, 220, 255), (x + 35, gun_y), (x + 58, gun_y), 2)
        pygame.draw.line(screen, (255, 80, 225), (x + 38, gun_y + 8), (x + 58, gun_y + 8), 1)
        core_colour = (180 + int(75 * pulse), 90 + int(80 * pulse), 255)
        pygame.draw.circle(screen, core_colour, (x + 49, gun_y + 4), 4)
        pygame.draw.circle(screen, WHITE, (x + 49, gun_y + 4), 1)
        pygame.draw.circle(screen, (70, 230, 255), (x + 74, gun_y + 3), 3)
        # Orbiting star particles make the skin feel alive.
        for star in range(5):
            angle = cosmic_time / 260.0 + star * math.tau / 5
            sx = x + 50 + int(math.cos(angle) * (17 + star % 2 * 5))
            sy = gun_y + 4 + int(math.sin(angle) * (8 + star % 2 * 3))
            colour = (255, 255, 255) if star % 2 == 0 else (110, 210, 255)
            pygame.draw.circle(screen, colour, (sx, sy), 1 + (star == 0))
    else:
        if gun_match == 0:
            gun_main, gun_dark, gun_grip, gun_glow = (65, 70, 78), (42, 45, 52), (75, 80, 88), (80, 220, 255)
        else:
            gun_main = (55 + gun_match * 47 % 190, 55 + gun_match * 83 % 190, 55 + gun_match * 113 % 190)
            gun_dark = tuple(max(20, value - 45) for value in gun_main)
            gun_grip = tuple(min(255, value + 25) for value in gun_main)
            gun_glow = (80 + gun_match * 31 % 176, 80 + gun_match * 67 % 176, 80 + gun_match * 97 % 176)
        pygame.draw.rect(screen, gun_main, (x + 31, gun_y, 28, 8), border_radius=3)
        pygame.draw.rect(screen, gun_dark, (x + 55, gun_y + 1, 15, 5), border_radius=2)
        pygame.draw.rect(screen, gun_grip, (x + 37, gun_y + 7, 7, 10), border_radius=2)
        pygame.draw.circle(screen, gun_glow, (x + 68, gun_y + 3), 2)

    if robot_skin:
        pygame.draw.rect(screen, (60, 220, 255), (x + 8, draw_y + 12, 8, 8))
        pygame.draw.line(screen, (70, 75, 85), (x + 20, draw_y), (x + 20, draw_y + 50), 2)

    if jumping:
        # Tucked airborne pose.
        pygame.draw.line(screen, BLACK, (x + 10, draw_y + 45), (x + 2, draw_y + 55), 7)
        pygame.draw.line(screen, BLACK, (x + 30, draw_y + 45), (x + 40, draw_y + 53), 7)
    else:
        # Alternating running stride.
        stride = int(run_phase * 10) if animated else 0
        pygame.draw.line(
            screen, BLACK,
            (x + 10, draw_y + 45),
            (x + 10 + stride, draw_y + 60),
            8,
        )
        pygame.draw.line(
            screen, BLACK,
            (x + 30, draw_y + 45),
            (x + 30 - stride, draw_y + 60),
            8,
        )


def blend_colour(a, b, amount):
    amount = max(0.0, min(1.0, amount))
    return tuple(int(x + (y - x) * amount) for x, y in zip(a, b))

def update_environment():
    global current_environment, next_environment, environment_started_at
    now = pygame.time.get_ticks()
    remaining = ENVIRONMENT_DURATION_MS - (now - environment_started_at)
    if remaining <= ENVIRONMENT_WARNING_MS and not next_environment:
        next_environment = random.choice([e for e in ENVIRONMENTS if e != current_environment])
    if remaining <= 0:
        current_environment = next_environment
        next_environment = ""
        environment_started_at = now

def environment_palette(night_strength):
    palettes = {
        "DESERT": ((105,190,235),(238,190,96),(194,126,52)),
        "JUNGLE": ((80,175,200),(42,132,68),(29,91,48)),
        "SNOW": ((155,205,235),(218,235,240),(155,185,198)),
        "VOLCANO": ((115,62,69),(88,58,52),(48,37,39)),
    }
    sky, ground, accent = palettes[current_environment]
    return blend_colour(sky, COLOR_NIGHT_SKY, night_strength * 0.72), blend_colour(ground, COLOR_NIGHT_GROUND, night_strength * 0.55), accent

def draw_parallax_background(ground_colour, night_strength=0.0):
    global parallax_offset
    parallax_offset = (parallax_offset + obstacle_speed * 0.18) % SCREEN_WIDTH
    now = pygame.time.get_ticks()
    sky, ground, accent = environment_palette(night_strength)
    for row in range(0, 461, 3):
        pygame.draw.rect(screen, blend_colour(sky, ground, row / 1100.0), (0,row,SCREEN_WIDTH,3))
    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    glow_colour = (255,115,45) if current_environment == "VOLCANO" else (255,238,165)
    for radius, alpha in ((64,18),(48,30),(34,55)):
        pygame.draw.circle(glow, (*glow_colour,alpha), (650,100), radius)
    pygame.draw.circle(glow, (*glow_colour,235), (650,100), 25)
    screen.blit(glow,(0,0))
    far = int(parallax_offset * .16)
    near = int(parallax_offset * .38)
    if current_environment == "DESERT":
        for base in (-400,0,400,800,1200):
            x=base-far%400
            pygame.draw.ellipse(screen,(211,154,74),(x,315,520,190))
            pygame.draw.ellipse(screen,(228,174,91),(x+120,350,430,145))
        for x in range(-100,SCREEN_WIDTH+160,210):
            px=x-near%210
            pygame.draw.rect(screen,(37,125,66),(px,365,14,75),border_radius=5)
            pygame.draw.rect(screen,(37,125,66),(px-14,387,20,10),border_radius=4)
    elif current_environment == "JUNGLE":
        pygame.draw.polygon(screen,(33,105,75),[(0,455),(150,245),(320,455)])
        pygame.draw.polygon(screen,(28,88,65),[(250,455),(500,205),(760,455)])
        for x in range(-80,SCREEN_WIDTH+120,105):
            px=x-near%105; height=105+(x%55)
            pygame.draw.rect(screen,(58,68,38),(px,455-height,16,height))
            for ox,oy,r in ((-20,-5,28),(8,-18,34),(30,0,26)):
                pygame.draw.circle(screen,(26,126+(x%25),54),(px+ox,455-height+oy),r)
        for x in (130,360,720,880):
            pygame.draw.arc(screen,(35,115,48),(x+int(math.sin(now/700+x)*8),40,45,220),.5,2.6,4)
    elif current_environment == "SNOW":
        for base in (-360,0,360,720):
            x=base-far%360
            pygame.draw.polygon(screen,(105,145,165),[(x,455),(x+180,210),(x+360,455)])
            pygame.draw.polygon(screen,(235,247,250),[(x+112,302),(x+180,210),(x+248,302),(x+210,286),(x+180,318),(x+150,286)])
        for x in range(-50,SCREEN_WIDTH+120,120):
            px=x-near%120
            pygame.draw.rect(screen,(86,68,55),(px,380,10,70))
            pygame.draw.polygon(screen,(48,106,89),[(px-32,405),(px+5,340),(px+42,405)])
            pygame.draw.polygon(screen,(230,245,248),[(px-20,385),(px+5,340),(px+28,385)])
    else:
        pygame.draw.polygon(screen,(54,42,44),[(0,455),(260,190),(520,455)])
        pygame.draw.polygon(screen,(68,45,43),[(390,455),(680,150),(960,455)])
        pygame.draw.polygon(screen,(255,80,25),[(610,245),(680,150),(748,250),(700,220),(675,270),(648,220)])
        lava=int(now/18)%90
        for x in range(-90,SCREEN_WIDTH+90,90):
            pygame.draw.ellipse(screen,(255,85,20),(x-lava,430,72,13))
            pygame.draw.ellipse(screen,(255,205,48),(x-lava+12,433,36,6))
    pygame.draw.rect(screen,ground,(0,440,SCREEN_WIDTH,SCREEN_HEIGHT-440))
    pygame.draw.line(screen,accent,(0,440),(SCREEN_WIDTH,440),5)

def draw_weather_effects():
    global weather_flash_until
    now=pygame.time.get_ticks()
    layer=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
    if current_environment == "DESERT":
        for i in range(52):
            x=(i*89-now//5)%(SCREEN_WIDTH+80)-40; y=95+(i*47)%350
            pygame.draw.line(layer,(240,205,135,105),(x,y),(x+18+i%25,y-3),2)
    elif current_environment == "JUNGLE":
        for i in range(70):
            x=(i*97+now//7)%SCREEN_WIDTH; y=(i*53+now//4)%450
            pygame.draw.line(layer,(170,220,245,170),(x,y),(x-7,y+17),2)
        if now%5200<75: weather_flash_until=now+100
        if now<weather_flash_until: layer.fill((235,245,255,90))
    elif current_environment == "SNOW":
        for i in range(85):
            x=int((i*73+now/(11+i%4)+math.sin(now/600+i)*18)%SCREEN_WIDTH)
            y=int((i*41+now/(15+i%5))%455)
            pygame.draw.circle(layer,(250,253,255,210),(x,y),1+i%3)
    else:
        for i in range(45):
            x=int((i*83+math.sin(now/310+i)*25)%SCREEN_WIDTH)
            y=int(435-((i*49+now/(8+i%5))%390))
            pygame.draw.circle(layer,(255,95+i%100,25,190),(x,y),1+i%3)
        layer.fill((255,45,15,18+int(10*(1+math.sin(now/280)))))
    screen.blit(layer,(0,0))

def draw_environment_banner():
    remaining=max(0,ENVIRONMENT_DURATION_MS-(pygame.time.get_ticks()-environment_started_at))
    badge=pygame.Surface((170,34),pygame.SRCALPHA); badge.fill((12,18,28,180))
    pygame.draw.rect(badge,(255,225,115,210),badge.get_rect(),2,border_radius=8)
    label=pygame.font.Font(None,23).render(current_environment.title(),True,WHITE)
    badge.blit(label,label.get_rect(center=badge.get_rect().center)); screen.blit(badge,(SCREEN_WIDTH-188,18))
    if remaining<=ENVIRONMENT_WARNING_MS and next_environment:
        seconds=max(1,math.ceil(remaining/1000))
        panel=pygame.Surface((490,72),pygame.SRCALPHA); panel.fill((12,18,28,215))
        pygame.draw.rect(panel,(255,205,70),panel.get_rect(),3,border_radius=14)
        title=font_ui.render(f"Entering {next_environment.title()} in {seconds}",True,(255,235,125))
        panel.blit(title,title.get_rect(center=(245,26)))
        sub=pygame.font.Font(None,22).render("Get ready for a new world and weather!",True,WHITE)
        panel.blit(sub,sub.get_rect(center=(245,52)))
        screen.blit(panel,panel.get_rect(center=(SCREEN_WIDTH//2,132)))

def draw_obstacle(x, y, kind, count):
    if kind == "spike":
        draw_spikes(x, y, count)
    elif kind == "kite":
        draw_kite(x, y)
    elif kind == "rock":
        pygame.draw.ellipse(screen, (95, 90, 85), (x, y + 12, 58, 38))
        pygame.draw.circle(screen, (125, 120, 112), (x + 20, y + 22), 7)
    elif kind == "cactus":
        pygame.draw.rect(screen, (40, 145, 65), (x + 18, y, 18, 50), border_radius=7)
        pygame.draw.rect(screen, (40, 145, 65), (x + 5, y + 15, 20, 10), border_radius=5)
        pygame.draw.rect(screen, (40, 145, 65), (x + 30, y + 25, 20, 10), border_radius=5)
    elif kind == "fire":
        pygame.draw.ellipse(screen, (90, 55, 35), (x, y + 35, 58, 15))
        pygame.draw.polygon(screen, (255, 90, 30), [(x+8,y+40),(x+28,y),(x+48,y+40)])
        pygame.draw.polygon(screen, (255, 220, 60), [(x+18,y+40),(x+30,y+15),(x+40,y+40)])
    else:
        pygame.draw.rect(screen, (105, 70, 38), (x, y + 28, 70, 22), border_radius=8)
        pygame.draw.circle(screen, (125, 85, 45), (x + 12, y + 39), 7)


def update_dust():
    for particle in dust_particles[:]:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["vy"] -= 0.02
        particle["life"] -= 1
        pygame.draw.circle(screen, (170, 135, 85), (int(particle["x"]), int(particle["y"])), max(1, particle["life"] // 8))
        if particle["life"] <= 0:
            dust_particles.remove(particle)


def draw_progress_bar():
    x, y, width, height = 245, 20, 310, 18
    pygame.draw.rect(screen, (35, 35, 45), (x, y, width, height), border_radius=8)
    fill = int(width * min(1.0, jump_count / 1000.0))
    pygame.draw.rect(screen, (50, 210, 110), (x, y, fill, height), border_radius=8)
    for mark, label in ((200, "K"), (300, "B"), (1000, "V")):
        mx = x + int(width * mark / 1000)
        pygame.draw.line(screen, WHITE, (mx, y - 3), (mx, y + height + 3), 2)
        tag = pygame.font.Font(None, 16).render(label, True, WHITE)
        screen.blit(tag, (mx - 4, y + 20))


def draw_hearts():
    for i in range(MAX_HEALTH):
        colour = RED if i < player_health else (90, 90, 90)
        hx, hy = 30 + i * 32, 88
        pygame.draw.circle(screen, colour, (hx, hy), 8)
        pygame.draw.circle(screen, colour, (hx + 12, hy), 8)
        pygame.draw.polygon(screen, colour, [(hx - 8, hy + 2), (hx + 20, hy + 2), (hx + 6, hy + 20)])


def update_and_draw_boss_timer():
    global boss_timer_remaining_ms
    global boss_timer_started
    global boss_entry_start
    global current_state

    if jump_count < 300 or boss_defeated:
        return

    if not boss_timer_started:
        boss_timer_started = True
        boss_entry_start = pygame.time.get_ticks()
        boss_timer_remaining_ms = BOSS_BATTLE_TIME_MS

    # clock.get_time() advances only while the PLAYING state is processed.
    # Therefore pausing the game also pauses the boss timer.
    boss_timer_remaining_ms = max(
        0,
        boss_timer_remaining_ms - clock.get_time(),
    )
    seconds_remaining = math.ceil(boss_timer_remaining_ms / 1000.0)

    timer_colour = (255, 220, 80) if seconds_remaining > 10 else RED
    timer_panel = pygame.Surface((190, 46), pygame.SRCALPHA)
    timer_panel.fill((15, 20, 35, 205))
    pygame.draw.rect(
        timer_panel,
        timer_colour,
        timer_panel.get_rect(),
        width=2,
        border_radius=8,
    )
    screen.blit(timer_panel, (300, 52))

    timer_text = font_ui.render(
        f"BOSS TIME: {seconds_remaining:02d}",
        True,
        timer_colour,
    )
    screen.blit(timer_text, timer_text.get_rect(center=(395, 75)))

    if seconds_remaining <= 10 and (pygame.time.get_ticks() // 250) % 2 == 0:
        warning = pygame.font.Font(None, 22).render("HURRY!", True, WHITE)
        screen.blit(warning, warning.get_rect(center=(395, 110)))

    if boss_timer_remaining_ms <= 0:
        play_sound(SOUND_COLLISION)
        current_state = GameState.ENTER_NAME


def get_ground_robot_position():
    if boss_entry_start == 0:
        entry_progress = 0.0
    else:
        entry_progress = min(
            1.0,
            (pygame.time.get_ticks() - boss_entry_start) / 1500.0,
        )
    # Smooth-step easing makes the robot visibly walk in from the right.
    eased_progress = entry_progress * entry_progress * (3.0 - 2.0 * entry_progress)
    robot_x = int((SCREEN_WIDTH + 100) + (650 - (SCREEN_WIDTH + 100)) * eased_progress)
    robot_y = 374
    return robot_x, robot_y, entry_progress


def update_boss():
    global next_boss_attack
    global boss_attack_count
    global boss_health
    global boss_defeated

    if jump_count < 300 or boss_defeated:
        boss_projectiles.clear()
        return False

    now = pygame.time.get_ticks()
    boss_x, boss_y, entry_progress = get_ground_robot_position()

    # Damage reaction: ground robot recoils, shakes, compresses, and flashes.
    damage_elapsed = now - boss_damage_animation_start
    damage_active = 0 <= damage_elapsed < 320
    recoil_x = 0
    shake_y = 0
    body_colour = (75, 85, 100)
    armour_colour = (125, 140, 155)
    if damage_active:
        reaction_progress = damage_elapsed / 320.0
        recoil_x = int(25 * math.sin(reaction_progress * math.pi))
        shake_y = int(math.sin(damage_elapsed * 0.24) * 6 * (1.0 - reaction_progress))
        flash_strength = 1.0 - reaction_progress
        body_colour = (
            int(75 + 180 * flash_strength),
            int(85 + 145 * flash_strength),
            int(100 + 120 * flash_strength),
        )
        armour_colour = (255, int(150 + 90 * flash_strength), int(120 + 130 * flash_strength))

    draw_x = boss_x + recoil_x
    draw_y = boss_y + shake_y
    walk_phase = math.sin(now / 120.0) if entry_progress < 1.0 else math.sin(now / 350.0) * 0.25

    # Ground shadow.
    pygame.draw.ellipse(screen, (20, 25, 25), (draw_x - 58, 444, 116, 16))

    # Mechanical legs and feet, standing on the ground line.
    left_foot_x = draw_x - 32 + int(walk_phase * 8)
    right_foot_x = draw_x + 13 - int(walk_phase * 8)
    pygame.draw.rect(screen, (55, 62, 72), (draw_x - 30, draw_y + 35, 18, 45), border_radius=5)
    pygame.draw.rect(screen, (55, 62, 72), (draw_x + 13, draw_y + 35, 18, 45), border_radius=5)
    pygame.draw.rect(screen, (35, 40, 48), (left_foot_x, draw_y + 72, 34, 14), border_radius=5)
    pygame.draw.rect(screen, (35, 40, 48), (right_foot_x, draw_y + 72, 34, 14), border_radius=5)
    pygame.draw.circle(screen, (80, 220, 255), (draw_x - 21, draw_y + 55), 5)
    pygame.draw.circle(screen, (80, 220, 255), (draw_x + 22, draw_y + 55), 5)

    # Torso armour and glowing power core.
    pygame.draw.rect(screen, body_colour, (draw_x - 48, draw_y - 38, 96, 82), border_radius=12)
    pygame.draw.rect(screen, armour_colour, (draw_x - 37, draw_y - 28, 74, 56), border_radius=8)
    pygame.draw.circle(screen, (35, 70, 95), (draw_x, draw_y), 16)
    pygame.draw.circle(screen, (80, 235, 255), (draw_x, draw_y), 10)
    pygame.draw.circle(screen, WHITE, (draw_x - 3, draw_y - 3), 3)

    # Robot head, antenna, eyes, and jaw.
    pygame.draw.rect(screen, (65, 72, 84), (draw_x - 35, draw_y - 82, 70, 47), border_radius=8)
    pygame.draw.rect(screen, (150, 165, 175), (draw_x - 27, draw_y - 73, 54, 27), border_radius=5)
    pygame.draw.circle(screen, RED, (draw_x - 14, draw_y - 60), 6)
    pygame.draw.circle(screen, RED, (draw_x + 14, draw_y - 60), 6)
    pygame.draw.line(screen, (55, 60, 68), (draw_x - 16, draw_y - 43), (draw_x + 16, draw_y - 43), 4)
    pygame.draw.line(screen, (95, 100, 110), (draw_x, draw_y - 82), (draw_x, draw_y - 99), 3)
    pygame.draw.circle(screen, GOLD, (draw_x, draw_y - 102), 5)

    # Left arm and right cannon arm.
    pygame.draw.rect(screen, (60, 68, 78), (draw_x - 70, draw_y - 25, 24, 58), border_radius=8)
    pygame.draw.circle(screen, (85, 95, 105), (draw_x - 58, draw_y + 34), 12)
    pygame.draw.rect(screen, (60, 68, 78), (draw_x + 46, draw_y - 25, 28, 52), border_radius=8)
    pygame.draw.rect(screen, (35, 42, 52), (draw_x + 64, draw_y - 18, 42, 22), border_radius=7)
    pygame.draw.circle(screen, (90, 230, 255), (draw_x + 104, draw_y - 7), 6)

    # Boss health bar.
    bar_x, bar_y, bar_width = 500, 70, 250
    pygame.draw.rect(screen, (35, 35, 45), (bar_x, bar_y, bar_width, 18), border_radius=8)
    health_width = int(bar_width * max(0, boss_health) / BOSS_MAX_HEALTH)
    pygame.draw.rect(screen, RED, (bar_x, bar_y, health_width, 18), border_radius=8)
    boss_label = pygame.font.Font(None, 22).render(f"ROBOT BOSS {boss_health} / 500", True, WHITE)
    screen.blit(boss_label, (bar_x + 35, bar_y - 24))

    # Robot hits back using alternating aimed cannon shots and ground shockwaves.
    if entry_progress >= 1.0 and now >= next_boss_attack:
        boss_attack_count += 1
        if boss_attack_count % 2 == 1:
            cannon_x = draw_x + 104.0
            cannon_y = draw_y - 7.0
            target_x = dino_x + dino_width / 2
            target_y = dino_y + dino_height / 2
            direction_x = target_x - cannon_x
            direction_y = target_y - cannon_y
            distance = max(1.0, math.hypot(direction_x, direction_y))
            projectile_speed = 8.5 + obstacle_speed * 0.18
            boss_projectiles.append({
                "type": "energy",
                "x": cannon_x, "y": cannon_y,
                "vx": direction_x / distance * projectile_speed,
                "vy": direction_y / distance * projectile_speed,
            })
        else:
            boss_projectiles.append({
                "type": "shockwave",
                "x": float(draw_x - 65),
                "y": 437.0,
                "vx": -9.0,
                "vy": 0.0,
            })
        next_boss_attack = now + 900

    hit = False
    dino_hitbox = pygame.Rect(dino_x, dino_y, dino_width, dino_height)
    for shot in boss_projectiles[:]:
        shot["x"] += shot["vx"]
        shot["y"] += shot["vy"]
        shot_x = int(shot["x"])
        shot_y = int(shot["y"])
        if shot.get("type") == "shockwave":
            wave_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.arc(wave_layer, (255, 150, 55, 210), (shot_x - 28, shot_y - 35, 56, 45), math.pi, math.tau, 6)
            pygame.draw.arc(wave_layer, (255, 230, 100, 150), (shot_x - 18, shot_y - 25, 36, 30), math.pi, math.tau, 4)
            screen.blit(wave_layer, (0, 0))
            attack_rect = pygame.Rect(shot_x - 25, shot_y - 30, 50, 35)
        else:
            pygame.draw.circle(screen, (70, 150, 255), (shot_x, shot_y), 12)
            pygame.draw.circle(screen, (110, 245, 255), (shot_x, shot_y), 7)
            pygame.draw.circle(screen, WHITE, (shot_x, shot_y), 3)
            attack_rect = pygame.Rect(shot_x - 8, shot_y - 8, 16, 16)

        if attack_rect.colliderect(dino_hitbox):
            hit = True
            boss_projectiles.remove(shot)
        elif shot_x < -30 or shot_x > SCREEN_WIDTH + 30 or shot_y < -30 or shot_y > SCREEN_HEIGHT + 30:
            boss_projectiles.remove(shot)
    return hit


def reset_fireworks():
    global fireworks
    global firework_sparks
    global next_firework_launch
    fireworks = []
    firework_sparks = []
    next_firework_launch = pygame.time.get_ticks()


def update_victory_fireworks():
    global next_firework_launch

    now = pygame.time.get_ticks()
    if next_firework_launch == 0:
        next_firework_launch = now

    # Launch rockets continuously from varied positions.
    if now >= next_firework_launch:
        fireworks.append(
            {
                "x": float(random.randint(80, SCREEN_WIDTH - 80)),
                "y": float(SCREEN_HEIGHT + 10),
                "target_y": float(random.randint(80, 275)),
                "vy": random.uniform(-8.5, -6.5),
                "colour": random.choice(
                    (
                        (255, 80, 80),
                        (255, 210, 70),
                        (80, 220, 255),
                        (130, 255, 120),
                        (210, 110, 255),
                        (255, 145, 60),
                    )
                ),
            }
        )
        next_firework_launch = now + random.randint(280, 650)

    layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    # Rising rockets with bright trails.
    for rocket in fireworks[:]:
        previous_y = rocket["y"]
        rocket["y"] += rocket["vy"]
        rocket["vy"] += 0.035
        x = int(rocket["x"])
        y = int(rocket["y"])
        pygame.draw.line(layer, (*rocket["colour"], 150), (x, int(previous_y) + 18), (x, y), 3)
        pygame.draw.circle(layer, (255, 255, 235, 255), (x, y), 4)

        if rocket["y"] <= rocket["target_y"] or rocket["vy"] >= -1.5:
            for index in range(42):
                angle = math.tau * index / 42 + random.uniform(-0.05, 0.05)
                speed = random.uniform(2.0, 5.8)
                firework_sparks.append(
                    {
                        "x": rocket["x"],
                        "y": rocket["y"],
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "life": random.randint(45, 80),
                        "max_life": 80,
                        "colour": rocket["colour"],
                        "trail": [],
                    }
                )
            fireworks.remove(rocket)

    # Burst sparks with fading trails and gravity.
    for spark in firework_sparks[:]:
        spark["trail"].append((spark["x"], spark["y"]))
        spark["trail"] = spark["trail"][-6:]
        spark["x"] += spark["vx"]
        spark["y"] += spark["vy"]
        spark["vx"] *= 0.985
        spark["vy"] = spark["vy"] * 0.985 + 0.055
        spark["life"] -= 1
        alpha = max(0, int(255 * spark["life"] / spark["max_life"]))

        if len(spark["trail"]) >= 2:
            for index in range(1, len(spark["trail"])):
                trail_alpha = int(alpha * index / len(spark["trail"]) * 0.55)
                start = spark["trail"][index - 1]
                end = spark["trail"][index]
                pygame.draw.line(
                    layer,
                    (*spark["colour"], trail_alpha),
                    (int(start[0]), int(start[1])),
                    (int(end[0]), int(end[1])),
                    2,
                )

        pygame.draw.circle(
            layer,
            (*spark["colour"], alpha),
            (int(spark["x"]), int(spark["y"])),
            3,
        )
        if spark["life"] <= 0 or spark["y"] > SCREEN_HEIGHT + 30:
            firework_sparks.remove(spark)

    screen.blit(layer, (0, 0))


def start_boss_defeat_effect(boss_x, boss_y):
    global boss_defeat_start
    global boss_defeat_particles
    global boss_defeat_debris

    boss_defeat_start = pygame.time.get_ticks()
    boss_defeat_particles = []
    boss_defeat_debris = []

    for _ in range(75):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(2.5, 9.0)
        boss_defeat_particles.append(
            {
                "x": float(boss_x),
                "y": float(boss_y),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.randint(35, 75),
                "max_life": 75,
                "size": random.randint(2, 7),
                "colour": random.choice(((255, 70, 25), (255, 145, 30), (255, 230, 90), (90, 220, 255))),
            }
        )

    for _ in range(18):
        boss_defeat_debris.append(
            {
                "x": float(boss_x + random.randint(-35, 35)),
                "y": float(boss_y + random.randint(-20, 20)),
                "vx": random.uniform(-6.0, 6.0),
                "vy": random.uniform(-7.0, -2.0),
                "rotation": random.uniform(0, math.tau),
                "spin": random.uniform(-0.25, 0.25),
                "life": random.randint(55, 95),
            }
        )


def update_boss_defeat_effect():
    if boss_defeat_start == 0:
        return

    now = pygame.time.get_ticks()
    elapsed = now - boss_defeat_start
    centre = (650, 374)

    # Bright initial flash.
    if elapsed < 260:
        flash_alpha = int(170 * (1.0 - elapsed / 260.0))
        flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 245, 210, flash_alpha))
        screen.blit(flash, (0, 0))

    # Expanding shockwave rings.
    if elapsed < 1300:
        progress = elapsed / 1300.0
        ring_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for offset, colour in ((0, (255, 200, 80)), (28, (90, 220, 255)), (55, (255, 95, 40))):
            radius = int(25 + progress * 170 + offset)
            alpha = max(0, int(180 * (1.0 - progress)))
            pygame.draw.circle(ring_layer, (*colour, alpha), centre, radius, 4)
        screen.blit(ring_layer, (0, 0))

    # Fire, sparks, and energy particles.
    particle_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for particle in boss_defeat_particles[:]:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["vy"] += 0.08
        particle["vx"] *= 0.985
        particle["life"] -= 1
        alpha = max(0, int(255 * particle["life"] / particle["max_life"]))
        pygame.draw.circle(
            particle_layer,
            (*particle["colour"], alpha),
            (int(particle["x"]), int(particle["y"])),
            particle["size"],
        )
        if particle["life"] <= 0:
            boss_defeat_particles.remove(particle)
    screen.blit(particle_layer, (0, 0))

    # Falling mechanical debris.
    for debris in boss_defeat_debris[:]:
        debris["x"] += debris["vx"]
        debris["y"] += debris["vy"]
        debris["vy"] += 0.22
        debris["rotation"] += debris["spin"]
        debris["life"] -= 1
        size = 8
        dx = math.cos(debris["rotation"]) * size
        dy = math.sin(debris["rotation"]) * size
        pygame.draw.line(
            screen,
            (85, 75, 105),
            (int(debris["x"] - dx), int(debris["y"] - dy)),
            (int(debris["x"] + dx), int(debris["y"] + dy)),
            5,
        )
        if debris["life"] <= 0 or debris["y"] > SCREEN_HEIGHT + 30:
            boss_defeat_debris.remove(debris)

    # Defeat announcement and short celebration.
    if 350 <= elapsed < 2600:
        scale = 1.0 + 0.08 * math.sin(elapsed / 90.0)
        banner_font = pygame.font.SysFont("Arial", int(42 * scale), bold=True)
        banner_shadow = banner_font.render("BOSS DEFEATED!", True, (65, 20, 20))
        banner = banner_font.render("BOSS DEFEATED!", True, (255, 230, 80))
        centre_x = SCREEN_WIDTH // 2
        screen.blit(banner_shadow, banner_shadow.get_rect(center=(centre_x + 3, 155 + 3)))
        screen.blit(banner, banner.get_rect(center=(centre_x, 155)))

    if 2600 <= elapsed < 3900:
        continue_text = font_sub.render("Reach 1000 jumps to complete the adventure!", True, WHITE)
        backing = pygame.Surface((continue_text.get_width() + 30, 46), pygame.SRCALPHA)
        backing.fill((15, 20, 35, 170))
        backing_rect = backing.get_rect(center=(SCREEN_WIDTH // 2, 155))
        screen.blit(backing, backing_rect)
        screen.blit(continue_text, continue_text.get_rect(center=(SCREEN_WIDTH // 2, 155)))


def fire_dino_gun():
    global next_dino_shot
    global muzzle_flash_until
    now = pygame.time.get_ticks()
    if jump_count < 300 or boss_defeated or now < next_dino_shot:
        return
    # Aim the arcade projectile at the boss's current position.
    start_x = float(dino_x + dino_width + 28)
    start_y = float(dino_y + 27)
    boss_x, boss_y, _ = get_ground_robot_position()
    target_x = float(boss_x)
    target_y = float(boss_y)

    direction_x = target_x - start_x
    direction_y = target_y - start_y
    distance = max(1.0, math.hypot(direction_x, direction_y))
    projectile_speed = 14.0

    dino_projectiles.append(
        {
            "x": start_x,
            "y": start_y,
            "vx": direction_x / distance * projectile_speed,
            "vy": direction_y / distance * projectile_speed,
            "trail": [],
        }
    )
    muzzle_flash_until = now + 90
    next_dino_shot = now + 280
    play_sound(SOUND_BUTTON)


def update_dino_projectiles():
    global boss_health
    global boss_defeated
    global boss_timer_started
    global boss_hit_flash_until
    global boss_damage_animation_start
    global screen_shake_until

    if jump_count < 300 or boss_defeated:
        dino_projectiles.clear()
        return

    boss_x, boss_y, _ = get_ground_robot_position()
    boss_rect = pygame.Rect(boss_x - 72, boss_y - 108, 180, 195)

    for shot in dino_projectiles[:]:
        shot["trail"].append((shot["x"], shot["y"]))
        shot["trail"] = shot["trail"][-10:]
        shot["x"] += shot["vx"]
        shot["y"] += shot["vy"]
        shot_x = int(shot["x"])
        shot_y = int(shot["y"])

        bullet_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for index in range(1, len(shot["trail"])):
            start = shot["trail"][index - 1]
            end = shot["trail"][index]
            alpha = int(25 + 170 * index / len(shot["trail"]))
            pygame.draw.line(
                bullet_layer,
                (40, 170, 255, alpha),
                (int(start[0]), int(start[1])),
                (int(end[0]), int(end[1])),
                max(1, index // 2),
            )
        pygame.draw.line(bullet_layer, (90, 225, 255, 220), (shot_x - 20, shot_y), (shot_x, shot_y), 5)
        pygame.draw.circle(bullet_layer, (80, 190, 255, 90), (shot_x, shot_y), 11)
        pygame.draw.circle(bullet_layer, WHITE, (shot_x, shot_y), 4)
        screen.blit(bullet_layer, (0, 0))

        if pygame.Rect(shot_x - 5, shot_y - 5, 10, 10).colliderect(boss_rect):
            boss_health = max(0, boss_health - 50)
            play_sound(SOUND_BULLET_HIT)
            play_sound(SOUND_BULLET_SPARK)
            boss_hit_flash_until = pygame.time.get_ticks() + 130
            boss_damage_animation_start = pygame.time.get_ticks()
            screen_shake_until = pygame.time.get_ticks() + 120
            boss_damage_numbers.append({"x": float(boss_x), "y": float(boss_y - 48), "life": 55})
            for _ in range(24):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(1.5, 6.0)
                bullet_impact_particles.append({
                    "x": float(shot_x), "y": float(shot_y),
                    "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
                    "life": random.randint(18, 38),
                    "colour": random.choice(((80,220,255),(255,245,170),(255,120,50))),
                })
            dino_projectiles.remove(shot)
            if boss_health == 0:
                boss_defeated = True
                boss_timer_started = False
                boss_projectiles.clear()
                dino_projectiles.clear()
                start_boss_defeat_effect(boss_x, boss_y)
                play_sound(SOUND_VICTORY)
        elif (
            shot_x > SCREEN_WIDTH + 30
            or shot_x < -30
            or shot_y < -30
            or shot_y > SCREEN_HEIGHT + 30
        ):
            dino_projectiles.remove(shot)


def update_bullet_effects():
    now = pygame.time.get_ticks()

    # Bright muzzle flash at the fictional arcade gun barrel.
    if now < muzzle_flash_until:
        flash_x = dino_x + dino_width + 29
        flash_y = int(dino_y + 26)
        flash_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(flash_layer, (255, 235, 120, 85), (flash_x, flash_y), 18)
        pygame.draw.polygon(
            flash_layer,
            (255, 245, 180, 245),
            [(flash_x, flash_y - 8), (flash_x + 22, flash_y), (flash_x, flash_y + 8)],
        )
        pygame.draw.circle(flash_layer, WHITE, (flash_x, flash_y), 5)
        screen.blit(flash_layer, (0, 0))

    # Impact sparks where a bullet hits the boss.
    impact_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for particle in bullet_impact_particles[:]:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["vx"] *= 0.96
        particle["vy"] = particle["vy"] * 0.96 + 0.09
        particle["life"] -= 1
        alpha = min(255, particle["life"] * 9)
        start = (int(particle["x"]), int(particle["y"]))
        end = (int(particle["x"] - particle["vx"] * 2.4), int(particle["y"] - particle["vy"] * 2.4))
        pygame.draw.line(impact_layer, (*particle["colour"], alpha), start, end, 3)
        if particle["life"] <= 0:
            bullet_impact_particles.remove(particle)
    screen.blit(impact_layer, (0, 0))

    # Floating damage indicators for confirmed hits.
    for damage_number in boss_damage_numbers[:]:
        damage_number["y"] -= 0.85
        damage_number["life"] -= 1
        alpha = max(0, min(255, damage_number["life"] * 6))
        damage_font = pygame.font.SysFont("Arial", 28, bold=True)
        damage_text = damage_font.render("-50", True, (255, 235, 95))
        damage_text.set_alpha(alpha)
        shadow = damage_font.render("-50", True, (80, 20, 20))
        shadow.set_alpha(alpha)
        position = (int(damage_number["x"]), int(damage_number["y"]))
        screen.blit(shadow, shadow.get_rect(center=(position[0] + 2, position[1] + 2)))
        screen.blit(damage_text, damage_text.get_rect(center=position))
        if damage_number["life"] <= 0:
            boss_damage_numbers.remove(damage_number)

    # Brief white-blue boss hit flash.
    if now < boss_hit_flash_until and not boss_defeated:
        hit_x, hit_y, _ = get_ground_robot_position()
        flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(flash, (190, 235, 255, 115), (hit_x - 76, hit_y - 112, 185, 200))
        screen.blit(flash, (0, 0))



def draw_spikes(x, y, count):
    for index in range(count):
        current_x = x + (index * single_spike_width)
        points = [
            (current_x, y + obstacle_height),
            (current_x + single_spike_width // 2, y),
            (current_x + single_spike_width, y + obstacle_height),
        ]
        pygame.draw.polygon(screen, RED, points)


def draw_kite(x, y):
    points = [
        (x + single_spike_width // 2, y),
        (x + single_spike_width, y + obstacle_height // 2),
        (x + single_spike_width // 2, y + obstacle_height),
        (x, y + obstacle_height // 2),
    ]
    pygame.draw.polygon(screen, GOLD, points)
    pygame.draw.line(
        screen,
        BLACK,
        (x + single_spike_width // 2, y + obstacle_height),
        (x + 10, y + 75),
        2,
    )


def draw_cup(x, y):
    pygame.draw.rect(
        screen,
        GOLD,
        (x, y, 60, 50),
        border_bottom_left_radius=15,
        border_bottom_right_radius=15,
    )
    pygame.draw.rect(screen, GOLD, (x + 20, y + 50, 20, 20))
    pygame.draw.rect(screen, GOLD, (x + 10, y + 70, 40, 10))
    pygame.draw.lines(
        screen,
        GOLD,
        False,
        [(x, y + 10), (x - 15, y + 20), (x, y + 35)],
        5,
    )
    pygame.draw.lines(
        screen,
        GOLD,
        False,
        [(x + 60, y + 10), (x + 75, y + 20), (x + 60, y + 35)],
        5,
    )


def submit_score():
    global player_name
    global leaderboard
    global current_state

    final_name = player_name.strip() or "Player"
    leaderboard.append({"name": final_name, "score": jump_count, "cups": int(player_progress.get("cups", 0))})
    leaderboard.sort(key=lambda entry: entry["score"], reverse=True)
    leaderboard = leaderboard[:10]
    save_leaderboard(leaderboard)
    player_name = active_account or ""
    current_state = GameState.LEADERBOARD


def pet_bonus(name):
    if name == SECRET_PET: return 50
    for rarity in PET_RARITIES:
        if name in rarity["pets"]: return rarity["bonus"]
    return 0

def draw_pet(name,x,y):
    """Detailed animated pet art for gameplay and the collection gallery."""
    now=pygame.time.get_ticks(); x=int(x); y=int(y)
    bob=int(math.sin(now/170.0)*3)
    bird=name in ("VULTURE","EAGLE","OWL")
    if bird: y += int(math.sin(now/150.0)*7)
    if name==SECRET_PET:
        rainbow=[(255,70,80),(255,160,35),(255,230,60),(70,220,110),(70,170,255),(170,90,255)]
        colour=rainbow[(now//120)%len(rainbow)]
    else:
        colour={"DOG":(150,96,50),"CAT":(120,125,145),"RABBIT":(235,235,242),"OCTOPUS":(160,65,195),"BUFFALO":(78,57,40),"COW":(235,232,220),"VULTURE":(78,68,62),"EAGLE":(120,72,30),"OWL":(145,95,48),"TIGER":(225,125,30),"LION":(200,142,52),"CHEETAH":(225,175,55)}.get(name,(100,190,235))
    # Soft shadow grounds every non-flying pet.
    if not bird: pygame.draw.ellipse(screen,(0,0,0,70),(x-30,y+13,62,12))
    if bird:
        wing=int(math.sin(now/90.0)*13)
        body=(x,y+bob)
        pygame.draw.ellipse(screen,colour,(x-20,y-10,40,25))
        pygame.draw.polygon(screen,colour,[(x-5,y),(x-48,y-17-wing),(x-25,y+8),(x-8,y+8)])
        pygame.draw.polygon(screen,colour,[(x+5,y),(x+48,y-17+wing),(x+25,y+8),(x+8,y+8)])
        feather=(45,38,35) if name=="VULTURE" else ((75,48,25) if name=="EAGLE" else (95,65,38))
        for side in (-1,1):
            for index in range(3):
                sx=x+side*(15+index*10); sy=y-3-index*3
                pygame.draw.line(screen,feather,(x+side*4,y+3),(sx,sy),4)
        head_colour=(220,205,185) if name=="VULTURE" else colour
        pygame.draw.circle(screen,head_colour,(x+18,y-8),12)
        pygame.draw.circle(screen,(255,220,60),(x+21,y-10),3)
        pygame.draw.circle(screen,BLACK,(x+22,y-10),1)
        pygame.draw.polygon(screen,(235,165,35),[(x+29,y-7),(x+42,y-3),(x+29,y+1)])
        if name=="OWL":
            pygame.draw.circle(screen,(235,215,165),(x+14,y-9),7); pygame.draw.circle(screen,(235,215,165),(x+24,y-9),7)
            pygame.draw.circle(screen,BLACK,(x+14,y-9),3); pygame.draw.circle(screen,BLACK,(x+24,y-9),3)
    elif name=="OCTOPUS":
        pygame.draw.ellipse(screen,colour,(x-24,y-24+bob,48,45))
        pygame.draw.ellipse(screen,(205,120,225),(x-16,y-18+bob,32,24))
        pygame.draw.circle(screen,WHITE,(x-10,y-8+bob),6); pygame.draw.circle(screen,WHITE,(x+10,y-8+bob),6)
        pygame.draw.circle(screen,BLACK,(x-9,y-8+bob),3); pygame.draw.circle(screen,BLACK,(x+9,y-8+bob),3)
        # Four visible tentacles keep the small pet clean and readable.
        for tentacle in range(4):
            tx=x-25+tentacle*17
            pygame.draw.arc(screen,colour,(tx,y+8+bob,27,30),0.1,3.0,5)
            pygame.draw.circle(screen,(225,155,235),(tx+12,y+27+bob),2)
    else:
        # Species-aware quadruped proportions.
        big=name in ("BUFFALO","COW","TIGER","LION",SECRET_PET)
        body_w=62 if big else 48; body_h=30 if big else 24
        head_r=20 if big else 15
        pygame.draw.ellipse(screen,colour,(x-body_w//2,y-body_h//2+bob,body_w,body_h))
        # Lighter belly and muzzle.
        belly=tuple(min(255,c+45) for c in colour)
        pygame.draw.ellipse(screen,belly,(x-body_w//3,y+bob,body_w//2,body_h//3))
        head_x=x+body_w//2-4; head_y=y-body_h//3+bob
        pygame.draw.circle(screen,colour,(head_x,head_y),head_r)
        muzzle=(230,195,150) if name in ("DOG","BUFFALO","TIGER","LION",SECRET_PET,"CHEETAH") else belly
        pygame.draw.ellipse(screen,muzzle,(head_x+2,head_y+2,head_r+7,head_r-2))
        pygame.draw.circle(screen,BLACK,(head_x+7,head_y-5),3)
        pygame.draw.circle(screen,WHITE,(head_x+6,head_y-6),1)
        pygame.draw.circle(screen,(35,25,25),(head_x+head_r,head_y+6),3)
        # Four articulated legs and paws/hooves.
        for index,leg_x in enumerate((x-body_w//3,x-body_w//8,x+body_w//5,x+body_w//3)):
            step=int(math.sin(now/130.0+index*math.pi)*3)
            pygame.draw.line(screen,colour,(leg_x,y+body_h//3+bob),(leg_x+step,y+body_h//2+16+bob),6 if big else 4)
            foot=(45,35,30) if name in ("BUFFALO","COW") else colour
            pygame.draw.ellipse(screen,foot,(leg_x-5+step,y+body_h//2+13+bob,12,6))
        # Tail details.
        tail_end=(x-body_w//2-18,y-8+bob+int(math.sin(now/150.0)*7))
        pygame.draw.line(screen,colour,(x-body_w//2+2,y-5+bob),tail_end,6 if big else 4)
        if name in ("LION","BUFFALO"): pygame.draw.circle(screen,(70,45,25),tail_end,6)
        # Ears/horns differ by species.
        if name=="RABBIT":
            pygame.draw.ellipse(screen,colour,(head_x-15,head_y-45,10,37)); pygame.draw.ellipse(screen,colour,(head_x+5,head_y-45,10,37))
            pygame.draw.ellipse(screen,(245,175,190),(head_x-12,head_y-40,4,28)); pygame.draw.ellipse(screen,(245,175,190),(head_x+8,head_y-40,4,28))
        elif name in ("BUFFALO","COW"):
            pygame.draw.arc(screen,(225,210,170),(head_x-29,head_y-27,31,30),1.6,3.3,5); pygame.draw.arc(screen,(225,210,170),(head_x+1,head_y-27,31,30),6.1,1.5,5)
            if name=="COW":
                pygame.draw.ellipse(screen,(35,35,38),(x-18,y-10+bob,16,12)); pygame.draw.ellipse(screen,(35,35,38),(x+7,y+5+bob,18,11))
        else:
            pygame.draw.polygon(screen,colour,[(head_x-13,head_y-10),(head_x-7,head_y-28),(head_x,head_y-12)])
            pygame.draw.polygon(screen,colour,[(head_x+6,head_y-12),(head_x+17,head_y-28),(head_x+18,head_y-6)])
        # Fur patterns and manes.
        if name in ("TIGER",SECRET_PET):
            for stripe in range(5):
                sx=x-body_w//3+stripe*12
                pygame.draw.line(screen,(35,30,30),(sx,y-body_h//2+4+bob),(sx+5,y+5+bob),3)
        elif name=="CHEETAH":
            for spot in range(8):
                sx=x-body_w//3+(spot*17)%body_w; sy=y-body_h//3+(spot*11)%body_h
                pygame.draw.circle(screen,(45,38,28),(sx,sy+bob),2)
        elif name=="LION":
            pygame.draw.circle(screen,(125,75,28),(head_x,head_y),head_r+8)
            pygame.draw.circle(screen,colour,(head_x,head_y),head_r)
            pygame.draw.ellipse(screen,muzzle,(head_x+2,head_y+2,head_r+7,head_r-2))
            pygame.draw.circle(screen,BLACK,(head_x+7,head_y-5),3)
        elif name=="DOG":
            pygame.draw.ellipse(screen,(95,55,30),(head_x-17,head_y-8,11,25)); pygame.draw.ellipse(screen,(95,55,30),(head_x+10,head_y-8,11,25))
        elif name=="CAT":
            for whisker_y in (-1,5):
                pygame.draw.line(screen,(230,230,235),(head_x+12,head_y+whisker_y),(head_x+33,head_y+whisker_y-3),1)


def draw_fused_pet(fusion_name,x,y):
    now=pygame.time.get_ticks(); x=int(x); y=int(y)
    # Base creature plus clear fusion-specific visual effects.
    base={"SKY HOUND":"DOG","NIGHT TIGER":"TIGER","COSMIC RABBIT":"RABBIT","ICE BULL":"BUFFALO"}.get(fusion_name,"DOG")
    draw_pet(base,x,y)
    layer=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
    if fusion_name=="SKY HOUND":
        wing=int(math.sin(now/100.0)*9)
        pygame.draw.polygon(layer,(220,240,255,220),[(x-8,y),(x-48,y-22-wing),(x-26,y+10)])
        pygame.draw.polygon(layer,(220,240,255,220),[(x+8,y),(x+48,y-22+wing),(x+26,y+10)])
        pygame.draw.circle(layer,(80,220,255,100),(x,y),42,3)
    elif fusion_name=="NIGHT TIGER":
        pygame.draw.circle(layer,(110,60,255,55),(x,y),45)
        for star in range(6):
            angle=now/400.0+star*math.tau/6; sx=x+int(math.cos(angle)*38); sy=y+int(math.sin(angle)*25)
            pygame.draw.circle(layer,(210,190,255),(sx,sy),3)
        pygame.draw.arc(layer,(220,210,255),(x+18,y-38,22,22),0,math.pi*1.8,3)
    elif fusion_name=="COSMIC RABBIT":
        for ring in (22,32,42): pygame.draw.circle(layer,(90,210,255,65),(x,y),ring,2)
        pygame.draw.circle(layer,(255,100,230),(x+26,y-14),6)
        pygame.draw.line(layer,(170,100,255),(x-25,y+5),(x-45,y-5),4)
    elif fusion_name=="ICE BULL":
        pygame.draw.polygon(layer,(175,240,255),[(x-28,y-15),(x-52,y-42),(x-18,y-25)])
        pygame.draw.polygon(layer,(175,240,255),[(x+28,y-15),(x+52,y-42),(x+18,y-25)])
        for shard in range(5):
            sx=x-28+shard*14; pygame.draw.polygon(layer,(205,250,255),[(sx,y+14),(sx+6,y-2),(sx+12,y+14)])
    screen.blit(layer,(0,0))

def draw_boss_theme(theme):
    now=pygame.time.get_ticks()
    if theme=="FUTURISTIC":
        screen.fill((8,18,35))
        for x in range(0,SCREEN_WIDTH,80): pygame.draw.line(screen,(20,80,120),(x,0),(x,SCREEN_HEIGHT),1)
        for y in range(0,SCREEN_HEIGHT,60): pygame.draw.line(screen,(20,80,120),(0,y),(SCREEN_WIDTH,y),1)
        for x in range(80,SCREEN_WIDTH,180):
            pygame.draw.rect(screen,(18,45,75),(x,250,100,190)); pygame.draw.circle(screen,(60,225,255),(x+50,290),12)
    elif theme=="CAVE":
        screen.fill((12,9,16)); pygame.draw.rect(screen,(35,28,40),(0,380,SCREEN_WIDTH,160))
        for i in range(14):
            x=i*75; pygame.draw.polygon(screen,(50,42,55),[(x,0),(x+30,100+(i%3)*35),(x+65,0)])
        blink=(now//350)%2==0
        for x,y in ((120,170),(270,260),(720,145),(820,290)):
            pygame.draw.circle(screen,(255,25,25) if blink else (80,5,5),(x,y),5)
    elif theme=="VOLCANO":
        screen.fill((80,25,24)); pygame.draw.polygon(screen,(45,35,38),[(0,430),(250,120),(500,430)]); pygame.draw.polygon(screen,(65,35,32),[(430,430),(690,90),(960,430)])
        for x in range(-60,SCREEN_WIDTH,90): pygame.draw.ellipse(screen,(255,90,20),((x+now//15)%1020-60,420,70,15))
    elif theme=="JUNGLE":
        screen.fill((35,110,85)); pygame.draw.rect(screen,(35,95,45),(0,400,SCREEN_WIDTH,140))
        for x in range(0,SCREEN_WIDTH,90):
            pygame.draw.rect(screen,(70,50,25),(x,200,18,240)); pygame.draw.circle(screen,(25,130,50),(x+8,190),45)
        for i in range(5):
            mx=100+i*170; my=120+int(math.sin(now/300+i)*15)
            pygame.draw.circle(screen,(112,72,40),(mx,my),15); pygame.draw.circle(screen,(190,135,85),(mx,my+3),9)
    elif theme=="SNOW":
        screen.fill((145,200,235)); pygame.draw.polygon(screen,(120,155,175),[(0,430),(210,130),(420,430)]); pygame.draw.polygon(screen,(235,248,255),[(130,245),(210,130),(285,245)])
        pygame.draw.rect(screen,(225,240,248),(0,410,SCREEN_WIDTH,130))
        for i in range(90): pygame.draw.circle(screen,WHITE,((i*71+now//9)%SCREEN_WIDTH,(i*43+now//12)%420),1+i%3)
    else:
        screen.fill((8,2,28))
        for i in range(120): pygame.draw.circle(screen,((120+i)%255,170,255),((i*83)%SCREEN_WIDTH,(i*47)%SCREEN_HEIGHT),1+i%2)
        pygame.draw.ellipse(screen,(90,35,150),(60,80,260,90)); pygame.draw.ellipse(screen,(35,140,210),(620,90,220,70))

def draw_arena_boss(name,x,y):
    now=pygame.time.get_ticks()
    layer=pygame.Surface((360,330),pygame.SRCALPHA)
    cx,cy=180,175
    pulse=0.5+0.5*math.sin(now/160.0)
    # Large shadow and aura make every boss feel heavier and more polished.
    pygame.draw.ellipse(layer,(0,0,0,95),(45,270,270,34))
    aura_colours={"ROBOT":(50,220,255),"GHOST":(190,80,255),"DRAGON":(255,75,25),"MONKEY":(80,220,85),"SNOW":(100,220,255),"ALIEN":(100,255,150)}
    aura=aura_colours[name]
    for radius,alpha in ((125,12),(95,22),(70,34)):
        pygame.draw.circle(layer,(*aura,alpha),(cx,cy),radius+int(5*pulse))
    if name=="ROBOT":
        # Ultra-detailed futuristic war mech with layered armour and animated energy.
        mech_pulse=int(18*pulse)
        # Back-mounted reactor halo and exhaust flames.
        pygame.draw.circle(layer,(25,70,95,90),(cx,cy-25),110+int(5*pulse),8)
        pygame.draw.arc(layer,(70,235,255),(cx-115,cy-140,230,230),0.2,2.9,5)
        for exhaust_x in (cx-58,cx+58):
            pygame.draw.polygon(layer,(255,105,25),[(exhaust_x-12,cy+98),(exhaust_x+12,cy+98),(exhaust_x,cy+145+mech_pulse)])
            pygame.draw.polygon(layer,(255,235,80),[(exhaust_x-5,cy+98),(exhaust_x+5,cy+98),(exhaust_x,cy+127+mech_pulse//2)])
        # Thick articulated legs, knee armour and mechanical feet.
        for side in (-1,1):
            lx=cx+side*52
            pygame.draw.rect(layer,(28,38,55),(lx-22,cy+52,44,74),border_radius=12)
            pygame.draw.polygon(layer,(120,150,180),[(lx-28,cy+58),(lx+28,cy+58),(lx+20,cy+95),(lx-20,cy+95)])
            pygame.draw.circle(layer,(65,225,255),(lx,cy+78),10); pygame.draw.circle(layer,WHITE,(lx,cy+78),4)
            pygame.draw.rect(layer,(45,58,78),(lx-25,cy+112,50,55),border_radius=10)
            pygame.draw.rect(layer,(135,155,180),(lx-38,cy+148,76,24),border_radius=9)
            pygame.draw.line(layer,(65,225,255),(lx-26,cy+160),(lx+26,cy+160),3)
        # Layered torso and angular chest plates.
        pygame.draw.polygon(layer,(30,42,62),[(cx-82,cy-90),(cx-105,cy-25),(cx-78,cy+72),(cx,cy+95),(cx+78,cy+72),(cx+105,cy-25),(cx+82,cy-90)])
        pygame.draw.polygon(layer,(100,130,165),[(cx-65,cy-72),(cx-88,cy-20),(cx-55,cy+45),(cx,cy+67),(cx+55,cy+45),(cx+88,cy-20),(cx+65,cy-72)])
        pygame.draw.polygon(layer,(155,180,205),[(cx-58,cy-55),(cx-12,cy-70),(cx-4,cy+23),(cx-48,cy+35)])
        pygame.draw.polygon(layer,(155,180,205),[(cx+58,cy-55),(cx+12,cy-70),(cx+4,cy+23),(cx+48,cy+35)])
        # Animated arc reactor with rotating energy segments.
        pygame.draw.circle(layer,(15,35,55),(cx,cy-10),42)
        pygame.draw.circle(layer,(50,220,255),(cx,cy-10),31)
        pygame.draw.circle(layer,(235,255,255),(cx,cy-10),13)
        for segment in range(6):
            angle=now/260.0+segment*math.tau/6
            px=cx+int(math.cos(angle)*35); py=cy-10+int(math.sin(angle)*35)
            pygame.draw.circle(layer,(100,245,255),(px,py),5)
        # Armoured head with antennae, face shield and expressive red optics.
        pygame.draw.polygon(layer,(32,42,58),[(cx-53,cy-155),(cx-35,cy-183),(cx+35,cy-183),(cx+53,cy-155),(cx+44,cy-96),(cx-44,cy-96)])
        pygame.draw.polygon(layer,(145,170,195),[(cx-40,cy-156),(cx-27,cy-171),(cx+27,cy-171),(cx+40,cy-156),(cx+34,cy-112),(cx-34,cy-112)])
        pygame.draw.rect(layer,(15,25,38),(cx-32,cy-151,64,25),border_radius=8)
        pygame.draw.ellipse(layer,(255,35,50),(cx-25,cy-146,19,12)); pygame.draw.ellipse(layer,(255,35,50),(cx+6,cy-146,19,12))
        pygame.draw.circle(layer,(255,230,230),(cx-17,cy-142),3); pygame.draw.circle(layer,(255,230,230),(cx+17,cy-142),3)
        pygame.draw.line(layer,(90,240,255),(cx-25,cy-183),(cx-38,cy-210),5); pygame.draw.circle(layer,(90,240,255),(cx-39,cy-211),6)
        pygame.draw.line(layer,(90,240,255),(cx+25,cy-183),(cx+38,cy-210),5); pygame.draw.circle(layer,(90,240,255),(cx+39,cy-211),6)
        # Huge shoulder armour, missile pods and articulated cannon arms.
        for side in (-1,1):
            shoulder_x=cx+side*106
            pygame.draw.polygon(layer,(55,72,98),[(shoulder_x-side*38,cy-82),(shoulder_x+side*15,cy-105),(shoulder_x+side*40,cy-55),(shoulder_x+side*22,cy-5),(shoulder_x-side*28,cy-10)])
            pygame.draw.polygon(layer,(140,165,190),[(shoulder_x-side*28,cy-73),(shoulder_x+side*11,cy-90),(shoulder_x+side*27,cy-50),(shoulder_x+side*14,cy-18),(shoulder_x-side*19,cy-22)])
            pod_x=shoulder_x+side*12
            pygame.draw.rect(layer,(28,38,55),(pod_x-25,cy-118,50,38),border_radius=8)
            for missile in range(3): pygame.draw.circle(layer,(255,90,40),(pod_x-14+missile*14,cy-99),5)
            elbow_x=cx+side*130
            pygame.draw.line(layer,(35,48,68),(shoulder_x,cy-10),(elbow_x,cy+50),28)
            pygame.draw.line(layer,(125,150,180),(shoulder_x,cy-10),(elbow_x,cy+50),12)
            pygame.draw.circle(layer,(60,225,255),(elbow_x,cy+50),12)
            # Left arm energy blade; right arm plasma cannon.
            if side<0:
                pygame.draw.line(layer,(24,45,65),(elbow_x,cy+50),(elbow_x-24,cy+118),20)
                blade=[(elbow_x-31,cy+103),(elbow_x-72,cy+155),(elbow_x-45,cy+112),(elbow_x-34,cy+65)]
                pygame.draw.polygon(layer,(50,225,255,180),blade); pygame.draw.lines(layer,(220,255,255),True,blade,3)
            else:
                pygame.draw.rect(layer,(30,42,60),(elbow_x-12,cy+38,78,34),border_radius=12)
                pygame.draw.rect(layer,(115,145,175),(elbow_x+10,cy+44,60,22),border_radius=9)
                pygame.draw.circle(layer,(75,235,255),(elbow_x+70,cy+55),16+int(3*pulse)); pygame.draw.circle(layer,WHITE,(elbow_x+70,cy+55),6)
        # Fine neon circuit lines and scratches across the armour.
        for index in range(7):
            yline=cy-62+index*18
            pygame.draw.line(layer,(60,220,255,160),(cx-52,yline),(cx-18,yline+8),2)
            pygame.draw.line(layer,(60,220,255,160),(cx+52,yline),(cx+18,yline+8),2)
    elif name=="GHOST":
        # Black-and-red Grim Reaper based on the supplied concept drawing.
        sway=int(math.sin(now/190.0)*7)
        # Long black robe with torn lower edge and red cracked armour plates.
        pygame.draw.polygon(layer,(3,3,7),[(cx-58,cy-92),(cx-92,cy-25),(cx-72,cy+55),(cx-112,cy+132),(cx-52,cy+120),(cx-20,cy+148),(cx+20,cy+136),(cx+58,cy+151),(cx+104,cy+126),(cx+65,cy+52),(cx+92,cy-25),(cx+55,cy-92)])
        pygame.draw.polygon(layer,(12,10,16),[(cx-55,cy-88),(cx-78,cy-10),(cx-48,cy+70),(cx-20,cy+120),(cx,cy+88),(cx+27,cy+122),(cx+58,cy+65),(cx+78,cy-8),(cx+52,cy-88)])
        # Oversized black hood and pale mask-like face.
        # Visible black hood: charcoal outer rim, black inner fabric and a clear opening around the face.
        pygame.draw.polygon(layer,(38,38,46),[(cx-82,cy-70),(cx-72,cy-150),(cx-30,cy-184),(cx+48,cy-180),(cx+88,cy-132),(cx+82,cy-52),(cx+48,cy-88),(cx-42,cy-88)])
        pygame.draw.polygon(layer,(4,4,8),[(cx-68,cy-74),(cx-58,cy-142),(cx-22,cy-168),(cx+38,cy-165),(cx+70,cy-125),(cx+66,cy-66),(cx+38,cy-98),(cx-34,cy-98)])
        pygame.draw.line(layer,(78,78,88),(cx-68,cy-74),(cx-58,cy-142),5)
        pygame.draw.line(layer,(78,78,88),(cx-58,cy-142),(cx-22,cy-168),5)
        pygame.draw.line(layer,(78,78,88),(cx+38,cy-165),(cx+70,cy-125),5)
        # Detailed skeleton skull visible inside the hood.
        skull=(232,228,210)
        bone_shadow=(175,168,150)
        pygame.draw.ellipse(layer,skull,(cx-42,cy-140,86,76))
        pygame.draw.polygon(layer,skull,[(cx-31,cy-86),(cx+33,cy-86),(cx+26,cy-55),(cx-22,cy-55)])
        # Hollow eye sockets with red supernatural pupils.
        pygame.draw.ellipse(layer,(20,15,18),(cx-29,cy-116,24,29))
        pygame.draw.ellipse(layer,(20,15,18),(cx+7,cy-116,24,29))
        pygame.draw.circle(layer,(235,20,38),(cx-17,cy-101),6)
        pygame.draw.circle(layer,(235,20,38),(cx+19,cy-101),6)
        pygame.draw.circle(layer,(255,210,210),(cx-15,cy-103),2)
        pygame.draw.circle(layer,(255,210,210),(cx+21,cy-103),2)
        # Nasal cavity, cheekbones and jaw definition.
        pygame.draw.polygon(layer,(35,28,30),[(cx,cy-91),(cx-8,cy-77),(cx+8,cy-77)])
        pygame.draw.arc(layer,bone_shadow,(cx-38,cy-105,76,55),0.15,1.15,4)
        pygame.draw.arc(layer,bone_shadow,(cx-38,cy-105,76,55),2.0,3.0,4)
        pygame.draw.line(layer,bone_shadow,(cx-30,cy-80),(cx-20,cy-62),4)
        pygame.draw.line(layer,bone_shadow,(cx+30,cy-80),(cx+20,cy-62),4)
        # Individual skeleton teeth.
        pygame.draw.line(layer,(55,45,42),(cx-23,cy-68),(cx+24,cy-68),3)
        for tooth in range(6):
            tx=cx-22+tooth*9
            pygame.draw.rect(layer,(245,240,220),(tx,cy-68,7,14),border_radius=2)
            pygame.draw.line(layer,bone_shadow,(tx+7,cy-67),(tx+7,cy-56),1)
        # Red cracked shoulder and chest armour.
        armour=(220,20,42); edge=(255,80,92)
        pygame.draw.polygon(layer,armour,[(cx-74,cy-55),(cx-110,cy-38),(cx-96,cy+3),(cx-62,cy-8)])
        pygame.draw.polygon(layer,armour,[(cx+68,cy-55),(cx+108,cy-35),(cx+92,cy+5),(cx+60,cy-10)])
        pygame.draw.polygon(layer,armour,[(cx-42,cy-52),(cx,cy-66),(cx+42,cy-50),(cx+32,cy+8),(cx,cy-2),(cx-34,cy+9)])
        for x1,y1,x2,y2 in ((cx-92,cy-35,cx-72,cy-12),(cx-83,cy-45,cx-88,cy-20),(cx-20,cy-48,cx-2,cy-12),(cx+15,cy-54,cx+8,cy-8),(cx+74,cy-42,cx+90,cy-14)):
            pygame.draw.line(layer,edge,(x1,y1),(x2,y2),2)
        # Clearly visible skeleton forearms and hands.
        bone=(235,230,210); bone_shadow=(150,142,125)
        pygame.draw.line(layer,(8,8,12),(cx-78,cy-6),(cx-116,cy+16),20)
        pygame.draw.line(layer,(8,8,12),(cx+78,cy-6),(cx+116,cy+16),20)
        pygame.draw.line(layer,bone,(cx-82,cy-4),(cx-116,cy+16),10)
        pygame.draw.line(layer,bone,(cx+82,cy-4),(cx+116,cy+16),10)
        pygame.draw.circle(layer,bone,(cx-120,cy+20),13)
        pygame.draw.circle(layer,bone,(cx+120,cy+20),13)
        pygame.draw.circle(layer,bone_shadow,(cx-120,cy+20),5)
        pygame.draw.circle(layer,bone_shadow,(cx+120,cy+20),5)
        # Five long finger bones on both hands, outlined for visibility.
        for finger in range(5):
            left_end=(cx-143-finger*4,cy+2+finger*10)
            right_end=(cx+143+finger*4,cy+2+finger*10)
            pygame.draw.line(layer,(18,16,18),(cx-121,cy+19),left_end,7)
            pygame.draw.line(layer,bone,(cx-121,cy+19),left_end,4)
            pygame.draw.circle(layer,bone,left_end,3)
            pygame.draw.line(layer,(18,16,18),(cx+121,cy+19),right_end,7)
            pygame.draw.line(layer,bone,(cx+121,cy+19),right_end,4)
            pygame.draw.circle(layer,bone,right_end,3)
        pygame.draw.polygon(layer,armour,[(cx-70,cy+113),(cx-30,cy+112),(cx-38,cy+148),(cx-82,cy+143)])
        pygame.draw.polygon(layer,armour,[(cx+35,cy+112),(cx+72,cy+114),(cx+86,cy+143),(cx+43,cy+148)])
        # Black shaft and large orange-red flame scythe matching the drawing.
        shaft_top=(cx+122+sway,cy-138); shaft_bottom=(cx+35,cy+34)
        pygame.draw.line(layer,(8,8,10),shaft_bottom,shaft_top,18); pygame.draw.line(layer,(55,50,55),shaft_bottom,shaft_top,5)
        blade=[(shaft_top[0]-8,shaft_top[1]+5),(cx+118+sway,cy-185),(cx+180+sway,cy-174),(cx+218+sway,cy-205),(cx+210+sway,cy-145),(cx+242+sway,cy-127),(cx+196+sway,cy-108),(cx+145+sway,cy-120)]
        pygame.draw.polygon(layer,(255,112,30),blade); pygame.draw.lines(layer,(10,8,10),True,blade,5)
        inner=[(cx+125+sway,cy-155),(cx+174+sway,cy-162),(cx+202+sway,cy-180),(cx+192+sway,cy-143),(cx+218+sway,cy-127),(cx+177+sway,cy-130),(cx+144+sway,cy-120)]
        pygame.draw.polygon(layer,(220,20,35),inner); pygame.draw.lines(layer,(255,70,55),False,inner,3)
        # Orbiting red-black eye orbs from the concept.
        for eye in range(16):
            angle=now/900.0+eye*math.tau/16
            radius=125+(eye%4)*28
            ex=cx+int(math.cos(angle)*radius); ey=cy-20+int(math.sin(angle)*radius*0.72)
            size=9+(eye%3)*3
            pygame.draw.circle(layer,(5,5,8),(ex,ey),size+4)
            pygame.draw.circle(layer,(230,20,35),(ex,ey),size)
            pygame.draw.ellipse(layer,(12,12,16),(ex-size//3,ey-size+2,max(5,size*2//3),size*2-4))
            pygame.draw.circle(layer,(245,235,235),(ex,ey),max(2,size//4))
            if eye%4==0:
                pygame.draw.line(layer,(255,115,125),(ex-size+2,ey-size//2),(ex+size-2,ey+size//2),2)
    elif name=="DRAGON":
        # True flying dragon silhouette: one continuous body, two wings, no arms or legs.
        wing_flap=int(math.sin(now/180.0)*10)
        flame_pulse=int(18*pulse)
        # Fire aura, smoke and embers.
        pygame.draw.circle(layer,(255,65,15,32),(cx,cy-20),128+int(5*pulse))
        for ember in range(18):
            ex=(ember*67+now//5)%330+15; ey=285-((ember*43+now//8)%260)
            pygame.draw.circle(layer,(255,80+ember%120,20,190),(ex,ey),2+ember%3)
        for smoke in range(5):
            sx=85+smoke*45; sy=35+int(math.sin(now/300.0+smoke)*12)
            pygame.draw.circle(layer,(75,55,60,55),(sx,sy),22+smoke%3*7)
        # Two clean wings, clearly separate from the body and never extending downward like legs.
        left_wing=[(cx-28,cy-35),(cx-118,cy-165-wing_flap),(cx-170,cy-135-wing_flap),(cx-138,cy-82),(cx-175,cy-45),(cx-92,cy-25)]
        right_wing=[(cx+28,cy-35),(cx+118,cy-165+wing_flap),(cx+170,cy-135+wing_flap),(cx+138,cy-82),(cx+175,cy-45),(cx+92,cy-25)]
        pygame.draw.polygon(layer,(70,16,22),left_wing); pygame.draw.polygon(layer,(70,16,22),right_wing)
        pygame.draw.lines(layer,(245,70,28),True,left_wing,6); pygame.draw.lines(layer,(245,70,28),True,right_wing,6)
        for wing_tip in (left_wing[1],left_wing[2],right_wing[1],right_wing[2]):
            pygame.draw.circle(layer,(255,120,40),wing_tip,5)
        pygame.draw.line(layer,(255,115,42),(cx-30,cy-25),left_wing[1],4); pygame.draw.line(layer,(255,115,42),(cx+30,cy-25),right_wing[1],4)
        pygame.draw.line(layer,(255,115,42),(cx-35,cy-15),left_wing[3],3); pygame.draw.line(layer,(255,115,42),(cx+35,cy-15),right_wing[3],3)
        # Continuous S-shaped serpentine torso and tail, with no limb-like side branches.
        spine=[(cx+65,cy-105),(cx+25,cy-62),(cx-12,cy-18),(cx+18,cy+30),(cx+42,cy+72),(cx+20,cy+112),(cx-22,cy+140),(cx-72,cy+148),(cx-120,cy+128),(cx-160,cy+102),(cx-205,cy+112)]
        pygame.draw.lines(layer,(90,18,20),False,spine,86)
        pygame.draw.lines(layer,(205,48,25),False,spine,64)
        pygame.draw.lines(layer,(245,85,32),False,spine,8)
        # Belly scales follow only the central body curve.
        for index in range(8):
            bx=cx+int(math.sin(index*0.85)*24); by=cy-28+index*20
            pygame.draw.arc(layer,(255,150,62),(bx-22,by,44,18),0,math.pi,3)
        # Dorsal spikes run along the upper serpent body.
        for index in range(8):
            sx=cx+42-index*11; sy=cy-70+index*14
            pygame.draw.polygon(layer,(255,115,35),[(sx-8,sy),(sx,sy-22-index%2*7),(sx+8,sy)])
        # Dragon neck and detailed head.
        pygame.draw.line(layer,(185,40,24),(cx+35,cy-65),(cx+105,cy-132),58)
        pygame.draw.line(layer,(235,65,28),(cx+35,cy-65),(cx+105,cy-132),36)
        pygame.draw.ellipse(layer,(225,62,28),(cx+72,cy-172,112,90))
        pygame.draw.polygon(layer,(235,75,30),[(cx+150,cy-143),(cx+215,cy-116),(cx+158,cy-92)])
        # Horns and ears are above the head, not below the body.
        pygame.draw.polygon(layer,(245,215,135),[(cx+92,cy-163),(cx+78,cy-218),(cx+118,cy-170)])
        pygame.draw.polygon(layer,(245,215,135),[(cx+137,cy-164),(cx+160,cy-214),(cx+159,cy-150)])
        pygame.draw.circle(layer,(255,238,75),(cx+148,cy-139),10); pygame.draw.circle(layer,(10,7,5),(cx+151,cy-139),4)
        pygame.draw.line(layer,(45,10,8),(cx+125,cy-103),(cx+184,cy-107),5)
        for tooth in range(5):
            pygame.draw.polygon(layer,(250,242,210),[(cx+132+tooth*11,cy-105),(cx+137+tooth*11,cy-89),(cx+142+tooth*11,cy-106)])
        # Tail finishes as a natural pointed dragon tail, not a foot or leg.
        tail_tip=[(cx-205,cy+112),(cx-250,cy+86),(cx-226,cy+120),(cx-260,cy+142),(cx-210,cy+134)]
        pygame.draw.polygon(layer,(195,42,25),tail_tip); pygame.draw.lines(layer,(255,95,35),True,tail_tip,4)
        # Large layered fire breath.
        mouth=(cx+187,cy-109); flame_end=cx+270+flame_pulse
        pygame.draw.polygon(layer,(255,50,12),[mouth,(flame_end,cy-145),(flame_end-20,cy-112),(flame_end+8,cy-78),(mouth[0]+4,cy-94)])
        pygame.draw.polygon(layer,(255,155,25),[(mouth[0]+6,mouth[1]),(flame_end-24,cy-132),(flame_end-10,cy-108),(flame_end-20,cy-88),(mouth[0]+10,cy-99)])
        pygame.draw.polygon(layer,(255,245,100),[(mouth[0]+13,mouth[1]),(flame_end-48,cy-121),(flame_end-35,cy-108),(mouth[0]+15,cy-102)])
    elif name=="MONKEY":
        # Ultra-detailed jungle titan matching the Robot and Grim Reaper quality.
        rage=int(12*pulse)
        # Jungle energy aura, leaves and dust.
        pygame.draw.circle(layer,(45,210,80,35),(cx,cy),128+int(7*pulse))
        for leaf in range(18):
            angle=now/850.0+leaf*math.tau/18
            radius=90+(leaf%4)*16
            lx=cx+int(math.cos(angle)*radius); ly=cy+int(math.sin(angle)*radius*0.75)
            pygame.draw.ellipse(layer,(35+leaf%3*25,145+leaf%4*20,45,180),(lx-5,ly-9,10,18))
        # Massive legs and planted feet.
        for side in (-1,1):
            leg_x=cx+side*46
            pygame.draw.line(layer,(48,34,24),(leg_x,cy+65),(leg_x+side*20,cy+132),44)
            pygame.draw.line(layer,(105,70,40),(leg_x,cy+65),(leg_x+side*20,cy+132),25)
            pygame.draw.ellipse(layer,(55,40,28),(leg_x+side*20-47,cy+120,94,34))
            for toe in range(4):
                tx=leg_x+side*20-30+toe*20
                pygame.draw.ellipse(layer,(35,28,23),(tx,cy+141,22,12))
        # Broad muscular torso with layered fur.
        pygame.draw.ellipse(layer,(48,34,24),(70,73,220,185))
        pygame.draw.ellipse(layer,(105,70,40),(94,88,172,155))
        pygame.draw.ellipse(layer,(150,102,60),(118,105,124,127))
        for row in range(6):
            for column in range(7):
                fx=105+column*24+(row%2)*8; fy=90+row*25
                pygame.draw.arc(layer,(65,44,29),(fx,fy,24,27),0.2,2.9,3)
        # Stone-vine chest armour and glowing jungle core.
        chest=[(cx-70,cy-62),(cx-30,cy-88),(cx,cy-72),(cx+30,cy-88),(cx+70,cy-62),(cx+53,cy+25),(cx,cy+50),(cx-55,cy+25)]
        pygame.draw.polygon(layer,(72,88,62),chest); pygame.draw.lines(layer,(135,150,98),True,chest,5)
        pygame.draw.circle(layer,(18,48,28),(cx,cy-8),35); pygame.draw.circle(layer,(55,235,95),(cx,cy-8),24+int(3*pulse)); pygame.draw.circle(layer,(220,255,190),(cx,cy-8),8)
        # Huge shoulders and long muscular arms.
        for side in (-1,1):
            shoulder_x=cx+side*98
            pygame.draw.circle(layer,(55,38,26),(shoulder_x,cy-42),52)
            pygame.draw.circle(layer,(114,75,42),(shoulder_x,cy-42),40)
            elbow_x=cx+side*132
            pygame.draw.line(layer,(48,34,24),(shoulder_x,cy-18),(elbow_x,cy+65),48)
            pygame.draw.line(layer,(108,72,42),(shoulder_x,cy-18),(elbow_x,cy+65),29)
            # Stone gauntlets and glowing fists.
            fist_x=cx+side*148; fist_y=cy+103
            pygame.draw.circle(layer,(62,78,62),(fist_x,fist_y),43+rage//5)
            pygame.draw.circle(layer,(95,118,80),(fist_x,fist_y),34)
            pygame.draw.circle(layer,(60,235,100,110),(fist_x,fist_y),49+int(4*pulse),5)
            for knuckle in range(4):
                kx=fist_x+side*(-20+knuckle*13)
                pygame.draw.circle(layer,(145,155,110),(kx,fist_y-17),9)
            pygame.draw.line(layer,(65,225,95),(shoulder_x-15*side,cy-42),(fist_x,fist_y),4)
        # Detailed gorilla head, brow, ears, muzzle and fangs.
        pygame.draw.circle(layer,(48,34,24),(cx,cy-110),78)
        pygame.draw.circle(layer,(48,34,24),(cx-66,cy-104),25); pygame.draw.circle(layer,(48,34,24),(cx+66,cy-104),25)
        pygame.draw.ellipse(layer,(126,84,50),(cx-51,cy-145,102,103))
        pygame.draw.polygon(layer,(62,43,30),[(cx-58,cy-135),(cx-18,cy-155),(cx,cy-142),(cx+18,cy-155),(cx+58,cy-135),(cx+38,cy-112),(cx-38,cy-112)])
        pygame.draw.ellipse(layer,(20,22,18),(cx-38,cy-127,27,23)); pygame.draw.ellipse(layer,(20,22,18),(cx+11,cy-127,27,23))
        pygame.draw.circle(layer,(55,245,105),(cx-24,cy-117),7); pygame.draw.circle(layer,(55,245,105),(cx+24,cy-117),7)
        pygame.draw.circle(layer,WHITE,(cx-22,cy-119),2); pygame.draw.circle(layer,WHITE,(cx+26,cy-119),2)
        pygame.draw.ellipse(layer,(185,128,78),(cx-45,cy-100,90,68))
        pygame.draw.ellipse(layer,(35,28,23),(cx-10,cy-87,20,13))
        pygame.draw.arc(layer,(35,25,20),(cx-31,cy-72,62,36),0.15,3.0,6)
        # Crown of jungle stone with vines and glowing gem.
        crown=[(cx-65,cy-158),(cx-43,cy-205),(cx-18,cy-168),(cx,cy-218),(cx+22,cy-170),(cx+48,cy-204),(cx+67,cy-158)]
        pygame.draw.polygon(layer,(80,95,65),crown); pygame.draw.lines(layer,(145,160,105),False,crown,5)
        pygame.draw.circle(layer,(65,235,100),(cx,cy-179),10+int(2*pulse))
        pygame.draw.arc(layer,(35,155,55),(cx-90,cy-185,180,90),0.2,2.9,5)
    elif name=="SNOW":
        # Ultra-detailed frost titan matching the Robot, Reaper and Monkey quality.
        frost_pulse=int(10*pulse)
        # Blizzard aura, drifting snow and icy mist.
        pygame.draw.circle(layer,(90,210,255,35),(cx,cy),130+int(7*pulse))
        for flake in range(45):
            fx=(flake*71+now//8)%350; fy=(flake*43+now//11)%310
            pygame.draw.circle(layer,(245,253,255,205),(fx,fy),1+flake%3)
        for mist in range(6):
            mx=35+mist*58; my=245+int(math.sin(now/330.0+mist)*9)
            pygame.draw.ellipse(layer,(190,235,255,45),(mx,my,95,30))
        # Heavy ice legs and crystal-plated feet.
        for side in (-1,1):
            leg_x=cx+side*48
            pygame.draw.rect(layer,(105,175,210),(leg_x-25,cy+55,50,90),border_radius=14)
            pygame.draw.polygon(layer,(170,225,245),[(leg_x-31,cy+62),(leg_x+31,cy+62),(leg_x+20,cy+118),(leg_x-20,cy+118)])
            pygame.draw.polygon(layer,(215,245,255),[(leg_x-45,cy+135),(leg_x+38,cy+135),(leg_x+52,cy+158),(leg_x-55,cy+158)])
            pygame.draw.line(layer,(70,205,255),(leg_x-26,cy+142),(leg_x+35,cy+142),4)
        # Broad frozen torso with layered translucent armour.
        pygame.draw.ellipse(layer,(115,190,220),(70,65,220,190))
        pygame.draw.ellipse(layer,(185,230,245),(94,75,172,165))
        chest=[(cx-72,cy-65),(cx-28,cy-91),(cx,cy-76),(cx+30,cy-91),(cx+72,cy-65),(cx+56,cy+32),(cx,cy+57),(cx-57,cy+32)]
        pygame.draw.polygon(layer,(125,210,240),chest); pygame.draw.lines(layer,(225,250,255),True,chest,5)
        pygame.draw.circle(layer,(35,120,205),(cx,cy-8),38); pygame.draw.circle(layer,(95,230,255),(cx,cy-8),26+int(3*pulse)); pygame.draw.circle(layer,WHITE,(cx,cy-8),9)
        # Crystal shoulders and massive ice arms.
        for side in (-1,1):
            shoulder_x=cx+side*102
            shoulder=[(shoulder_x-side*45,cy-70),(shoulder_x,cy-112),(shoulder_x+side*45,cy-70),(shoulder_x+side*34,cy-15),(shoulder_x-side*25,cy-18)]
            pygame.draw.polygon(layer,(105,205,240),shoulder); pygame.draw.lines(layer,(225,250,255),True,shoulder,5)
            elbow_x=cx+side*135
            pygame.draw.line(layer,(85,165,210),(shoulder_x,cy-15),(elbow_x,cy+68),48)
            pygame.draw.line(layer,(175,225,245),(shoulder_x,cy-15),(elbow_x,cy+68),27)
            fist_x=cx+side*151; fist_y=cy+108
            pygame.draw.circle(layer,(165,225,245),(fist_x,fist_y),42+frost_pulse//5)
            pygame.draw.circle(layer,(80,205,250,125),(fist_x,fist_y),50+int(3*pulse),5)
            for knuckle in range(4):
                kx=fist_x+side*(-20+knuckle*13)
                pygame.draw.polygon(layer,(235,252,255),[(kx-7,fist_y-13),(kx,fist_y-28),(kx+7,fist_y-13)])
        # Frost titan head, frozen beard, glowing eyes and ice crown.
        pygame.draw.circle(layer,(125,195,225),(cx,cy-112),76)
        pygame.draw.ellipse(layer,(205,240,250),(cx-52,cy-148,104,105))
        pygame.draw.polygon(layer,(105,165,205),[(cx-55,cy-136),(cx-20,cy-158),(cx,cy-145),(cx+20,cy-158),(cx+55,cy-136),(cx+38,cy-112),(cx-38,cy-112)])
        pygame.draw.ellipse(layer,(25,70,120),(cx-39,cy-130,29,28)); pygame.draw.ellipse(layer,(25,70,120),(cx+10,cy-130,29,28))
        pygame.draw.circle(layer,(105,235,255),(cx-24,cy-116),8); pygame.draw.circle(layer,(105,235,255),(cx+24,cy-116),8)
        pygame.draw.circle(layer,WHITE,(cx-22,cy-118),3); pygame.draw.circle(layer,WHITE,(cx+26,cy-118),3)
        pygame.draw.polygon(layer,(230,248,255),[(cx-42,cy-78),(cx-25,cy-34),(cx-8,cy-68),(cx+8,cy-30),(cx+25,cy-68),(cx+42,cy-78)])
        crown=[(cx-70,cy-156),(cx-52,cy-216),(cx-24,cy-166),(cx,cy-230),(cx+26,cy-166),(cx+55,cy-216),(cx+72,cy-156)]
        pygame.draw.polygon(layer,(115,215,250),crown); pygame.draw.lines(layer,(235,253,255),False,crown,5)
        pygame.draw.circle(layer,(125,240,255),(cx,cy-187),11+int(2*pulse))
        # Orbiting ice crystals and frost runes.
        for crystal in range(10):
            angle=now/700.0+crystal*math.tau/10
            radius=112+crystal%2*20
            ix=cx+int(math.cos(angle)*radius); iy=cy+int(math.sin(angle)*radius*0.75)
            pygame.draw.polygon(layer,(180,240,255),[(ix,iy-10),(ix+7,iy),(ix,iy+10),(ix-7,iy)])
            pygame.draw.circle(layer,(80,220,255,100),(ix,iy),15,2)
    else:
        # Ultra-detailed alien warlord and biomechanical UFO.
        alien_pulse=int(9*pulse)
        # Tractor-beam aura, stars and floating alien particles.
        pygame.draw.ellipse(layer,(55,220,255,28),(35,205,290,92))
        pygame.draw.polygon(layer,(65,225,255,28),[(cx-95,cy+40),(cx+95,cy+40),(cx+145,cy+145),(cx-145,cy+145)])
        for particle in range(18):
            angle=now/650.0+particle*math.tau/18
            radius=85+(particle%4)*18
            px=cx+int(math.cos(angle)*radius); py=cy+20+int(math.sin(angle)*radius*0.55)
            pygame.draw.circle(layer,(90,255,170,190),(px,py),2+particle%3)
        # Large transparent command dome.
        dome=pygame.Surface((210,155),pygame.SRCALPHA)
        pygame.draw.ellipse(dome,(75,205,245,60),(10,5,190,140))
        pygame.draw.ellipse(dome,(165,240,255,150),(10,5,190,140),5)
        pygame.draw.arc(dome,(230,255,255,185),(30,18,145,90),3.4,5.7,5)
        layer.blit(dome,(cx-105,cy-165))
        # Realistic humanoid alien body inside the dome.
        pygame.draw.ellipse(layer,(78,175,96),(cx-42,cy-139,84,118))
        pygame.draw.ellipse(layer,(122,228,140),(cx-31,cy-124,62,92))
        pygame.draw.line(layer,(75,168,95),(cx-28,cy-45),(cx-55,cy+15),14)
        pygame.draw.line(layer,(75,168,95),(cx+28,cy-45),(cx+55,cy+15),14)
        pygame.draw.circle(layer,(112,215,128),(cx-57,cy+18),10); pygame.draw.circle(layer,(112,215,128),(cx+57,cy+18),10)
        # Enlarged alien head with textured cranium and facial detail.
        pygame.draw.ellipse(layer,(70,165,90),(cx-55,cy-188,110,102))
        pygame.draw.ellipse(layer,(124,225,140),(cx-43,cy-172,86,76))
        for vein in range(6):
            vx=cx-30+vein*12
            pygame.draw.arc(layer,(55,130,82),(vx,cy-177,25,50),1.4,4.7,2)
        pygame.draw.ellipse(layer,(8,16,22),(cx-39,cy-148,31,52)); pygame.draw.ellipse(layer,(8,16,22),(cx+8,cy-148,31,52))
        pygame.draw.ellipse(layer,(180,255,205),(cx-27,cy-134,11,24)); pygame.draw.ellipse(layer,(180,255,205),(cx+16,cy-134,11,24))
        pygame.draw.circle(layer,(255,255,255),(cx-22,cy-138),3); pygame.draw.circle(layer,(255,255,255),(cx+21,cy-138),3)
        pygame.draw.polygon(layer,(45,105,63),[(cx,cy-119),(cx-7,cy-100),(cx+7,cy-100)])
        pygame.draw.arc(layer,(35,80,48),(cx-22,cy-106,44,28),0.2,2.9,3)
        # Biomechanical UFO hull with layered armour.
        pygame.draw.ellipse(layer,(55,65,95),(25,130,310,105))
        pygame.draw.ellipse(layer,(130,150,185),(45,142,270,76))
        pygame.draw.ellipse(layer,(38,48,80),(76,160,208,58))
        pygame.draw.ellipse(layer,(60,225,255),(100,174,160,34))
        pygame.draw.ellipse(layer,(205,255,255),(125,182,110,17))
        # Hull panels, vents and damage scratches.
        for panel in range(8):
            angle=panel*math.tau/8
            hx=cx+int(math.cos(angle)*112); hy=cy+40+int(math.sin(angle)*25)
            pygame.draw.circle(layer,(175,195,220),(hx,hy),11)
            pygame.draw.circle(layer,(75,255,170),(hx,hy),6+panel%2*2)
        for scratch in range(5):
            sx=95+scratch*42
            pygame.draw.line(layer,(225,235,245),(sx,cy+68),(sx+20,cy+57),2)
        # Three visible plasma cannons corresponding to the three-shot attack.
        for cannon_index,cannon_y in enumerate((cy+26,cy+50,cy+74)):
            cannon_x=cx-130
            pygame.draw.rect(layer,(45,55,85),(cannon_x-50,cannon_y-7,63,14),border_radius=6)
            pygame.draw.rect(layer,(125,145,180),(cannon_x-28,cannon_y-4,40,8),border_radius=4)
            pygame.draw.circle(layer,(85,255,175),(cannon_x-51,cannon_y),10+int(2*pulse))
            pygame.draw.circle(layer,WHITE,(cannon_x-51,cannon_y),4)
        # Under-hull tentacles, articulated like mechanical landing appendages.
        for tentacle_index,tx in enumerate((cx-90,cx-42,cx+42,cx+90)):
            sway=int(math.sin(now/230.0+tentacle_index)*10)
            points=[(tx,cy+75),(tx+sway,cy+105),(tx-sway,cy+135),(tx+sway//2,cy+158)]
            pygame.draw.lines(layer,(70,195,135),False,points,10)
            pygame.draw.lines(layer,(145,255,190),False,points,3)
            pygame.draw.circle(layer,(80,255,170),points[-1],7)
        # Rotating energy ring under the craft.
        for ring_light in range(10):
            angle=now/300.0+ring_light*math.tau/10
            rx=cx+int(math.cos(angle)*105); ry=cy+86+int(math.sin(angle)*18)
            pygame.draw.circle(layer,(90,235,255),(rx,ry),5+ring_light%2)
        # Side shields and alien glyphs.
        for side in (-1,1):
            shield_x=cx+side*142
            pygame.draw.arc(layer,(95,255,170),(shield_x-32,cy-2,64,120),1.2 if side<0 else -1.9,5.0 if side<0 else 1.9,5)
        for glyph in range(5):
            gx=cx-45+glyph*23
            pygame.draw.line(layer,(80,255,170),(gx,cy+43),(gx+9,cy+54),3)
            pygame.draw.circle(layer,(80,255,170),(gx+10,cy+55),3)
    if name == "DRAGON":
        layer = pygame.transform.flip(layer, True, False)
    screen.blit(layer,(int(x)-180,int(y)-180))


def start_arena_boss_death(name, x, y):
    global arena_death_start, arena_death_particles
    arena_death_start=pygame.time.get_ticks(); arena_death_particles=[]
    palettes={
        "ROBOT":((70,220,255),(145,165,190),(255,100,35)),
        "GHOST":((180,70,255),(240,235,215),(255,25,45)),
        "DRAGON":((255,70,20),(255,190,45),(110,20,20)),
        "MONKEY":((70,230,100),(110,75,42),(145,160,105)),
        "SNOW":((130,235,255),(235,252,255),(65,145,225)),
        "ALIEN":((80,255,160),(100,220,255),(165,120,255)),
        "SHADOW TARUN":((160,70,255),(255,215,70),(25,10,45)),
    }
    colours=palettes[name]
    for index in range(95):
        angle=random.uniform(0,math.tau); speed=random.uniform(2.0,8.0)
        arena_death_particles.append({"x":float(x+random.randint(-70,70)),"y":float(y+random.randint(-100,80)),"vx":math.cos(angle)*speed,"vy":math.sin(angle)*speed-random.uniform(0,3),"life":random.randint(55,110),"size":random.randint(3,9),"colour":random.choice(colours),"kind":"spark"})
    # Larger identifiable fragments make each defeat feel physical.
    for index in range(18):
        arena_death_particles.append({"x":float(x+random.randint(-75,75)),"y":float(y+random.randint(-90,60)),"vx":random.uniform(-5,5),"vy":random.uniform(-8,-2),"life":random.randint(75,135),"size":random.randint(8,18),"colour":random.choice(colours),"kind":"chunk"})

def draw_arena_boss_death(name,x,y):
    if arena_death_start==0: return False
    elapsed=pygame.time.get_ticks()-arena_death_start
    # Expanding shockwave and bright impact flash.
    shock=min(150,int(elapsed/5))
    death_layer=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
    if elapsed<650:
        alpha=max(0,150-int(elapsed/5))
        pygame.draw.circle(death_layer,(255,245,210,alpha),(int(x),int(y)),shock,5)
        pygame.draw.circle(death_layer,(255,255,255,max(0,100-int(elapsed/7))),(int(x),int(y)),max(5,70-int(elapsed/12)))
    # Boss-specific final collapse visuals.
    if name=="GHOST" and elapsed<1500:
        for soul in range(12):
            angle=elapsed/500+soul*math.tau/12; sx=x+math.cos(angle)*(30+elapsed/15); sy=y-40+math.sin(angle)*30-elapsed/8
            pygame.draw.circle(death_layer,(190,80,255,max(0,180-elapsed//9)),(int(sx),int(sy)),8)
    elif name=="ROBOT" and elapsed<1200:
        for bolt in range(8):
            bx=x+random.randint(-95,95); by=y+random.randint(-100,80)
            pygame.draw.line(death_layer,(80,230,255,180),(int(x),int(y)),(int(bx),int(by)),3)
    elif name=="DRAGON" and elapsed<1200:
        pygame.draw.circle(death_layer,(255,80,20,max(0,130-elapsed//10)),(int(x),int(y)),max(10,100-elapsed//10))
    elif name=="SNOW" and elapsed<1500:
        for shard in range(16):
            angle=shard*math.tau/16; radius=elapsed/8
            px=x+math.cos(angle)*radius; py=y+math.sin(angle)*radius
            pygame.draw.polygon(death_layer,(210,250,255,190),[(px,py-10),(px+7,py),(px,py+10),(px-7,py)])
    elif name=="ALIEN" and elapsed<1400:
        pygame.draw.ellipse(death_layer,(75,230,255,max(0,135-elapsed//11)),(int(x-140-elapsed/8),int(y-45),int(280+elapsed/4),90),5)
    elif name=="MONKEY" and elapsed<1200:
        pygame.draw.circle(death_layer,(65,230,95,max(0,120-elapsed//10)),(int(x),int(y)),max(10,95-elapsed//12),6)
    screen.blit(death_layer,(0,0))
    for particle in arena_death_particles[:]:
        particle["x"]+=particle["vx"]; particle["y"]+=particle["vy"]; particle["vy"]+=0.20; particle["life"]-=1
        fade=max(0,min(255,particle["life"]*3)); colour=(*particle["colour"],fade)
        item=pygame.Surface((particle["size"]*4,particle["size"]*4),pygame.SRCALPHA); center=particle["size"]*2
        if particle["kind"]=="chunk":
            pygame.draw.polygon(item,colour,[(center,0),(center*2,center),(center,center*2),(0,center)])
        else: pygame.draw.circle(item,colour,(center,center),particle["size"])
        screen.blit(item,(particle["x"]-center,particle["y"]-center))
        if particle["life"]<=0 or particle["y"]>SCREEN_HEIGHT+50: arena_death_particles.remove(particle)
    return elapsed<2200

def draw_shadow_tarun(x,y,large=False):
    now=pygame.time.get_ticks(); scale=1.35 if large else 1.0
    layer=pygame.Surface((420,390),pygame.SRCALPHA); cx,cy=210,205; pulse=0.5+0.5*math.sin(now/150.0)
    for radius,alpha in ((155,12),(125,20),(92,35),(65,55)):
        pygame.draw.circle(layer,(130,45,255,alpha),(cx,cy),int(radius+8*pulse))
    pygame.draw.arc(layer,(255,205,55,160),(cx-145,cy-145,290,290),now/700%math.tau,now/700%math.tau+4.7,5)
    pygame.draw.arc(layer,(90,220,255,140),(cx-118,cy-118,236,236),-now/550%math.tau,-now/550%math.tau+4.5,4)
    cape=[(cx-72,cy-90),(cx-125,cy-20),(cx-145,cy+120),(cx-88,cy+92),(cx-55,cy+145),(cx-18,cy+112),(cx+15,cy+150),(cx+52,cy+110),(cx+92,cy+145),(cx+135,cy+92),(cx+122,cy-18),(cx+70,cy-90)]
    pygame.draw.polygon(layer,(7,4,15),cape); pygame.draw.lines(layer,(100,40,180),True,cape,5)
    inner=[(cx-60,cy-70),(cx-92,cy-5),(cx-88,cy+85),(cx-45,cy+62),(cx,cy+112),(cx+45,cy+62),(cx+88,cy+85),(cx+92,cy-5),(cx+60,cy-70)]
    pygame.draw.polygon(layer,(35,12,62),inner)
    torso=[(cx-65,cy-72),(cx-30,cy-102),(cx,cy-87),(cx+30,cy-102),(cx+65,cy-72),(cx+54,cy+35),(cx,cy+68),(cx-54,cy+35)]
    pygame.draw.polygon(layer,(18,22,35),torso); pygame.draw.lines(layer,(255,205,55),True,torso,5)
    pygame.draw.polygon(layer,(78,32,130),[(cx-45,cy-58),(cx-8,cy-75),(cx-5,cy+18),(cx-38,cy+28)])
    pygame.draw.polygon(layer,(78,32,130),[(cx+45,cy-58),(cx+8,cy-75),(cx+5,cy+18),(cx+38,cy+28)])
    pygame.draw.circle(layer,(20,10,38),(cx,cy-18),38); pygame.draw.circle(layer,(165,65,255),(cx,cy-18),27+int(3*pulse)); pygame.draw.circle(layer,(255,225,90),(cx,cy-18),9)
    # Armoured legs and floating boots.
    for side in (-1,1):
        lx=cx+side*38
        pygame.draw.polygon(layer,(22,25,40),[(lx-20,cy+48),(lx+20,cy+48),(lx+24,cy+112),(lx-18,cy+112)])
        pygame.draw.lines(layer,(255,205,55),True,[(lx-20,cy+48),(lx+20,cy+48),(lx+24,cy+112),(lx-18,cy+112)],4)
        pygame.draw.circle(layer,(145,60,255),(lx,cy+114),13)
        pygame.draw.polygon(layer,(25,28,45),[(lx-24,cy+122),(lx+27,cy+122),(lx+42,cy+145),(lx-35,cy+145)])
        pygame.draw.line(layer,(90,220,255),(lx-26,cy+140),(lx+30,cy+140),4)
    # Shoulder armour and spectral arms.
    for side in (-1,1):
        sx=cx+side*84
        pygame.draw.polygon(layer,(25,28,44),[(sx-side*38,cy-78),(sx,cy-104),(sx+side*38,cy-70),(sx+side*28,cy-15),(sx-side*24,cy-20)])
        pygame.draw.lines(layer,(255,205,55),True,[(sx-side*38,cy-78),(sx,cy-104),(sx+side*38,cy-70),(sx+side*28,cy-15),(sx-side*24,cy-20)],4)
        ex=cx+side*140; ey=cy+42
        pygame.draw.line(layer,(50,20,85),(sx,cy-18),(ex,ey),30); pygame.draw.line(layer,(145,65,230),(sx,cy-18),(ex,ey),12)
        pygame.draw.circle(layer,(205,175,255),(ex,ey),15)
        for finger in range(4): pygame.draw.line(layer,(225,205,255),(ex,ey),(ex+side*(18+finger*3),ey-12+finger*8),3)
    # Hooded creator mask and glowing eyes.
    pygame.draw.polygon(layer,(2,2,8),[(cx-63,cy-112),(cx-54,cy-188),(cx-18,cy-218),(cx+42,cy-212),(cx+67,cy-168),(cx+60,cy-98)])
    pygame.draw.polygon(layer,(76,65,88),[(cx-39,cy-174),(cx-22,cy-196),(cx+24,cy-194),(cx+42,cy-168),(cx+33,cy-110),(cx-34,cy-110)])
    pygame.draw.ellipse(layer,(12,8,18),(cx-29,cy-158,23,22)); pygame.draw.ellipse(layer,(12,8,18),(cx+7,cy-158,23,22))
    pygame.draw.circle(layer,(255,55,70),(cx-18,cy-147),6); pygame.draw.circle(layer,(255,55,70),(cx+18,cy-147),6)
    # Golden creator crown.
    crown=[(cx-58,cy-196),(cx-49,cy-244),(cx-23,cy-211),(cx,cy-260),(cx+26,cy-211),(cx+52,cy-244),(cx+61,cy-196)]
    pygame.draw.polygon(layer,(255,205,45),crown); pygame.draw.lines(layer,(255,245,150),False,crown,5)
    for gx,gc in ((cx-35,(255,65,85)),(cx,(70,225,255)),(cx+36,(165,85,255))): pygame.draw.circle(layer,gc,(gx,cy-207),7)
    # Energy sword and plasma cannon.
    pygame.draw.line(layer,(45,20,75),(cx-142,cy+44),(cx-190,cy-74),12); pygame.draw.line(layer,(185,90,255),(cx-185,cy-64),(cx-210,cy-145),16); pygame.draw.line(layer,(240,220,255),(cx-185,cy-64),(cx-210,cy-145),5)
    pygame.draw.rect(layer,(28,32,52),(cx+132,cy+18,90,32),border_radius=10); pygame.draw.circle(layer,(255,205,55),(cx+222,cy+34),15+int(3*pulse)); pygame.draw.circle(layer,WHITE,(cx+222,cy+34),6)
    for orb in range(12):
        angle=now/430.0+orb*math.tau/12; radius=135+(orb%3)*15
        ox=cx+int(math.cos(angle)*radius); oy=cy+int(math.sin(angle)*radius*0.68); colour=(160,65,255) if orb%2==0 else (255,210,60)
        pygame.draw.circle(layer,colour,(ox,oy),6); pygame.draw.line(layer,(*colour[:3],150),(ox-9,oy),(ox+9,oy),2); pygame.draw.line(layer,(*colour[:3],150),(ox,oy-9),(ox,oy+9),2)
    if scale!=1.0: layer=pygame.transform.smoothscale(layer,(int(layer.get_width()*scale),int(layer.get_height()*scale)))
    screen.blit(layer,(x-layer.get_width()//2,y-layer.get_height()//2))


def unlocked_boss_companions():
    counts=player_progress.get("boss_win_counts",{})
    return [companion for boss,companion in BOSS_COMPANIONS.items() if int(counts.get(boss,0))>=10]

def draw_boss_companion(name,x,y):
    x=int(x); y=int(y); now=pygame.time.get_ticks(); bob=int(math.sin(now/170.0)*4)
    pygame.draw.ellipse(screen,(0,0,0,70),(x-25,y+22,50,10))
    colours={"MINI ROBOT":(100,145,180),"MINI REAPER":(35,20,55),"MINI DRAGON":(205,55,25),"MINI MONKEY":(105,70,40),"MINI SNOW TITAN":(180,235,250),"MINI ALIEN":(100,210,125),"MINI SHADOW TARUN":(70,30,110)}
    colour=colours.get(name,(110,180,220)); pygame.draw.circle(screen,colour,(x,y+bob),22); pygame.draw.circle(screen,colour,(x,y-18+bob),15)
    eye=(255,60,70) if name in ("MINI ROBOT","MINI REAPER","MINI SHADOW TARUN") else (80,235,255)
    pygame.draw.circle(screen,eye,(x-6,y-20+bob),3); pygame.draw.circle(screen,eye,(x+6,y-20+bob),3)
    if name=="MINI DRAGON":
        pygame.draw.polygon(screen,(130,30,25),[(x-13,y),(x-38,y-22),(x-25,y+12)]); pygame.draw.polygon(screen,(130,30,25),[(x+13,y),(x+38,y-22),(x+25,y+12)])
    elif name=="MINI REAPER": pygame.draw.line(screen,(210,215,225),(x+18,y),(x+35,y-28),4); pygame.draw.arc(screen,(230,235,245),(x+20,y-38,30,22),2.6,5.8,4)
    elif name=="MINI ROBOT": pygame.draw.circle(screen,(65,235,255),(x,y+5+bob),7)
    elif name=="MINI SNOW TITAN": pygame.draw.polygon(screen,(125,215,250),[(x-12,y-30),(x,y-48),(x+12,y-30)])
    elif name=="MINI ALIEN": pygame.draw.ellipse(screen,(105,120,155),(x-28,y+10,56,18))
    elif name=="MINI SHADOW TARUN": pygame.draw.polygon(screen,GOLD,[(x-12,y-30),(x-8,y-45),(x,y-35),(x+8,y-45),(x+12,y-30)])

def draw_arena_destruction(name,level,final_form,now):
    if level<=0: return
    overlay=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
    intensity=min(4,level+(2 if final_form else 0))
    if name=="ROBOT":
        for i in range(intensity*3):
            x=520+i*45; pygame.draw.rect(overlay,(35,45,60,220),(x,315,28,125)); pygame.draw.line(overlay,(255,80,60,220),(x,315),(x+25,380),4)
            pygame.draw.circle(overlay,(75,225,255,180),(x+12,335),5)
    elif name=="GHOST":
        for i in range(intensity*5):
            x=470+i*34; pygame.draw.line(overlay,(120,70,130,210),(x,80),(x-20+(i%3)*18,260),3)
            if i%2==0: pygame.draw.circle(overlay,(255,35,45,180),(x,170),4)
    elif name=="DRAGON":
        lava_height=15+intensity*12; pygame.draw.rect(overlay,(255,70,15,190),(0,SCREEN_HEIGHT-lava_height,SCREEN_WIDTH,lava_height))
        for i in range(intensity*4): pygame.draw.circle(overlay,(255,180,30,210),(500+i*70,(now//7+i*53)%330),5+i%4)
    elif name=="MONKEY":
        for i in range(intensity*3):
            x=500+i*80; pygame.draw.line(overlay,(80,50,25,230),(x,220),(x-35,440),18); pygame.draw.circle(overlay,(35,135,45,220),(x-10,210),30)
    elif name=="SNOW":
        for i in range(intensity*5):
            x=460+i*42; h=35+(i%3)*22; pygame.draw.polygon(overlay,(190,245,255,210),[(x,440),(x+18,440),(x+9,440-h)])
    elif name=="ALIEN":
        for i in range(intensity*3):
            x=480+i*80; pygame.draw.ellipse(overlay,(75,230,255,170),(x,120+(i%2)*80,100,32),4); pygame.draw.line(overlay,(140,75,255,180),(x+50,145),(x+20,360),3)
    else:
        for i in range(intensity*5):
            x=440+i*45; pygame.draw.line(overlay,(160,65,255,190),(x,60),(x+random.randint(-40,40),420),5)
    screen.blit(overlay,(0,0))

def draw_pet_ultimate_effect(name,x,y,boss_x,boss_y,progress):
    layer=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
    if name in SECRET_EGG_PETS:
        radius=int(40+progress*220); pygame.draw.circle(layer,(180,75,255,max(0,220-int(progress*150))),(int(boss_x),int(boss_y)),radius,8)
        for i in range(12):
            angle=progress*8+i*math.tau/12; px=boss_x+math.cos(angle)*radius; py=boss_y+math.sin(angle)*radius*.55; pygame.draw.circle(layer,(255,220,80),(int(px),int(py)),8)
    elif name in ("VULTURE","EAGLE","OWL","SKY HOUND","COSMIC EAGLE"):
        for i in range(8): pygame.draw.line(layer,(90,220,255,220),(int(boss_x-120+i*30),0),(int(boss_x-80+i*22),int(boss_y+100)),6)
    elif name in ("TIGER","LION","CHEETAH",SECRET_PET,"NIGHT TIGER","ROBOT TIGER"):
        for i in range(5): pygame.draw.arc(layer,(255,190,60,220),(int(boss_x-100+i*18),int(boss_y-90+i*12),180,150),0.2,2.8,8)
    elif "ICE" in name or name in ("COW","BUFFALO","ICE BULL"):
        for i in range(10): pygame.draw.polygon(layer,(190,245,255,210),[(boss_x-120+i*25,boss_y+90),(boss_x-106+i*25,boss_y+90),(boss_x-113+i*25,boss_y-50-(i%3)*25)])
    else:
        pygame.draw.line(layer,(100,255,160,230),(int(x),int(y)),(int(boss_x),int(boss_y)),18); pygame.draw.circle(layer,WHITE,(int(boss_x),int(boss_y)),35)
    screen.blit(layer,(0,0))

def selectable_bosses():
    return list(BOSS_TYPES)+[SHADOW_TARUN]

def start_selected_boss():
    global arena_boss,arena_health,arena_player_health,arena_shots,arena_enemy_shots,arena_next_attack,arena_message,arena_reward_given
    global arena_dino_y,arena_dino_velocity,arena_is_jumping
    global arena_intro_start,arena_attack_animation_start,arena_attack_kind
    global pet_next_attack,pet_attack_projectiles,pet_attack_message_until,boss_final_form
    global companion_next_attack,companion_projectiles
    global pet_attack_count,pet_ultimate_ready,arena_destruction_level,arena_debris
    global arena_death_start,arena_death_particles,arena_combo,arena_finisher_ready,arena_power_used
    global boss_power_message,boss_power_message_until
    arena_boss=dict(selectable_bosses()[boss_select_index])
    arena_boss["health"]=int(arena_boss["health"]*BOSS_DIFFICULTIES[boss_difficulty]["health"])
    arena_boss["reward"]=int(round(arena_boss["reward"]*BOSS_DIFFICULTIES[boss_difficulty]["reward"]))
    arena_health=arena_boss["health"]; arena_player_health=10
    arena_shots=[]; arena_enemy_shots=[]; arena_next_attack=pygame.time.get_ticks()+1200; arena_message=""; arena_reward_given=False
    arena_dino_y=390.0; arena_dino_velocity=0.0; arena_is_jumping=False
    arena_intro_start=pygame.time.get_ticks(); arena_attack_animation_start=0; arena_attack_kind=""
    pet_next_attack=pygame.time.get_ticks()+10000
    pet_attack_projectiles=[]
    companion_next_attack=pygame.time.get_ticks()+20000
    companion_projectiles=[]
    pet_attack_message_until=0
    boss_final_form=False
    pet_attack_count=0; pet_ultimate_ready=False; arena_destruction_level=0; arena_debris=[]
    arena_death_start=0; arena_death_particles=[]
    arena_combo=0; arena_finisher_ready=False; arena_power_used=False
    boss_power_message=""; boss_power_message_until=0
    start_boss_music(arena_boss["name"])

def activate_account(account_name):
    global active_account, player_name, player_progress, selected_skin, selected_gun_skin
    active_account = account_name
    player_name = account_name
    player_progress = load_progress(account_name)
    player_progress["jump_upgrade"] = min(MAX_JUMP_LEVEL, int(player_progress.get("jump_upgrade", 0)))
    selected_skin = player_progress.get("selected_skin", "default")
    selected_gun_skin = player_progress.get("selected_gun_skin", "gun_default")

def refresh_achievements():
    unlocked=list(player_progress.get("achievements",[]))
    changed=False
    for title,description,rule in ACHIEVEMENT_RULES:
        if title not in unlocked and rule(player_progress):
            unlocked.append(title); changed=True
    if changed:
        player_progress["achievements"]=unlocked; save_progress()

def trophy_rank(count):
    if count>=25: return "DIAMOND",(110,235,255)
    if count>=10: return "GOLD",(255,215,60)
    if count>=5: return "SILVER",(205,215,225)
    if count>=1: return "BRONZE",(190,115,60)
    return "LOCKED",(70,75,85)

# Main Game Loop
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            FULLSCREEN_MODE = not FULLSCREEN_MODE
            display_flags = pygame.FULLSCREEN | pygame.SCALED if FULLSCREEN_MODE else 0
            screen = pygame.display.set_mode(
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                display_flags,
            )

        # Volume controls are active only on the main lobby screen.
        if current_state == GameState.LOBBY:
            handle_volume_event(event)

    if not running:
        break

    # Password-free account screen. Choose an existing account or create a new one.
    if current_state in (GameState.ACCOUNT_NAME, GameState.ACCOUNT_PASSWORD):
        current_state=GameState.ACCOUNT_NAME
        screen.fill((12,25,48))
        title=font_title.render("CHOOSE YOUR ACCOUNT",True,(220,245,255)); screen.blit(title,title.get_rect(center=(SCREEN_WIDTH//2,48)))
        help_text=font_sub.render("Each account keeps separate progress",True,(160,205,235)); screen.blit(help_text,help_text.get_rect(center=(SCREEN_WIDTH//2,82)))
        account_buttons=[]; saved_accounts=sorted(accounts.values(),key=lambda item:item.get("name","").lower())
        for index,account_data in enumerate(saved_accounts[:8]):
            col=index%4; row=index//4; bx=45+col*190; by=115+row*100; saved_name=account_data.get("name","Player")
            colour=(45+(index*31)%100,90+(index*23)%90,135+(index*17)%90)
            button=Button(bx,by,170,68,saved_name[:14],colour); button.draw(screen)
            pygame.draw.circle(screen,(235,245,255),(bx+24,by+22),9); pygame.draw.arc(screen,(235,245,255),(bx+13,by+29,22,18),3.2,6.2,3)
            account_buttons.append((button,saved_name))
        label=font_ui.render("CREATE A NEW ACCOUNT",True,(255,225,120)); screen.blit(label,label.get_rect(center=(SCREEN_WIDTH//2,330)))
        box=pygame.Rect(180,355,300,52); pygame.draw.rect(screen,WHITE,box,border_radius=9); pygame.draw.rect(screen,(70,210,255),box,2,border_radius=9)
        shown=account_name_input or "Type new account name"; screen.blit(font_ui.render(shown,True,BLACK if account_name_input else (130,130,140)),(box.x+12,box.y+14))
        create=Button(500,355,165,52,"CREATE",(50,155,95)); create.draw(screen)
        if account_message:
            msg=font_sub.render(account_message,True,RED); screen.blit(msg,msg.get_rect(center=(SCREEN_WIDTH//2,445)))
        for event in events:
            selected=""
            for button,saved_name in account_buttons:
                if button.is_clicked(mouse_pos,event): selected=saved_name; break
            if selected:
                activate_account(selected); account_name_input=""; account_message=""; current_state=GameState.LOBBY; break
            requested=False
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_BACKSPACE: account_name_input=account_name_input[:-1]
                elif event.key==pygame.K_RETURN: requested=True
                elif event.unicode.isprintable() and len(account_name_input)<15: account_name_input+=event.unicode
            elif create.is_clicked(mouse_pos,event): requested=True
            if requested:
                name=account_name_input.strip()
                if not name: account_message="Please enter an account name."
                elif name.lower() in accounts:
                    activate_account(accounts[name.lower()].get("name",name)); account_name_input=""; account_message=""; current_state=GameState.LOBBY
                else:
                    accounts[name.lower()]={"name":name}; save_accounts(); activate_account(name); account_name_input=""; account_message=""; current_state=GameState.LOBBY
                break

    # 1. Lobby State
    elif current_state == GameState.LOBBY:
        draw_lobby_background()

        # Keep the centered title below the top-right audio panel.
        title_y = 92
        title_shadow = font_title.render("Dinosaur Adventure", True, (20, 65, 45))
        screen.blit(
            title_shadow,
            (SCREEN_WIDTH // 2 - title_shadow.get_width() // 2 + 3, title_y + 3),
        )
        txt = font_title.render("Dinosaur Adventure", True, (255, 245, 170))
        screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, title_y))
        draw_dinosaur(SCREEN_WIDTH // 2 - 25, 190)
        account_badge = font_ui.render(f"Account: {active_account}", True, WHITE)
        screen.blit(account_badge, (20, 20))

        # Keep only START on the main page. Other features are inside ALL.
        btn_start = Button(SCREEN_WIDTH // 2 - 110, 330, 220, 58, "START", GREEN)
        btn_start.draw(screen)

        # Premium animated creator title with gold, cyan glow and a crown emblem.
        credit_time = pygame.time.get_ticks()
        credit_panel = pygame.Surface((255, 58), pygame.SRCALPHA)
        credit_panel.fill((5, 12, 28, 225))
        glow_strength = 120 + int(70 * (0.5 + 0.5 * math.sin(credit_time / 260.0)))
        for inset, alpha in ((0, glow_strength), (3, 150), (6, 80)):
            pygame.draw.rect(credit_panel, (45, 205, 255, alpha), (inset, inset, 255-inset*2, 58-inset*2), 2, border_radius=13)
        # Crown icon.
        crown_points=[(17,34),(20,17),(30,27),(39,13),(48,27),(57,17),(60,34)]
        pygame.draw.polygon(credit_panel, (255, 210, 55), crown_points)
        pygame.draw.line(credit_panel, (255, 245, 150), (18,35), (60,35), 4)
        for gem_x, gem_colour in ((25,(255,75,90)),(39,(80,225,255)),(53,(175,90,255))):
            pygame.draw.circle(credit_panel, gem_colour, (gem_x,31), 3)
        small_font = pygame.font.SysFont("Arial", 13, bold=True)
        name_font = pygame.font.SysFont("Arial", 24, bold=True)
        made_text = small_font.render("GAME CREATED BY", True, (145, 220, 255))
        name_shadow = name_font.render("TARUN", True, (90, 50, 10))
        name_text = name_font.render("TARUN", True, (255, 230, 95))
        credit_panel.blit(made_text, made_text.get_rect(center=(160,17)))
        credit_panel.blit(name_shadow, name_shadow.get_rect(center=(162,41)))
        credit_panel.blit(name_text, name_text.get_rect(center=(160,39)))
        # Animated star sparkles.
        for sparkle in range(5):
            sx = 75 + (sparkle * 41 + credit_time // 18) % 170
            sy = 8 + (sparkle * 17) % 42
            size = 1 + sparkle % 2
            pygame.draw.line(credit_panel, (255,255,210), (sx-size*2,sy), (sx+size*2,sy), 1)
            pygame.draw.line(credit_panel, (255,255,210), (sx,sy-size*2), (sx,sy+size*2), 1)
        screen.blit(credit_panel, (18, SCREEN_HEIGHT - 72))
        btn_all = Button(SCREEN_WIDTH - 138, SCREEN_HEIGHT - 68, 120, 48, "ALL", (55, 75, 125))
        btn_all.draw(screen)

        for event in events:
            if btn_all.is_clicked(mouse_pos, event):
                current_state = GameState.ALL_MENU
                break
            if btn_start.is_clicked(mouse_pos, event):
                cup_awarded_this_run = False
                current_state = GameState.LEVEL_SELECT
                break

    # Large ALL menu: every main feature except START.
    elif current_state == GameState.ALL_MENU:
        draw_lobby_background(); overlay=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); overlay.fill((4,8,20,215)); screen.blit(overlay,(0,0))
        panel=pygame.Rect(35,25,890,490); pygame.draw.rect(screen,(15,28,55),panel,border_radius=24); pygame.draw.rect(screen,(80,200,255),panel,4,border_radius=24)
        title=font_title.render("ALL FEATURES",True,(225,245,255)); screen.blit(title,title.get_rect(center=(480,68)))
        all_accounts=Button(45,105,190,48,"ACCOUNTS",(45,75,115)); all_collection=Button(250,105,190,48,"COLLECTION",(35,150,175)); all_skills=Button(455,105,190,48,"SKILLS",(125,65,190)); all_skins=Button(660,105,190,48,"SKINS",(45,105,200))
        all_mansion=Button(45,170,190,48,"DINO MANSION",(135,82,42)); all_bosses=Button(250,170,190,48,"ALL BOSSES",(180,55,55)); all_team=Button(455,170,190,48,"TEAM BATTLE",(160,65,95)); all_rush=Button(660,170,190,48,"BOSS RUSH",(180,80,35))
        all_workshop=Button(45,235,190,48,"WORKSHOP",(75,110,145)); all_fusion=Button(250,235,190,48,"PET FUSION",(65,145,105)); all_powers=Button(455,235,190,48,"BOSS POWERS",(65,95,190)); all_trophies=Button(660,235,190,48,"TROPHIES",(165,120,40))
        all_secret_egg=Button(45,300,190,46,"SECRET EGG",(105,55,140)); all_weapons=Button(250,300,190,46,"BOSS WEAPONS",(135,65,40)); all_tournament=Button(455,300,190,46,"TOURNAMENT",(155,115,35)); all_armour=Button(660,300,190,46,"PET ARMOUR",(70,125,145))
        all_achievements=Button(145,365,220,46,"ACHIEVEMENTS",(90,135,65)); all_leaderboard=Button(385,365,220,46,"LEADERBOARD",GOLD,BLACK); all_exit=Button(625,365,220,46,"EXIT GAME",RED)
        all_back=Button(365,435,230,46,"BACK",(40,50,70))
        buttons=(all_accounts,all_collection,all_skills,all_skins,all_mansion,all_bosses,all_team,all_rush,all_workshop,all_fusion,all_powers,all_trophies,all_secret_egg,all_weapons,all_tournament,all_armour,all_achievements,all_leaderboard,all_exit,all_back)
        for button in buttons: button.draw(screen)
        for event in events:
            if all_accounts.is_clicked(mouse_pos,event): save_progress(); active_account=""; player_name=""; account_name_input=""; account_password_input=""; account_message=""; current_state=GameState.ACCOUNT_NAME; break
            if all_collection.is_clicked(mouse_pos,event): current_state=GameState.COLLECTION; break
            if all_skills.is_clicked(mouse_pos,event): current_state=GameState.SKILLS; break
            if all_skins.is_clicked(mouse_pos,event): current_state=GameState.SKIN_MENU; break
            if all_mansion.is_clicked(mouse_pos,event): current_state=GameState.DINO_MANSION; break
            if all_bosses.is_clicked(mouse_pos,event): boss_select_index=0; current_state=GameState.ALL_BOSSES; break
            if all_team.is_clicked(mouse_pos,event): team_message=""; current_state=GameState.TEAM_BATTLE; break
            if all_rush.is_clicked(mouse_pos,event): boss_rush_index=0; current_state=GameState.BOSS_RUSH; break
            if all_workshop.is_clicked(mouse_pos,event): current_state=GameState.WORKSHOP; break
            if all_fusion.is_clicked(mouse_pos,event): current_state=GameState.PET_FUSION; break
            if all_powers.is_clicked(mouse_pos,event): current_state=GameState.BOSS_POWERS; break
            if all_trophies.is_clicked(mouse_pos,event): current_state=GameState.TROPHY_ROOM; break
            if all_secret_egg.is_clicked(mouse_pos,event): current_state=GameState.SECRET_EGG; break
            if all_weapons.is_clicked(mouse_pos,event): current_state=GameState.BOSS_WEAPONS; break
            if all_tournament.is_clicked(mouse_pos,event): current_state=GameState.TOURNAMENT; break
            if all_armour.is_clicked(mouse_pos,event): current_state=GameState.PET_ARMOUR; break
            if all_achievements.is_clicked(mouse_pos,event): refresh_achievements(); current_state=GameState.ACHIEVEMENTS; break
            if all_leaderboard.is_clicked(mouse_pos,event): leaderboard=load_leaderboard(); current_state=GameState.LEADERBOARD; break
            if all_exit.is_clicked(mouse_pos,event): running=False; break
            if all_back.is_clicked(mouse_pos,event): current_state=GameState.LOBBY; break

    elif current_state == GameState.SECRET_EGG:
        screen.fill((12,5,24)); title=font_title.render("SECRET EGG",True,(245,220,255)); screen.blit(title,title.get_rect(center=(480,52)))
        unlocked=all(p in player_progress.get("owned_pets",[]) for p in ALL_NORMAL_PETS)
        pygame.draw.ellipse(screen,(28,18,38),(385,125,190,245)); pygame.draw.ellipse(screen,(255,205,55),(395,135,170,225),5)
        for spot in range(12): pygame.draw.circle(screen,(145,55,235),(425+(spot*37)%110,170+(spot*43)%145),7+spot%4)
        status="100 CUPS - OPEN" if unlocked else "LOCKED - COLLECT ALL NORMAL PETS"
        open_egg=Button(300,405,360,55,status,(105,55,150) if unlocked else (65,65,75)); open_egg.draw(screen)
        owned_secret=font_ui.render("Owned: "+(", ".join(player_progress.get("secret_egg_pets",[])) or "None"),True,WHITE); screen.blit(owned_secret,owned_secret.get_rect(center=(480,480)))
        back=Button(25,25,120,40,"BACK",(35,45,65)); back.draw(screen)
        for event in events:
            if open_egg.is_clicked(mouse_pos,event) and unlocked and int(player_progress.get("cups",0))>=100:
                player_progress["cups"]-=100; choices=[p for p in SECRET_EGG_PETS if p not in player_progress.get("secret_egg_pets",[])] or SECRET_EGG_PETS
                won=random.choice(choices); owned=list(player_progress.get("secret_egg_pets",[]))
                if won not in owned: owned.append(won)
                player_progress["secret_egg_pets"]=owned; player_progress["selected_secret_pet"]=won; player_progress["selected_pet_fusion"]=""; save_progress(); break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.BOSS_WEAPONS:
        screen.fill((10,16,28)); title=font_title.render("BOSS WEAPONS",True,(255,225,180)); screen.blit(title,title.get_rect(center=(480,48)))
        wins=set(player_progress.get("boss_wins",[])); owned=list(player_progress.get("owned_boss_weapons",[])); weapon_buttons=[]
        for i,(boss,weapon) in enumerate(BOSS_WEAPON_DATA.items()):
            col=i%2; row=i//2; x=80+col*430; y=105+row*92; unlock=boss in wins
            pygame.draw.rect(screen,(45,40,35) if unlock else (38,38,45),(x,y,370,68),border_radius=14)
            screen.blit(font_ui.render(f"{boss}: {weapon}",True,WHITE),(x+18,y+20))
            equipped=player_progress.get("selected_boss_weapon")==weapon; text="EQUIPPED" if equipped else ("EQUIP" if unlock else "LOCKED")
            b=Button(x+245,y+15,110,38,text,GOLD if equipped else ((115,75,35) if unlock else (65,65,70)),BLACK if equipped else WHITE); b.draw(screen); weapon_buttons.append((b,boss,weapon,unlock))
        back=Button(390,500,180,42,"BACK",(35,45,65)); back.draw(screen)
        for event in events:
            for b,boss,weapon,unlock in weapon_buttons:
                if b.is_clicked(mouse_pos,event) and unlock:
                    if weapon not in owned: owned.append(weapon)
                    player_progress["owned_boss_weapons"]=owned; player_progress["selected_boss_weapon"]=weapon; save_progress(); break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.PET_ARMOUR:
        screen.fill((8,20,28)); title=font_title.render("PET ARMOUR",True,(210,245,255)); screen.blit(title,title.get_rect(center=(480,50)))
        pet=player_progress.get("selected_pet","") or player_progress.get("selected_secret_pet","") or "NO PET"
        screen.blit(font_ui.render(f"Selected pet: {pet}",True,GOLD),(340,105)); armour_map=dict(player_progress.get("pet_armour",{})); current=armour_map.get(pet,"NONE")
        armour_buttons=[]
        for i,(name,cost,bonus) in enumerate(PET_ARMOUR_LEVELS[1:]):
            y=155+i*75; owned=(current==name); b=Button(225,y,510,52,f"{name} ARMOUR  {cost} CUPS  +{bonus} DAMAGE",GOLD if owned else (55,105,125),BLACK if owned else WHITE); b.draw(screen); armour_buttons.append((b,name,cost))
        back=Button(390,480,180,42,"BACK",(35,45,65)); back.draw(screen)
        for event in events:
            for b,name,cost in armour_buttons:
                if b.is_clicked(mouse_pos,event) and pet!="NO PET" and int(player_progress.get("cups",0))>=cost:
                    player_progress["cups"]-=cost; armour_map[pet]=name; player_progress["pet_armour"]=armour_map; save_progress(); break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.TOURNAMENT:
        screen.fill((26,16,8)); title=font_title.render("WEEKLY TOURNAMENT",True,GOLD); screen.blit(title,title.get_rect(center=(480,48)))
        completed=set(player_progress.get("tournament_days",[])); day_names=["MON","TUE","WED","THU","FRI","SAT","SUN"]
        tournament_buttons=[]
        for i,boss in enumerate(TOURNAMENT_ORDER):
            col=i%4; row=i//4; x=55+col*225; y=125+row*135; done=day_names[i] in completed
            b=Button(x,y,195,82,f"{day_names[i]}: {boss}",GOLD if done else (115,65,30),BLACK if done else WHITE); b.draw(screen); tournament_buttons.append((b,i,boss))
        reward_text=font_ui.render(f"Completed {len(completed)}/7 - Full reward: 200 cups",True,WHITE); screen.blit(reward_text,reward_text.get_rect(center=(480,405)))
        claim=Button(330,440,300,48,"CLAIM CHAMPION REWARD",(45,135,85)); claim.draw(screen); back=Button(390,500,180,38,"BACK",(35,45,65)); back.draw(screen)
        for event in events:
            for b,i,boss in tournament_buttons:
                if b.is_clicked(mouse_pos,event): boss_select_index=min(i,len(selectable_bosses())-1); boss_difficulty="HARD"; boss_loading_start=pygame.time.get_ticks(); current_state=GameState.BOSS_LOADING; break
            if claim.is_clicked(mouse_pos,event) and len(completed)>=7 and not player_progress.get("tournament_claimed",False): player_progress["cups"]+=200; player_progress["tournament_claimed"]=True; save_progress(); break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    # Collection hub: owned dinosaurs, guns and pets.
    elif current_state == GameState.COLLECTION:
        screen.fill((6,12,30))
        for star in range(70): pygame.draw.circle(screen,(110,185,240),((star*89+17)%SCREEN_WIDTH,(star*53+31)%SCREEN_HEIGHT),1+star%2)
        panel=pygame.Rect(85,55,790,445); pygame.draw.rect(screen,(15,29,58),panel,border_radius=26); pygame.draw.rect(screen,(65,215,255),panel,4,border_radius=26)
        title=pygame.font.Font(None,62).render("MY COLLECTION",True,(225,248,255)); screen.blit(title,title.get_rect(center=(480,105)))
        subtitle=font_sub.render("View everything owned by this account",True,(155,205,235)); screen.blit(subtitle,subtitle.get_rect(center=(480,145)))
        dino_count=sum(1 for key,value in player_progress.items() if key.endswith("_owned") and key not in {item["owned_key"] for item in GUN_SKINS} and value)
        gun_count=sum(1 for item in GUN_SKINS if player_progress.get(item["owned_key"],False))
        pet_count=len(player_progress.get("owned_pets",[]))+(1 if player_progress.get("secret_pet_unlocked",False) else 0)+len(player_progress.get("owned_pet_fusions",[]))+len(player_progress.get("secret_egg_pets",[]))+len(unlocked_boss_companions())
        dino_btn=Button(155,205,650,65,f"DINO SKINS   OWNED {dino_count}",GREEN)
        gun_btn=Button(155,295,650,65,f"GUN SKINS   OWNED {gun_count}",(45,105,200))
        pet_btn=Button(155,385,650,65,f"PETS   OWNED {pet_count}",(35,155,120))
        back=Button(365,515,230,48,"BACK",(35,45,65))
        for button in (dino_btn,gun_btn,pet_btn,back): button.draw(screen)
        for event in events:
            if dino_btn.is_clicked(mouse_pos,event): shop_skin_index=0; current_state=GameState.SKINS; break
            if gun_btn.is_clicked(mouse_pos,event): gun_skin_index=0; current_state=GameState.GUN_SKINS; break
            if pet_btn.is_clicked(mouse_pos,event): pet_collection_page=0; current_state=GameState.PET_COLLECTION; break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    # Owned-pets gallery. Only pets belonging to the active account are shown.
    elif current_state == GameState.PET_COLLECTION:
        screen.fill((5,14,28)); now=pygame.time.get_ticks()
        title=font_title.render("MY PETS",True,(220,248,255)); screen.blit(title,title.get_rect(center=(480,48)))
        owned=list(player_progress.get("owned_pets",[]))
        if player_progress.get("secret_pet_unlocked",False): owned.append(SECRET_PET)
        for fusion_name in player_progress.get("owned_pet_fusions",[]):
            if fusion_name not in owned: owned.append(fusion_name)
        for secret_name in player_progress.get("secret_egg_pets",[]):
            if secret_name not in owned: owned.append(secret_name)
        for companion_name in unlocked_boss_companions():
            if companion_name not in owned: owned.append(companion_name)
        per_page=6; page_count=max(1,math.ceil(len(owned)/per_page)); pet_collection_page=max(0,min(pet_collection_page,page_count-1))
        shown=owned[pet_collection_page*per_page:(pet_collection_page+1)*per_page]
        pet_buttons=[]
        if not shown:
            empty=font_title.render("NO PETS OWNED YET",True,(145,175,200)); screen.blit(empty,empty.get_rect(center=(480,270)))
            hint=font_sub.render("Open eggs from PETS & EGGS to unlock pets",True,WHITE); screen.blit(hint,hint.get_rect(center=(480,320)))
        for index,name in enumerate(shown):
            col=index%3; row=index//3; center_x=190+col*290; center_y=190+row*185
            card=pygame.Rect(center_x-112,center_y-72,224,145)
            if name in {fusion[0] for fusion in PET_FUSIONS}:
                equipped=player_progress.get("selected_pet_fusion","")==name
            elif name in BOSS_COMPANIONS.values():
                draw_boss_companion(name,center_x,center_y-10)
            elif name in BOSS_COMPANIONS.values():
                equipped=player_progress.get("selected_boss_companion","")==name
            elif name in SECRET_EGG_PETS:
                equipped=player_progress.get("selected_secret_pet","")==name and not player_progress.get("selected_pet_fusion","")
            else:
                equipped=player_progress.get("selected_pet","")==name and not player_progress.get("selected_pet_fusion","") and not player_progress.get("selected_secret_pet","")
            pygame.draw.rect(screen,(18,40,58) if not equipped else (25,75,62),card,border_radius=18)
            pygame.draw.rect(screen,(65,210,255) if not equipped else GOLD,card,3,border_radius=18)
            if name in {fusion[0] for fusion in PET_FUSIONS}:
                draw_fused_pet(name,center_x,center_y-10)
            elif name in SECRET_EGG_PETS:
                secret_base={"SHADOW DRAGON":"EAGLE","ROBOT TIGER":"TIGER","COSMIC EAGLE":"EAGLE","ICE LION":"LION"}[name]
                draw_pet(secret_base,center_x,center_y-10)
                secret_layer=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
                aura_colour={"SHADOW DRAGON":(155,65,255),"ROBOT TIGER":(70,225,255),"COSMIC EAGLE":(100,90,255),"ICE LION":(145,235,255)}[name]
                pygame.draw.circle(secret_layer,(*aura_colour,45),(center_x,center_y-10),48)
                pygame.draw.circle(secret_layer,(*aura_colour,180),(center_x,center_y-10),43,3)
                if name=="SHADOW DRAGON":
                    pygame.draw.polygon(secret_layer,(110,40,180),[(center_x-12,center_y-17),(center_x-52,center_y-48),(center_x-35,center_y),(center_x-10,center_y+8)])
                    pygame.draw.polygon(secret_layer,(110,40,180),[(center_x+12,center_y-17),(center_x+52,center_y-48),(center_x+35,center_y),(center_x+10,center_y+8)])
                elif name=="ROBOT TIGER":
                    pygame.draw.rect(secret_layer,(80,105,135),(center_x-23,center_y-27,45,18),border_radius=6)
                    pygame.draw.circle(secret_layer,(255,55,65),(center_x-10,center_y-18),4); pygame.draw.circle(secret_layer,(255,55,65),(center_x+10,center_y-18),4)
                elif name=="COSMIC EAGLE":
                    for star in range(6):
                        angle=now/400+star*math.tau/6; sx=center_x+int(math.cos(angle)*43); sy=center_y-10+int(math.sin(angle)*28); pygame.draw.circle(secret_layer,(255,220,90),(sx,sy),3)
                elif name=="ICE LION":
                    for shard in range(5):
                        sx=center_x-28+shard*14; pygame.draw.polygon(secret_layer,(210,250,255),[(sx,center_y+12),(sx+6,center_y-8),(sx+12,center_y+12)])
                screen.blit(secret_layer,(0,0))
            else:
                draw_pet(name,center_x,center_y-10)
            label=pygame.font.Font(None,24).render(name,True,WHITE); screen.blit(label,label.get_rect(center=(center_x,center_y+45)))
            if equipped:
                eq=pygame.font.Font(None,19).render("EQUIPPED",True,GOLD); screen.blit(eq,eq.get_rect(center=(center_x,center_y+64)))
            button=Button(card.x,card.y,card.width,card.height,"",(0,0,0,0)); pet_buttons.append((button,name,card))
        prev=Button(210,510,100,45,"<",(25,45,70)); page_label=font_ui.render(f"Page {pet_collection_page+1}/{page_count}",True,WHITE); nxt=Button(650,510,100,45,">",(25,45,70)); back=Button(390,510,180,45,"BACK",(35,45,65))
        prev.draw(screen); nxt.draw(screen); back.draw(screen); screen.blit(page_label,page_label.get_rect(center=(480,495)))
        for event in events:
            for button,name,card in pet_buttons:
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and card.collidepoint(event.pos):
                    if name in {fusion[0] for fusion in PET_FUSIONS}:
                        player_progress["selected_pet_fusion"]=name; player_progress["selected_secret_pet"]=""
                    elif name in BOSS_COMPANIONS.values():
                        player_progress["selected_boss_companion"]=name
                    elif name in SECRET_EGG_PETS:
                        player_progress["selected_secret_pet"]=name; player_progress["selected_pet_fusion"]=""
                    else:
                        player_progress["selected_pet"]=name; player_progress["selected_pet_fusion"]=""; player_progress["selected_secret_pet"]=""
                    save_progress(); break
            if prev.is_clicked(mouse_pos,event): pet_collection_page=(pet_collection_page-1)%page_count; break
            if nxt.is_clicked(mouse_pos,event): pet_collection_page=(pet_collection_page+1)%page_count; break
            if back.is_clicked(mouse_pos,event): current_state=GameState.COLLECTION; break

    elif current_state == GameState.WORKSHOP:
        screen.fill((12,20,32)); title=font_title.render("GUN WORKSHOP",True,(210,235,255)); screen.blit(title,title.get_rect(center=(480,55)))
        level=int(player_progress.get("gun_damage_level",1)); damage=GUN_DAMAGE_LEVELS[level-1]
        pygame.draw.rect(screen,(25,38,55),(205,130,550,245),border_radius=22); pygame.draw.rect(screen,(80,210,255),(205,130,550,245),3,border_radius=22)
        pygame.draw.rect(screen,(55,70,90),(310,205,270,55),border_radius=12); pygame.draw.rect(screen,(125,150,185),(540,215,120,35),border_radius=8); pygame.draw.circle(screen,(75,235,255),(650,232),14)
        info=font_title.render(f"DAMAGE {damage}",True,GOLD); screen.blit(info,info.get_rect(center=(480,310)))
        if level<5:
            cost=GUN_UPGRADE_COSTS[level]; upgrade=Button(330,400,300,55,f"UPGRADE TO LEVEL {level+1} - {cost} CUPS",(45,135,95))
        else: upgrade=Button(330,400,300,55,"MAX LEVEL",(75,75,85))
        back=Button(390,490,180,45,"BACK",(35,45,65)); upgrade.draw(screen); back.draw(screen)
        for event in events:
            if upgrade.is_clicked(mouse_pos,event) and level<5 and int(player_progress.get("cups",0))>=cost:
                player_progress["cups"]-=cost; player_progress["gun_damage_level"]=level+1; save_progress(); break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.PET_FUSION:
        screen.fill((8,18,30)); title=font_title.render("PET COMBINATION",True,(210,245,230)); screen.blit(title,title.get_rect(center=(480,50)))
        owned=set(player_progress.get("owned_pets",[])); fusion_buttons=[]
        for i,(fusion,a,b) in enumerate(PET_FUSIONS):
            y=115+i*95; unlocked=a in owned and (b in owned or b=="SNOW" and "SNOW" in player_progress.get("boss_wins",[]))
            pygame.draw.rect(screen,(20,55,48) if unlocked else (40,40,45),(150,y,660,70),border_radius=16)
            pygame.draw.rect(screen,(75,220,160) if unlocked else (80,80,85),(150,y,660,70),3,border_radius=16)
            screen.blit(font_ui.render(f"{a} + {b} = {fusion}",True,WHITE),(185,y+20))
            is_equipped=player_progress.get("selected_pet_fusion","")==fusion
            btn_text="EQUIPPED" if is_equipped else ("EQUIP" if unlocked else "LOCKED")
            btn=Button(620,y+16,150,38,btn_text,GOLD if is_equipped else ((45,140,95) if unlocked else (65,65,70)),BLACK if is_equipped else WHITE)
            btn.draw(screen); fusion_buttons.append((btn,fusion,unlocked))
            if unlocked: draw_fused_pet(fusion,120,y+34)
        clear_fusion=Button(180,510,180,45,"USE NORMAL PET",(65,75,85)); clear_fusion.draw(screen)
        back=Button(600,510,180,45,"BACK",(35,45,65)); back.draw(screen)
        for event in events:
            for button,fusion,unlocked in fusion_buttons:
                if button.is_clicked(mouse_pos,event) and unlocked:
                    player_progress["selected_pet_fusion"]=fusion
                    owned_fusions=list(player_progress.get("owned_pet_fusions",[]))
                    if fusion not in owned_fusions: owned_fusions.append(fusion)
                    player_progress["owned_pet_fusions"]=owned_fusions
                    save_progress()
                    pet_message=f"{fusion} EQUIPPED"
                    break
            if clear_fusion.is_clicked(mouse_pos,event): player_progress["selected_pet_fusion"]=""; save_progress(); pet_message="NORMAL PET EQUIPPED"; break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.TEAM_BATTLE:
        screen.fill((18,10,28)); title=font_title.render("BOSS TEAM BATTLE",True,(255,220,230)); screen.blit(title,title.get_rect(center=(480,50)))
        first=BOSS_TYPES[team_first_index]; second=BOSS_TYPES[team_second_index]
        draw_arena_boss(first["name"],310,270); draw_arena_boss(second["name"],650,270)
        screen.blit(font_ui.render(first["name"],True,GOLD),(260,390)); screen.blit(font_ui.render(second["name"],True,GOLD),(610,390))
        left=Button(80,220,70,60,"<",(40,40,65)); swap=Button(445,220,70,60,"SWAP",(80,55,100)); right=Button(810,220,70,60,">",(40,40,65)); fight=Button(350,455,260,55,"FIGHT TEAM - 100 CUPS",RED); back=Button(25,25,120,40,"BACK",(35,45,65))
        for b in (left,swap,right,fight,back): b.draw(screen)
        for event in events:
            if left.is_clicked(mouse_pos,event): team_first_index=(team_first_index-1)%6; break
            if right.is_clicked(mouse_pos,event): team_second_index=(team_second_index+1)%6; break
            if swap.is_clicked(mouse_pos,event): team_first_index,team_second_index=team_second_index,team_first_index; break
            if fight.is_clicked(mouse_pos,event): boss_select_index=team_first_index; boss_difficulty="HARD"; boss_loading_start=pygame.time.get_ticks(); current_state=GameState.BOSS_LOADING; break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.BOSS_RUSH:
        screen.fill((25,8,12)); title=font_title.render("BOSS RUSH",True,(255,210,120)); screen.blit(title,title.get_rect(center=(480,55)))
        boss=BOSS_TYPES[boss_rush_index%len(BOSS_TYPES)]; draw_arena_boss(boss["name"],480,275)
        screen.blit(font_title.render(f"ROUND {boss_rush_index+1}: {boss['name']}",True,WHITE),(300,410))
        best=font_ui.render(f"Best completed: {player_progress.get('boss_rush_best',0)} bosses",True,GOLD); screen.blit(best,best.get_rect(center=(480,455)))
        fight=Button(350,500,260,50,"START NEXT BOSS",RED); back=Button(25,25,120,40,"BACK",(35,45,65)); fight.draw(screen); back.draw(screen)
        for event in events:
            if fight.is_clicked(mouse_pos,event): boss_select_index=boss_rush_index%6; boss_difficulty="HARD"; boss_loading_start=pygame.time.get_ticks(); current_state=GameState.BOSS_LOADING; break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.BOSS_POWERS:
        screen.fill((7,12,32)); title=font_title.render("BOSS POWERS",True,(210,235,255)); screen.blit(title,title.get_rect(center=(480,50)))
        wins=set(player_progress.get("boss_wins",[])); chosen=player_progress.get("selected_boss_power","")
        power_buttons=[]
        for i,boss in enumerate(BOSS_TYPES):
            col=i%3; row=i//3; x=80+col*290; y=115+row*180
            unlocked=boss["name"] in wins; card=pygame.Rect(x,y,240,145)
            pygame.draw.rect(screen,(20,48,72) if unlocked else (38,38,45),card,border_radius=18); pygame.draw.rect(screen,GOLD if chosen==boss["name"] else ((70,210,255) if unlocked else (80,80,85)),card,3,border_radius=18)
            label=font_ui.render(BOSS_POWERS[boss["name"]] if unlocked else "LOCKED",True,WHITE); screen.blit(label,label.get_rect(center=(x+120,y+50)))
            sub=pygame.font.Font(None,21).render(boss["name"],True,GOLD); screen.blit(sub,sub.get_rect(center=(x+120,y+88)))
            equipped=chosen==boss["name"]
            button_text="EQUIPPED" if equipped else ("EQUIP" if unlocked else "DEFEAT BOSS")
            button_colour=GOLD if equipped else ((45,130,90) if unlocked else (65,65,70))
            b=Button(x+45,y+105,150,32,button_text,button_colour,BLACK if equipped else WHITE); b.draw(screen); power_buttons.append((b,boss["name"],unlocked))
        back=Button(390,500,180,45,"BACK",(35,45,65)); back.draw(screen)
        for event in events:
            for button,name,unlocked in power_buttons:
                if button.is_clicked(mouse_pos,event) and unlocked: player_progress["selected_boss_power"]=name; save_progress(); break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.TROPHY_ROOM:
        screen.fill((24,18,28)); title=font_title.render("BOSS TROPHY ROOM",True,GOLD); screen.blit(title,title.get_rect(center=(480,50)))
        counts=player_progress.get("boss_win_counts",{})
        for i,boss in enumerate(BOSS_TYPES):
            col=i%3; row=i//3; x=95+col*290; y=125+row*200; count=int(counts.get(boss["name"],0)); rank,colour=trophy_rank(count)
            pygame.draw.rect(screen,(35,30,42),(x,y,190,150),border_radius=18); pygame.draw.rect(screen,colour,(x,y,190,150),3,border_radius=18)
            pygame.draw.polygon(screen,colour,[(x+70,y+30),(x+120,y+30),(x+110,y+85),(x+80,y+85)]); pygame.draw.rect(screen,colour,(x+83,y+85,24,25)); pygame.draw.rect(screen,colour,(x+65,y+110,60,10))
            screen.blit(font_ui.render(boss["name"],True,WHITE),(x+55,y+123)); screen.blit(pygame.font.Font(None,20).render(f"{rank}  WINS {count}",True,colour),(x+30,y+6))
        back=Button(390,530,180,42,"BACK",(45,45,55)); back.draw(screen)
        for event in events:
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.ACHIEVEMENTS:
        screen.fill((8,18,34)); title=font_title.render("ACHIEVEMENT MEDALS",True,(230,245,255)); screen.blit(title,title.get_rect(center=(480,55)))
        unlocked=set(player_progress.get("achievements",[]))
        for i,(name,desc,rule) in enumerate(ACHIEVEMENT_RULES):
            y=125+i*95; colour=GOLD if name in unlocked else (80,85,95)
            pygame.draw.circle(screen,colour,(145,y+25),28); pygame.draw.circle(screen,(255,245,190) if name in unlocked else (45,45,50),(145,y+25),15)
            screen.blit(font_ui.render(name,True,colour),(195,y+5)); screen.blit(font_sub.render(desc,True,WHITE),(195,y+38))
        back=Button(390,520,180,45,"BACK",(35,45,65)); back.draw(screen)
        for event in events:
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    elif current_state == GameState.BOSS_LOADING:
        boss=selectable_bosses()[boss_select_index]; draw_boss_theme(boss["theme"]); elapsed=pygame.time.get_ticks()-boss_loading_start; progress=min(1.0,elapsed/2200.0)
        shade=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); shade.fill((0,0,0,150)); screen.blit(shade,(0,0))
        if boss["name"]=="SHADOW TARUN":
            draw_shadow_tarun(480,285)
        else: draw_arena_boss(boss["name"],480,285)
        name=pygame.font.Font(None,68).render(f"{boss['name']} BOSS",True,GOLD); screen.blit(name,name.get_rect(center=(480,105)))
        tips={"ROBOT":"Jump between the twin plasma shots","GHOST":"Watch the spread of the soul orbs","DRAGON":"Jump early before the fire burst","MONKEY":"Its fists hit hard","SNOW":"Find the gap between ice shards","ALIEN":"Three plasma lanes leave one jump gap","SHADOW TARUN":"The creator's shadow copies every combat skill"}
        tip=font_ui.render(tips[boss["name"]],True,WHITE); screen.blit(tip,tip.get_rect(center=(480,420)))
        pygame.draw.rect(screen,(30,35,50),(180,475,600,28),border_radius=12); pygame.draw.rect(screen,(70,220,255),(180,475,int(600*progress),28),border_radius=12)
        if elapsed>=2200: start_selected_boss(); current_state=GameState.BOSS_ARENA

    # Boss selection carousel.
    elif current_state == GameState.ALL_BOSSES:
        bosses=selectable_bosses(); boss=BOSSES_CURRENT=bosses[boss_select_index]; draw_boss_theme(boss["theme"])
        shade=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); shade.fill((0,0,0,75)); screen.blit(shade,(0,0))
        title=font_title.render("ALL BOSSES",True,WHITE); screen.blit(title,title.get_rect(center=(480,45)))
        if boss["name"]=="SHADOW TARUN":
            draw_shadow_tarun(480,285)
        else:
            draw_arena_boss(boss["name"],480,285)
        if boss["name"]=="SHADOW TARUN" and not player_progress.get("shadow_tarun_unlocked",False):
            lock_surface=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); lock_surface.fill((0,0,0,105)); screen.blit(lock_surface,(0,0))
            lock_text=font_title.render("LOCKED",True,(255,90,90)); screen.blit(lock_text,lock_text.get_rect(center=(480,285)))
        display_name="GRIM REAPER" if boss["name"]=="GHOST" else boss["name"]
        name=font_title.render(display_name,True,GOLD); screen.blit(name,name.get_rect(center=(480,95)))
        info=font_ui.render(f"Life: {boss['health']}   Reward: {boss['reward']} cups   Bullet damage: 500",True,WHITE); screen.blit(info,info.get_rect(center=(480,135)))
        prev=Button(55,245,90,70,"<",(25,45,75)); nxt=Button(815,245,90,70,">",(25,45,75)); fight=Button(350,445,260,60,"FIGHT BOSS",RED); back=Button(25,25,130,42,"BACK",(30,40,60))
        difficulty=Button(350,370,260,48,f"DIFFICULTY: {boss_difficulty}",(75,65,135))
        for button in (prev,nxt,fight,back,difficulty): button.draw(screen)
        wins=set(player_progress.get("boss_wins",[])); defeated=boss["name"] in wins
        shadow_unlocked=bool(player_progress.get("shadow_tarun_unlocked",False))
        nightmare_count=len(set(player_progress.get("nightmare_boss_wins",[])))
        if boss["name"]=="SHADOW TARUN" and not shadow_unlocked: status_text=f"LOCKED - NIGHTMARE BOSSES {nightmare_count}/6"
        elif boss["name"]=="SHADOW TARUN" and not defeated: status_text="SECRET BOSS UNLOCKED"
        else: status_text="DEFEATED" if defeated else "NOT DEFEATED"
        status=font_ui.render(status_text,True,(100,255,140) if defeated else (255,180,100)); screen.blit(status,status.get_rect(center=(480,410)))
        for event in events:
            if prev.is_clicked(mouse_pos,event): boss_select_index=(boss_select_index-1)%len(bosses); play_sound(BOSS_AUDIO.get(bosses[boss_select_index]["name"], SOUND_VICTORY)); break
            if nxt.is_clicked(mouse_pos,event): boss_select_index=(boss_select_index+1)%len(bosses); play_sound(BOSS_AUDIO.get(bosses[boss_select_index]["name"], SOUND_VICTORY)); break
            if difficulty.is_clicked(mouse_pos,event):
                levels=list(BOSS_DIFFICULTIES); boss_difficulty=levels[(levels.index(boss_difficulty)+1)%len(levels)]; break
            if fight.is_clicked(mouse_pos,event):
                if boss["name"]!="SHADOW TARUN" or player_progress.get("shadow_tarun_unlocked",False):
                    boss_loading_start=pygame.time.get_ticks(); current_state=GameState.BOSS_LOADING
                break
            if back.is_clicked(mouse_pos,event): current_state=GameState.ALL_MENU; break

    # Stand-alone boss arena. Every player bullet deals exactly 500 damage.
    elif current_state == GameState.BOSS_ARENA:
        draw_boss_theme(arena_boss["theme"]); now=pygame.time.get_ticks()
        health_lost_ratio=1.0-arena_health/max(1,arena_boss["health"])
        arena_destruction_level=min(4,int(health_lost_ratio*5))
        draw_arena_destruction(arena_boss["name"],arena_destruction_level,boss_final_form,now)
        intro_elapsed=now-arena_intro_start
        intro_active=intro_elapsed<3200
        intro_progress=min(1.0,intro_elapsed/2200.0)
        eased=intro_progress*intro_progress*(3-2*intro_progress)
        if arena_boss["name"]=="SHADOW TARUN":
            boss_x=745
            entrance_phase=min(1.0,intro_elapsed/2200.0)
            boss_y=int(-180+(335+180)*eased)
        else:
            boss_x=int(SCREEN_WIDTH+220+(745-(SCREEN_WIDTH+220))*eased); boss_y=335
        if arena_is_jumping and not intro_active:
            arena_dino_y += arena_dino_velocity
            arena_dino_velocity += 0.65
            if arena_dino_y >= 390:
                arena_dino_y=390.0; arena_dino_velocity=0.0; arena_is_jumping=False
        # Attack animation temporarily pushes or lifts the boss.
        attack_elapsed=now-arena_attack_animation_start
        if 0<=attack_elapsed<520:
            phase=math.sin((attack_elapsed/520.0)*math.pi)
            if arena_attack_kind in ("ROBOT","MONKEY","SNOW"): boss_x-=int(38*phase)
            else: boss_y-=int(24*phase)
        draw_dinosaur(120,arena_dino_y,jumping=arena_is_jumping,animated=True)
        battle_fusion=player_progress.get("selected_pet_fusion","")
        battle_secret=player_progress.get("selected_secret_pet","")
        battle_pet=battle_secret or player_progress.get("selected_pet","")
        if battle_fusion:
            draw_fused_pet(battle_fusion,82,arena_dino_y+32)
        elif battle_pet:
            battle_pet_y=arena_dino_y-42 if battle_pet in ("VULTURE","EAGLE","OWL") else arena_dino_y+38
            draw_pet(battle_pet,82,battle_pet_y)
        selected_companion=player_progress.get("selected_boss_companion","")
        if selected_companion in unlocked_boss_companions(): draw_boss_companion(selected_companion,42,arena_dino_y+20)
        if arena_death_start==0:
            if arena_boss["name"]=="SHADOW TARUN":
                if intro_active:
                    entrance_layer=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
                    portal_alpha=max(0,220-intro_elapsed//16)
                    portal_center=(boss_x,boss_y+40)
                    for ring in range(6):
                        radius=150-ring*18+int(math.sin(now/100.0+ring)*8)
                        pygame.draw.ellipse(entrance_layer,(135+ring*15,45,255,portal_alpha),(portal_center[0]-radius,portal_center[1]-radius//2,radius*2,radius),4)
                    for lightning in range(9):
                        angle=now/220.0+lightning*math.tau/9
                        sx=portal_center[0]+int(math.cos(angle)*125); sy=portal_center[1]+int(math.sin(angle)*58)
                        mx=portal_center[0]+int(math.cos(angle+0.18)*70); my=portal_center[1]+int(math.sin(angle+0.18)*35)
                        pygame.draw.lines(entrance_layer,(190,90,255,210),False,[(sx,sy),(mx,my),portal_center],3)
                    for pillar in range(7):
                        px=boss_x-120+pillar*40; height=int(120*entrance_phase)+pillar%2*25
                        pygame.draw.polygon(entrance_layer,(65,15,105,120),[(px,boss_y+150),(px+22,boss_y+150),(px+11,boss_y+150-height)])
                    if intro_elapsed>1700:
                        landing=(intro_elapsed-1700)/500.0; wave_radius=int(180*min(1.0,landing))
                        pygame.draw.ellipse(entrance_layer,(180,75,255,max(0,190-int(landing*150))),(boss_x-wave_radius,boss_y+110-wave_radius//5,wave_radius*2,max(12,wave_radius//2)),5)
                        pygame.draw.circle(entrance_layer,(255,220,70,max(0,180-int(landing*120))),(boss_x,boss_y-100),max(8,55-int(35*landing)),4)
                    screen.blit(entrance_layer,(0,0))
                draw_shadow_tarun(boss_x,boss_y-25)
            else: draw_arena_boss(arena_boss["name"],boss_x,boss_y)
        if intro_active:
            dark=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); dark.fill((0,0,0,max(0,150-int(140*intro_progress)))); screen.blit(dark,(0,0))
            warning_text="THE CREATOR'S SHADOW AWAKENS" if arena_boss["name"]=="SHADOW TARUN" else "BOSS APPROACHING"
            warning=font_title.render(warning_text,True,(210,120,255) if arena_boss["name"]=="SHADOW TARUN" else (255,90,80)); screen.blit(warning,warning.get_rect(center=(480,140)))
            title_text="SHADOW TARUN" if arena_boss["name"]=="SHADOW TARUN" else ("GRIM REAPER" if arena_boss["name"]=="GHOST" else f"{arena_boss['name']} BOSS")
            boss_title=pygame.font.Font(None,72).render(title_text,True,GOLD); screen.blit(boss_title,boss_title.get_rect(center=(480,210)))
            reward=font_ui.render(f"LIFE {arena_boss['health']}   REWARD {arena_boss['reward']} CUPS",True,WHITE); screen.blit(reward,reward.get_rect(center=(480,265)))
            intro_line=BOSS_DIALOGUE.get(arena_boss["name"],("", ""))[0]
            dialogue=font_ui.render(intro_line,True,(245,225,180)); screen.blit(dialogue,dialogue.get_rect(center=(480,315)))
        pygame.draw.rect(screen,(25,25,35),(260,30,610,24),border_radius=10); fill=int(610*max(0,arena_health)/arena_boss["health"]); pygame.draw.rect(screen,RED,(260,30,fill,24),border_radius=10)
        label=font_ui.render(f"{'GRIM REAPER' if arena_boss['name']=='GHOST' else arena_boss['name']+' BOSS'}  {arena_health}/{arena_boss['health']}",True,WHITE); screen.blit(label,label.get_rect(center=(565,75)))
        hp=font_ui.render(f"Your hearts: {arena_player_health}/10",True,WHITE); screen.blit(hp,(25,25))
        health_ratio=arena_health/max(1,arena_boss["health"])
        if health_ratio<=0.25 and arena_health>0:
            boss_final_form=True
            final_overlay=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); final_overlay.fill((90,0,120,35)); screen.blit(final_overlay,(0,0))
            final_text=font_title.render("FINAL FORM!",True,(255,90,70)); screen.blit(final_text,final_text.get_rect(center=(480,115)))
        power_text=pygame.font.Font(None,22).render(f"Attack power: { {'ROBOT':2,'GHOST':2,'DRAGON':3,'MONKEY':2,'SNOW':2,'ALIEN':3,'SHADOW TARUN':3}[arena_boss['name']] } hearts",True,(255,155,100))
        screen.blit(power_text,(25,53))
        selected_power_name=player_progress.get("selected_boss_power","")
        selected_power_label=BOSS_POWERS.get(selected_power_name,"NO POWER EQUIPPED")
        power_status="USED" if arena_power_used else "READY"
        power_label=pygame.font.Font(None,21).render(f"Power: {selected_power_label} [{power_status}]",True,(210,185,255))
        screen.blit(power_label,(25,125))
        if pygame.time.get_ticks()<boss_power_message_until:
            power_message_surface=font_title.render(boss_power_message,True,(235,210,255))
            screen.blit(power_message_surface,power_message_surface.get_rect(center=(480,150)))
        # Boss-specific arena hazards.
        if arena_boss["name"]=="ROBOT" and now%5000<800: pygame.draw.rect(screen,(255,50,50,120),(0,360,SCREEN_WIDTH,18))
        elif arena_boss["name"]=="GHOST":
            darkness=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); darkness.fill((0,0,0,40+int(30*math.sin(now/300.0)))); screen.blit(darkness,(0,0))
        elif arena_boss["name"]=="DRAGON" and now%6000<1200: pygame.draw.rect(screen,(255,70,20),(0,430,SCREEN_WIDTH,45))
        elif arena_boss["name"]=="MONKEY" and now%3500<200: pygame.draw.circle(screen,(90,65,45),(random.randint(100,800),100),22)
        elif arena_boss["name"]=="SNOW": arena_dino_velocity+=0.008
        elif arena_boss["name"]=="ALIEN" and arena_is_jumping: arena_dino_velocity-=0.05
        pygame.draw.rect(screen,(35,35,45),(25,80,180,18),border_radius=8); pygame.draw.rect(screen,(255,85,35),(25,80,int(180*rage_meter/100),18),border_radius=8)
        screen.blit(pygame.font.Font(None,20).render(f"RAGE {rage_meter}%",True,WHITE),(30,101))
        if not intro_active and not arena_message and now>=arena_next_attack:
            arena_attack_animation_start=now; arena_attack_kind=arena_boss["name"]
            play_sound(BOSS_ATTACK_AUDIO.get(arena_boss["name"],SOUND_BULLET_SPARK))
            sx,sy=boss_x-80,boss_y-30; dx,dy=150-sx,(arena_dino_y+30)-sy; dist=max(1,math.hypot(dx,dy))
            damage={"ROBOT":2,"GHOST":2,"DRAGON":3,"MONKEY":2,"SNOW":2,"ALIEN":3,"SHADOW TARUN":3}[arena_boss["name"]]
            speed={"ROBOT":10,"GHOST":8,"DRAGON":11,"MONKEY":9,"SNOW":8,"ALIEN":12,"SHADOW TARUN":13}[arena_boss["name"]]
            shot_count={"ROBOT":2,"GHOST":3,"DRAGON":2,"MONKEY":2,"SNOW":3,"ALIEN":3,"SHADOW TARUN":3}[arena_boss["name"]]
            spread={"ROBOT":0.08,"GHOST":0.16,"DRAGON":0.10,"MONKEY":0.12,"SNOW":0.15,"ALIEN":0.20,"SHADOW TARUN":0.16}[arena_boss["name"]]
            base_angle=math.atan2(dy,dx)
            for shot_index in range(shot_count):
                offset=(shot_index-(shot_count-1)/2)*spread
                angle=base_angle+offset
                # Alien always launches three clearly separated projectiles.
                launch_y = sy + ((shot_index - 1) * 24 if arena_boss["name"] == "ALIEN" else 0)
                arena_enemy_shots.append([float(sx),float(launch_y),math.cos(angle)*speed,math.sin(angle)*speed,damage,arena_boss["name"]])
            attack_delay={"ROBOT":850,"GHOST":950,"DRAGON":800,"MONKEY":900,"SNOW":1000,"ALIEN":700,"SHADOW TARUN":650}[arena_boss["name"]]
            arena_next_attack=now+int(attack_delay*(0.80 if boss_final_form else 1.0))
        # Unlocked boss companion attacks every 20 seconds for 2,000 damage.
        if selected_companion and selected_companion in unlocked_boss_companions() and not intro_active and not arena_message and now>=companion_next_attack:
            companion_projectiles.append({"x":60.0,"y":float(arena_dino_y+15),"tx":float(boss_x),"ty":float(boss_y-15)})
            companion_next_attack=now+20000
        for cshot in companion_projectiles[:]:
            dx=cshot["tx"]-cshot["x"]; dy=cshot["ty"]-cshot["y"]; dist=max(1,math.hypot(dx,dy)); cshot["x"]+=dx/dist*15; cshot["y"]+=dy/dist*15
            px,py=int(cshot["x"]),int(cshot["y"]); pygame.draw.circle(screen,(255,210,70),(px,py),13); pygame.draw.circle(screen,(150,70,255),(px,py),6)
            if dist<22:
                arena_health=max(0,arena_health-2000); companion_projectiles.remove(cshot); boss_power_message=f"{selected_companion}: 2000 DAMAGE"; boss_power_message_until=now+1700; play_sound(SOUND_BULLET_HIT)
        if selected_companion and not arena_message:
            cseconds=max(0,math.ceil((companion_next_attack-now)/1000)); screen.blit(pygame.font.Font(None,19).render(f"Companion attack: {cseconds}s",True,GOLD),(25,215))

        # Equipped pet automatically attacks every 10 seconds.
        active_companion=battle_fusion or battle_pet
        if active_companion and not intro_active and not arena_message and arena_death_start==0 and now>=pet_next_attack:
            if battle_fusion: pet_damage=1500
            elif battle_pet in SECRET_EGG_PETS: pet_damage=2500
            elif battle_pet==SECRET_PET: pet_damage=2000
            elif battle_pet in ("TIGER","LION","CHEETAH"): pet_damage=1500
            elif battle_pet in ("VULTURE","EAGLE","OWL"): pet_damage=1000
            elif battle_pet in ("OCTOPUS","BUFFALO","COW"): pet_damage=800
            else: pet_damage=500
            armour_name=player_progress.get("pet_armour",{}).get(battle_pet or battle_fusion,"NONE")
            pet_damage+=dict((name,bonus) for name,cost,bonus in PET_ARMOUR_LEVELS).get(armour_name,0)
            pet_origin_y=arena_dino_y+18
            pet_attack_projectiles.append({"x":100.0,"y":float(pet_origin_y),"target_x":float(boss_x),"target_y":float(boss_y-20),"damage":pet_damage,"name":active_companion})
            pet_next_attack=now+10000
            pet_attack_message_until=now+1400
            play_sound(SOUND_BULLET_SPARK)
        for pet_shot in pet_attack_projectiles[:]:
            dx=pet_shot["target_x"]-pet_shot["x"]; dy=pet_shot["target_y"]-pet_shot["y"]; distance=max(1.0,math.hypot(dx,dy))
            pet_shot["x"]+=dx/distance*13; pet_shot["y"]+=dy/distance*13
            px,py=int(pet_shot["x"]),int(pet_shot["y"])
            pygame.draw.circle(screen,(120,255,170),(px,py),11)
            pygame.draw.circle(screen,WHITE,(px,py),5)
            pygame.draw.line(screen,(80,220,255),(px-int(dx/distance*28),py-int(dy/distance*28)),(px,py),6)
            if distance<20:
                arena_health=max(0,arena_health-pet_shot["damage"])
                boss_power_message=f"{pet_shot['name']} ATTACKED: {pet_shot['damage']} DAMAGE"
                boss_power_message_until=now+1700
                pet_attack_projectiles.remove(pet_shot)
                pet_attack_count+=1
                if pet_attack_count>=5: pet_ultimate_ready=True
                play_sound(SOUND_BULLET_HIT)
                if arena_health==0 and not arena_message:
                    start_arena_boss_death(arena_boss["name"],boss_x,boss_y)
                    arena_message=f"YOU WON! +{arena_boss['reward']} CUPS"
                    if not arena_reward_given:
                        player_progress["cups"]=int(player_progress.get("cups",0))+arena_boss["reward"]
                        wins=list(player_progress.get("boss_wins",[]))
                        if arena_boss["name"] not in wins: wins.append(arena_boss["name"])
                        player_progress["boss_wins"]=wins
                        counts=dict(player_progress.get("boss_win_counts",{})); counts[arena_boss["name"]]=int(counts.get(arena_boss["name"],0))+1; player_progress["boss_win_counts"]=counts
                        save_progress(); arena_reward_given=True
        if active_companion and not arena_message:
            seconds=max(0,math.ceil((pet_next_attack-now)/1000))
            pet_timer=pygame.font.Font(None,20).render(f"Pet attack in: {seconds}s",True,(140,255,190))
            screen.blit(pet_timer,(25,148))
            pygame.draw.rect(screen,(30,35,45),(25,174,180,17),border_radius=7)
            pygame.draw.rect(screen,(90,235,160),(25,174,int(180*min(5,pet_attack_count)/5),17),border_radius=7)
            ultimate_label=pygame.font.Font(None,19).render("PET ULTIMATE READY" if pet_ultimate_ready else f"PET ULTIMATE {pet_attack_count}/5",True,GOLD if pet_ultimate_ready else WHITE)
            screen.blit(ultimate_label,(28,194))
        if now<pet_attack_message_until:
            ready_text=pygame.font.Font(None,23).render("PET ATTACK!",True,(120,255,170))
            screen.blit(ready_text,(25,170))

        for shot in arena_shots[:]:
            shot[0]+=shot[2]; shot[1]+=shot[3]; pygame.draw.circle(screen,(90,225,255),(int(shot[0]),int(shot[1])),8)
            if pygame.Rect(int(shot[0])-6,int(shot[1])-6,12,12).colliderect(pygame.Rect(boss_x-120,boss_y-140,240,210)):
                shot_damage=1200 if player_progress.get("selected_boss_weapon","") else GUN_DAMAGE_LEVELS[int(player_progress.get("gun_damage_level",1))-1]
                if pygame.time.get_ticks()<rage_active_until: shot_damage*=2
                arena_health=max(0,arena_health-shot_damage); arena_combo+=1; rage_meter=min(100,rage_meter+12)
                if arena_combo>=5: arena_finisher_ready=True
                play_sound(SOUND_BULLET_HIT); arena_shots.remove(shot)
                if arena_health==0:
                    start_arena_boss_death(arena_boss["name"],boss_x,boss_y)
                    arena_message=f"YOU WON! +{arena_boss['reward']} CUPS"; stop_boss_music(); play_sound(BOSS_DEFEAT_AUDIO.get(arena_boss["name"],SOUND_VICTORY))
                    if not arena_reward_given:
                        player_progress["cups"]=int(player_progress.get("cups",0))+arena_boss["reward"]
                        wins=list(player_progress.get("boss_wins",[]))
                        if arena_boss["name"] not in wins: wins.append(arena_boss["name"])
                        player_progress["boss_wins"]=wins
                        counts=dict(player_progress.get("boss_win_counts",{})); counts[arena_boss["name"]]=int(counts.get(arena_boss["name"],0))+1; player_progress["boss_win_counts"]=counts
                        if boss_difficulty=="NIGHTMARE" and arena_boss["name"] in {boss["name"] for boss in BOSS_TYPES}:
                            nightmare_wins=list(player_progress.get("nightmare_boss_wins",[]))
                            if arena_boss["name"] not in nightmare_wins: nightmare_wins.append(arena_boss["name"])
                            player_progress["nightmare_boss_wins"]=nightmare_wins
                            if len(set(nightmare_wins))>=6: player_progress["shadow_tarun_unlocked"]=True
                        save_progress(); refresh_achievements(); arena_reward_given=True
                        victory_stats={"boss":arena_boss["name"],"reward":arena_boss["reward"],"difficulty":boss_difficulty,"hearts":arena_player_health,"combo":arena_combo}
            elif shot[0]>SCREEN_WIDTH: arena_shots.remove(shot)
        for shot in arena_enemy_shots[:]:
            shot[0]+=shot[2]; shot[1]+=shot[3]
            sx,sy=int(shot[0]),int(shot[1]); attack_name=shot[5]
            colours={"ROBOT":((70,220,255),(255,255,255)),"GHOST":((180,70,255),(255,70,90)),"DRAGON":((255,65,20),(255,230,55)),"MONKEY":((80,230,90),(220,255,120)),"SNOW":((130,230,255),(255,255,255)),"ALIEN":((80,255,150),(180,100,255)),"SHADOW TARUN":((175,75,255),(255,215,70))}
            outer,inner=colours.get(attack_name,((175,75,255),(255,215,70)))
            pygame.draw.circle(screen,outer,(sx,sy),18); pygame.draw.circle(screen,inner,(sx,sy),8)
            pygame.draw.line(screen,outer,(sx-int(shot[2]*4),sy-int(shot[3]*4)),(sx,sy),8)
            if pygame.Rect(sx-14,sy-14,28,28).colliderect(pygame.Rect(110,int(arena_dino_y)-15,75,85)):
                arena_player_health-=shot[4]; arena_combo=0; arena_finisher_ready=False; rage_meter=min(100,rage_meter+20)
                arena_enemy_shots.remove(shot); play_sound(SOUND_COLLISION)
                if arena_player_health<=0: arena_message="BOSS WON - TRY AGAIN"; stop_boss_music()
            elif shot[0]<-20 or shot[1]>SCREEN_HEIGHT: arena_enemy_shots.remove(shot)
        if arena_death_start:
            draw_arena_boss_death(arena_boss["name"],boss_x,boss_y)
        equipped_power=player_progress.get("selected_boss_power","")
        power_button_text="POWER USED" if arena_power_used else ("USE POWER" if equipped_power else "NO POWER")
        shoot=Button(25,460,115,55,"SHOOT",(45,110,170)); jump_boss=Button(145,460,110,55,"JUMP / SPACE",(25,35,50)); finisher=Button(260,460,130,55,"FINISHER" if arena_finisher_ready else f"COMBO {arena_combo}/5",(170,75,35) if arena_finisher_ready else (70,70,78)); pet_ultimate=Button(400,460,145,55,"PET ULTIMATE",(45,145,100) if pet_ultimate_ready else (65,65,72)); power=Button(555,460,105,55,power_button_text,(75,55,150) if equipped_power and not arena_power_used else (65,65,72)); rage=Button(670,460,90,55,"RAGE",(190,65,25)); quit_boss=Button(770,460,90,55,"EXIT",(55,55,70))
        for button in (shoot,jump_boss,finisher,pet_ultimate,power,rage,quit_boss): button.draw(screen)
        if arena_message:
            msg=font_title.render(arena_message,True,GOLD if arena_health==0 else RED); screen.blit(msg,msg.get_rect(center=(480,180)))
            if arena_health==0:
                defeat_line=BOSS_DIALOGUE.get(arena_boss["name"],("", ""))[1]
                defeat_text=font_ui.render(defeat_line,True,(225,205,255)); screen.blit(defeat_text,defeat_text.get_rect(center=(480,220)))
            retry=Button(300,245,170,55,"PLAY AGAIN",GREEN); results_button=Button(490,245,170,55,"RESULTS",(55,105,165)); retry.draw(screen); results_button.draw(screen)
        for event in events:
            fire=shoot.is_clicked(mouse_pos,event) or (event.type==pygame.KEYDOWN and event.key==pygame.K_f)
            jump_pressed=jump_boss.is_clicked(mouse_pos,event) or (event.type==pygame.KEYDOWN and event.key in (pygame.K_SPACE,pygame.K_UP))
            if jump_pressed and not intro_active and not arena_message and not arena_is_jumping:
                arena_is_jumping=True; arena_dino_velocity=-14.0; play_sound(SOUND_JUMP); break
            if fire and not intro_active and not arena_message:
                sx,sy=195.0,420.0; dx,dy=boss_x-sx,boss_y-sy; dist=max(1,math.hypot(dx,dy)); arena_shots.append([sx,sy,dx/dist*15,dy/dist*15]); play_sound(SOUND_BUTTON); break
            if finisher.is_clicked(mouse_pos,event) and arena_finisher_ready and not arena_message:
                arena_health=max(0,arena_health-1500); arena_combo=0; arena_finisher_ready=False; play_sound(SOUND_VICTORY)
                if arena_health==0: start_arena_boss_death(arena_boss["name"],boss_x,boss_y); arena_message=f"YOU WON! +{arena_boss['reward']} CUPS"
                break
            if pet_ultimate.is_clicked(mouse_pos,event) and pet_ultimate_ready and active_companion and not arena_message:
                ultimate_damage=5000 if active_companion in SECRET_EGG_PETS else (4000 if battle_fusion else 3000)
                draw_pet_ultimate_effect(active_companion,100,arena_dino_y,boss_x,boss_y,0.75)
                arena_health=max(0,arena_health-ultimate_damage); pet_attack_count=0; pet_ultimate_ready=False
                boss_power_message=f"{active_companion} ULTIMATE: {ultimate_damage} DAMAGE"; boss_power_message_until=pygame.time.get_ticks()+2200; play_sound(SOUND_VICTORY)
                if active_companion in ("SNOW","ICE BULL","ICE LION"): arena_next_attack=pygame.time.get_ticks()+4500; arena_enemy_shots.clear()
                if arena_health==0: start_arena_boss_death(arena_boss["name"],boss_x,boss_y); arena_message=f"YOU WON! +{arena_boss['reward']} CUPS"
                break
            if power.is_clicked(mouse_pos,event) and not arena_power_used and not arena_message:
                selected_power=player_progress.get("selected_boss_power","")
                if not selected_power:
                    boss_power_message="EQUIP A BOSS POWER FIRST"
                    boss_power_message_until=pygame.time.get_ticks()+1800
                else:
                    if selected_power=="ROBOT":
                        arena_player_health=min(10,arena_player_health+2); boss_power_message="LASER ARMOUR: +2 HEARTS"
                    elif selected_power=="GHOST":
                        arena_enemy_shots.clear(); arena_dino_y=max(260.0,arena_dino_y-70); boss_power_message="SHADOW TELEPORT"
                    elif selected_power=="DRAGON":
                        arena_health=max(0,arena_health-1500); boss_power_message="FIRE BREATH: 1500 DAMAGE"
                    elif selected_power=="MONKEY":
                        arena_health=max(0,arena_health-1000); arena_enemy_shots.clear(); boss_power_message="GROUND SMASH: 1000 DAMAGE"
                    elif selected_power=="SNOW":
                        arena_next_attack=pygame.time.get_ticks()+5000; arena_enemy_shots.clear(); boss_power_message="FREEZE TIME: 5 SECONDS"
                    elif selected_power=="ALIEN":
                        arena_health=max(0,arena_health-1500); boss_power_message="TRIPLE PLASMA: 1500 DAMAGE"
                    arena_power_used=True
                    boss_power_message_until=pygame.time.get_ticks()+2200
                    play_sound(BOSS_AUDIO.get(selected_power,SOUND_VICTORY))
                    if arena_health==0:
                        start_arena_boss_death(arena_boss["name"],boss_x,boss_y)
                        arena_message=f"YOU WON! +{arena_boss['reward']} CUPS"
                        if not arena_reward_given:
                            player_progress["cups"]=int(player_progress.get("cups",0))+arena_boss["reward"]
                            wins=list(player_progress.get("boss_wins",[]))
                            if arena_boss["name"] not in wins: wins.append(arena_boss["name"])
                            player_progress["boss_wins"]=wins
                            counts=dict(player_progress.get("boss_win_counts",{})); counts[arena_boss["name"]]=int(counts.get(arena_boss["name"],0))+1; player_progress["boss_win_counts"]=counts
                            save_progress(); arena_reward_given=True
                break
            if rage.is_clicked(mouse_pos,event) and rage_meter>=100 and not arena_message:
                rage_meter=0; rage_active_until=pygame.time.get_ticks()+8000; play_sound(SOUND_VICTORY); break
            if quit_boss.is_clicked(mouse_pos,event): stop_boss_music(); current_state=GameState.ALL_BOSSES; break
            if arena_message and retry.is_clicked(mouse_pos,event): start_selected_boss(); break
            if arena_message and results_button.is_clicked(mouse_pos,event): current_state=GameState.VICTORY_RESULTS; break

    elif current_state == GameState.VICTORY_RESULTS:
        screen.fill((9,18,34)); pygame.draw.rect(screen,(18,40,68),(130,55,700,450),border_radius=25); pygame.draw.rect(screen,GOLD,(130,55,700,450),4,border_radius=25)
        title=font_title.render("BOSS DEFEATED",True,GOLD); screen.blit(title,title.get_rect(center=(480,105)))
        lines=[f"Boss: {victory_stats.get('boss','')}",f"Difficulty: {victory_stats.get('difficulty','NORMAL')}",f"Cups earned: {victory_stats.get('reward',0)}",f"Hearts remaining: {victory_stats.get('hearts',0)}",f"Best combo: {victory_stats.get('combo',0)}",f"Pet: {player_progress.get('selected_pet','None') or 'None'}"]
        for i,line in enumerate(lines): screen.blit(font_ui.render(line,True,WHITE),(300,165+i*43))
        again=Button(170,440,190,48,"PLAY AGAIN",GREEN); selection=Button(385,440,190,48,"BOSS SELECT",(55,95,150)); home=Button(600,440,190,48,"MAIN PAGE",(55,55,70))
        for b in (again,selection,home): b.draw(screen)
        for event in events:
            if again.is_clicked(mouse_pos,event): boss_loading_start=pygame.time.get_ticks(); current_state=GameState.BOSS_LOADING; break
            if selection.is_clicked(mouse_pos,event): stop_boss_music(); current_state=GameState.ALL_BOSSES; break
            if home.is_clicked(mouse_pos,event): stop_boss_music(); current_state=GameState.LOBBY; break

    # Dino Mansion: enter for 5 cups, receive +10 starting jumps, and use fusion skins.
    elif current_state == GameState.DINO_MANSION:
        screen.fill((23, 35, 55))
        # Mansion exterior.
        pygame.draw.rect(screen,(65,115,70),(0,450,SCREEN_WIDTH,150))
        pygame.draw.polygon(screen,(95,45,35),[(180,230),(400,85),(620,230)])
        pygame.draw.rect(screen,(225,190,135),(220,220,360,250),border_radius=8)
        pygame.draw.rect(screen,(120,65,35),(355,350,90,120),border_radius=10)
        for wx in (270,490):
            pygame.draw.rect(screen,(85,190,235),(wx,275,55,70)); pygame.draw.line(screen,WHITE,(wx+27,275),(wx+27,345),3); pygame.draw.line(screen,WHITE,(wx,310),(wx+55,310),3)
        pygame.draw.circle(screen,(255,220,90),(400,145),35)
        title=font_title.render("DINO MANSION",True,(255,240,170)); screen.blit(title,title.get_rect(center=(400,40)))
        cups=font_ui.render(f"Cups: {player_progress.get('cups',0)}",True,GOLD); screen.blit(cups,cups.get_rect(center=(400,76)))
        boost_owned=bool(player_progress.get("mansion_jump_boost",False))
        boost_text="+10 JUMPS READY" if boost_owned else "ENTER MANSION: 5 CUPS  |  NEXT RUN +10 JUMPS"
        enter=Button(245,485,310,46,boost_text,(45,145,85) if boost_owned else (150,90,35)); enter.draw(screen)

        fusion_defs=[
            ("FROSTFIRE","frostfire","fire_owned","ice_owned",(100,205,255)),
            ("GALAXY MECH","galaxy_mech","robot_owned","galaxy_owned",(140,75,235)),
            ("STORM NINJA","storm_ninja","ninja_owned","thunder_owned",(235,215,70)),
            ("VENOM CRYSTAL","venom_crystal","toxic_owned","extra_05_owned",(75,235,130)),
        ]
        fusion_buttons=[]
        for i,(label,fid,key1,key2,colour) in enumerate(fusion_defs):
            bx=25+i*195; by=535
            unlocked=bool(player_progress.get(key1,False) and player_progress.get(key2,False))
            text=label if unlocked else "LOCKED"
            b=Button(bx,by,180,38,text,colour if unlocked else (70,70,75),BLACK if unlocked else WHITE); b.draw(screen)
            fusion_buttons.append((b,fid,unlocked,label))
        back=Button(650,20,120,36,"BACK",(30,35,48)); back.draw(screen)
        for event in events:
            if enter.is_clicked(mouse_pos,event):
                if not boost_owned and int(player_progress.get("cups",0))>=5:
                    player_progress["cups"]-=5; player_progress["mansion_jump_boost"]=True; save_progress()
                break
            for button,fid,unlocked,label in fusion_buttons:
                if button.is_clicked(mouse_pos,event) and unlocked:
                    player_progress["fusion_skin"]=fid; save_progress(); break
            if back.is_clicked(mouse_pos,event): current_state=GameState.LOBBY; break

    # Pet egg shop.
    elif current_state == GameState.PETS:
        screen.fill((7,12,28)); now=pygame.time.get_ticks()
        for star in range(45): pygame.draw.circle(screen,(120,180,235),((star*79+23)%SCREEN_WIDTH,(star*43+17)%SCREEN_HEIGHT),1+star%2)
        title=font_title.render("PETS & EGGS",True,(220,245,255)); screen.blit(title,title.get_rect(center=(400,45)))
        cups=font_ui.render(f"Cups: {player_progress.get('cups',0)}",True,GOLD); screen.blit(cups,cups.get_rect(center=(400,80)))
        rarity=PET_RARITIES[pet_rarity_index]; card=pygame.Rect(185,105,430,310)
        pygame.draw.rect(screen,(14,25,48),card,border_radius=22); pygame.draw.rect(screen,rarity["colour"],card,4,border_radius=22)
        rtext=font_title.render(rarity["name"],True,rarity["colour"]); screen.blit(rtext,rtext.get_rect(center=(400,140)))
        ey=220+int(math.sin(now/250)*4); pygame.draw.ellipse(screen,(245,245,235),(352,158,96,130)); pygame.draw.ellipse(screen,rarity["colour"],(358,165,84,118),5)
        for i in range(6): pygame.draw.circle(screen,rarity["colour"],(375+(i*19)%55,195+(i*31)%70),5+i%3)
        names=font_sub.render(" | ".join(rarity["pets"]),True,WHITE); screen.blit(names,names.get_rect(center=(400,305)))
        bonus=font_sub.render(f"Unlock bonus: +{rarity['bonus']} cups",True,(180,220,255)); screen.blit(bonus,bonus.get_rect(center=(400,337)))
        owned=[p for p in rarity["pets"] if p in player_progress.get("owned_pets",[])]
        status=pygame.font.Font(None,22).render(f"Owned {len(owned)}/3",True,(170,235,190)); screen.blit(status,status.get_rect(center=(400,365)))
        buy=Button(300,380,200,42,f"OPEN - {rarity['cost']} CUPS",(145,88,15)); buy.draw(screen)
        prev=Button(105,210,60,70,"<",(25,50,80),(90,230,255)); nxt=Button(635,210,60,70,">",(25,50,80),(90,230,255)); prev.draw(screen); nxt.draw(screen)
        owned_buttons=[]; all_owned=list(player_progress.get("owned_pets",[]))
        if player_progress.get("secret_pet_unlocked",False): all_owned.append(SECRET_PET)
        for i,name in enumerate(all_owned[:6]):
            b=Button(55+(i%3)*245,435+(i//3)*45,215,36,("* " if player_progress.get("selected_pet")==name else "")+name,(45,110,95)); b.draw(screen); owned_buttons.append((b,name))
        back=Button(320,520,160,38,"BACK",(30,40,60)); back.draw(screen)
        if pet_message:
            msg=pygame.font.Font(None,21).render(pet_message,True,(255,230,120)); screen.blit(msg,msg.get_rect(center=(400,515)))
        for event in events:
            if prev.is_clicked(mouse_pos,event): pet_rarity_index=(pet_rarity_index-1)%4; pet_message=""; break
            if nxt.is_clicked(mouse_pos,event): pet_rarity_index=(pet_rarity_index+1)%4; pet_message=""; break
            if buy.is_clicked(mouse_pos,event):
                total=int(player_progress.get("cups",0))
                if total>=rarity["cost"]:
                    player_progress["cups"]=total-rarity["cost"]
                    unowned=[p for p in rarity["pets"] if p not in player_progress["owned_pets"]]
                    won=random.choice(unowned if unowned else rarity["pets"])
                    if won not in player_progress["owned_pets"]:
                        player_progress["owned_pets"].append(won); player_progress["selected_pet"]=won
                        reward=pet_bonus(won); player_progress["cups"]+=reward; pet_message=f"{won} unlocked! +{reward} cups"
                    else: pet_message=f"Duplicate {won}"
                    if all(p in player_progress["owned_pets"] for p in ALL_NORMAL_PETS) and not player_progress.get("secret_pet_unlocked",False):
                        player_progress["secret_pet_unlocked"]=True; player_progress["selected_pet"]=SECRET_PET; player_progress["cups"]+=50
                        pet_message="SECRET PET UNLOCKED: RAINBOW TIGER! +50 cups"
                    save_progress()
                else: pet_message="Not enough cups"
                break
            for button,name in owned_buttons:
                if button.is_clicked(mouse_pos,event): player_progress["selected_pet"]=name; save_progress(); pet_message=f"{name} equipped"; break
            if back.is_clicked(mouse_pos,event): current_state=GameState.LOBBY; break

    # Graphical skills carousel with Heart, Jump, Shield and Double Cups.
    elif current_state == GameState.SKILLS:
        now=pygame.time.get_ticks(); screen.fill((5,9,24))
        for star in range(55):
            sx=(star*83+37)%SCREEN_WIDTH; sy=(star*47+19)%430
            pygame.draw.circle(screen,(170,220,255),(sx,sy),1+star%2)
        pygame.draw.polygon(screen,(9,16,33),[(0,500),(120,400),(220,500),(340,405),(480,500),(650,390),(800,500)])
        title_panel=pygame.Rect(215,28,370,72)
        pygame.draw.rect(screen,(15,34,82),title_panel,border_radius=15); pygame.draw.rect(screen,(55,215,255),title_panel,3,border_radius=15)
        title=font_title.render("SKILLS",True,(225,245,255)); screen.blit(title,title.get_rect(center=title_panel.center))
        heart_level=min(MAX_HEARTS_LIMIT-BASE_MAX_HEALTH,int(player_progress.get("heart_upgrade",0))); jump_level=min(MAX_JUMP_LEVEL,int(player_progress.get("jump_upgrade",0)))
        shield_owned=bool(player_progress.get("shield_owned",False)); double_owned=bool(player_progress.get("double_cups_owned",False))
        edge,fill=[((255,65,105),(52,13,34)),((40,210,255),(8,35,65)),((95,155,255),(15,35,78)),((255,205,55),(78,48,8))][skill_index]
        card=pygame.Rect(230,125,340,285); pygame.draw.rect(screen,fill,card,border_radius=22); pygame.draw.rect(screen,edge,card,4,border_radius=22)
        owned=False
        if skill_index==0:
            heading="+1 HEART"; description="Increase maximum health by 1"; cost=10
            hp=[(400,290),(335,230),(355,190),(400,220),(445,190),(465,230)]
            pygame.draw.polygon(screen,(235,38,72),hp); pygame.draw.polygon(screen,(255,112,135),hp,4)
            pygame.draw.rect(screen,WHITE,(438,226,18,58),border_radius=5); pygame.draw.rect(screen,WHITE,(418,246,58,18),border_radius=5)
            heart_total=min(MAX_HEARTS_LIMIT,BASE_MAX_HEALTH+heart_level)
            level_text="MAX LEVEL  Hearts 10/10" if heart_total>=MAX_HEARTS_LIMIT else f"Level {heart_level}  Hearts {heart_total}/10"
            owned=heart_total>=MAX_HEARTS_LIMIT
        elif skill_index==1:
            heading="JUMP +1"; description="Increase jump height by 1"; cost=20
            pygame.draw.circle(screen,(20,50,80),(400,225),34); pygame.draw.circle(screen,(80,230,255),(400,225),34,4)
            for ax,ay in ((455,255),(485,225)):
                pygame.draw.polygon(screen,(100,235,255),[(ax,ay-30),(ax-16,ay-8),(ax-6,ay-8),(ax-6,ay+20),(ax+6,ay+20),(ax+6,ay-8),(ax+16,ay-8)])
            level_text="MAX LEVEL 10/10" if jump_level>=MAX_JUMP_LEVEL else f"Level {jump_level}/10  Power {abs(JUMP_STRENGTH)+jump_level}"
            owned=jump_level>=MAX_JUMP_LEVEL
        elif skill_index==2:
            heading="SHIELD"; description="Block one collision every run"; cost=30; owned=shield_owned
            pulse=4+int(3*math.sin(now/160)); pts=[(400,180),(465,205),(450,270),(400,300),(350,270),(335,205)]
            pygame.draw.circle(screen,(80,190,255),(400,235),70+pulse,3); pygame.draw.polygon(screen,(35,105,205),pts); pygame.draw.polygon(screen,(120,225,255),pts,5)
            pygame.draw.line(screen,WHITE,(400,205),(400,278),5); pygame.draw.line(screen,WHITE,(372,241),(428,241),5)
            level_text="OWNED - One shield each run" if owned else "Blocks one hit per run"
        else:
            heading="DOUBLE CUPS"; description="Double victory cup rewards"; cost=40; owned=double_owned
            for radius,colour in ((62,(125,75,12)),(52,(255,180,20)),(42,(255,225,75))): pygame.draw.circle(screen,colour,(400,235),radius)
            two=pygame.font.SysFont("Arial",54,bold=True).render("2X",True,(95,55,5)); screen.blit(two,two.get_rect(center=(400,235)))
            level_text="OWNED - Rewards doubled" if owned else "Permanently doubles victory cups"
        heading_surface=font_title.render(heading,True,WHITE); screen.blit(heading_surface,heading_surface.get_rect(center=(400,160)))
        desc=font_sub.render(description,True,(235,240,250)); screen.blit(desc,desc.get_rect(center=(400,325)))
        level=pygame.font.Font(None,22).render(level_text,True,(170,220,245)); screen.blit(level,level.get_rect(center=(400,352)))
        buy_text="OWNED" if owned else f"{cost} CUPS"; buy=Button(305,370,190,48,buy_text,(45,145,85) if owned else (145,88,15),WHITE); buy.draw(screen)
        prev=Button(135,220,65,75,"<",(22,43,70),(90,230,255)); nxt=Button(600,220,65,75,">",(22,43,70),(90,230,255)); prev.draw(screen); nxt.draw(screen)
        for dot in range(4): pygame.draw.circle(screen,(55,220,255) if dot==skill_index else (80,95,120),(355+dot*30,430),7)
        status=pygame.Rect(90,455,620,52); pygame.draw.rect(screen,(8,25,48),status,border_radius=14); pygame.draw.rect(screen,(50,210,255),status,2,border_radius=14)
        screen.blit(font_ui.render(f"CUPS {player_progress.get('cups',0)}",True,GOLD),(125,471)); screen.blit(font_ui.render(f"HEARTS {min(MAX_HEARTS_LIMIT,BASE_MAX_HEALTH+heart_level)}/10",True,(255,110,140)),(330,471)); screen.blit(font_ui.render(f"JUMP LV {jump_level}/10",True,(100,230,255)),(535,471))
        back=Button(320,515,160,42,"BACK",(25,35,55),WHITE); back.draw(screen)
        for event in events:
            if prev.is_clicked(mouse_pos,event): skill_index=(skill_index-1)%4; break
            if nxt.is_clicked(mouse_pos,event): skill_index=(skill_index+1)%4; break
            if buy.is_clicked(mouse_pos,event):
                cups_now=int(player_progress.get("cups",0))
                if not owned and cups_now>=cost:
                    player_progress["cups"]=cups_now-cost
                    if skill_index==0 and BASE_MAX_HEALTH+heart_level<MAX_HEARTS_LIMIT:
                        player_progress["heart_upgrade"]=heart_level+1
                    elif skill_index==1 and jump_level<MAX_JUMP_LEVEL: player_progress["jump_upgrade"]=min(MAX_JUMP_LEVEL,jump_level+1)
                    elif skill_index==2: player_progress["shield_owned"]=True
                    else: player_progress["double_cups_owned"]=True
                    save_progress()
                break
            if back.is_clicked(mouse_pos,event): current_state=GameState.LOBBY; break

    # 2. Level Selection State
    elif current_state == GameState.LEVEL_SELECT:
        screen.fill(WHITE)

        txt = font_title.render("Select Difficulty", True, BLACK)
        screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 100))

        easy_button = Button(250, 180, 300, 50, "EASY - NORMAL SPEED", GREEN)
        medium_button = Button(250, 245, 300, 50, "MEDIUM - FASTER", GOLD, BLACK)
        hard_button = Button(250, 310, 300, 50, "HARD - VERY FAST", RED)
        mode_text = "METEOR SHOWER: ON" if meteor_shower_mode else "METEOR SHOWER: OFF"
        mode_colour = (85, 85, 170) if meteor_shower_mode else (110, 110, 110)
        meteor_mode_button = Button(250, 385, 300, 50, mode_text, mode_colour)
        back_button = Button(300, 455, 200, 46, "BACK", BLACK)

        easy_button.draw(screen)
        medium_button.draw(screen)
        hard_button.draw(screen)
        meteor_mode_button.draw(screen)
        back_button.draw(screen)

        for event in events:
            if easy_button.is_clicked(mouse_pos, event):
                selected_difficulty = "EASY"
                obstacle_speed = DIFFICULTY_SPEEDS[selected_difficulty]
                current_state = GameState.READY_SCREEN
                break
            if medium_button.is_clicked(mouse_pos, event):
                selected_difficulty = "MEDIUM"
                obstacle_speed = DIFFICULTY_SPEEDS[selected_difficulty]
                current_state = GameState.READY_SCREEN
                break
            if hard_button.is_clicked(mouse_pos, event):
                selected_difficulty = "HARD"
                obstacle_speed = DIFFICULTY_SPEEDS[selected_difficulty]
                current_state = GameState.READY_SCREEN
                break
            if meteor_mode_button.is_clicked(mouse_pos, event):
                meteor_shower_mode = not meteor_shower_mode
                break
            if back_button.is_clicked(mouse_pos, event):
                current_state = GameState.LOBBY
                break

    # 3. Ready Screen State
    elif current_state == GameState.READY_SCREEN:
        screen.fill(WHITE)

        txt = font_title.render("Are you ready for the adventure?", True, BLACK)
        screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 160))

        level_text = font_sub.render(
            f"Level: {selected_difficulty}   Meteor Shower: {'ON' if meteor_shower_mode else 'OFF'}",
            True,
            BLACK,
        )
        screen.blit(
            level_text,
            (SCREEN_WIDTH // 2 - level_text.get_width() // 2, 235),
        )

        btn_start_adv = Button(
            SCREEN_WIDTH // 2 - 100,
            320,
            200,
            50,
            "START",
            GREEN,
        )
        btn_start_adv.draw(screen)

        for event in events:
            if btn_start_adv.is_clicked(mouse_pos, event):
                reset_game()
                current_state = GameState.PLAYING
                break

    # 3. Playing State
    elif current_state == GameState.PLAYING:
        update_environment()
        current_sky_color, night_progress = get_current_color(
            jump_count,
            COLOR_DAY_SKY,
            COLOR_SUNSET_SKY,
            COLOR_NIGHT_SKY,
        )
        current_ground_color, _ = get_current_color(
            jump_count,
            COLOR_DAY_GROUND,
            COLOR_SUNSET_GROUND,
            COLOR_NIGHT_GROUND,
        )

        screen.fill(current_sky_color)
        draw_parallax_background(current_ground_color, night_progress)

        if night_progress > 0.3:
            star_intensity = min(1.0, (night_progress - 0.3) / 0.7)
            animation_time = pygame.time.get_ticks() / 1000.0

            # Soft moon halo built from translucent concentric circles.
            moon_layer = pygame.Surface(
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                pygame.SRCALPHA,
            )
            for glow_radius, glow_alpha in ((62, 10), (52, 18), (43, 28)):
                pygame.draw.circle(
                    moon_layer,
                    (225, 235, 255, int(glow_alpha * star_intensity)),
                    (650, 100),
                    glow_radius,
                )
            moon_colour = tuple(
                int(component * star_intensity) for component in MOON_COLOR
            )
            pygame.draw.circle(moon_layer, (*moon_colour, 255), (650, 100), 35)
            pygame.draw.circle(
                moon_layer,
                (225, 225, 205, int(90 * star_intensity)),
                (639, 91),
                6,
            )
            pygame.draw.circle(
                moon_layer,
                (225, 225, 205, int(75 * star_intensity)),
                (662, 111),
                4,
            )
            screen.blit(moon_layer, (0, 0))

            # Stars brighten individually and twinkle subtly rather than flashing.
            star_layer = pygame.Surface(
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                pygame.SRCALPHA,
            )
            for star in stars:
                twinkle = 0.82 + 0.18 * math.sin(
                    animation_time * star["twinkle_speed"] + star["twinkle_phase"]
                )
                alpha = int(255 * star_intensity * star["brightness"] * twinkle)
                colour = (*star["colour"], max(0, min(255, alpha)))
                position = (star["x"], star["y"])
                pygame.draw.circle(star_layer, colour, position, star["radius"])

                # Only the brightest stars receive a restrained cross-shaped flare.
                if star["radius"] == 3 and alpha > 180:
                    flare_colour = (*star["colour"], alpha // 3)
                    pygame.draw.line(
                        star_layer,
                        flare_colour,
                        (star["x"] - 5, star["y"]),
                        (star["x"] + 5, star["y"]),
                    )
                    pygame.draw.line(
                        star_layer,
                        flare_colour,
                        (star["x"], star["y"] - 5),
                        (star["x"], star["y"] + 5),
                    )
            screen.blit(star_layer, (0, 0))
            update_and_draw_shooting_star(screen, star_intensity)
            update_and_draw_meteor_shower(screen, star_intensity)
            update_and_draw_alien_ship(screen, star_intensity)

        # Cancel an active meteor as daylight returns.
        elif shooting_star["active"]:
            shooting_star["active"] = False
            next_shooting_star_time = (
                pygame.time.get_ticks() + star_generator.randint(3500, 8500)
            )


        if safe_spawn_timer > 0:
            safe_spawn_timer -= 1

        base_speed = DIFFICULTY_SPEEDS[selected_difficulty]
        obstacle_speed = min(base_speed + jump_count // 80, base_speed + 8)

        was_jumping = is_jumping
        if is_jumping:
            dino_y += dino_velocity_y
            dino_velocity_y += GRAVITY
            if dino_y >= 400:
                dino_y = 400
                is_jumping = False
                for _ in range(12):
                    dust_particles.append({"x": dino_x + 20, "y": 455, "vx": random.uniform(-2.5, 2.5), "vy": random.uniform(-1.8, -0.3), "life": random.randint(12, 25)})

        boss_battle_active = jump_count >= 300 and not boss_defeated

        if boss_battle_active:
            update_and_draw_boss_timer()
            if current_state == GameState.ENTER_NAME:
                continue

        # Normal obstacles stop completely while the boss battle is active.
        if not boss_battle_active:
            obstacle_x -= obstacle_speed
        else:
            obstacle_x = SCREEN_WIDTH + 300

        obstacle_y = 320 if obstacle_type == "kite" else 410

        if not boss_battle_active and obstacle_x < -150:
            if golden_obstacle:
                perfect_jump_message_until=pygame.time.get_ticks()+1800
            obstacle_x = SCREEN_WIDTH + 100
            golden_obstacle = random.randint(1,50) == 1

            ground_types = ["spike", "rock", "cactus", "fire", "log"]
            obstacle_type = random.choice(ground_types + (["kite"] if jump_count >= 200 else []))
            if obstacle_type == "spike":
                spike_count = random.choice([1, 2, 3])
                obstacle_width = single_spike_width * spike_count
            elif obstacle_type == "log":
                spike_count = 1
                obstacle_width = 70
            else:
                spike_count = 1
                obstacle_width = 58 if obstacle_type != "kite" else single_spike_width

        if safe_spawn_timer == 0:
            dino_rect = pygame.Rect(dino_x, dino_y, dino_width, dino_height)
            obstacle_rect = pygame.Rect(
                obstacle_x,
                obstacle_y,
                obstacle_width,
                obstacle_height,
            )

            boss_hit = update_boss()
            obstacle_hit = (
                not boss_battle_active
                and dino_rect.colliderect(obstacle_rect)
            )
            if (obstacle_hit or boss_hit) and pygame.time.get_ticks() >= invincible_until:
                play_sound(SOUND_COLLISION)
                if shield_available:
                    shield_available=False
                    invincible_until=pygame.time.get_ticks()+1300
                else:
                    player_health -= 1
                    invincible_until = pygame.time.get_ticks() + 1800
                if obstacle_hit:
                    obstacle_x = SCREEN_WIDTH + 180
                if player_health <= 0:
                    current_state = GameState.ENTER_NAME
        else:
            update_boss()

        update_dino_projectiles()
        update_bullet_effects()
        update_boss_defeat_effect()
        draw_dinosaur(dino_x, dino_y, jumping=is_jumping, animated=True)
        if shield_available:
            shield_layer=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
            pulse=4+int(3*math.sin(pygame.time.get_ticks()/160.0))
            pygame.draw.circle(shield_layer,(70,190,255,32),(dino_x+20,int(dino_y+20)),52+pulse)
            pygame.draw.circle(shield_layer,(100,225,255,180),(dino_x+20,int(dino_y+20)),48+pulse,3)
            screen.blit(shield_layer,(0,0))
        equipped_pet=player_progress.get("selected_pet","")
        equipped_fusion=player_progress.get("selected_pet_fusion","")
        equipped_secret=player_progress.get("selected_secret_pet","")
        if equipped_fusion:
            draw_fused_pet(equipped_fusion,dino_x-58,dino_y+28)
        elif equipped_secret:
            base={"SHADOW DRAGON":"EAGLE","ROBOT TIGER":"TIGER","COSMIC EAGLE":"EAGLE","ICE LION":"LION"}.get(equipped_secret,"EAGLE")
            draw_pet(base,dino_x-58,dino_y-42 if "EAGLE" in equipped_secret or "DRAGON" in equipped_secret else dino_y+35)
        elif equipped_pet:
            draw_pet(equipped_pet,dino_x-58,dino_y-45 if equipped_pet in ("VULTURE","EAGLE","OWL") else dino_y+35)
        gameplay_companion=player_progress.get("selected_boss_companion","")
        if gameplay_companion in unlocked_boss_companions(): draw_boss_companion(gameplay_companion,dino_x-105,dino_y+20)

        if not boss_battle_active:
            draw_obstacle(obstacle_x, obstacle_y, obstacle_type, spike_count)
            if golden_obstacle:
                glow=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
                pygame.draw.rect(glow,(255,210,45,65),(int(obstacle_x)-8,int(obstacle_y)-8,int(obstacle_width)+16,68),border_radius=10)
                pygame.draw.rect(glow,(255,235,90,220),(int(obstacle_x)-8,int(obstacle_y)-8,int(obstacle_width)+16,68),3,border_radius=10)
                screen.blit(glow,(0,0))
        update_dust()
        draw_weather_effects()

        ui_text_color = WHITE if night_progress > 0.5 else BLACK
        txt_jumps = font_ui.render(
            f"Jumps: {jump_count} / 1000",
            True,
            ui_text_color,
        )
        screen.blit(txt_jumps, (30, 20))
        if shield_available:
            screen.blit(pygame.font.Font(None,22).render("SHIELD READY",True,(90,225,255)),(30,150))
        if player_progress.get("double_cups_owned",False):
            screen.blit(pygame.font.Font(None,24).render("2X CUPS",True,GOLD),(30,176))
        if pygame.time.get_ticks() < perfect_jump_message_until:
            perfect=font_title.render("PERFECT JUMP!",True,GOLD); screen.blit(perfect,perfect.get_rect(center=(400,105)))
        txt_level = font_ui.render(f"Level: {selected_difficulty}", True, ui_text_color)
        screen.blit(txt_level, (30, 52))
        speed_text = pygame.font.Font(None, 20).render(f"Speed: {obstacle_speed}", True, ui_text_color)
        screen.blit(speed_text, (30, 122))
        draw_hearts()
        draw_progress_bar()

        btn_shoot = Button(
            SCREEN_WIDTH // 2 - 250,
            470,
            150,
            58,
            "SHOOT",
            (45, 110, 155),
        )
        btn_jump = Button(
            SCREEN_WIDTH // 2 - 80,
            470,
            180,
            58,
            "JUMP / SPACE",
            BLACK,
        )
        btn_pause = Button(
            SCREEN_WIDTH // 2 + 110,
            470,
            150,
            58,
            "PAUSE",
            (65, 70, 90),
        )
        btn_shoot.draw(screen)
        btn_jump.draw(screen)
        btn_pause.draw(screen)

        if jump_count < 300:
            shoot_hint = pygame.font.Font(None, 18).render(
                "Gun activates at boss: 300 jumps",
                True,
                ui_text_color,
            )
            screen.blit(
                shoot_hint,
                shoot_hint.get_rect(center=(SCREEN_WIDTH // 2 - 200, 455)),
            )

        triggered_jump = False
        triggered_shot = False
        pause_requested = False
        for event in events:
            if btn_shoot.is_clicked(mouse_pos, event):
                triggered_shot = True
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                triggered_shot = True
                break
            if btn_pause.is_clicked(mouse_pos, event):
                pause_requested = True
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                pause_requested = True
                break
            if btn_jump.is_clicked(mouse_pos, event):
                triggered_jump = True
                break
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_UP):
                triggered_jump = True
                break

        if triggered_shot:
            fire_dino_gun()

        if pause_requested:
            paused_game_frame = screen.copy()
            current_state = GameState.PAUSED
            continue

        if triggered_jump and not is_jumping:
            play_sound(SOUND_JUMP)
            is_jumping = True
            dino_velocity_y = JUMP_STRENGTH - int(player_progress.get("jump_upgrade", 0))
            jump_count += 10

            if jump_count == 10 and not has_paused_first_jump:
                current_state = GameState.PAUSE_FIRST_JUMP
                has_paused_first_jump = True

            if jump_count >= 1000 and boss_defeated:
                if not cup_awarded_this_run:
                    cup_rewards = {"EASY": 1, "MEDIUM": 5, "HARD": 20}
                    cups_earned = cup_rewards.get(selected_difficulty, 1)
                    if player_progress.get("double_cups_owned",False): cups_earned *= 2
                    player_progress["cups"] = int(player_progress.get("cups", 0)) + cups_earned
                    cup_awarded_this_run = True
                    save_progress()
                play_sound(SOUND_VICTORY)
                reset_fireworks()
                current_state = GameState.VICTORY

    # Manual Pause State
    elif current_state == GameState.PAUSED:
        screen.fill((24, 30, 48))
        panel = pygame.Rect(150, 120, 500, 360)
        pygame.draw.rect(screen, (245, 245, 235), panel, border_radius=16)
        pygame.draw.rect(screen, GOLD, panel, width=4, border_radius=16)

        pause_title = font_title.render("GAME PAUSED", True, BLACK)
        screen.blit(pause_title, pause_title.get_rect(center=(SCREEN_WIDTH // 2, 175)))
        pause_info = font_sub.render(
            f"Level: {selected_difficulty}   Jumps: {jump_count} / 1000", True, BLACK
        )
        screen.blit(pause_info, pause_info.get_rect(center=(SCREEN_WIDTH // 2, 235)))

        btn_pause_resume = Button(290, 290, 220, 52, "RESUME", GREEN)
        btn_pause_menu = Button(290, 365, 220, 52, "MAIN MENU", BLACK)
        btn_pause_resume.draw(screen)
        btn_pause_menu.draw(screen)

        for event in events:
            if btn_pause_resume.is_clicked(mouse_pos, event):
                resume_countdown_start = pygame.time.get_ticks()
                current_state = GameState.RESUME_COUNTDOWN
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                resume_countdown_start = pygame.time.get_ticks()
                current_state = GameState.RESUME_COUNTDOWN
                break
            if btn_pause_menu.is_clicked(mouse_pos, event):
                reset_game()
                current_state = GameState.LOBBY
                break

    # Five-second countdown before returning from manual pause.
    elif current_state == GameState.RESUME_COUNTDOWN:
        # Show the frozen game behind a translucent countdown overlay.
        if paused_game_frame is not None:
            screen.blit(paused_game_frame, (0, 0))
        else:
            screen.fill((24, 30, 48))

        countdown_overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.SRCALPHA,
        )
        countdown_overlay.fill((10, 15, 30, 145))
        screen.blit(countdown_overlay, (0, 0))

        elapsed_seconds = (pygame.time.get_ticks() - resume_countdown_start) / 1000.0
        remaining_seconds = max(0, 5 - int(elapsed_seconds))

        countdown_title = font_title.render("GET READY", True, GOLD)
        screen.blit(
            countdown_title,
            countdown_title.get_rect(center=(SCREEN_WIDTH // 2, 185)),
        )

        countdown_font = pygame.font.SysFont("Arial", 120, bold=True)
        countdown_text = countdown_font.render(str(remaining_seconds), True, WHITE)
        screen.blit(
            countdown_text,
            countdown_text.get_rect(center=(SCREEN_WIDTH // 2, 320)),
        )

        info_text = font_sub.render("Gameplay resumes automatically", True, WHITE)
        screen.blit(
            info_text,
            info_text.get_rect(center=(SCREEN_WIDTH // 2, 420)),
        )

        if elapsed_seconds >= 5.0:
            current_state = GameState.PLAYING

    # 4. Pause First Jump State
    elif current_state == GameState.PAUSE_FIRST_JUMP:
        pygame.draw.rect(screen, WHITE, (150, 150, 500, 300), border_radius=12)
        pygame.draw.rect(
            screen,
            BLACK,
            (150, 150, 500, 300),
            width=3,
            border_radius=12,
        )

        txt_congrats = font_title.render("Congratulations!", True, GREEN)
        screen.blit(
            txt_congrats,
            (SCREEN_WIDTH // 2 - txt_congrats.get_width() // 2, 180),
        )

        txt_msg = font_sub.render("You made your first jump!", True, BLACK)
        screen.blit(
            txt_msg,
            (SCREEN_WIDTH // 2 - txt_msg.get_width() // 2, 250),
        )

        btn_resume = Button(
            SCREEN_WIDTH // 2 - 100,
            360,
            200,
            50,
            "RESUME",
            GREEN,
        )
        btn_resume.draw(screen)

        for event in events:
            if btn_resume.is_clicked(mouse_pos, event):
                current_state = GameState.PLAYING
                break

    # 5. Victory State
    elif current_state == GameState.VICTORY:
        # Night-sky celebration background.
        for row in range(SCREEN_HEIGHT):
            ratio = row / SCREEN_HEIGHT
            victory_colour = (
                int(8 + 20 * ratio),
                int(12 + 24 * ratio),
                int(35 + 40 * ratio),
            )
            pygame.draw.line(screen, victory_colour, (0, row), (SCREEN_WIDTH, row))

        update_victory_fireworks()

        txt_victory = font_title.render(
            "Victory! You completed the adventure!",
            True,
            GOLD,
        )
        victory_shadow = font_title.render(
            "Victory! You completed the adventure!", True, BLACK
        )
        title_x = SCREEN_WIDTH // 2 - txt_victory.get_width() // 2
        screen.blit(victory_shadow, (title_x + 3, 183))
        screen.blit(txt_victory, (title_x, 180))

        draw_cup(SCREEN_WIDTH // 2 - 30, 260)

        btn_restart = Button(
            SCREEN_WIDTH // 2 - 100,
            390,
            200,
            50,
            "PLAY AGAIN",
            GREEN,
        )
        btn_restart.draw(screen)

        btn_victory_lobby = Button(
            SCREEN_WIDTH // 2 - 100,
            460,
            200,
            50,
            "MAIN MENU",
            BLACK,
        )
        btn_victory_lobby.draw(screen)

        for event in events:
            if btn_restart.is_clicked(mouse_pos, event):
                reset_game()
                current_state = GameState.LEVEL_SELECT
                break
            if btn_victory_lobby.is_clicked(mouse_pos, event):
                current_state = GameState.LOBBY
                break

    # 6. Enter Name State
    elif current_state == GameState.ENTER_NAME:
        screen.fill(LIGHT_GRAY)

        txt_game_over = font_title.render("Game Over!", True, RED)
        screen.blit(
            txt_game_over,
            (SCREEN_WIDTH // 2 - txt_game_over.get_width() // 2, 120),
        )

        txt_score = font_sub.render(
            f"Your score: {jump_count} jumps",
            True,
            BLACK,
        )
        screen.blit(
            txt_score,
            (SCREEN_WIDTH // 2 - txt_score.get_width() // 2, 190),
        )

        txt_prompt = font_sub.render("Enter your name:", True, BLACK)
        screen.blit(
            txt_prompt,
            (SCREEN_WIDTH // 2 - txt_prompt.get_width() // 2, 250),
        )

        name_box = pygame.Rect(SCREEN_WIDTH // 2 - 150, 300, 300, 50)
        pygame.draw.rect(screen, WHITE, name_box, border_radius=8)
        pygame.draw.rect(
            screen,
            BLACK,
            name_box,
            width=2,
            border_radius=8,
        )

        displayed_name = player_name if player_name else "Type your name"
        name_color = BLACK if player_name else (140, 140, 140)
        name_surface = font_ui.render(displayed_name, True, name_color)
        screen.blit(
            name_surface,
            (
                name_box.x + 10,
                name_box.y + name_box.height // 2 - name_surface.get_height() // 2,
            ),
        )

        btn_save_score = Button(
            SCREEN_WIDTH // 2 - 100,
            390,
            200,
            50,
            "SAVE SCORE",
            GREEN,
        )
        btn_save_score.draw(screen)

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                elif event.key == pygame.K_RETURN:
                    submit_score()
                    break
                elif event.unicode.isprintable() and len(player_name) < 15:
                    player_name += event.unicode
            elif btn_save_score.is_clicked(mouse_pos, event):
                submit_score()
                break

    # Skin category page.
    elif current_state == GameState.SKIN_MENU:
        screen.fill((220, 235, 250))
        title = font_title.render("Choose Skin Type", True, BLACK)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 95)))
        btn_dino_skins = Button(300, 190, 360, 70, "DINO SKINS", GREEN)
        btn_gun_skins = Button(300, 285, 360, 70, "GUN SKINS", (45, 105, 200))
        btn_skin_menu_back = Button(380, 405, 200, 50, "BACK", BLACK)
        btn_dino_skins.draw(screen)
        btn_gun_skins.draw(screen)
        btn_skin_menu_back.draw(screen)
        for event in events:
            if btn_dino_skins.is_clicked(mouse_pos, event):
                shop_skin_index = 0
                current_state = GameState.SKINS
                break
            if btn_gun_skins.is_clicked(mouse_pos, event):
                gun_skin_index = 0
                current_state = GameState.GUN_SKINS
                break
            if btn_skin_menu_back.is_clicked(mouse_pos, event):
                current_state = GameState.ALL_MENU
                break

    # Gun skins shop with 61 selectable skins.
    elif current_state == GameState.GUN_SKINS:
        screen.fill((225, 235, 245))
        gun_skin = GUN_SKINS[gun_skin_index]
        title = font_title.render("Gun Skins", True, BLACK)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 48)))
        cups_text = font_ui.render(f"Cups: {player_progress.get('cups', 0)}", True, GOLD)
        screen.blit(cups_text, cups_text.get_rect(center=(SCREEN_WIDTH // 2, 88)))
        # Large gun preview.
        preview_index = gun_skin_index
        if gun_skin["id"] == "gun_cosmic":
            cosmic_time = pygame.time.get_ticks()
            pulse = 0.5 + 0.5 * math.sin(cosmic_time / 160.0)
            # Space-card backdrop and layered neon aura.
            cosmic_panel = pygame.Surface((390, 145), pygame.SRCALPHA)
            cosmic_panel.fill((10, 6, 28, 225))
            pygame.draw.rect(cosmic_panel, (100, 55, 210, 220), cosmic_panel.get_rect(), 3, border_radius=18)
            for star in range(34):
                sx = (star * 71 + 19) % 390
                sy = (star * 43 + 11) % 145
                pygame.draw.circle(cosmic_panel, (200, 225, 255, 110 + star % 120), (sx, sy), 1 + star % 2)
            screen.blit(cosmic_panel, (285, 125))
            aura = pygame.Surface((360, 120), pygame.SRCALPHA)
            for radius, alpha in ((72, 16), (53, 24), (35, 42)):
                pygame.draw.circle(aura, (125, 45, 255, alpha), (270, 50), radius)
            screen.blit(aura, (300, 125))
            pygame.draw.rect(screen, (25, 10, 58), (345, 157, 220, 50), border_radius=14)
            pygame.draw.rect(screen, (72, 24, 145), (365, 166, 180, 32), border_radius=12)
            pygame.draw.rect(screen, (13, 6, 32), (540, 165, 100, 34), border_radius=9)
            pygame.draw.polygon(screen, (38, 16, 78), [(395,200),(450,200),(440,258),(400,245)])
            pygame.draw.line(screen, (75, 225, 255), (370, 165), (548, 165), 5)
            pygame.draw.line(screen, (255, 70, 225), (380, 198), (540, 198), 3)
            core = (180 + int(75 * pulse), 80 + int(95 * pulse), 255)
            pygame.draw.circle(screen, core, (475, 181), 17)
            pygame.draw.circle(screen, WHITE, (475, 181), 5)
            pygame.draw.circle(screen, (75, 235, 255), (632, 182), 11)
            for star in range(9):
                angle = cosmic_time / 350.0 + star * math.tau / 9
                sx = 475 + int(math.cos(angle) * (70 + star % 3 * 12))
                sy = 181 + int(math.sin(angle) * (25 + star % 2 * 8))
                pygame.draw.circle(screen, WHITE if star % 2 == 0 else (100,210,255), (sx,sy), 2)
        else:
            if preview_index == 0:
                preview_main, preview_dark, preview_glow = (65,70,78), (42,45,52), (80,220,255)
            else:
                preview_main = (55 + preview_index * 47 % 190, 55 + preview_index * 83 % 190, 55 + preview_index * 113 % 190)
                preview_dark = tuple(max(20, value - 45) for value in preview_main)
                preview_glow = (80 + preview_index * 31 % 176, 80 + preview_index * 67 % 176, 80 + preview_index * 97 % 176)
            pygame.draw.rect(screen, preview_main, (365, 150, 190, 45), border_radius=9)
            pygame.draw.rect(screen, preview_dark, (535, 158, 95, 28), border_radius=6)
            pygame.draw.rect(screen, preview_dark, (410, 190, 40, 70), border_radius=6)
            pygame.draw.circle(screen, preview_glow, (615, 172), 8)
        name_text = font_ui.render(gun_skin["name"], True, BLACK)
        screen.blit(name_text, name_text.get_rect(center=(SCREEN_WIDTH // 2, 290)))
        counter = pygame.font.Font(None, 22).render(f"Gun {gun_skin_index + 1} of {len(GUN_SKINS)}", True, BLACK)
        screen.blit(counter, counter.get_rect(center=(SCREEN_WIDTH // 2, 320)))
        btn_prev_gun = Button(220, 165, 70, 60, "<", BLACK)
        btn_next_gun = Button(670, 165, 70, 60, ">", BLACK)
        btn_prev_gun.draw(screen)
        btn_next_gun.draw(screen)
        gun_owned = bool(player_progress.get(gun_skin["owned_key"], False))
        if gun_owned:
            gun_action_text = "EQUIPPED" if selected_gun_skin == gun_skin["id"] else "EQUIP"
            gun_action_colour = GREEN
        else:
            gun_action_text = f"BUY - {gun_skin['cost']} CUPS"
            gun_action_colour = GOLD
        btn_gun_action = Button(330, 350, 300, 55, gun_action_text, gun_action_colour, BLACK)
        btn_gun_back = Button(380, 445, 200, 50, "BACK", BLACK)
        btn_gun_action.draw(screen)
        btn_gun_back.draw(screen)
        for event in events:
            if btn_prev_gun.is_clicked(mouse_pos, event):
                gun_skin_index = (gun_skin_index - 1) % len(GUN_SKINS)
                break
            if btn_next_gun.is_clicked(mouse_pos, event):
                gun_skin_index = (gun_skin_index + 1) % len(GUN_SKINS)
                break
            if btn_gun_action.is_clicked(mouse_pos, event):
                if gun_owned:
                    selected_gun_skin = gun_skin["id"]
                    player_progress["selected_gun_skin"] = selected_gun_skin
                    save_progress()
                elif int(player_progress.get("cups", 0)) >= gun_skin["cost"]:
                    player_progress["cups"] -= gun_skin["cost"]
                    player_progress[gun_skin["owned_key"]] = True
                    selected_gun_skin = gun_skin["id"]
                    player_progress["selected_gun_skin"] = selected_gun_skin
                    save_progress()
                break
            if btn_gun_back.is_clicked(mouse_pos, event):
                current_state = GameState.COLLECTION
                break

    # Skins Shop State
    elif current_state == GameState.SKINS:
        screen.fill((225, 235, 250))
        skins = [
            {"id": "spider", "name": "SPIDER DINO", "cost": 1, "owned_key": "spider_owned"},
            {"id": "iron", "name": "IRON DINO", "cost": 3, "owned_key": "iron_owned"},
            {"id": "robot", "name": "ROBOT DINO", "cost": 5, "owned_key": "robot_owned"},
            {"id": "ninja", "name": "NINJA DINO", "cost": 7, "owned_key": "ninja_owned"},
            {"id": "fire", "name": "FIRE DINO", "cost": 10, "owned_key": "fire_owned"},
            {"id": "legendary", "name": "LEGENDARY COSMIC DINO", "cost": 230, "owned_key": "legendary_owned"},
            {"id": "ice", "name": "ICE DINO", "cost": 25, "owned_key": "ice_owned"},
            {"id": "thunder", "name": "THUNDER DINO", "cost": 30, "owned_key": "thunder_owned"},
            {"id": "shadow", "name": "SHADOW DINO", "cost": 35, "owned_key": "shadow_owned"},
            {"id": "toxic", "name": "TOXIC DINO", "cost": 40, "owned_key": "toxic_owned"},
            {"id": "galaxy", "name": "GALAXY DINO", "cost": 50, "owned_key": "galaxy_owned"},
        ] + EXTRA_SKINS
        skin = skins[shop_skin_index]
        title = font_title.render("Dinosaur Skins", True, BLACK)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 55)))
        cups_text = font_ui.render(f"Cups: {player_progress.get('cups', 0)}", True, GOLD)
        screen.blit(cups_text, cups_text.get_rect(center=(SCREEN_WIDTH // 2, 100)))

        old_skin = selected_skin
        selected_skin = skin["id"]
        draw_dinosaur(SCREEN_WIDTH // 2 - 25, 205)
        selected_skin = old_skin
        name_text = font_ui.render(skin["name"], True, BLACK)
        screen.blit(name_text, name_text.get_rect(center=(SCREEN_WIDTH // 2, 295)))
        skin_counter = pygame.font.Font(None, 22).render(
            f"Skin {shop_skin_index + 1} of {len(skins)}", True, BLACK
        )
        screen.blit(skin_counter, skin_counter.get_rect(center=(SCREEN_WIDTH // 2, 322)))

        btn_prev_skin = Button(155, 205, 65, 55, "<", BLACK)
        btn_next_skin = Button(580, 205, 65, 55, ">", BLACK)
        btn_prev_skin.draw(screen)
        btn_next_skin.draw(screen)

        owned = bool(player_progress.get(skin["owned_key"], False))
        if owned:
            action_text = "EQUIPPED" if selected_skin == skin["id"] else "EQUIP"
            action_colour = GREEN
        else:
            action_text = f"BUY - {skin['cost']} CUP" if skin["cost"] == 1 else f"BUY - {skin['cost']} CUPS"
            action_colour = GOLD
        btn_skin_action = Button(250, 345, 300, 55, action_text, action_colour, BLACK)
        btn_skin_action.draw(screen)
        btn_default_skin = Button(250, 415, 300, 50, "USE DEFAULT DINO", GREEN)
        btn_default_skin.draw(screen)
        btn_skins_back = Button(300, 485, 200, 50, "BACK", BLACK)
        btn_skins_back.draw(screen)

        for event in events:
            if btn_prev_skin.is_clicked(mouse_pos, event):
                shop_skin_index = (shop_skin_index - 1) % len(skins)
                break
            if btn_next_skin.is_clicked(mouse_pos, event):
                shop_skin_index = (shop_skin_index + 1) % len(skins)
                break
            if btn_skin_action.is_clicked(mouse_pos, event):
                if owned:
                    selected_skin = skin["id"]
                    player_progress["selected_skin"] = selected_skin
                    save_progress()
                elif int(player_progress.get("cups", 0)) >= skin["cost"]:
                    player_progress["cups"] -= skin["cost"]
                    player_progress[skin["owned_key"]] = True
                    selected_skin = skin["id"]
                    player_progress["selected_skin"] = selected_skin
                    save_progress()
                break
            if btn_default_skin.is_clicked(mouse_pos, event):
                selected_skin = "default"
                player_progress["selected_skin"] = "default"
                save_progress()
                break
            if btn_skins_back.is_clicked(mouse_pos, event):
                current_state = GameState.COLLECTION
                break

    # 7. Leaderboard State
    elif current_state == GameState.LEADERBOARD:
        screen.fill(LIGHT_GRAY)

        txt_title = font_title.render("Leaderboard", True, BLACK)
        screen.blit(
            txt_title,
            (SCREEN_WIDTH // 2 - txt_title.get_width() // 2, 50),
        )

        leaderboard = sorted(
            leaderboard,
            key=lambda entry: entry["score"],
            reverse=True,
        )[:10]

        if not leaderboard:
            txt_empty = font_sub.render("No scores recorded yet.", True, BLACK)
            screen.blit(
                txt_empty,
                (SCREEN_WIDTH // 2 - txt_empty.get_width() // 2, 180),
            )
        else:
            header_rank = font_ui.render("Rank", True, BLACK)
            header_name = font_ui.render("Name", True, BLACK)
            header_cups = font_ui.render("Cups", True, BLACK)
            header_jumps = font_ui.render("Jumps", True, BLACK)

            screen.blit(header_rank, (115, 120))
            screen.blit(header_name, (225, 120))
            screen.blit(header_cups, (475, 120))
            screen.blit(header_jumps, (600, 120))

            for index, entry in enumerate(leaderboard):
                row_y = 165 + index * 32
                rank_surface = font_sub.render(str(index + 1), True, BLACK)
                name_surface = font_sub.render(str(entry["name"])[:15], True, BLACK)
                cups_surface = font_sub.render(str(entry.get("cups", 0)), True, GOLD)
                jumps_surface = font_sub.render(str(entry["score"]), True, BLACK)

                screen.blit(rank_surface, (135, row_y))
                screen.blit(name_surface, (225, row_y))
                screen.blit(cups_surface, (500, row_y))
                screen.blit(jumps_surface, (620, row_y))

        btn_back = Button(
            SCREEN_WIDTH // 2 - 100,
            485,
            200,
            45,
            "BACK",
            BLACK,
        )
        btn_back.draw(screen)

        for event in events:
            if btn_back.is_clicked(mouse_pos, event):
                current_state = GameState.LOBBY
                break

    if current_state == GameState.LOBBY:
        draw_volume_controls()

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
