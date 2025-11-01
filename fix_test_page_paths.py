with open('templates/thumbnail_test.html', 'r') as f:
    content = f.read()

# Find and replace the displayThumbnails call
old_line = "            displayThumbnails(thumbnails, '/tmp/thumb_test/');"
new_line = "            displayThumbnails(thumbnails, '/static/thumbnails/');"

content = content.replace(old_line, new_line)

with open('templates/thumbnail_test.html', 'w') as f:
    f.write(content)

print("✅ Fixed JavaScript path to /static/thumbnails/")
