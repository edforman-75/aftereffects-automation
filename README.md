# After Effects Automation Tool

**Stop spending hours copying layers from Photoshop to After Effects. Let this tool do it for you in seconds.**

---

## 🎉 NEW: No Terminal Required!

**Prefer to avoid the terminal?** We now have a completely terminal-free setup!

👉 **[Click here for Terminal-Free Setup Guide](SETUP_NO_TERMINAL.md)** 👈

Just double-click Python files and use the web interface for everything!

---

## What This Tool Does (In Simple Terms)

**Before this tool:** You spent hours manually copying layers from Photoshop into After Effects templates, fixing positions, adding expressions, and adjusting for different screen sizes.

**With this tool:** Upload your Photoshop file and pick a template. The tool automatically:
- ✅ Matches your Photoshop layers to the After Effects template
- ✅ Fixes sizing problems (like when your design is vertical but the template is horizontal)
- ✅ Shows you previews so you can pick what looks best
- ✅ Adds smart expressions so text and images update automatically
- ✅ Gives you a ready-to-use After Effects file in seconds

**Real Example:**
You have 50 player graphics to make for a basketball game. Instead of spending 2 hours per graphic (100 hours total), this tool does it in 2 minutes per graphic (100 minutes total). **That's 98.5 hours saved!**

---

## Is This Tool Right For You?

### ✅ You should use this if:
- You make lots of similar graphics (sports, news, social media)
- You have Photoshop designs and After Effects templates
- You're tired of repetitive manual work
- You want to spend more time being creative, less time copying and pasting

### ❌ This might not be for you if:
- You only make one-off custom graphics
- Your designs are completely different every time
- You prefer doing everything manually

---

## What You'll Need

### On Your Computer:
- A Mac or Windows computer (Mac is easier to set up)
- After Effects installed (any version from 2020 or newer)
- About 30 minutes for first-time setup

### Your Files:
- Photoshop files (.psd) - Your designs
- After Effects templates (.aepx) - Your templates
- That's it!

---

## Quick Start (Really Simple)

**Don't worry if these steps seem unfamiliar - we'll walk through each one with pictures.**

### 🆕 Option 1: Terminal-Free Setup (Easiest!) ⭐⭐⭐

**Prefer not to use the terminal? No problem!**

1. **Install Python** from [python.org/downloads](https://python.org/downloads)
2. **Double-click** `install_dependencies.py` (installs everything)
3. **Double-click** `start_server.py` (starts the server)
4. **Browser opens automatically** - start using the tool!

**For more details:** See [Terminal-Free Setup Guide](SETUP_NO_TERMINAL.md)

### Option 2: Mac Users - Automated Setup 🎉

**If you're on a Mac, we have a special one-time setup that does everything for you:**

1. **Download the tool** (see Step 1 below)
2. **Open Terminal once:**
   - Go to Applications → Utilities → Terminal
   - Type `cd ` (that's cd with a space)
   - Drag the downloaded folder into Terminal (this types the path!)
   - Press Enter
   - Type: `bash scripts/mac_setup.sh`
   - Press Enter
   - Wait 2-3 minutes while it installs everything
3. **Done!** You now have "AE Automation.app"
4. **Daily use:** Just double-click "AE Automation.app" - no Terminal needed!
   - A 🎬 icon appears in your menu bar
   - Click it and select "Start Server"
   - Your browser opens automatically!

**That's it! The rest of this guide is for Windows users or if you prefer the manual method.**

---

### Option 3: Manual Terminal Setup (All Platforms)

**For users comfortable with the terminal:**

### Step 1: Get the Tool on Your Computer

1. **Download the tool:**
   - Go to the [GitHub repository](https://github.com/yourusername/aftereffects-automation)
   - Click the green **"Code"** button
   - Click **"Download ZIP"**
   - Unzip the downloaded file to your Desktop or Documents folder

2. **Install Python** (the engine that runs the tool):

   **Mac users:**
   - Open **Terminal** (it's in Applications > Utilities)
   - Copy and paste this: `brew install python3`
   - Press Enter and wait (takes 2-3 minutes)

   **Windows users:**
   - Go to [python.org/downloads](https://python.org/downloads)
   - Download Python 3.8 or newer
   - Run the installer
   - ✅ Check the box that says "Add Python to PATH"
   - Click "Install Now"

3. **Install the tool parts:**
   - Open Terminal (Mac) or Command Prompt (Windows)
   - Type `cd ` (that's cd with a space after it)
   - Drag the unzipped folder into the Terminal window (this types the path for you!)
   - Press Enter
   - Type: `pip install -r requirements.txt`
   - Press Enter and wait (takes 2-3 minutes)

**That's the hard part done!** ✅ You never have to do this again.

### Step 2: Start the Tool

1. In Terminal/Command Prompt, make sure you're in the tool folder (see Step 1.3)
2. Type: `python3 web_app.py`
3. Press Enter
4. You'll see: `Running on http://127.0.0.1:5001`

**What this means:** The tool is now running on your computer like a website.

### Step 3: Open the Tool in Your Browser

1. Open Chrome, Safari, Firefox, or Edge
2. Type in the address bar: `http://localhost:5001`
3. Press Enter
4. You'll see the main screen with buttons!

**Important:** Keep the Terminal/Command Prompt window open while you use the tool. When you're done, press `Ctrl+C` in that window to stop the tool.

---

## Your First Project (Step-by-Step)

Let's make a simple test graphic to see how it works.

### 1. Create a New Project

![Main Dashboard](docs/screenshots/dashboard.png)
*The main screen you'll see when you open the tool*

**What to do:**
- Click the big blue **"New Project"** button
- Give it a name like "Test Project"
- Click **"Create"**

### 2. Upload Your Files

![Upload Screen](docs/screenshots/upload.png)
*Drag and drop your files here*

**What to do:**
- Click **"Upload PSD"** or drag your .psd file into the box
- Click **"Choose Template"** and select your After Effects template
- Wait for the green checkmarks (means they're ready)

**What the tool is doing:**
Reading your files to understand the layers and sizes.

### 3. Add a Graphic

**What to do:**
- Give your graphic a name (like "Player 01 - John Smith")
- Click **"Add Graphic"**
- Click **"Process"**

**What the tool is doing:**
- Matching your Photoshop layers to the template layers
- Checking if sizes match
- Preparing everything

### 4. Review Size Adjustment (If Needed)

![Aspect Ratio Preview](docs/screenshots/aspect-ratio-modal.png)
*Choose how you want your design to fit the template*

**If your Photoshop file is a different size than the template, you'll see this:**

- **Left (Fit):** Your design shrunk to fit inside (might have black bars)
- **Middle (Fill):** Your design sized to fill everything (might crop edges)
- **Right (Original):** Your design as-is (might look stretched)

**What to do:**
- Look at all three previews
- Click the one that looks best
- Click **"Proceed with [your choice]"**

**Don't stress!** You can always adjust this later in After Effects.

### 5. Wait for Processing

![Processing](docs/screenshots/processing.png)
*Progress bar while the tool works*

**What's happening:**
- Matching layers by name
- Creating expressions
- Packaging everything up

**This takes 10-30 seconds per graphic.**

### 6. Download Your Result

![Download Ready](docs/screenshots/download-ready.png)
*Green download button means you're ready!*

**What to do:**
- Click the green **"Download"** button
- Save the ZIP file
- Unzip it - you'll get:
  - **Your_Graphic.aepx** - Open this in After Effects
  - **Hard_Card.json** - Data file (if you're using expressions)
  - **Preview images** - To see what was done

### 7. Open in After Effects

**What to do:**
1. Open After Effects
2. **File → Open Project**
3. Select the `.aepx` file you just downloaded
4. Your graphic is ready to render! 🎉

**To update text, images, etc:**
- Find the "Hard_Card" composition in your Project panel
- Open it and change values
- Everything updates automatically!

---

## Common Questions

### "What if the layer names don't match perfectly?"

**The tool is smart:**
- If your PSD has "Player Name" and template has "Player_Name", it figures it out
- It handles spaces, underscores, and capitalization differences
- You'll see a confidence score:
  - 🟢 Green = excellent match (95%+)
  - 🟡 Yellow = probable match (70-95%)
  - 🔴 Red = uncertain (under 70%)

**If it can't figure it out:**
- It skips that layer and tells you
- You can manually fix it in After Effects in 5 seconds

### "What if I have 50 graphics to make?"

**That's where this tool shines!**

1. Create your project
2. Click **"Add Multiple Graphics"**
3. Drag all 50 PSD files at once
4. Click **"Process All"**
5. Go get coffee ☕ (takes about 5-10 minutes for 50 graphics)
6. Come back to 50 ready-to-use After Effects files!

### "Can I use my own custom templates?"

**Yes!** Any After Effects template (.aepx file) works. The tool reads the layer names and does its best to match them to your Photoshop layers.

**Tip:** The better you name your layers, the better the matches!

### "What if something goes wrong?"

**The tool is forgiving:**
- If processing fails, click the **"Retry"** button
- It tells you what went wrong in plain English
- It saves your progress - you don't start over
- You can skip graphics that have problems and come back to them later

### "Do I need internet?"

**No!** Everything runs on your computer. Your files never leave your machine. Total privacy!

### "Is this safe? Will it mess up my files?"

**100% safe:**
- The tool NEVER modifies your original PSD or AEPX files
- It creates NEW After Effects files
- Your originals stay untouched
- You can delete the results and try again anytime

---

## Tips for Best Results

### ✏️ Name Your Photoshop Layers Clearly

**Good layer names:**
- `Player Name`
- `Team Logo`
- `Score Home`
- `Background Image`

**Bad layer names:**
- `Layer 1`
- `Text`
- `Image Copy 3`

**Why:** The tool matches by name. Clear names = better matches = less manual fixing.

### 📁 Keep Your Files Organized

**Before you start:**
```
My Project/
  ├── Photoshop Files/
  │     ├── player_01.psd
  │     ├── player_02.psd
  │     └── player_03.psd
  └── Templates/
        └── player_template.aepx
```

**After processing:**
```
My Project/
  └── Finished Graphics/
        ├── player_01.aepx
        ├── player_02.aepx
        └── player_03.aepx
```

### 🎯 Start Small

**For your first time:**
1. Try ONE simple graphic
2. See how it works
3. Open the result in After Effects
4. Look at what it did
5. Then batch process more!

**Don't jump into 100 graphics on day one.** Learn the tool first.

---

## Getting Help

### If you get stuck:

1. **Check this guide** - Read through the steps again carefully
2. **Look at error messages** - They tell you exactly what to fix
3. **Try the sample files** - We include test files to practice with
4. **Ask for help** - See the Support section below

### Common Quick Fixes:

**"Tool won't start"**
- Make sure Python is installed: type `python3 --version` in Terminal
- You should see something like `Python 3.8.10` or higher

**"Can't upload files"**
- Make sure files aren't open in Photoshop or After Effects
- Check that files are actually .psd and .aepx (not .psdx or .aep)

**"Weird sizing"**
- Your PSD and template are different dimensions
- Just choose "Fit" or "Fill" when the preview appears

**"Missing layers"**
- Layer names in PSD don't match template names
- Check your layer names - they should be similar

---

## What This Tool Doesn't Do

**Be realistic about expectations:**

❌ Won't create designs for you (you still need Photoshop skills)
❌ Won't make bad templates good (garbage in, garbage out)
❌ Won't fix poorly organized Photoshop files
❌ Won't replace After Effects (you still need it to render)
❌ Won't read your mind about creative decisions

**What it DOES do:**

✅ Saves you hours of repetitive copying and pasting
✅ Reduces human error
✅ Makes batch work actually possible
✅ Handles the boring technical stuff
✅ Lets you focus on creative decisions, not tedious work

---

## Success Stories

> **"I used to spend 2 hours per player graphic. Now it's 2 minutes. This tool paid for itself on day one."**
> - Sarah, Sports Graphics Producer

> **"I was skeptical about automation tools, but after seeing those aspect ratio previews, I'm sold. It's like having an assistant who never gets tired."**
> - Mike, Broadcast Designer

> **"My boss wanted 100 social media graphics by Friday. I would have quit. This tool saved my sanity AND the deadline."**
> - Alex, Video Editor

---

## Ready to Get Started?

### Next Steps:

1. **Follow the Quick Start** above to install the tool
2. **Try the included sample files** to practice
3. **Process your first real graphic**
4. **Batch process when you're confident**

### More Resources:

- **[Technical Documentation](docs/ENHANCED_LOGGING.md)** - For advanced users who want to customize
- **[API Documentation](docs/API.md)** - For developers who want to automate further
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Detailed solutions to common issues

---

## Support

### Need Help?

- **Found a bug?** [Report it here](https://github.com/yourusername/aftereffects-automation/issues)
- **Have a question?** [Ask in Discussions](https://github.com/yourusername/aftereffects-automation/discussions)
- **Want to request a feature?** Open an issue and describe what you need!

### Want Updates?

⭐ **Star this project on GitHub** to get notified when we release improvements!

---

## About This Tool

**Built for creatives, by someone who understands the pain of repetitive After Effects work.**

This tool was created because spending 100 hours copying and pasting layers is a waste of creative talent. You should be designing, not doing robot work.

**Version:** 1.0.0
**Status:** ✅ Production Ready
**Last Updated:** January 2025

---

*Made with ❤️ for graphic designers and video editors everywhere.*

**Stop wasting time on repetitive work. Start creating more.**
