# Bug Fix: Missing Footage Files Breaking aerender

## Date: October 30, 2025

---

## 🐛 ISSUE

**Problem**: aerender fails because AEPX file references footage files with absolute paths that don't exist on this system.

**Error from aerender**:
```
WARNING: After Effects warning: logged 10 errors, please check log.
First error was "error: Unable to Render: File Not Found
/Users/benforman/Downloads/2025-26 Templates/Gameday_Components/green_yellow_bg.png"
```

**Root Cause**:
The AEPX template file contains **hardcoded absolute paths** from the original creator's machine:
```
/Users/benforman/Downloads/2025-26 Templates/Gameday_Components/green_yellow_bg.png
/Users/benforman/Downloads/2025-26 Templates/Gameday_Components/cutout.png
```

These paths don't exist on the rendering system, so After Effects can't find the footage files and rendering fails.

**Why This Happens**:
- Templates are created on one machine with specific folder structures
- Absolute paths get embedded in the AEPX XML
- When template is used on another machine, those paths are invalid
- Previous code only checked if absolute paths exist, didn't search for alternatives

---

## 🔧 FIX APPLIED

### 1. Added Footage Search Function (Lines 387-418)

**New Function**: `search_for_footage_by_filename(filename: str) -> str | None`

**What it does**:
- Takes a filename (e.g., "green_yellow_bg.png")
- Searches across multiple project directories
- Recursively searches subdirectories
- Returns absolute path if found, None otherwise

**Search locations**:
```python
search_dirs = [
    'uploads',
    'footage',
    'sample_files',
    'sample_files/footage',
    'assets',
    'media',
    'static/uploads',
]
```

**Code**:
```python
def search_for_footage_by_filename(filename: str) -> str | None:
    """Search for footage file by filename across multiple directories."""
    # Search locations
    search_dirs = [
        'uploads', 'footage', 'sample_files',
        'sample_files/footage', 'assets', 'media', 'static/uploads',
    ]

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue

        # Search in directory and all subdirectories
        for root, dirs, files in os.walk(search_dir):
            if filename in files:
                found_path = os.path.join(root, filename)
                return os.path.abspath(found_path)

    return None
```

---

### 2. Added Placeholder Image Generator (Lines 421-458)

**New Function**: `create_placeholder_image(output_path: str, width: int = 1920, height: int = 1080) -> bool`

**What it does**:
- Creates a placeholder image when footage file can't be found
- Prevents rendering from failing completely
- Displays "MISSING FOOTAGE" message with filename
- Uses PIL (Pillow) to generate image

**Visual result**:
```
┌─────────────────────────────┐
│                             │
│    MISSING FOOTAGE          │
│    green_yellow_bg.png      │
│                             │
└─────────────────────────────┘
(Gray background with text)
```

**Code**:
```python
def create_placeholder_image(output_path: str, width: int = 1920, height: int = 1080) -> bool:
    """Create a placeholder image for missing footage."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create solid color image
        img = Image.new('RGB', (width, height), color='#333333')
        draw = ImageDraw.Draw(img)

        # Add text
        filename = os.path.basename(output_path)
        text = f"MISSING FOOTAGE\n{filename}"

        # Draw text in center
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) / 2, (height - text_height) / 2)

        draw.text(position, text, fill='#999999')

        # Save
        img.save(output_path)
        return True

    except Exception as e:
        print(f"    ⚠️  Could not create placeholder: {e}")
        return False
```

---

### 3. Enhanced Footage Copying Logic (Lines 489-569)

**Before**:
```python
if is_absolute:
    # For absolute paths, use as-is
    if os.path.exists(ref_path):
        source_file = Path(ref_path)
    # ❌ If doesn't exist, just skip it
```

**After**:
```python
if is_absolute:
    # For absolute paths, check if exists
    if os.path.exists(ref_path):
        source_file = Path(ref_path)
        search_method = "original path"
    else:
        # ✅ Absolute path doesn't exist - search by filename
        print(f"    ❌ Original path not found: {ref_path}")
        print(f"    🔍 Searching for '{filename}' in project directories...")

        found_path = search_for_footage_by_filename(filename)
        if found_path:
            source_file = Path(found_path)
            search_method = f"found in {os.path.dirname(found_path)}"
            print(f"    ✅ Found alternative: {found_path}")
```

**Added path_mapping tracking**:
```python
path_mapping = {}  # Track original path -> new path for AEPX updates

# When file is found or placeholder created:
path_mapping[ref_path] = str(dest_file)
```

**Added placeholder fallback**:
```python
else:
    # File not found anywhere - create placeholder
    print(f"    ⚠️  Not found anywhere - creating placeholder")

    # Create placeholder image
    if create_placeholder_image(str(dest_file)):
        print(f"    ✅ Created placeholder: {dest_file}")
        path_mapping[ref_path] = str(dest_file)
```

---

### 4. Enhanced AEPX Path Rewriting (Lines 583-617)

**Before**:
```python
# Only update relative paths
if not os.path.isabs(ref_path):
    # Convert to absolute path in temp directory
    abs_path = str(Path(temp_dir) / ref_path)
    # ❌ Doesn't handle broken absolute paths
```

**After**:
```python
# Replace all mapped paths (both absolute and relative)
for old_path, new_path in path_mapping.items():
    # Replace in AEPX content (escape special regex chars)
    import re
    old_path_escaped = re.escape(old_path)

    # Count matches before replacing
    matches = len(re.findall(old_path_escaped, aepx_content))

    if matches > 0:
        aepx_content = re.sub(old_path_escaped, new_path, aepx_content)
        print(f"  ✓ Updated: {os.path.basename(old_path)} ({matches} reference(s))")
        updated_count += matches
```

**Key improvements**:
- ✅ Updates **both** absolute and relative paths
- ✅ Uses path_mapping to know exactly what to replace
- ✅ Counts and reports how many references were updated
- ✅ Shows filename instead of full path for readability

---

## 📊 WHAT THIS FIXES

### Issues Resolved:

✅ **Missing absolute paths**
- Detects when absolute paths don't exist
- Searches for file by name across project directories
- Uses found file instead of failing

✅ **Fallback to placeholders**
- Creates placeholder images for completely missing files
- Prevents render from failing with "File Not Found"
- Visual indicator shows what was missing

✅ **AEPX path updates**
- Updates AEPX XML to point to new paths
- Handles both absolute and relative paths
- Reports exactly what was changed

✅ **Better diagnostics**
```
Before:
  ✗ Not found: /Users/benforman/.../green_yellow_bg.png

After:
  Looking for: green_yellow_bg.png
    ❌ Original path not found: /Users/benforman/.../green_yellow_bg.png
    🔍 Searching for 'green_yellow_bg.png' in project directories...
    ✅ Found alternative: /Users/edf/uploads/green_yellow_bg.png
    ✅ Copied to temp directory (found in /Users/edf/uploads)
```

---

## 🧪 TESTING SCENARIOS

### Scenario 1: Footage Found in Alternative Location

**Setup**:
- AEPX references: `/Users/benforman/Downloads/.../green_yellow_bg.png`
- File exists in: `uploads/green_yellow_bg.png`

**Expected Output**:
```
Step 3.5: Copying footage files to temp directory...

  Looking for: green_yellow_bg.png
    ❌ Original path not found: /Users/benforman/Downloads/.../green_yellow_bg.png
    🔍 Searching for 'green_yellow_bg.png' in project directories...
    ✅ Found alternative: /Users/edf/uploads/green_yellow_bg.png
    ✅ Copied to temp directory (found in /Users/edf/uploads)

✅ Copied 1 footage file(s)

Step 3.6: Updating AEPX footage paths...
  ✓ Updated: green_yellow_bg.png (2 reference(s))

✅ Updated 2 footage path(s) in AEPX
```

**Result**: ✅ Render succeeds with found footage

---

### Scenario 2: Footage Not Found - Placeholder Created

**Setup**:
- AEPX references: `/Users/benforman/Downloads/.../cutout.png`
- File doesn't exist anywhere

**Expected Output**:
```
Step 3.5: Copying footage files to temp directory...

  Looking for: cutout.png
    ❌ Original path not found: /Users/benforman/Downloads/.../cutout.png
    🔍 Searching for 'cutout.png' in project directories...
    ⚠️  Not found anywhere - creating placeholder
    ✅ Created placeholder: /tmp/ae_preview_xxx/cutout.png

Step 3.6: Updating AEPX footage paths...
  ✓ Updated: cutout.png (1 reference(s))

✅ Updated 1 footage path(s) in AEPX
```

**Result**: ✅ Render succeeds with placeholder (shows "MISSING FOOTAGE")

---

### Scenario 3: Mixed - Some Found, Some Missing

**Setup**:
- AEPX references 3 files
- 1 exists at original path
- 1 exists in uploads/
- 1 doesn't exist anywhere

**Expected Output**:
```
Step 3.5: Copying footage files to temp directory...

  Looking for: background.png
    ✅ Copied to temp directory (original path)

  Looking for: green_yellow_bg.png
    ❌ Original path not found: /Users/benforman/.../green_yellow_bg.png
    🔍 Searching for 'green_yellow_bg.png' in project directories...
    ✅ Found alternative: /Users/edf/uploads/green_yellow_bg.png
    ✅ Copied to temp directory (found in /Users/edf/uploads)

  Looking for: cutout.png
    ❌ Original path not found: /Users/benforman/.../cutout.png
    🔍 Searching for 'cutout.png' in project directories...
    ⚠️  Not found anywhere - creating placeholder
    ✅ Created placeholder: /tmp/ae_preview_xxx/cutout.png

✅ Copied 2 footage file(s)

Step 3.6: Updating AEPX footage paths...
  ✓ Updated: background.png (1 reference(s))
  ✓ Updated: green_yellow_bg.png (2 reference(s))
  ✓ Updated: cutout.png (1 reference(s))

✅ Updated 4 footage path(s) in AEPX
```

**Result**: ✅ Render succeeds (2 real files + 1 placeholder)

---

## 🔑 KEY INSIGHTS

### 1. Templates With Absolute Paths Are Common

Many After Effects templates use absolute paths because:
- Template creators work from their own machines
- Paths get embedded when saving AEPX
- Users often don't realize paths are hardcoded

**Solution**: Always search by filename, not just path.

### 2. Graceful Degradation is Better Than Failure

Instead of failing completely when footage is missing:
- ✅ Search for alternatives
- ✅ Create placeholders
- ✅ Let render complete
- ⚠️ User can see what's missing

### 3. Path Mapping Simplifies Updates

Tracking `original_path -> new_path` makes AEPX updates straightforward:
```python
path_mapping = {
    '/Users/benforman/.../green_yellow_bg.png': '/tmp/ae_preview_xxx/green_yellow_bg.png',
    'relative/path/to/file.png': '/tmp/ae_preview_xxx/file.png',
}

# Then simply replace all mapped paths
for old_path, new_path in path_mapping.items():
    aepx_content = aepx_content.replace(old_path, new_path)
```

### 4. Diagnostic Logging is Essential

Clear, step-by-step logging helps users understand:
- What files were found
- Where they were found
- What was replaced with what
- Why placeholders were created

---

## 📁 FILES MODIFIED

### modules/phase5/preview_generator.py

**Lines 387-418**: Added `search_for_footage_by_filename()` function
- Searches multiple directories recursively
- Returns absolute path if found

**Lines 421-458**: Added `create_placeholder_image()` function
- Creates gray placeholder with text
- Uses PIL to generate image

**Lines 489-569**: Enhanced footage copying logic
- Searches by filename if absolute path missing
- Creates placeholders for files not found anywhere
- Tracks path_mapping for AEPX updates

**Lines 583-617**: Enhanced AEPX path rewriting
- Uses path_mapping to replace all paths
- Handles both absolute and relative paths
- Reports update counts

**Total changes**: ~180 lines added/modified

---

## ✅ SUCCESS CRITERIA

**Preview generation should succeed when**:
- ✓ Footage files referenced by absolute paths that don't exist
- ✓ System searches for files by filename
- ✓ Found files are copied to temp directory
- ✓ Missing files get placeholder images
- ✓ AEPX paths are updated correctly
- ✓ aerender completes successfully
- ✓ Video preview is generated

---

## 🚀 TESTING INSTRUCTIONS

### How to Test:

1. **Use an AEPX template with absolute paths**:
   - Template should reference footage with paths like `/Users/someone/...`
   - Paths should not exist on your system

2. **Place footage files in uploads/ directory**:
   ```bash
   cp green_yellow_bg.png uploads/
   # Don't copy cutout.png - test placeholder generation
   ```

3. **Run preview generation**:
   - Upload PSD + AEPX
   - Complete workflow
   - Click "Generate Side-by-Side Previews"

4. **Watch the logs**:
   ```bash
   tail -f logs/app.log | grep -A 5 "Step 3.5"
   ```

5. **Verify results**:
   - Step 3.5 should show search and copy activity
   - Step 3.6 should show AEPX updates
   - aerender should complete successfully
   - Video preview should be generated

### What to Look For:

✅ **Search activity**:
```
🔍 Searching for 'green_yellow_bg.png' in project directories...
✅ Found alternative: /Users/edf/uploads/green_yellow_bg.png
```

✅ **Placeholder creation**:
```
⚠️  Not found anywhere - creating placeholder
✅ Created placeholder: /tmp/ae_preview_xxx/cutout.png
```

✅ **AEPX updates**:
```
✓ Updated: green_yellow_bg.png (2 reference(s))
✓ Updated: cutout.png (1 reference(s))
```

✅ **Successful render**:
```
✅ aerender completed successfully
✅ PREVIEW GENERATION COMPLETED SUCCESSFULLY
```

---

## 📈 EXPECTED BEHAVIOR COMPARISON

### Before Fix:
```
Step 3.5: Copying footage files to temp directory...
  ✗ Not found: /Users/benforman/.../green_yellow_bg.png
  ✗ Not found: /Users/benforman/.../cutout.png
⚠️  Could not find 2 file(s)

Step 5: Rendering with aerender...
❌ AERENDER FAILED
WARNING: After Effects warning: logged 10 errors
error: Unable to Render: File Not Found
/Users/benforman/Downloads/.../green_yellow_bg.png
```

### After Fix:
```
Step 3.5: Copying footage files to temp directory...

  Looking for: green_yellow_bg.png
    ❌ Original path not found: /Users/benforman/.../green_yellow_bg.png
    🔍 Searching for 'green_yellow_bg.png' in project directories...
    ✅ Found alternative: /Users/edf/uploads/green_yellow_bg.png
    ✅ Copied to temp directory (found in /Users/edf/uploads)

  Looking for: cutout.png
    ❌ Original path not found: /Users/benforman/.../cutout.png
    🔍 Searching for 'cutout.png' in project directories...
    ⚠️  Not found anywhere - creating placeholder
    ✅ Created placeholder: /tmp/ae_preview_xxx/cutout.png

✅ Copied 1 footage file(s)

Step 3.6: Updating AEPX footage paths...
  ✓ Updated: green_yellow_bg.png (2 reference(s))
  ✓ Updated: cutout.png (1 reference(s))

✅ Updated 3 footage path(s) in AEPX

Step 5: Rendering with aerender...
✅ aerender completed successfully
✅ PREVIEW GENERATION COMPLETED SUCCESSFULLY
Video: /path/to/preview.mp4
```

---

## 🔮 FUTURE ENHANCEMENTS

### Potential Improvements:

1. **Intelligent placeholder images**:
   - Match dimensions of missing file
   - Different colors for different types (images vs video)
   - Show metadata in placeholder

2. **User notification of placeholders**:
   - Show warning in UI when placeholders were used
   - List which files were missing
   - Provide upload mechanism for missing files

3. **Footage library management**:
   - Maintain a library of common footage files
   - Auto-download from CDN if available
   - Cache frequently used footage

4. **Path portability warnings**:
   - Detect absolute paths during upload
   - Warn user to use relative paths
   - Offer to convert template to use relative paths

---

**Status**: Fixed ✅
**Tested**: Ready for user testing 🧪
**Impact**: Prevents render failures from missing footage 🚀

---

*Fixed: October 30, 2025*
