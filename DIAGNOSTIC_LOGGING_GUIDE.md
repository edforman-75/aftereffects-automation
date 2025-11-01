# Diagnostic Logging Guide

## Comprehensive Logging Added

Extensive diagnostic logging has been added to `services/thumbnail_service.py` to trace the entire thumbnail generation process.

## How to Test

1. **Clear any existing Flask console output** or open a new terminal
2. **Start the Flask server**: `python3 web_app.py`
3. **Open the web interface**: http://localhost:5001
4. **Upload PSD and AEPX files**
5. **Click "Load Visual Previews"**
6. **Watch the Flask console** for detailed diagnostic output

## What the Logs Show

### Section 1: Thumbnail Generation Started
```
======================================================================
THUMBNAIL GENERATION STARTED
======================================================================
PSD path: /path/to/file.psd
PSD exists: True/False
PSD is absolute: True/False
Output folder: /path/to/output
Session ID: xxxxx
Thumbnail folder: /path/to/thumbnails/session_id
Thumbnail folder exists: True/False
Results file path: /tmp/tmp_xxxxx.json
Generated ExtendScript: XXXX characters
```

**What to check**:
- ✅ PSD file exists
- ✅ PSD path is absolute
- ✅ Thumbnail folder was created
- ✅ ExtendScript is not empty

### Section 2: ExtendScript Details
```
======================================================================
THUMBNAIL GENERATION - DETAILED DIAGNOSTICS
======================================================================
ExtendScript length: XXXX characters
ExtendScript file: /tmp/tmp_xxxxx.jsx
Results file: /tmp/tmp_xxxxx.json
JSX file exists: True
First 300 chars of script:
// Thumbnail Export Script
var psdFile = new File("/path/to/file.psd");
...
Last 300 chars of script:
...
resultsFile.write(toJSON(results));
resultsFile.close();
```

**What to check**:
- ✅ ExtendScript looks correct (compare with test script)
- ✅ PSD path in script is correct
- ✅ Results file path is correct
- ✅ Script ends with file write operations

### Section 3: AppleScript Execution
```
Executing Photoshop script for thumbnail generation...
AppleScript:
tell application "Adobe Photoshop 2026"
    activate
    do javascript file (POSIX file "/tmp/tmp_xxxxx.jsx")
end tell

AppleScript return code: 0
AppleScript stdout:
AppleScript stderr:
```

**What to check**:
- ✅ Return code is 0 (success)
- ⚠️ If return code != 0, check stderr for errors
- ℹ️ stdout is usually empty (Photoshop doesn't output here)

### Section 4: Results File
```
Results file exists after execution: True/False
Results file size: XXXX bytes
Results file content (XXXX chars):
[{"layer":"LayerName","safeName":"LayerName","file":"...","success":true},...]
```

**What to check**:
- ✅ Results file exists
- ✅ File size > 0
- ✅ Content is valid JSON array
- ✅ Each layer has success:true
- ⚠️ If success:false, check error/reason fields

### Section 5: Parsed Results
```
Parsed thumbnails count: 6
Thumbnails dict: {'Layer1': 'Layer1.png', 'Layer2': 'Layer2.png', ...}
======================================================================
FINAL RESULT: Generated 6 thumbnails
Thumbnails keys: ['Layer1', 'Layer2', 'Layer3', ...]
```

**What to check**:
- ✅ Count matches number of layers in PSD
- ✅ Dict has correct mapping of layer names to filenames
- ✅ Final result shows expected count

## Common Issues to Diagnose

### Issue 1: Empty Thumbnails Dict
**Symptom**: `Parsed thumbnails count: 0`

**Check**:
1. Results file exists?
2. Results file size > 0?
3. Results file contains valid JSON?
4. JSON has success:true for any layers?

**Likely causes**:
- Photoshop script didn't run
- All layers failed to export
- Results file not written

### Issue 2: Photoshop Script Error
**Symptom**: `AppleScript return code: 1`

**Check**:
- AppleScript stderr message
- Is Photoshop 2026 installed?
- Is the JSX file path correct?
- Does PSD file exist?

### Issue 3: Wrong Layer Names
**Symptom**: Count is correct but frontend shows 0 matching keys

**Check**:
- Compare `Thumbnails keys` in logs
- vs keys shown in browser console
- Look for name transformation (spaces vs underscores)

### Issue 4: ExtendScript Different from Test
**Symptom**: Test works but production fails

**Check**:
- Save First 300 chars from log
- Compare with test_photoshop_thumbnails.py
- Look for differences in:
  - File paths
  - Document activation points
  - Resize operations
  - Results file writing

## Next Steps After Reviewing Logs

1. **If PSD path is wrong**: Check web_app.py session handling
2. **If ExtendScript is wrong**: Compare with test script character-by-character
3. **If Photoshop fails**: Check error message, verify Photoshop 2026 installed
4. **If results file empty**: Photoshop script ran but didn't export anything
5. **If keys don't match**: Add name normalization in frontend/backend

## Files to Check

- `services/thumbnail_service.py` - The service with logging
- `web_app.py` - The /generate-thumbnails endpoint
- `test_photoshop_thumbnails.py` - The working reference script
- Browser console - Frontend key matching

## Testing Checklist

- [ ] Flask server running
- [ ] Upload PSD file
- [ ] Upload AEPX file
- [ ] Click "Load Visual Previews"
- [ ] Copy entire Flask console output
- [ ] Copy browser console output
- [ ] Check for "THUMBNAIL GENERATION STARTED"
- [ ] Check for "FINAL RESULT" with count
- [ ] Compare with this guide
