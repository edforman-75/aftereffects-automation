# Read the file
with open('services/thumbnail_service.py', 'r') as f:
    lines = f.readlines()

# Find the line "for (var i = 0; i < doc.layers.length; i++)" and add the fix after it
for i, line in enumerate(lines):
    if 'for (var i = 0; i < doc.layers.length; i++)' in line:
        # Find the opening brace
        for j in range(i, min(i+5, len(lines))):
            if '{{' in lines[j]:
                # Insert the fix right after the opening brace and "var layer = doc.layers[i];"
                # Find "var layer = doc.layers[i];"
                for k in range(j+1, min(j+5, len(lines))):
                    if 'var layer = doc.layers[i];' in lines[k]:
                        indent = '            '
                        new_line = f'{indent}app.activeDocument = doc;  // Ensure doc is active for this iteration\n'
                        lines.insert(k + 1, '\n')
                        lines.insert(k + 2, new_line)
                        print(f"✅ Inserted Fix #2 at line {k+3}")
                        break
                break
        break

# Write back
with open('services/thumbnail_service.py', 'w') as f:
    f.writelines(lines)

print("✅ Fix applied!")
