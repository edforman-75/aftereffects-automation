import re

# Read the file
with open('services/thumbnail_service.py', 'r') as f:
    content = f.read()

# Find the section where we open the document and add app.activeDocument
old_pattern = r'// Open PSD\nvar doc = app\.open\(psdFile\);'
new_code = '''// Open PSD
var doc = app.open(psdFile);
app.activeDocument = doc;  // Make sure document is active and frontmost'''

content = re.sub(old_pattern, new_code, content)

# Write back
with open('services/thumbnail_service.py', 'w') as f:
    f.write(content)

print("✅ Added app.activeDocument = doc to ensure document is frontmost")
