# Troubleshooting Guide

This guide helps you solve common problems when using the After Effects Automation tool.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Starting the Application](#starting-the-application)
3. [File Upload Problems](#file-upload-problems)
4. [Processing Errors](#processing-errors)
5. [Aspect Ratio Issues](#aspect-ratio-issues)
6. [Layer Matching Problems](#layer-matching-problems)
7. [Performance Issues](#performance-issues)
8. [Download Issues](#download-issues)
9. [After Effects Integration](#after-effects-integration)
10. [Getting More Help](#getting-more-help)

---

## Installation Issues

### "Python not found" or "command not found: python3"

**Problem:** Terminal says Python isn't installed.

**Solution:**

**Mac:**
```bash
# Install Homebrew first (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install Python
brew install python3

# Verify installation
python3 --version
```

**Windows:**
1. Download from [python.org/downloads](https://python.org/downloads)
2. Run installer
3. ✅ **IMPORTANT:** Check "Add Python to PATH"
4. Restart Command Prompt
5. Type `python --version` to verify

---

### "pip: command not found"

**Problem:** pip isn't available after installing Python.

**Solution:**

**Mac:**
```bash
# pip should come with Python, but if not:
python3 -m ensurepip --upgrade
```

**Windows:**
```bash
python -m ensurepip --upgrade
```

---

### "Requirements installation failed"

**Problem:** `pip install -r requirements.txt` fails with errors.

**Solution:**

```bash
# Update pip first
pip install --upgrade pip

# Try installing again
pip install -r requirements.txt

# If still failing, install packages one by one:
pip install flask
pip install pillow
pip install psd-tools
# ... etc
```

**Common specific errors:**

**"Microsoft Visual C++ required" (Windows):**
- Download and install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

**"Permission denied":**
```bash
# Use --user flag
pip install --user -r requirements.txt
```

---

## Starting the Application

### "Address already in use" / "Port 5001 already in use"

**Problem:** Another process is using port 5001.

**Solution:**

**Mac:**
```bash
# Find what's using port 5001
lsof -ti :5001

# Kill that process
lsof -ti :5001 | xargs kill -9

# Or use a different port
python3 web_app.py --port 5002
```

**Windows:**
```bash
# Find process using port 5001
netstat -ano | findstr :5001

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

---

### "ModuleNotFoundError: No module named 'flask'"

**Problem:** Python can't find installed modules.

**Solution:**

```bash
# Make sure you're using the same Python that has the modules
which python3  # Mac/Linux
where python   # Windows

# Reinstall requirements
pip3 install -r requirements.txt

# If you have multiple Python versions:
python3.9 -m pip install -r requirements.txt
python3.9 web_app.py
```

---

### "Can't access http://localhost:5001"

**Problem:** Browser can't connect to the application.

**Solution:**

1. **Check the terminal** - Does it say "Running on http://127.0.0.1:5001"?
   - If yes, try `http://127.0.0.1:5001` instead of localhost

2. **Check firewall** - Your firewall might be blocking the connection
   - Mac: System Preferences → Security & Privacy → Firewall → Allow Python
   - Windows: Windows Defender Firewall → Allow an app → Python

3. **Try a different browser** - Sometimes browser caching causes issues

4. **Check terminal for errors** - Look for error messages in the terminal window

---

## File Upload Problems

### "Can't upload PSD file" / "Upload failed"

**Problem:** PSD file won't upload.

**Solutions:**

1. **Check file is actually .psd format**
   ```bash
   # Verify file extension
   file your_design.psd
   ```

2. **File is not open in Photoshop**
   - Close the file in Photoshop first
   - Photoshop locks files while they're open

3. **File size too large**
   - Try compressing the PSD (Layer → Flatten Image to reduce size for testing)
   - Check available disk space

4. **File path has special characters**
   - Rename file to remove spaces, accents, or special characters
   - Good: `player_01.psd`
   - Bad: `Player #1 (Final) v2.psd`

---

### "Template file invalid" / "Can't read template"

**Problem:** After Effects template won't upload.

**Solutions:**

1. **Check file extension**
   - Must be `.aepx` (XML-based project file)
   - NOT `.aep` (binary format - not supported yet)

2. **Save template as AEPX in After Effects:**
   - Open your template in After Effects
   - File → Save As → Choose "After Effects Project (XML)"
   - File extension should be `.aepx`

3. **File is not open in After Effects**
   - Close the template in After Effects first

---

## Processing Errors

### "Processing failed" / "Something went wrong"

**Problem:** Generic processing error.

**Steps to diagnose:**

1. **Check the logs**
   ```bash
   # Look at the terminal running web_app.py
   # Recent errors will be shown there

   # Or check the log file
   tail -50 app.log
   ```

2. **Enable debug mode for more information**
   ```bash
   # In .env file:
   DEBUG_MODE=true
   USE_ENHANCED_LOGGING=true
   LOG_LEVEL=DEBUG

   # Restart the application
   python3 web_app.py
   ```

3. **Try with a simpler file**
   - Use a PSD with just 2-3 layers
   - Use a simple template
   - If this works, your original files might be too complex

---

### "PSD parsing failed"

**Problem:** Can't read the Photoshop file.

**Solutions:**

1. **Check Photoshop version**
   - Save as Photoshop CS6 or newer format
   - File → Save As → Format: "Photoshop" (not "Large Document Format")

2. **Flatten some layers**
   - Too many layers or effects can cause issues
   - Try merging some effect layers

3. **Remove problematic features:**
   - Smart objects (rasterize them)
   - Complex blend modes
   - 3D layers (flatten to 2D)

---

### "Layer matching failed"

**Problem:** Tool can't match PSD layers to template layers.

**See [Layer Matching Problems](#layer-matching-problems) below**

---

## Aspect Ratio Issues

### "No aspect ratio preview shown"

**Problem:** Expected to see Fit/Fill/Original options but didn't.

**Explanation:** The preview only appears when your PSD and template have **different** dimensions or aspect ratios.

**Example:**
- PSD: 1080x1920 (vertical, 9:16)
- Template: 1920x1080 (horizontal, 16:9)
- → Preview WILL appear

- PSD: 1920x1080
- Template: 1920x1080
- → No preview needed (perfect match)

---

### "Aspect ratio choices look wrong"

**Problem:** All three preview options (Fit, Fill, Original) look bad.

**Understanding the options:**

**Fit:**
- Your design shrunk to fit inside template
- Maintains aspect ratio
- May have black bars on sides
- **Best for:** Keeping full design visible

**Fill:**
- Your design sized to fill entire template
- Maintains aspect ratio
- May crop edges
- **Best for:** No black bars, okay with slight cropping

**Original:**
- Your design placed as-is
- May be stretched or distorted
- **Best for:** Rarely - only when you want exact pixel placement

**Solution:**
1. Choose "Fill" or "Fit" based on your preference
2. You can always adjust in After Effects afterward
3. Or redesign your PSD to match template dimensions exactly

---

### "Design is stretched or distorted"

**Problem:** Output looks stretched even after choosing an option.

**Solution:**

1. **Check your template comp settings:**
   - Open template in After Effects
   - Check main composition size
   - Make sure it matches what you expect

2. **Redesign at template dimensions:**
   - If template is 1920x1080, design your PSD at 1920x1080
   - This avoids all sizing issues

---

## Layer Matching Problems

### "Layers not matched" / "Many unmatched layers"

**Problem:** Tool couldn't match your PSD layers to template layers.

**Understanding layer matching:**

The tool matches layers by **name similarity**. It uses fuzzy matching to handle differences like:
- Spaces vs underscores: "Player Name" matches "Player_Name"
- Case: "playername" matches "PlayerName"
- Common abbreviations: "bg" matches "background"

**Solutions:**

1. **Name your PSD layers to match template:**

   **Template has:**
   - Player_Name
   - Team_Logo
   - Jersey_Number

   **Your PSD should have:**
   - Player Name (or Player_Name)
   - Team Logo (or Team_Logo)
   - Jersey Number (or Jersey_Number)

2. **Check confidence scores:**
   - 🟢 Green (95%+) = excellent match, use it
   - 🟡 Yellow (70-95%) = probable match, verify in AE
   - 🔴 Red (<70%) = uncertain, manually fix in AE

3. **Simplify layer names:**
   - Bad: "Layer 1 Copy 3 Final v2"
   - Good: "Background"

4. **View template layer names:**
   ```bash
   # If you have command-line access:
   python3 scripts/list_template_layers.py path/to/template.aepx
   ```

---

### "Too many unmatched layers - is this normal?"

**Answer:** It depends!

**Normal unmatched layers:**
- Guide layers
- Background effects
- Template-specific layers you don't need

**Problematic unmatched layers:**
- Your main content layers (player name, team, etc.)
- If >50% of your layers are unmatched, something's wrong

**What to do:**
1. Check a few key layers matched correctly (player name, main image, etc.)
2. If yes, proceed! You can manually place the unmatched layers in After Effects
3. If no, rename layers and try again

---

## Performance Issues

### "Processing is very slow"

**Problem:** Each graphic takes 5+ minutes to process.

**Solutions:**

1. **Simplify your files:**
   - Reduce PSD file size (flatten unnecessary layers)
   - Remove unused layers from template
   - Reduce image dimensions if extremely large (10000px+)

2. **Check system resources:**
   ```bash
   # Mac - check memory usage
   top

   # Look for Python process using lots of RAM
   ```

3. **Close other applications:**
   - Close Photoshop, After Effects, Chrome
   - Free up RAM and CPU

4. **Disable memory tracking if enabled:**
   ```bash
   # In .env
   TRACK_MEMORY=false
   ```

---

### "Application becomes unresponsive"

**Problem:** Web interface freezes or stops responding.

**Solutions:**

1. **Check terminal for errors**
   - Look at the terminal running web_app.py
   - Any error messages?

2. **Restart the application:**
   ```bash
   # In terminal, press Ctrl+C to stop
   # Then start again
   python3 web_app.py
   ```

3. **Clear browser cache:**
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

4. **Check disk space:**
   - Make sure you have at least 5GB free disk space

---

## Download Issues

### "Download failed" / "ZIP file corrupted"

**Problem:** Can't download result or ZIP won't open.

**Solutions:**

1. **Try downloading again:**
   - Click the download button again
   - Browser downloads sometimes fail

2. **Check disk space:**
   - Make sure you have space for the download

3. **Try a different browser:**
   - Chrome, Firefox, or Safari

4. **Download directly from file system:**
   ```bash
   # Results are saved in:
   /path/to/aftereffects-automation/output/{project_id}/{graphic_id}/

   # Look for the .zip file there
   ```

---

### "Downloaded file won't open in After Effects"

**Problem:** After Effects says "File is damaged" or "Can't open project".

**Solutions:**

1. **Check the ZIP extracted correctly:**
   - Unzip the downloaded file
   - You should see:
     - `Your_Graphic.aepx`
     - `Hard_Card.json`
     - Preview images

2. **Check .aepx file size:**
   - If it's 0 bytes or very small (<1KB), something went wrong
   - Try processing again

3. **Open template directly in AE first:**
   - Make sure the original template works in After Effects
   - Then try the generated file

---

## After Effects Integration

### "Can't find composition in After Effects"

**Problem:** Opened the .aepx file but can't find your graphic.

**Solution:**

1. **Look in Project panel** (usually left side)
2. **Find composition named "Hard_Card"** or similar
3. **Double-click it to open**

If you don't see it:
- Check for a folder structure in the Project panel
- Expand all folders
- Look for recently imported items

---

### "Layers are in wrong positions"

**Problem:** Layers are there but not positioned correctly.

**Solutions:**

1. **This is expected for unmatched layers**
   - The tool places matched layers correctly
   - Unmatched layers default to center
   - Manually position unmatched layers

2. **Check layer parenting:**
   - Some layers might be parented to others
   - Changing parent position affects children

3. **Check for expressions:**
   - Some positioning might be controlled by expressions
   - Edit the Hard_Card.json data to update positions

---

### "Text doesn't update when I change Hard_Card.json"

**Problem:** Changed JSON file but text in comp doesn't change.

**Solution:**

1. **Reload the JSON:**
   - The JSON is loaded when the project opens
   - Save project, close After Effects
   - Edit Hard_Card.json
   - Reopen After Effects

2. **Check expression errors:**
   - Select text layer
   - Press U to reveal animated/expression properties
   - Look for yellow warning triangles
   - Fix any expression errors

---

## Getting More Help

### Debug Mode

Enable debug mode for detailed logging:

```bash
# In .env file:
USE_ENHANCED_LOGGING=true
DEBUG_MODE=true
LOG_FORMAT=text
LOG_LEVEL=DEBUG

# Restart application
python3 web_app.py

# Logs will be much more verbose
# Check app.log or terminal output
```

### Check Logs

```bash
# View recent logs
tail -100 app.log

# Search for errors
grep ERROR app.log

# Search for specific graphic
grep "graphic_id=g1" app.log

# Analyze timing
python scripts/analyze_logs.py app.log --timing
```

### Performance Analysis

```bash
# Enable enhanced logging first
USE_ENHANCED_LOGGING=true

# Run your operation
# Then check performance:
curl http://localhost:5001/api/performance-summary
```

### Still Stuck?

If none of the above solutions work:

1. **Gather information:**
   - What operation were you trying to do?
   - What error message did you see?
   - What does app.log show?
   - Screenshots of the error

2. **Check documentation:**
   - [Main README](../README.md) - General usage
   - [Enhanced Logging](ENHANCED_LOGGING.md) - Monitoring
   - [API Documentation](API.md) - API details

3. **Report the issue:**
   - [GitHub Issues](https://github.com/yourusername/aftereffects-automation/issues)
   - Include:
     - Error message
     - Steps to reproduce
     - Relevant log entries
     - OS and Python version

---

## Quick Reference: Common Error Messages

| Error Message | Most Likely Cause | Quick Fix |
|--------------|-------------------|-----------|
| "Address already in use" | Port 5001 occupied | `lsof -ti :5001 \| xargs kill -9` |
| "ModuleNotFoundError" | Missing Python package | `pip install -r requirements.txt` |
| "File not found" | Wrong file path | Check path is absolute, file exists |
| "PSD parsing failed" | Incompatible PSD | Save as CS6 format, remove smart objects |
| "No layers matched" | Layer names don't match | Rename PSD layers to match template |
| "Aspect ratio undefined" | Invalid dimensions | Check PSD and template are valid sizes |
| "Processing timeout" | File too complex | Simplify PSD (fewer layers) |
| "Download failed" | Disk space or browser | Check free space, try different browser |
| "Can't open in AE" | Corrupted .aepx | Try processing again |
| "Expression error" | Invalid JSON data | Check Hard_Card.json syntax |

---

**Last Updated:** January 2025
**Version:** 1.0
