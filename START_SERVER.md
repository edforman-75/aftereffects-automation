# Starting the After Effects Automation Web Server

## Quick Start

### Option 1: Simple Command Line Start

```bash
# Navigate to project directory
cd /home/user/aftereffects-automation

# Start the web server
python3 web_app.py
```

**You'll see:**
```
 * Running on http://127.0.0.1:5001
 * Press CTRL+C to quit
```

**Then open your browser to:** `http://localhost:5001`

---

### Option 2: Mac Users - Use the Menu Bar App

If you're on macOS, you can use the menu bar application:

```bash
# One-time setup
bash scripts/mac_setup.sh

# This creates "AE Automation.app"
# Just double-click it to start!
```

A 🎬 icon appears in your menu bar. Click it → "Start Server" → Browser opens automatically!

---

## What Happens When You Start

### Behind the Scenes (All Silent & Headless):

1. **Flask Web Server** starts on port 5001
2. **SQLite Database** initializes (`data/production.db`)
3. **Service Container** loads all processing services
4. **Configuration** loads from `config.json`

### What You DON'T See:

- ❌ No Photoshop windows opening
- ❌ No After Effects UI launching
- ❌ No command prompts or scripts visible to users
- ✅ Just a clean HTML interface in your browser!

---

## User Workflow (Pure HTML Interface)

### Stage 0: Upload Batch
**Page:** `http://localhost:5001/dashboard`

1. Click "Upload CSV Batch"
2. Select your batch CSV file containing:
   - PSD file paths
   - AEPX template paths
   - Output names
   - Client/project metadata
3. System validates files (PSD and AEPX must exist)
4. Creates jobs in database

**What runs in background:**
- CSV parsing
- File path validation
- Database job creation
- NO Photoshop or After Effects launched yet!

---

### Stage 1: Automated Processing (Headless)
**Trigger:** Click "Start Batch Processing"

**What happens silently:**

```
PSD Processing (No Photoshop UI):
├── psd-tools library reads PSD file structure
├── Extracts layer hierarchy (names, positions, sizes)
├── Exports each layer as PNG thumbnail (150px width)
├── Detects text layers and fonts used
├── Checks if fonts are installed on system
└── Saves layer data to database

AEPX Processing (No After Effects UI):
├── lxml library parses AEPX as XML
├── Extracts composition structure
├── Identifies placeholders and layer names
├── Detects required assets and footage
├── Checks for missing files
└── Saves template structure to database

Auto-Matching (ML-Based):
├── sentence-transformers model loads
├── Compares PSD layer names to AEPX placeholder names
├── Generates confidence scores (0-100%)
├── Creates initial layer mappings
└── Flags low-confidence matches for manual review
```

**You see in HTML:**
- Progress bar
- "Processing..." message
- Completion notification
- Green checkmark when done

**Time:** 10-30 seconds per job

---

### Stage 2: Manual Layer Matching Review
**Page:** `http://localhost:5001/stage2/review/<job_id>`

**HTML Interface Shows:**
- Left column: PSD layers with thumbnails
- Right column: AEPX placeholders
- Color-coded confidence:
  - 🟢 Green: 95%+ (excellent match)
  - 🟡 Yellow: 70-95% (good match)
  - 🔴 Red: <70% (needs review)

**Actions:**
- Click to remap layers manually
- Drag and drop to reassign
- Click "Auto-Match" to reset
- Click "Approve Matches" to proceed

**Backend processing:** None - just HTML/JavaScript interactions

---

### Stage 3: Automatic Validation (Headless)
**Trigger:** Auto-runs after Stage 2 approval

**Validation Checks (All Headless):**
```
Conflict Detection:
├── Text overflow detection (content too long for text box)
├── Aspect ratio mismatches (vertical design → horizontal template)
├── Resolution conflicts (size differences)
├── Font availability (missing fonts on system)
├── Layer count verification (PSD layers vs AEPX placeholders)
└── Asset existence checks (footage files present?)
```

**You see in HTML:**
- Validation results page
- Issues categorized:
  - 🔴 CRITICAL: Requires user review (Stage 4)
  - 🟡 WARNING: Logged but proceeding
  - ✅ PASS: No issues

**If CRITICAL issues:** Routes to Stage 4
**If only warnings/pass:** Auto-proceeds to Stage 5

---

### Stage 4: Validation Review (Conditional)
**Page:** `http://localhost:5001/stage4/validate/<job_id>`

**Only appears if Stage 3 found CRITICAL issues**

**HTML Interface Shows:**
- List of critical issues with descriptions
- Visual previews where applicable
- Options:
  - "Return to Stage 2" (fix matches)
  - "Override Issue" (proceed anyway with justification)
  - "Approve All" (if you've reviewed everything)

**Backend processing:** Stores user decisions in database

---

### Stage 5: ExtendScript Generation (Headless)
**Trigger:** Auto-runs after Stage 4 approval (or Stage 3 if no critical issues)

**What happens silently:**
```
Script Generation (No After Effects UI):
├── Reads approved layer mappings from database
├── Generates ExtendScript (.jsx) code
│   ├── Creates Hard_Card composition
│   ├── Adds expressions to link layers
│   ├── Populates asset paths
│   └── Includes safety checks
├── Writes .jsx file to output directory
├── Creates Hard_Card.json data file
└── Updates job status to Stage 6
```

**You see in HTML:**
- "Generating script..." progress indicator
- "Generation complete" notification
- Download button appears

**Time:** 1-5 seconds per job

---

### Stage 6: Preview & Approval
**Page:** `http://localhost:5001/stage6/preview/<job_id>`

**HTML Interface Shows:**
- "Generate Preview" button
- Preview settings:
  - Resolution (Full/Half/Quarter)
  - Duration (5s default)
  - Format (MP4/MOV/AVI)
  - Quality (Draft/Medium/High)

**Click "Generate Preview":**

**Background Processing (Headless AE Rendering):**
```
aerender Process:
├── Launches After Effects in CLI mode (no UI)
├── Opens the AEPX file
├── Applies the generated .jsx script
├── Renders specified composition
├── Outputs video file to previews/ directory
├── Closes After Effects automatically
└── Updates job status
```

**You see in HTML:**
- "Rendering preview..." progress bar
- Estimated time remaining
- Video player appears when done
- Playback controls (play/pause/scrub)
- Approval buttons:
  - ✅ "Approve & Complete"
  - 🔁 "Regenerate Script" (back to Stage 5)
  - ❌ "Reject" (back to Stage 2)

**Time:** 30 seconds - 5 minutes (depends on complexity)

---

### Completion: Download & Archive
**Trigger:** Click "Approve & Complete"

**You get:**
- ZIP file download containing:
  - Modified AEPX file
  - ExtendScript (.jsx) file
  - Hard_Card.json data file
  - Preview video
  - Layer mappings report (PDF/JSON)

**Job moves to:** Completed Jobs Archive
**Page:** `http://localhost:5001/completed-jobs`

---

## What Stays Silent (Headless Operations)

### Photoshop Never Launches:
- `psd-tools` library reads PSD binary format directly
- Pure Python parsing - no Adobe software needed
- Fallback to ExtendScript only if psd-tools fails on newer PS formats
- Even then, runs via command line (no UI)

### After Effects Stays in Background:
- AEPX parsing is XML reading (no AE needed)
- Only launches for preview rendering via `aerender`
- Runs in CLI mode - no UI windows
- Automatically closes when rendering completes

### Requirements:
- ✅ Photoshop must be **installed** (for font validation)
- ✅ After Effects must be **installed** (for aerender CLI)
- ❌ Neither needs to be **running**
- ❌ Neither shows **UI to users**

---

## System Requirements

### Software:
- Python 3.8+ (runs the web server)
- Adobe After Effects 2020+ (for aerender)
- Adobe Photoshop (optional - only for fallback parsing)

### Hardware:
- Runs on any machine that can run After Effects
- Web browser (Chrome, Firefox, Safari, Edge)

### Network:
- No internet required (runs locally)
- Uses `localhost:5001` (never exposed to internet)

---

## Stopping the Server

### Command Line:
Press `Ctrl+C` in the terminal window

### Mac Menu Bar App:
Click the 🎬 icon → "Stop Server"

### What Happens:
- Flask server shuts down gracefully
- Database connections close
- Background jobs finish or pause
- Can restart anytime without data loss

---

## Troubleshooting

### "Server won't start"
```bash
# Check Python version
python3 --version
# Should show 3.8 or higher

# Check if port 5001 is in use
lsof -i :5001
# If something else is using it, kill that process or change port in web_app.py
```

### "Can't connect to http://localhost:5001"
- Make sure server is running (see terminal output)
- Try `http://127.0.0.1:5001` instead
- Check firewall isn't blocking port 5001

### "Preview generation fails"
```bash
# Verify aerender is accessible
/Applications/Adobe\ After\ Effects\ 2025/aerender -version

# Check path in settings
# Go to http://localhost:5001/settings
# Verify "aerender Path" points to correct location
```

### "Photoshop layers not extracting"
- Ensure PSD file isn't corrupted
- Check file isn't open in Photoshop
- Verify path has no special characters
- Check logs in `logs/` directory

---

## Advanced Configuration

### Change Port:
Edit `web_app.py` line ~50:
```python
app.run(host='0.0.0.0', port=5001)  # Change 5001 to your desired port
```

### Production Deployment:
Use a WSGI server instead of Flask development server:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 web_app:app
```

### Enable HTTPS:
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Update web_app.py
app.run(host='0.0.0.0', port=5001, ssl_context=('cert.pem', 'key.pem'))
```

---

## Architecture Summary

```
User's Browser (HTML/CSS/JS)
         ↕ HTTP (localhost:5001)
Flask Web Server (web_app.py)
         ↓
Route Blueprints (routes/*.py)
         ↓
Service Layer (services/*.py)
         ↓
Processing Modules (modules/phase*/)
         ↓
External Tools (headless):
  ├── psd-tools (PSD parsing)
  ├── lxml (AEPX XML parsing)
  └── aerender (AE CLI rendering)
         ↓
SQLite Database (data/production.db)
```

**Key Points:**
- User only sees HTML pages
- All processing happens server-side
- No Adobe UI ever shown to user
- PSD/AE run as "headless servers" in background
- Results delivered through web interface

---

## Daily Usage Workflow

### Morning: Start Server
```bash
cd /home/user/aftereffects-automation
python3 web_app.py
```
(Or double-click Mac menu bar app)

### During Day: Use HTML Interface
- Open browser to `http://localhost:5001`
- Upload batches
- Review matches
- Approve previews
- Download results

### Evening: Stop Server
- Press `Ctrl+C` in terminal
- All progress saved to database
- Can resume tomorrow exactly where you left off

---

## What Makes This "Headless"?

### Traditional Workflow (User Sees Everything):
```
User clicks "Process"
  → Photoshop window opens
  → User sees layers loading
  → User sees export progress bars
  → Photoshop closes
  → After Effects window opens
  → User sees rendering progress
  → After Effects closes
  → Done
```

### Your System (Headless):
```
User clicks "Process"
  → HTML shows "Processing..."
  → (psd-tools reads file silently)
  → (lxml parses XML silently)
  → (aerender renders in background)
  → HTML shows "Complete!"
  → Download button appears
  → Done
```

**User never sees:**
- Photoshop splash screen
- Layer panels
- Export dialogs
- After Effects render queue
- Progress bars from Adobe apps
- Any Adobe UI whatsoever

**User only sees:**
- Clean HTML interface
- Progress indicators in browser
- Preview videos
- Download buttons

---

## Summary

Your system is **production-ready** and **already configured** to run as requested:

✅ **HTML pages are the head** - Flask serves 11 comprehensive HTML pages
✅ **PSD acts as headless server** - psd-tools library, no Photoshop UI
✅ **AE acts as headless server** - XML parsing + aerender CLI, no AE UI
✅ **Both must be installed** - Required for font checks and rendering
✅ **Both remain silent** - Never show UI to end users

**To start using it:** Run `python3 web_app.py` and open `http://localhost:5001`

All processing happens invisibly in the background. Users only interact with clean, modern HTML interfaces.
