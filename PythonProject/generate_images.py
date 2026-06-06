import os
import math
from PIL import Image, ImageDraw

# KONFIGURACJA
SHAPES = ['kolo', 'kwadrat', 'szesciokat', 'gwiazda', 'trapez']
TEXTURES = ['paski_pionowe', 'paski_poziome', 'kropki']
COLORS = ['czerwony', 'niebieski', 'zielony']
SIZE = 200  # Tutaj ustawiasz rozmiar obrazka

COLOR_MAP = {
    'czerwony': (220, 50, 50),
    'niebieski': (50, 100, 220),
    'zielony': (50, 200, 50)
}

os.makedirs("images", exist_ok=True)


def draw_texture(texture_type, color_rgb, size):
    img = Image.new('RGB', (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    if texture_type == 'paski_pionowe':
        for x in range(0, size, 15):  # zagęszczone linie
            draw.line([(x, 0), (x, size)], fill=color_rgb, width=6)
    elif texture_type == 'paski_poziome':
        for y in range(0, size, 15):
            draw.line([(0, y), (size, y)], fill=color_rgb, width=6)
    elif texture_type == 'kropki':
        for x in range(10, size, 20):
            for y in range(10, size, 20):
                draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=color_rgb)
    return img


def get_shape_mask(shape_type, size):
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = size // 2, size // 2
    r = size // 2.8  # dynamiczne skalowanie promienia

    if shape_type == 'kolo':
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    elif shape_type == 'kwadrat':
        draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill=255)
    elif shape_type == 'szesciokat':
        pts = [(cx + r * math.cos(math.radians(60 * i)), cy + r * math.sin(math.radians(60 * i))) for i in range(6)]
        draw.polygon(pts, fill=255)
    elif shape_type == 'gwiazda':
        pts = []
        for i in range(10):
            angle = math.radians(36 * i - 90)
            current_r = r if i % 2 == 0 else r // 2.2
            pts.append((cx + current_r * math.cos(angle), cy + current_r * math.sin(angle)))
        draw.polygon(pts, fill=255)
    elif shape_type == 'trapez':
        h, w_top, w_bot = r * 0.7, r * 0.5, r
        pts = [(cx - w_top, cy - h), (cx + w_top, cy - h), (cx + w_bot, cy + h), (cx - w_bot, cy + h)]
        draw.polygon(pts, fill=255)
    return mask


print(f"Generowanie {len(SHAPES) * len(TEXTURES) * len(COLORS)} bodźców...")

count = 0
for shape in SHAPES:
    for texture in TEXTURES:
        for color in COLORS:
            tex_img = draw_texture(texture, COLOR_MAP[color], SIZE)
            mask_img = get_shape_mask(shape, SIZE)

            # Tło lekko szare, żeby figura była widoczna
            final_img = Image.new('RGB', (SIZE, SIZE), (220, 220, 220))
            final_img.paste(tex_img, (0, 0), mask_img)

            # ZAPIS Z NOWĄ NAZWĄ
            filename = f"images/{shape}_{texture}_{color}.png"
            final_img.save(filename, quality=95)
            count += 1
            print(f"Zapisano: {filename}")

print(f"\nGotowe! Wygenerowano {count} obrazków w folderze 'images'.")