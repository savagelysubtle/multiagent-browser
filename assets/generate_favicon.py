from PIL import Image, ImageDraw, ImageFont
import os

# Create a 32x32 image (standard favicon size)
img = Image.new('RGB', (32, 32), color='blue')
draw = ImageDraw.Draw(img)

# Add some text (simple 'W' for Web UI)
try:
    font = ImageFont.load_default()
except:
    font = None
draw.text((10, 10), 'W', fill='white', font=font)

# Save as favicon.ico in assets/
assets_dir = 'assets'
os.makedirs(assets_dir, exist_ok=True)
img.save(os.path.join(assets_dir, 'favicon.ico'))

print('Favicon generated and saved to assets/favicon.ico')
