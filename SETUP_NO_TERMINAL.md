# After Effects Automation - Terminal-Free Setup

**No command line knowledge required! Just double-click and go.**

---

## Quick Start (3 Easy Steps)

### Step 1: Install Python (One-Time Setup)

**Windows:**
1. Visit [python.org/downloads](https://python.org/downloads)
2. Download Python 3.8 or newer
3. Run the installer
4. ✅ **IMPORTANT:** Check "Add Python to PATH"
5. Click "Install Now"

**Mac:**
1. Visit [python.org/downloads](https://python.org/downloads)
2. Download Python 3.8 or newer
3. Run the installer and follow prompts

**Linux:**
Python is usually pre-installed. If not, use your package manager (e.g., `sudo apt install python3`)

---

### Step 2: Install Dependencies (One-Time Setup)

**Option A: Double-Click Installer (Easiest)**

1. Navigate to the `aftereffects-automation` folder
2. Double-click `install_dependencies.py`
3. Wait 2-3 minutes while it installs
4. You'll see "✅ Installation complete!"

**Option B: Via Terminal (Alternative)**

If the double-click doesn't work:
1. Open Terminal/Command Prompt
2. Navigate to the project folder
3. Run: `pip install -r requirements.txt`

---

### Step 3: Start the Server

**Three Ways to Start (Pick One):**

#### Method 1: One-Click Launcher (Simplest) ⭐
1. Double-click `start_server.py` in the main folder
2. Wait for browser to open automatically
3. Start using the tool!

#### Method 2: Auto-Start Service (Best for Daily Use) ⭐⭐⭐
1. Double-click `start_server.py` to start the server
2. Open browser to: http://localhost:5001
3. Click **Admin** (bottom of page) or visit: http://localhost:5001/admin
4. Click **"Install Service"**
5. Done! Server will now start automatically every time you log in

#### Method 3: Menu Bar App (Mac Only)
1. Double-click `AE Automation.app` (if you ran the Mac setup)
2. Click the 🎬 icon in your menu bar
3. Click "Start Server"
4. Your browser opens automatically!

---

## Daily Usage (After Setup)

### If You Installed as Service:
- **Nothing to do!** The server starts automatically
- Open your browser to: http://localhost:5001
- Start uploading files and creating graphics!

### If You Use the One-Click Launcher:
- Double-click `start_server.py`
- Wait for browser to open
- Start working!

### If You Use the Mac Menu Bar App:
- The 🎬 icon shows server status
- Click it for options:
  - Start Server
  - Stop Server
  - Open in Browser
  - View Logs

---

## Server Management (All from Web Browser!)

Visit **http://localhost:5001/admin** for full control:

### What You Can Do:
- ✅ **View server status** - See if running, PID, platform info
- ✅ **Restart server** - If something goes wrong
- ✅ **Stop server** - When you're done for the day
- ✅ **Install auto-start service** - Make server start on boot
- ✅ **View logs** - See what's happening behind the scenes
- ✅ **Uninstall service** - Remove auto-start if needed

**No terminal required for any of this!**

---

## Troubleshooting

### Server Won't Start
1. Make sure Python is installed: Double-click `check_python.py`
2. Make sure dependencies are installed: Double-click `install_dependencies.py`
3. Check if port 5001 is in use:
   - Visit: http://localhost:5001/admin
   - If page loads, server is already running!

### Browser Doesn't Open Automatically
- Manually open browser
- Type: `http://localhost:5001`
- Bookmark it for easy access!

### "Module Not Found" Error
- Double-click `install_dependencies.py` again
- Wait for it to complete
- Try starting the server again

### Port Already in Use
The server is probably already running!
- Try opening: http://localhost:5001
- Or visit the admin page to check status

### Can't Stop the Server
1. Visit: http://localhost:5001/admin
2. Click "Stop Server"
3. Or restart your computer (if all else fails)

---

## Uninstalling Auto-Start

If you installed the service and want to remove it:

1. Visit: http://localhost:5001/admin
2. Scroll to "Auto-Start Service"
3. Click "Uninstall Service"
4. Done! Server will no longer start automatically

---

## Advanced: Using the Terminal (Optional)

If you prefer terminal commands, you still can:

**Start server:**
```bash
python3 start_server.py
```

**Install service:**
```bash
python3 install/install_service.py
```

**Uninstall service:**
```bash
python3 install/install_service.py uninstall
```

But you don't need to! Everything works with double-clicking and web interface.

---

## File Overview

### Files You'll Use:
- **start_server.py** - Double-click to start the server
- **install_dependencies.py** - Double-click to install dependencies
- **install/install_service.py** - Double-click to install auto-start

### Files You Can Ignore:
- **web_app.py** - The actual server (started by start_server.py)
- **requirements.txt** - List of dependencies
- Everything in `/install/` folder (handled by installer)
- Everything in `/scripts/` folder (old terminal scripts)

---

## Platform-Specific Notes

### Windows
- Double-clicking `.py` files should work if Python is installed correctly
- If not, right-click → "Open with" → Python
- Or create shortcuts to `start_server.py` for easy access

### macOS
- Double-clicking `.py` files opens them in Terminal automatically
- Or use the "AE Automation.app" (if you ran mac_setup.sh once)
- Service installation creates a LaunchAgent for auto-start

### Linux
- May need to set `.py` files as executable first:
  - Right-click → Properties → Permissions → "Execute as program"
- Or use the auto-start service installer
- Service installation uses systemd user service

---

## Summary

**What This Setup Gives You:**

1. ✅ **No Terminal Required** - Everything done by double-clicking or web interface
2. ✅ **Auto-Start Option** - Server starts when you log in (if installed)
3. ✅ **Web-Based Control** - Manage server from browser at /admin
4. ✅ **Simple Updates** - Just download new version and double-click to start
5. ✅ **Cross-Platform** - Works on Windows, Mac, and Linux

**You'll never need to open a terminal unless you want to!**

---

## Questions?

- **Where are my files?** Check the `/uploads/` folder for uploads, `/output/` for results
- **How do I update?** Download new version, copy your files, start new version
- **Can I access from other computers?** Yes, but requires network setup (advanced)
- **Is my data safe?** Everything runs locally, nothing goes to the cloud

**Enjoy your terminal-free experience!** 🎉
