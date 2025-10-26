# How to Test the PSD Parser

## Quick Test

### Option 1: Use Your Uploaded File

If you have uploaded `test-photoshop-doc.psd`, place it in the `sample_files/` directory:

```bash
# Copy your uploaded file
cp /path/to/test-photoshop-doc.psd sample_files/

# Run the test
python tests/test_psd_parser_real.py
```

### Option 2: Use Any PSD File

Test with any PSD file you have:

```bash
# Run the demo script with your PSD
python examples/demo_psd_parser.py /path/to/your/file.psd
```

### Option 3: Quick Python Test

```python
# In Python or IPython
from modules.phase1.psd_parser import parse_psd
import json

# Parse your PSD
result = parse_psd("path/to/your/file.psd")

# View results
print(json.dumps(result, indent=2))
```

---

## Expected Output

When you run `python tests/test_psd_parser_real.py` with a valid PSD, you'll see:

```
✓ Found PSD file: sample_files/test-photoshop-doc.psd

======================================================================
PARSING PSD FILE
======================================================================

📄 Filename: test-photoshop-doc.psd
📐 Dimensions: 1920 x 1080 pixels
🎨 Total Layers: 5

======================================================================
LAYER STRUCTURE
======================================================================

🖼️  Background (image) 👁️  [1920x1080]
   ↳ Position: (0, 0) → (1920, 1080)
📁 Content Group (group) 👁️  [800x600]
  📝 Title (text) 👁️  [500x80]
     ↳ Position: (210, 100) → (710, 180)
  📝 Subtitle (text) 👁️  [400x40]
     ↳ Position: (260, 200) → (660, 240)

======================================================================
FULL JSON OUTPUT
======================================================================

{
  "filename": "test-photoshop-doc.psd",
  "width": 1920,
  "height": 1080,
  "layers": [
    {
      "name": "Background",
      "type": "image",
      "visible": true,
      "path": "Background",
      "bbox": {
        "left": 0,
        "top": 0,
        "right": 1920,
        "bottom": 1080
      },
      "width": 1920,
      "height": 1080
    },
    ...
  ]
}

======================================================================
VERIFICATION
======================================================================

✓ Has 'filename' key
✓ Has 'width' key
✓ Has 'height' key
✓ Has 'layers' key
✓ Layers is a list
✓ Width is positive
✓ Height is positive

🎉 ALL CHECKS PASSED!
```

---

## Upload Your PSD File

To test with your `test-photoshop-doc.psd`:

1. **Save it to the project:**
   ```bash
   cp test-photoshop-doc.psd sample_files/
   ```

2. **Run the test:**
   ```bash
   python tests/test_psd_parser_real.py
   ```

3. **Or use the demo:**
   ```bash
   python examples/demo_psd_parser.py sample_files/test-photoshop-doc.psd
   ```

---

## What the Test Verifies

✅ File can be opened and parsed
✅ Has required keys: filename, width, height, layers
✅ Dimensions are positive numbers
✅ Layers is a proper list
✅ Each layer has: name, type, visible, bbox
✅ Nested groups work correctly
✅ Layer types are identified (text, image, shape, group, smartobject)

---

## Next Steps After Testing

Once testing confirms the parser works:

1. ✅ Add more sample PSD files to `sample_files/`
2. ✅ Expand tests to verify specific layer properties
3. ✅ Test with complex PSDs (many layers, deep nesting)
4. ✅ Move to Module 1.2 (text content extraction)

---

## Troubleshooting

**"PSD file not found"**
- Check the file path
- Make sure file is in `sample_files/` directory
- Try absolute path: `/full/path/to/file.psd`

**"Invalid PSD file"**
- Ensure file is a valid Photoshop document
- Try opening in Photoshop first
- Check file isn't corrupted

**"No module named psd_tools"**
```bash
source venv/bin/activate
pip install psd-tools
```
