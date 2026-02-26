from PIL import Image
import os

def convert_to_ico(png_path):
    img = Image.open(png_path)
    icon_path = os.path.splitext(png_path)[0] + '.ico'
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    # Save as ICO
    img.save(icon_path, format='ICO')
    return icon_path

if __name__ == '__main__':
    png_file = 'alarm_icon0.1.png'
    ico_file = convert_to_ico(png_file)
    print(f"Created {ico_file}")
