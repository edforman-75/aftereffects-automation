# Temp Directory Debug - Current State

## ✅ Cleanup Now Disabled

**File:** `modules/phase5/preview_generator.py` (lines 183-191)

**Output:**
```
Step 8: NOT cleaning up temp directory for inspection: /var/.../ae_preview_xyz
⚠️  Manually inspect: /var/.../ae_preview_xyz
⚠️  To re-enable cleanup, uncomment shutil.rmtree() in preview_generator.py
```

Temp directories are now preserved for inspection after preview generation.

## 📁 Temp Directory Contents (Verified)

**Inspection of:** `/var/folders/.../ae_preview_pd5z44bt`

```
ae_preview_pd5z44bt/
├── test-correct-fixed.aepx (670,422 bytes) ✅
├── footage/
│   ├── cutout.png (2,569 bytes) ✅
│   ├── green_yellow_bg.png (8,863 bytes) ✅
│   └── test-photoshop-doc.psd (12,736,935 bytes) ✅
└── test-correct-fixed.aepx Logs/
    └── AE 10-27-25 12-49-15 PDT.txt
```

**✅ All footage files successfully copied!**
- Files are in correct location: `footage/` subdirectory
- File sizes match originals
- Directory structure maintained

## ❌ The Problem

After Effects is still reporting: **"File Not Found footage/green_yellow_bg.png"**

### From AE Log:
```
After Effects error: Unable to Render: File Not Found footage/green_yellow_bg.png
```

### But Files Exist!
```
$ ls -la /var/.../ae_preview_pd5z44bt/footage/green_yellow_bg.png
-rw-r--r--  1 edf  staff  8863 Oct 27 10:07 green_yellow_bg.png
```

## 🔍 Investigation

### What We Know:

1. **Footage files ARE copied** ✅
   - All 3 files present in temp directory
   - Correct directory structure (`footage/` subdirectory)
   - File sizes correct

2. **AEPX references are relative** ✅
   - AEPX contains: `footage/green_yellow_bg.png`
   - Files are in: `temp_dir/footage/green_yellow_bg.png`
   - Should work!

3. **aerender is being called** ✅
   - Composition renders
   - AE log file created
   - But reports "File Not Found"

### Possible Causes:

#### Hypothesis 1: AEPX Still Has Old Paths
The AEPX file might still contain absolute paths internally, even though we copied it.

**Test:** Check AEPX content
```bash
grep -o "/Users/benforman" temp_dir/test-correct-fixed.aepx
```

#### Hypothesis 2: AE Working Directory Issue
aerender might be running from a different directory, making relative paths fail.

**Test:** Check aerender command working directory

#### Hypothesis 3: AEPX Needs Re-import
The copied AEPX might have cached absolute paths that need to be refreshed.

**Solution:** Use `fix_footage_paths()` to update AEPX in temp directory

## 🔧 Potential Fix

### Option 1: Fix AEPX Paths Before Copying

Update `prepare_temp_project()` to use `fix_footage_paths()`:

```python
from modules.phase2.aepx_path_fixer import fix_footage_paths

# Copy AEPX to temp location
temp_project = os.path.join(temp_dir, project_name)
shutil.copy2(aepx_path, temp_project)

# Fix paths in the copied AEPX to use temp directory locations
result = fix_footage_paths(
    temp_project,
    output_path=temp_project,  # Overwrite
    footage_dir=temp_dir  # Point to temp directory
)
```

This would update the AEPX file itself to have correct paths for the temp directory.

### Option 2: Pass Working Directory to aerender

Ensure aerender runs with temp_dir as working directory:

```python
subprocess.run(
    cmd,
    cwd=temp_dir,  # Set working directory
    capture_output=True,
    text=True
)
```

### Option 3: Use Absolute Paths in AEPX

Update AEPX to use absolute paths to temp directory:

```python
# Update footage references to absolute paths
for ref in footage_refs:
    old_path = ref['path']  # "footage/file.png"
    new_path = os.path.join(temp_dir, old_path)  # "/tmp/.../footage/file.png"
    # Replace in AEPX content
```

## 📝 Next Steps

1. **Check if AEPX still has old paths**
   ```bash
   # Look for old absolute paths
   strings temp_dir/test-correct-fixed.aepx | grep "/Users/benforman"
   ```

2. **Test fix_footage_paths() approach**
   - Update AEPX in temp directory
   - Point to temp directory footage
   - Re-run aerender

3. **Test working directory approach**
   - Add `cwd=temp_dir` to subprocess.run()
   - Verify relative paths work

4. **Test with absolute paths**
   - Update AEPX to use absolute temp paths
   - Verify aerender can find files

## 🎯 Recommended Solution

**Use fix_footage_paths() in prepare_temp_project():**

```python
def prepare_temp_project(aepx_path: str, mappings: Dict[str, Any], temp_dir: str) -> str:
    # Copy AEPX to temp location
    project_name = Path(aepx_path).name
    temp_project = os.path.join(temp_dir, project_name)
    shutil.copy2(aepx_path, temp_project)

    # Copy footage files to temp directory
    print("Step 3.5: Copying footage files to temp directory...")
    # ... existing copying code ...

    # Fix AEPX paths to point to temp directory footage
    print("Step 3.6: Fixing AEPX footage paths...")
    from modules.phase2.aepx_path_fixer import fix_footage_paths

    result = fix_footage_paths(
        temp_project,
        output_path=temp_project,  # Overwrite
        footage_dir=temp_dir  # Use temp directory
    )

    if result['success']:
        print(f"✅ Fixed {len(result['fixed_paths'])} paths in AEPX")

    return temp_project
```

This ensures the AEPX file itself has correct paths for the temp directory.

## 🔄 To Re-enable Cleanup

When debugging is complete, uncomment cleanup code in `preview_generator.py`:

```python
# Change this:
# try:
#     shutil.rmtree(temp_dir)
#     print(f"✅ Temp directory cleaned up\n")
# except Exception as e:
#     print(f"⚠️  Failed to cleanup temp directory: {str(e)}\n")

# Back to this:
try:
    shutil.rmtree(temp_dir)
    print(f"✅ Temp directory cleaned up\n")
except Exception as e:
    print(f"⚠️  Failed to cleanup temp directory: {str(e)}\n")
```

---

**Status:** Debugging in progress
**Temp cleanup:** Disabled
**Footage copying:** ✅ Working
**Issue:** aerender can't find files that exist
**Next:** Fix AEPX paths in temp directory
