# Temp Directory Cleanup - Temporarily Disabled

## ✅ Update Complete

Temp directory cleanup has been temporarily disabled for debugging purposes.

## What Changed

**File:** `modules/phase5/preview_generator.py` (lines 183-191)

**Before:**
```python
finally:
    # Cleanup temp directory
    print(f"Step 8: Cleaning up temp directory: {temp_dir}")
    try:
        shutil.rmtree(temp_dir)
        print(f"✅ Temp directory cleaned up\n")
    except Exception as e:
        print(f"⚠️  Failed to cleanup temp directory: {str(e)}\n")
```

**After:**
```python
finally:
    # Cleanup temp directory (TEMPORARILY DISABLED FOR DEBUGGING)
    print(f"Step 8: NOT cleaning up temp directory for inspection: {temp_dir}")
    print(f"⚠️  Manually inspect: {temp_dir}")
    print(f"⚠️  To re-enable cleanup, uncomment shutil.rmtree() in preview_generator.py\n")
    # try:
    #     shutil.rmtree(temp_dir)
    #     print(f"✅ Temp directory cleaned up\n")
    # except Exception as e:
    #     print(f"⚠️  Failed to cleanup temp directory: {str(e)}\n")
```

## New Output

When preview generation runs:
```
Step 8: NOT cleaning up temp directory for inspection: /var/.../ae_preview_xyz
⚠️  Manually inspect: /var/.../ae_preview_xyz
⚠️  To re-enable cleanup, uncomment shutil.rmtree() in preview_generator.py
```

## Purpose

This allows inspection of temp directory contents after preview generation to debug issues like:
- Were footage files copied correctly?
- Is the directory structure correct?
- What does the After Effects log say?
- Are paths correct in the copied AEPX?

## How to Inspect

After running preview generation:

```bash
# Get temp directory path from output
TEMP_DIR="/var/folders/.../ae_preview_xyz"

# List contents
ls -laR "$TEMP_DIR"

# Check footage directory
ls -la "$TEMP_DIR/footage/"

# Read AE log
cat "$TEMP_DIR/[AEPX_NAME] Logs/"*.txt

# Check AEPX for paths
strings "$TEMP_DIR/template.aepx" | grep footage
```

## What We Found

### ✅ Footage Copying Works

Temp directory contains:
```
temp_dir/
├── test-correct-fixed.aepx ✅
└── footage/
    ├── cutout.png ✅
    ├── green_yellow_bg.png ✅
    └── test-photoshop-doc.psd ✅
```

All files copied successfully!

### ❌ But aerender Still Fails

```
After Effects error: Unable to Render: File Not Found footage/green_yellow_bg.png
```

Even though the file exists at `temp_dir/footage/green_yellow_bg.png`.

### 🔍 Root Cause (Suspected)

The AEPX file might still contain old absolute paths internally that need to be updated.

### 🔧 Potential Fix

Use `fix_footage_paths()` to update the AEPX in temp directory:

```python
# After copying AEPX to temp directory
from modules.phase2.aepx_path_fixer import fix_footage_paths

result = fix_footage_paths(
    temp_project,
    output_path=temp_project,  # Overwrite
    footage_dir=temp_dir  # Point to temp directory
)
```

## To Re-enable Cleanup

When debugging is complete:

1. Open `modules/phase5/preview_generator.py`
2. Go to lines 183-191
3. Uncomment the `shutil.rmtree(temp_dir)` lines
4. Remove or comment the "TEMPORARILY DISABLED" message

```python
finally:
    # Cleanup temp directory
    print(f"Step 8: Cleaning up temp directory: {temp_dir}")
    try:
        shutil.rmtree(temp_dir)
        print(f"✅ Temp directory cleaned up\n")
    except Exception as e:
        print(f"⚠️  Failed to cleanup temp directory: {str(e)}\n")
```

## Benefit

Temp directories accumulate quickly during testing. Remember to either:
- Re-enable cleanup after debugging
- Manually clean up old temp directories:
  ```bash
  # Clean up old temp directories
  rm -rf /tmp/ae_preview_*
  rm -rf /var/folders/*/T/ae_preview_*
  ```

## Files

**Modified:**
- `modules/phase5/preview_generator.py` (lines 183-191)

**Documentation:**
- `CLEANUP_DISABLED_SUMMARY.md` (this file)
- `TEMP_DIRECTORY_DEBUG.md` (debug findings)

---

**Status:** Cleanup disabled for debugging
**Remember:** Re-enable cleanup after debugging complete!
