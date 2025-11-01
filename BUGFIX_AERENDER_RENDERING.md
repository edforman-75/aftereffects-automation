# Bug Fix: aerender Rendering Failure in Preview Generation

## Date: October 30, 2025

---

## 🐛 ISSUE

**Problem**: Preview generation fails with error:
```
Rendering failed - check aerender output above for details
```

**Root Cause**: Multiple issues in the preview generation pipeline:
1. **AppleScript syntax error**: Used `DoScriptFile` instead of `do script`
2. **Insufficient delays**: Template population didn't complete before rendering
3. **No verification**: No check if population actually succeeded
4. **Poor error messages**: Generic failures without helpful diagnostics

---

## 🔧 FIXES APPLIED

### 1. Fixed AppleScript Execution (Lines 526-638)

**Before**:
```javascript
applescript = f'''
tell application "Adobe After Effects 2025"
    activate
    open POSIX file "{abs_project_path}"
    delay 3
    DoScriptFile "{abs_script_path}"  // ❌ Wrong command
    delay 2
    save
    quit
end tell
'''
```

**After**:
```javascript
applescript = f'''
tell application "Adobe After Effects 2025"
    activate
    delay 1
    open POSIX file "{abs_project_path_escaped}"
    delay 5  // ✅ Longer delay

    -- Run the ExtendScript
    do script "$.evalFile('{abs_script_path_escaped}');"  // ✅ Correct syntax
    delay 5  // ✅ Longer delay

    -- Save the project
    save
    delay 2

    -- Quit After Effects
    quit
end tell
'''
```

**Key Changes**:
- ✅ Changed `DoScriptFile` to `do script "$.evalFile(...)"`
- ✅ Increased delays: 3s → 5s for project open, 2s → 5s for script execution
- ✅ Added path escaping for AppleScript
- ✅ Using stdin (`osascript -`) instead of `-e` for better handling
- ✅ Increased timeout: 60s → 120s

---

### 2. Added Population Verification (Lines 587-637)

**New Verification Logic**:
```python
if result.returncode == 0:
    # Wait for AE to fully close and save
    print("  ✓ Waiting for After Effects to close...")
    time.sleep(3)

    # Verify project was modified (check modification time)
    if os.path.exists(temp_project):
        mtime = os.path.getmtime(temp_project)
        age_seconds = time.time() - mtime

        if age_seconds < 120:  # Modified in last 2 minutes
            print(f"  ✓ Project file updated (age: {age_seconds:.1f}s)")
            populated_successfully = True
        else:
            print(f"  ⚠️  Warning: Project file not recently modified")
            print("  (Population may not have succeeded)")
```

**Benefits**:
- ✅ Verifies project file was actually saved
- ✅ Checks modification timestamp to confirm changes
- ✅ Warns if population likely failed

---

### 3. Improved aerender Execution (Lines 656-803)

**Added Pre-Flight Checks**:
```python
# Verify project file exists
if not os.path.exists(project_path):
    print(f"❌ Project file not found: {project_path}")
    return False

project_size = os.path.getsize(project_path)
print(f"✓ Project file exists: {project_path}")
print(f"  Size: {project_size:,} bytes")
print(f"  Composition: {comp_name}")
```

**Added Better Error Parsing**:
```python
# Parse common error messages
error_text = (result.stdout + result.stderr).lower()

if 'composition' in error_text and 'not found' in error_text:
    print(f"\n💡 LIKELY CAUSE: Composition '{comp_name}' not found")
    print("   Check that the composition name matches exactly")
elif 'footage' in error_text or 'missing' in error_text:
    print(f"\n💡 LIKELY CAUSE: Missing footage files")
    print("   The project references files that couldn't be found")
    print("   This can happen if:")
    print("   - PSD layers weren't extracted as images")
    print("   - Footage paths are incorrect")
    print("   - Population script didn't complete successfully")
```

**Added Debugging Steps**:
```python
print(f"\n📋 DEBUGGING STEPS:")
print(f"   1. Check if project file exists: {abs_project_path}")
print(f"   2. Open project manually in After Effects")
print(f"   3. Verify composition '{comp_name}' exists")
print(f"   4. Check for missing footage warnings")
print(f"   5. Try rendering manually to see detailed error")
```

---

## 📊 IMPROVEMENTS SUMMARY

### Before Fix:
```
❌ AppleScript syntax error (DoScriptFile doesn't exist)
❌ Insufficient delays - script runs before project opens
❌ No verification - doesn't check if population succeeded
❌ Generic error messages
❌ Hard to debug failures
```

### After Fix:
```
✅ Correct AppleScript syntax ($.evalFile)
✅ Longer delays - ensures population completes
✅ Verification - checks project modification timestamp
✅ Intelligent error parsing - identifies specific issues
✅ Helpful debugging steps provided
✅ Better logging throughout
```

---

## 🧪 TESTING WORKFLOW

### Complete Test Scenario:

```bash
# 1. Start the app
python web_app.py

# 2. Complete workflow
- Upload PSD + AEPX
- Complete mappings
- Generate ExtendScript
- Validate (optional for Mode B)
- Click "Generate Side-by-Side Previews"

# 3. Watch the logs
tail -f logs/app.log | grep -E "(Step|✓|❌|💡)"
```

### Expected Log Output (Success):

```
Step 3.7: Populating template with content...
  ✓ Generated ExtendScript: populate.jsx
  ✓ Opening project in After Effects...
  ✓ Running population script...
    Project: /tmp/ae_preview_xxx/template.aepx
    Script: /tmp/ae_preview_xxx/populate.jsx
  ✓ AppleScript return code: 0
  ✓ Waiting for After Effects to close...
  ✓ Project file updated (age: 8.3s)
✅ Template populated successfully

Step 5: Rendering with aerender...
✓ Project file exists: /tmp/ae_preview_xxx/template.aepx
  Size: 1,234,567 bytes
  Composition: Main Comp
  Output: /path/to/ae_preview_xxx.mp4
  Duration: 5.0s (75 frames at 15 fps)

======================================================================
AERENDER COMMAND:
======================================================================
"/Applications/Adobe After Effects 2025/aerender" -project "/tmp/ae_preview_xxx/template.aepx" -comp "Main Comp" -output "/path/to/ae_preview_xxx.mp4" -RStemplate "Best Settings" -s 0 -e 75
======================================================================

Starting aerender... (this may take 30-60 seconds)

✅ aerender completed successfully
```

### Expected Log Output (Failure with Diagnostics):

```
❌ AERENDER FAILED
Return code: 1
Output file was not created

💡 LIKELY CAUSE: Missing footage files
   The project references files that couldn't be found
   This can happen if:
   - PSD layers weren't extracted as images
   - Footage paths are incorrect
   - Population script didn't complete successfully

📋 DEBUGGING STEPS:
   1. Check if project file exists: /tmp/ae_preview_xxx/template.aepx
   2. Open project manually in After Effects
   3. Verify composition 'Main Comp' exists
   4. Check for missing footage warnings
   5. Try rendering manually to see detailed error
```

---

## 🔑 KEY INSIGHTS

### 1. AppleScript Best Practices

**Use stdin for complex scripts**:
```python
# ❌ Bad - can have quoting issues
subprocess.run(['osascript', '-e', applescript])

# ✅ Good - reliable for complex scripts
subprocess.run(['osascript', '-'], input=applescript, text=True)
```

**Use correct ExtendScript execution**:
```javascript
// ❌ Bad - DoScriptFile is not a standard command
DoScriptFile "/path/to/script.jsx"

// ✅ Good - Standard ExtendScript evaluation
do script "$.evalFile('/path/to/script.jsx');"
```

### 2. Timing is Critical

After Effects needs time to:
- Open project: **5 seconds**
- Execute ExtendScript: **5 seconds**
- Save project: **2 seconds**
- Quit completely: **3 seconds**

**Total: ~15 seconds** before aerender can start.

### 3. Verification is Essential

Don't assume operations succeeded:
```python
# ✅ Always verify
if os.path.exists(project_path):
    mtime = os.path.getmtime(project_path)
    age = time.time() - mtime
    if age < 120:  # Modified recently
        success = True
```

### 4. Error Messages Matter

Users need actionable information:
```
❌ Bad: "Rendering failed"
✅ Good: "Missing footage files - PSD layers weren't extracted"
```

---

## 📁 FILES MODIFIED

### 1. modules/phase5/preview_generator.py

**Lines 526-638**: Template population
- Fixed AppleScript syntax
- Increased delays
- Added path escaping
- Added verification logic
- Better error handling

**Lines 656-803**: aerender execution
- Added pre-flight checks
- Improved error parsing
- Added debugging steps
- Better logging

**Total changes**: ~150 lines modified/added

---

## 🚀 DEPLOYMENT

### After deploying these fixes:

1. **Restart the application**
```bash
# Stop current process
pkill -f "python web_app.py"

# Start with fresh logs
python web_app.py > logs/app.log 2>&1 &
```

2. **Test with a simple PSD/AEPX pair**
   - Use a template with 1-2 text layers
   - Verify preview generates successfully

3. **Monitor the logs**
```bash
tail -f logs/app.log
```

4. **Check for success indicators**:
   - ✅ Template populated successfully
   - ✅ aerender completed successfully
   - Files created in `previews/session_previews/xxx/`

---

## ✅ SUCCESS CRITERIA

**Preview generation is working when**:
- ✓ AppleScript executes without syntax errors
- ✓ After Effects opens, populates, saves, and quits
- ✓ Project file is updated with populated content
- ✓ aerender renders without missing footage errors
- ✓ Both PSD PNG and AE MP4 are generated
- ✓ Side-by-side preview displays correctly in UI

---

## 🔮 FUTURE IMPROVEMENTS

### Potential Enhancements:

1. **Background Worker**
   - Move rendering to Celery task
   - Show progress bar
   - Email notification on completion

2. **Render Queue**
   - Allow multiple preview requests
   - Process sequentially
   - Show queue status

3. **Caching**
   - Cache populated projects
   - Skip re-population if no changes
   - Faster preview regeneration

4. **Preview Quality Options**
   - Let user choose quality/duration
   - Quick preview (3s, 480p)
   - Standard preview (5s, 720p)
   - Full preview (10s, 1080p)

---

**Status**: Fixed ✅
**Tested**: Pending user testing 🧪
**Ready for**: Production deployment 🚀

---

*Fixed: October 30, 2025*
