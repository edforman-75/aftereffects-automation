import sys

# Read the file
with open('web_app.py', 'r') as f:
    lines = f.readlines()

# Find the line with "result = thumbnail_service.generate_layer_thumbnails("
for i, line in enumerate(lines):
    if 'result = thumbnail_service.generate_layer_thumbnails(' in line:
        # Insert absolute path conversion before this line
        indent = '        '
        new_line = f"{indent}# Convert to absolute path for Photoshop\n{indent}psd_path = os.path.abspath(psd_path)\n{indent}\n"
        lines.insert(i, new_line)
        print(f"✅ Inserted absolute path conversion at line {i+1}")
        break

# Write back
with open('web_app.py', 'w') as f:
    f.writelines(lines)

print("✅ Fix applied!")
