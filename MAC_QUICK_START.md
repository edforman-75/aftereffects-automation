# Mac Quick Start Guide

**🎉 The easiest way to use After Effects Automation on Mac!**

---

## One-Time Setup (5 Minutes)

### What You Need:
- A Mac (macOS 10.15 or newer)
- Python 3.10+ installed ([get it here](https://www.python.org/downloads/) if you don't have it)
- This downloaded project folder

### Setup Steps:

**1. Open Terminal**
   - Go to **Applications** → **Utilities** → **Terminal**
   - A white or black window will open

**2. Navigate to the project**
   - In Terminal, type: `cd ` (that's cd with a space after it)
   - **Don't press Enter yet!**
   - Find the downloaded project folder in Finder
   - **Drag the folder** into the Terminal window
   - The path will appear automatically
   - Now press **Enter**

**3. Run the setup**
   - Type: `bash scripts/mac_setup.sh`
   - Press **Enter**
   - Wait 2-3 minutes while it installs everything
   - You'll see progress messages

**4. Done!**
   - You'll see "✅ Setup Complete!" when finished
   - You can close Terminal now
   - You'll never need Terminal again!

---

## Daily Use (30 Seconds)

### Starting the Tool:

**1. Find "AE Automation.app"**
   - It's in the same folder you downloaded
   - Has a blue icon (or generic app icon)

**2. Double-click it**
   - The app will launch
   - A 🎬 icon appears in your menu bar (top-right corner)

**3. Click the menu bar icon**
   - Click the 🎬 icon
   - Select **"Start Server"**
   - Wait 3 seconds

**4. Browser opens automatically!**
   - Goes to `http://localhost:5001`
   - The tool is ready to use!

### Using the Tool:

Now just use the web interface:
- Upload your PSD files
- Select your template
- Process graphics
- Download results

### Stopping the Tool:

When you're done:
- Click the 🎬 icon in menu bar
- Select **"Quit"**
- Done! Server stops automatically

---

## Menu Bar Options

Click the 🎬 icon to see:

- **Start Server** - Starts the tool (opens browser)
- **Stop Server** - Stops the tool (keeps menu bar icon running)
- **Open in Browser** - Opens the tool in your browser
- **View Logs** - Opens the log file (for troubleshooting)
- **About** - Version information
- **Quit** - Exits completely (stops server if running)

---

## Visual Status

- 🟢 **Green dot** = Server is running, tool is ready
- 🔴 **Red dot** = Server is stopped

---

## Troubleshooting

### "App can't be opened because it's from an unidentified developer"

**Solution:**
1. Right-click (or Control+click) on "AE Automation.app"
2. Select **"Open"** from the menu
3. Click **"Open"** in the dialog
4. This only needs to be done once!

### Menu bar icon doesn't appear

**Solution:**
1. Open Terminal
2. Type: `cd ` (drag project folder in)
3. Press Enter
4. Type: `source venv/bin/activate`
5. Type: `pip install rumps`
6. Try launching the app again

### Server won't start

**Solution:**
1. Click 🎬 → **"View Logs"**
2. Look for error messages
3. Most common issue: Port 5001 already in use
4. Fix: Open Terminal, type: `lsof -ti :5001 | xargs kill -9`

### Python not installed

**Solution:**
1. Go to [python.org/downloads](https://www.python.org/downloads)
2. Download Python 3.10 or newer
3. Run the installer
4. Run setup script again: `bash scripts/mac_setup.sh`

---

## Optional: Move to Applications Folder

Want the app to show in Launchpad and Spotlight?

1. Find "AE Automation.app"
2. Drag it to **Applications** folder
3. Done! Now it's like any other Mac app

You can search for it with Spotlight (Cmd+Space) or find it in Launchpad.

---

## Tips

### Keep Terminal Closed
- You never need Terminal after setup
- The app handles everything

### Leave Menu Bar Icon Running
- Keep the 🎬 icon running in background
- Start/stop server as needed
- Only quit when completely done

### Check Status at a Glance
- Look at menu bar: 🟢 = ready, 🔴 = stopped
- No need to open browser to check

### Quick Restart
- If something goes wrong: Click 🎬 → Stop Server → Start Server
- This resets everything

---

## What Gets Installed?

The setup script creates:
- **Virtual environment** (isolated Python packages)
- **Dependencies** (Flask, PSD tools, etc.)
- **Data directories** (for your projects)
- **The Mac app** (AE Automation.app)

Everything stays in the project folder - nothing installed system-wide except Python (which you need anyway).

---

## Uninstalling

If you ever want to remove the tool:

1. Quit the app (🎬 → Quit)
2. Delete the entire project folder
3. Done!

No system files are modified, so it's completely clean.

---

## Need More Help?

- **General usage:** See [README.md](README.md)
- **Troubleshooting:** See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Menu bar app:** See [scripts/mac_app/MENU_BAR_APP.md](scripts/mac_app/MENU_BAR_APP.md)

---

## Comparison: Before vs After

### Before (Traditional Method)
```
1. Open Terminal
2. cd /path/to/project
3. source venv/bin/activate
4. python3 web_app.py
5. Leave Terminal open
6. Open browser manually
7. Remember to stop with Ctrl+C
```

### After (Mac App Bundle)
```
1. Double-click app
2. Click 🎬 → Start Server
3. Done!
```

**Time saved:** 90% less friction!

---

**Enjoy your new streamlined workflow!** 🎉

Stop wasting time on repetitive After Effects work. Start creating more.
