import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def create_noise_background(width, height):
    """Create a textured background with randomized brightness and tones."""
    bg_type = random.choice(["dark", "bright", "brownish", "gray"])
    
    if bg_type == "dark":
        base_r = random.randint(20, 45)
        base_g = random.randint(20, 45)
        base_b = random.randint(20, 45)
    elif bg_type == "bright":
        base_r = random.randint(180, 240)
        base_g = random.randint(180, 240)
        base_b = random.randint(180, 240)
    elif bg_type == "brownish":
        base_r = random.randint(110, 160)
        base_g = random.randint(80, 120)
        base_b = random.randint(50, 85)
    else: # gray
        val = random.randint(100, 160)
        base_r = base_g = base_b = val
        
    bg = Image.new("RGB", (width, height), (base_r, base_g, base_b))
    draw = ImageDraw.Draw(bg)
    
    # Add subtle random grain/noise
    pixels = bg.load()
    for x in range(width):
        for y in range(height):
            noise = random.randint(-12, 12)
            r, g, b = pixels[x, y]
            pixels[x, y] = (
                max(0, min(255, r + noise)),
                max(0, min(255, g + noise)),
                max(0, min(255, b + noise))
            )
            
    # Add some soft background gradient/vignette
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    cx, cy = width // 2, height // 2
    max_dist = np.sqrt(cx**2 + cy**2)
    for x in range(0, width, 4):
        for y in range(0, height, 4):
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
            alpha = int((dist / max_dist) * (40 if bg_type in ["bright", "gray"] else 75))
            overlay_draw.rectangle([x, y, x+4, y+4], fill=(0, 0, 0, alpha))
            
    bg.paste(overlay, (0, 0), overlay)
    return bg

def draw_stem(draw, cx, cy, r):
    """Draw a green/brown star-like stem on top of the tomato."""
    num_leaves = random.randint(4, 6)
    stem_color = (random.randint(60, 100), random.randint(110, 160), random.randint(30, 60))
    
    # Draw leaves radiating from center
    for i in range(num_leaves):
        angle = (2 * np.pi / num_leaves) * i + random.uniform(-0.2, 0.2)
        leaf_len = r * random.uniform(0.25, 0.45)
        leaf_width = r * random.uniform(0.06, 0.12)
        
        # Calculate leaf points (triangle)
        x1 = cx + int(leaf_len * np.cos(angle))
        y1 = cy + int(leaf_len * np.sin(angle))
        
        ortho_angle = angle + np.pi / 2
        x2 = cx + int(leaf_width * np.cos(ortho_angle))
        y2 = cy + int(leaf_width * np.sin(ortho_angle))
        
        x3 = cx - int(leaf_width * np.cos(ortho_angle))
        y3 = cy - int(leaf_width * np.sin(ortho_angle))
        
        draw.polygon([(cx, cy), (x2, y2), (x1, y1), (x3, y3)], fill=stem_color)
        
    # Center core
    core_radius = max(2, int(r * 0.08))
    draw.ellipse([cx - core_radius, cy - core_radius, cx + core_radius, cy + core_radius], fill=(60, 45, 20))

def generate_tomato_image(category, size=(128, 128)):
    # 1. Start with background
    img = create_noise_background(size[0], size[1])
    draw = ImageDraw.Draw(img)
    
    # 2. Random tomato position and size
    cx = size[0] // 2 + random.randint(-10, 10)
    cy = size[1] // 2 + random.randint(-10, 10)
    r = random.randint(35, 48)
    
    # 3. Base color definition depending on category
    # We will draw a series of concentric circles to simulate spherical shading (3D)
    steps = 15
    for step in range(steps):
        factor = step / steps # 0 to 1
        curr_r = int(r * (1.0 - factor * 0.6))
        # Offset center slightly to the top-left to simulate light from top-left
        offset_x = int(factor * r * 0.18)
        offset_y = int(factor * r * 0.18)
        scx = cx - offset_x
        scy = cy - offset_y
        
        if category == "mentah":
            # Dark green to light yellow-green (with randomized variations)
            g_shift = random.randint(-15, 15)
            r_shift = random.randint(-10, 20)
            color_start = np.array([max(10, 20 + r_shift), max(60, 80 + g_shift), 15])
            color_end = np.array([max(60, 90 + r_shift * 2), max(150, 210 + g_shift), max(30, 70 + r_shift)])
            color = tuple((color_start + factor * (color_end - color_start)).astype(int))
            
        elif category == "busuk":
            # Base stage can be red, green, or orange/yellow
            base_stage = random.choice(["red", "green", "orange"])
            if base_stage == "green":
                color_start = np.array([max(10, 20 + random.randint(-5, 15)), max(50, 70 + random.randint(-15, 15)), 15])
                color_end = np.array([max(45, 75 + random.randint(-10, 15)), max(120, 160 + random.randint(-20, 15)), 45])
            elif base_stage == "red":
                color_start = np.array([max(90, 110 + random.randint(-15, 15)), 10, 10])
                color_end = np.array([max(180, 220 + random.randint(-20, 20)), 45, 30])
            else: # orange
                color_start = np.array([120, 60, 15])
                color_end = np.array([220, 140, 35])
                
            # Dull the base colors significantly to simulate decay
            color_start = (color_start * random.uniform(0.65, 0.85)).astype(int)
            color_end = (color_end * random.uniform(0.65, 0.85)).astype(int)
            color = tuple((color_start + factor * (color_end - color_start)).astype(int))
            
        else: # matang
            # Dark red to bright red-orange (with variations)
            r_shift = random.randint(-15, 15)
            color_start = np.array([max(100, 130 + r_shift), 10, 10])
            color_end = np.array([max(210, 255 + r_shift), max(35, 55 + random.randint(-10, 10)), max(25, 40 + random.randint(-10, 10))])
            color = tuple((color_start + factor * (color_end - color_start)).astype(int))
            
        draw.ellipse([scx - curr_r, scy - curr_r, scx + curr_r, scy + curr_r], fill=color)
        
    # 3.5 Draw rot spots for "busuk" category to simulate decay
    if category == "busuk":
        for _ in range(random.randint(2, 4)):
            spot_r = random.randint(7, 14)
            spot_angle = random.uniform(0, 2 * np.pi)
            spot_dist = random.uniform(0, r * 0.6)
            spot_cx = cx + int(spot_dist * np.cos(spot_angle))
            spot_cy = cy + int(spot_dist * np.sin(spot_angle))
            
            spot_draw_img = Image.new("RGBA", size, (0, 0, 0, 0))
            spot_draw = ImageDraw.Draw(spot_draw_img)
            spot_color = (random.randint(25, 45), random.randint(15, 30), random.randint(10, 20), random.randint(160, 230))
            spot_draw.ellipse([spot_cx - spot_r, spot_cy - spot_r, spot_cx + spot_r, spot_cy + spot_r], fill=spot_color)
            
            spot_draw_img = spot_draw_img.filter(ImageFilter.GaussianBlur(1.8))
            img.paste(spot_draw_img, (0, 0), spot_draw_img)
        
    # 4. Glossy Highlight (Specular Reflection)
    # Draw a soft, semi-transparent white highlight at top-left
    highlight_img = Image.new("RGBA", size, (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight_img)
    
    hx = cx - int(r * 0.35)
    hy = cy - int(r * 0.35)
    hr_w = int(r * 0.28)
    hr_h = int(r * 0.16)
    
    # Dull highlight for rotten tomato, bright highlight for others
    alpha_val = 35 if category == "busuk" else 140
    highlight_draw.ellipse([hx - hr_w, hy - hr_h, hx + hr_w, hy + hr_h], fill=(255, 255, 255, alpha_val))
    # Rotate slightly to follow curvature
    highlight_img = highlight_img.rotate(25, center=(hx, hy), resample=Image.BICUBIC)
    img.paste(highlight_img, (0, 0), highlight_img)
    
    # 5. Add stem
    # Sometimes tomato is shown from the back (with stem) or from the front (no stem)
    # Let's say 70% of tomatoes have stem visible
    if random.random() < 0.7:
        draw_stem(draw, cx, cy, r)
        
    # 6. Apply mild Gaussian blur to blend features and edges
    img = img.filter(ImageFilter.GaussianBlur(1.0))
    
    # 7. Add mild final grain to the entire image
    pixels = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            noise = random.randint(-4, 4)
            r_c, g_c, b_c = pixels[x, y]
            pixels[x, y] = (
                max(0, min(255, r_c + noise)),
                max(0, min(255, g_c + noise)),
                max(0, min(255, b_c + noise))
            )
            
    return img

def main(num_images=100):
    print("Memulai pembuatan dataset tomat sintetis...")
    base_dir = "dataset"
    categories = ["mentah", "busuk", "matang"]
    
    for cat in categories:
        cat_dir = os.path.join(base_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        
        # Clear existing images if any
        for f in os.listdir(cat_dir):
            if f.endswith(".jpg") or f.endswith(".png"):
                os.remove(os.path.join(cat_dir, f))
                
        print(f"Membuat {num_images} gambar untuk kategori: '{cat}'...")
        for i in range(num_images):
            img = generate_tomato_image(cat)
            img_path = os.path.join(cat_dir, f"tomato_{cat}_{i:03d}.jpg")
            img.save(img_path, "JPEG", quality=95)
            
    print("Pembuatan dataset selesai!")

if __name__ == "__main__":
    main()
