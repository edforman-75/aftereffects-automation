with open('templates/thumbnail_test.html', 'r') as f:
    content = f.read()

# Find the img styling and add a background
old_style = '''        .thumbnail-card img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ccc;
        }'''

new_style = '''        .thumbnail-card img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ccc;
            background: repeating-conic-gradient(#ddd 0% 25%, white 0% 50%) 50% / 20px 20px;
        }'''

content = content.replace(old_style, new_style)

with open('templates/thumbnail_test.html', 'w') as f:
    f.write(content)

print("✅ Added checkered background to thumbnails")
