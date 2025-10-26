"""
Create a simple test PSD file for testing the parser.
"""

from PIL import Image, ImageDraw, ImageFont

# Create a simple test image
width, height = 800, 600
img = Image.new('RGB', (width, height), color='white')
draw = ImageDraw.Draw(img)

# Add some colored rectangles
draw.rectangle([50, 50, 250, 150], fill='red', outline='black', width=3)
draw.rectangle([300, 200, 500, 400], fill='blue', outline='black', width=3)
draw.rectangle([550, 50, 750, 250], fill='green', outline='black', width=3)

# Add text
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
except:
    font = ImageFont.load_default()

draw.text((width // 2 - 100, height - 100), "Test PSD", fill='black', font=font)

# Save as PSD
output_path = "sample_files/simple_test.psd"
img.save(output_path, format='PSD')

print(f"✓ Created test PSD: {output_path}")
print(f"  Dimensions: {width} x {height}")
