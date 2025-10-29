# Mac Menu Bar Application

The After Effects Automation tool includes a Mac menu bar application for easy control.

## Features

- 🟢 **Visual Status** - Green dot when running, red when stopped
- 🚀 **Easy Start/Stop** - Click to start or stop the server
- 🌐 **Quick Browser Access** - Open tool in browser with one click
- 📋 **View Logs** - Quick access to application logs
- 🔔 **Notifications** - Get notified when server starts/stops

## Menu Options

- **Start Server** - Starts the web server and opens browser
- **Stop Server** - Stops the web server
- **Open in Browser** - Opens http://localhost:5001
- **View Logs** - Opens log file in Console.app
- **About** - Version and info
- **Quit** - Exits the menu bar app (stops server if running)

## First Time Setup

1. Open Terminal just once
2. Navigate to the project folder
3. Run: `bash scripts/create_mac_app.sh`
4. Done! Now you have "AE Automation.app"

## Daily Use

1. Double-click "AE Automation.app"
2. Click the 🎬 menu bar icon
3. Click "Start Server"
4. Browser opens automatically!
5. Do your work
6. Click 🎬 → "Quit" when done

## Troubleshooting

**Menu bar icon doesn't appear:**
- Make sure Python 3 is installed
- Run: `pip install rumps`

**Server won't start:**
- Check if port 5001 is already in use
- View logs: Click 🎬 → "View Logs"

**Can't find the app:**
- It's in the same folder as all the other files
- Optionally drag it to Applications folder
