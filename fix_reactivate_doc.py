# Read the file
with open('services/thumbnail_service.py', 'r') as f:
    lines = f.readlines()

# Find the line with "tempDoc.close(SaveOptions.DONOTSAVECHANGES);" and add reactivation after it
for i, line in enumerate(lines):
    if 'tempDoc.close(SaveOptions.DONOTSAVECHANGES);' in line:
        # Add reactivation of original document after closing temp doc
        indent = '                '
        new_line = f'{indent}app.activeDocument = doc;  // Re-activate original document\n'
        lines.insert(i + 1, new_line)
        print(f"✅ Inserted document re-activation at line {i+2}")
        break

# Write back
with open('services/thumbnail_service.py', 'w') as f:
    f.writelines(lines)

print("✅ Fix applied!")
