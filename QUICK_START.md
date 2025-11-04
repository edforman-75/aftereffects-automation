# Quick Start - HTML Interface

## Your System is Ready! ✅

This After Effects automation runs as a **web-based system** with HTML pages as the primary interface. Photoshop and After Effects work silently in the background as headless servers.

---

## Starting the System (Choose One Method)

### Method 1: Use the Start Script (Easiest)

**Mac/Linux:**
```bash
./start.sh
```

**Windows:**
```
start.bat
```

### Method 2: Manual Start
```bash
python3 web_app.py
```

---

## Opening the HTML Interface

Once the server starts, you'll see:
```
* Running on http://127.0.0.1:5001
```

**Then open your browser to:**
```
http://localhost:5001
```

**Bookmark this URL** for easy access!

---

## What You'll See (All HTML Pages)

### Main Dashboard
`http://localhost:5001/`
- Overview of all jobs
- Quick statistics
- Upload new batches

### Production Dashboard
`http://localhost:5001/dashboard`
- Active jobs by stage
- Batch processing status
- Stage progression view

### Stage 2: Layer Matching Review
`http://localhost:5001/stage2/review/<job_id>`
- Visual layer matching interface
- Click-to-map layers
- Confidence scores
- Manual adjustments

### Stage 4: Validation Review
`http://localhost:5001/stage4/validate/<job_id>`
- Critical issues display
- Override options
- Return to previous stage

### Stage 6: Preview & Approval
`http://localhost:5001/stage6/preview/<job_id>`
- Video preview player
- Generate preview button
- Approve/Reject controls
- Download final files

### Completed Jobs Archive
`http://localhost:5001/completed-jobs`
- All completed work
- Download past projects
- Restore archived jobs

### Settings
`http://localhost:5001/settings`
- Configure paths
- Adjust thresholds
- Set preview defaults

---

## Behind the Scenes (Silent Operations)

### When You Upload Files:
- ✅ PSD parsed with `psd-tools` (no Photoshop UI)
- ✅ AEPX parsed as XML (no After Effects UI)
- ✅ Layers matched with ML algorithms
- ❌ No Adobe windows open

### When You Generate Previews:
- ✅ After Effects `aerender` runs in CLI mode
- ✅ Renders in background (no UI)
- ✅ Creates video file
- ✅ Closes automatically
- ❌ You never see After Effects

### What Must Be Installed:
- ✅ Python 3.8+ (runs web server)
- ✅ After Effects 2020+ (for aerender CLI)
- ✅ Photoshop (optional, for fallback parsing)

### What Doesn't Need to Run:
- ❌ Photoshop doesn't need to be open
- ❌ After Effects doesn't need to be open
- ❌ No manual Adobe interactions required

---

## Daily Workflow

### 1. Morning: Start Server
```bash
./start.sh
```
Leave the terminal window open (server stays running)

### 2. Work: Use HTML Interface
- Open browser to `http://localhost:5001`
- Upload batches via HTML form
- Review matches in browser
- Approve previews
- Download results

### 3. Evening: Stop Server
- Press `Ctrl+C` in terminal window
- All progress saved to database
- Resume tomorrow exactly where you left off

---

## 6-Stage HTML Workflow

```
📤 Stage 0: Upload Batch (HTML form)
        ↓
⚙️  Stage 1: Auto Process (runs in background, no UI)
        ↓
👤 Stage 2: Manual Review (HTML page with visual interface)
        ↓
✓  Stage 3: Auto Validate (runs in background, no UI)
        ↓
👤 Stage 4: Validation Review (HTML page, only if critical issues)
        ↓
⚙️  Stage 5: Generate Script (runs in background, no UI)
        ↓
👤 Stage 6: Preview & Approve (HTML page with video player)
        ↓
✅ Complete: Download ZIP package
```

**👤 = You interact via HTML**
**⚙️ = System works silently in background**

---

## Key Features

### Headless Photoshop Processing
- Extracts all layer data without opening PS
- Exports thumbnails for HTML preview
- Detects fonts automatically
- Pure Python parsing

### Headless After Effects Processing
- Parses AEPX as XML (no AE needed)
- Generates ExtendScript automatically
- Renders previews via CLI
- Never shows After Effects UI

### Web-Based Interface
- Modern HTML/CSS/JavaScript
- Responsive design
- Real-time updates
- No desktop app needed

### Batch Processing
- Upload CSV with multiple jobs
- Process all at once
- Track progress in HTML dashboard
- Download all results

---

## System Architecture

```
┌─────────────────────────────────────┐
│   User's Web Browser (HTML/CSS/JS) │
│         http://localhost:5001       │
└───────────────┬─────────────────────┘
                │ HTTP Requests
                ↓
┌─────────────────────────────────────┐
│    Flask Web Server (Python)        │
│         Routes + Templates          │
└───────────────┬─────────────────────┘
                │
                ↓
┌─────────────────────────────────────┐
│    Service Layer (Business Logic)   │
│   30+ Services via DI Container     │
└───────────────┬─────────────────────┘
                │
        ┌───────┴────────┐
        ↓                ↓
┌──────────────┐  ┌──────────────┐
│  Headless    │  │  Headless    │
│  Photoshop   │  │    After     │
│  (psd-tools) │  │   Effects    │
│              │  │  (aerender)  │
└──────────────┘  └──────────────┘
        │                │
        └────────┬───────┘
                 ↓
        ┌─────────────────┐
        │ SQLite Database │
        │  (Job Tracking) │
        └─────────────────┘
```

---

## Troubleshooting

### Can't Access http://localhost:5001
**Fix:** Make sure the server is running (check terminal for "Running on...")

### Preview Generation Fails
**Fix:** Verify After Effects is installed and check aerender path in Settings page

### PSD Layers Not Extracting
**Fix:** Ensure PSD file isn't open in Photoshop and isn't corrupted

### Port 5001 Already in Use
**Fix:**
```bash
# Find what's using port 5001
lsof -i :5001

# Kill that process, or change port in web_app.py
```

---

## Support

### Documentation
- **Detailed Guide:** See `START_SERVER.md`
- **API Docs:** See `docs/API.md`
- **Logging:** See `docs/ENHANCED_LOGGING.md`

### Getting Help
- Check logs in `logs/` directory
- Review error messages in HTML interface
- Enable debug mode in Settings page

---

## What Makes This "Headless"?

### Traditional Workflow:
```
User clicks button
  → Photoshop window opens
  → User waits watching progress bars
  → Photoshop closes
  → After Effects window opens
  → User watches render queue
  → After Effects closes
```

### Your System:
```
User clicks button in HTML page
  → Processing happens invisibly
  → HTML shows progress indicator
  → User gets notification when done
  → Downloads results
```

**No Adobe UI ever shown to users!** ✨

---

## Summary

Your system is **production-ready** and **already configured** for HTML-first operation:

✅ HTML pages are the primary interface
✅ Flask web server handles all requests
✅ Photoshop runs headless (psd-tools)
✅ After Effects runs headless (aerender CLI)
✅ Both must be installed
✅ Both remain completely silent
✅ Users only see clean web pages

**To start:** Run `./start.sh` and open `http://localhost:5001`

🎉 **You're ready to process graphics at scale!**
