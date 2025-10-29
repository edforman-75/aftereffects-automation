# Screenshots Guide

This directory contains screenshots referenced in the main README.md.

## Required Screenshots

The following screenshots are referenced in the README and need to be captured:

### 1. dashboard.png
**Location in README**: "Your First Project" → Step 1
**What to show**: The main dashboard/home screen when users first open the tool at `http://localhost:5001`
**Key elements to capture**:
- "New Project" button prominently visible
- Clean, simple interface
- Any project list (if projects exist) or empty state

**Recommended size**: 1200px wide (retina quality)

---

### 2. upload.png
**Location in README**: "Your First Project" → Step 2
**What to show**: The file upload screen
**Key elements to capture**:
- "Upload PSD" button or drag-and-drop area
- "Choose Template" button or file selector
- Any visual indicators (checkmarks mentioned in text)
- Clean interface showing both upload zones

**Recommended size**: 1200px wide (retina quality)

---

### 3. aspect-ratio-modal.png
**Location in README**: "Your First Project" → Step 4
**What to show**: The aspect ratio adjustment modal/dialog
**Key elements to capture**:
- Three preview options side-by-side (Fit, Fill, Original)
- Visual difference between the three options clearly visible
- "Proceed with [choice]" button
- Any labels explaining each option

**Recommended size**: 1200px wide (retina quality)
**Note**: This is a critical screenshot - users need to see the visual difference between the three sizing options

---

### 4. processing.png
**Location in README**: "Your First Project" → Step 5
**What to show**: The processing/progress screen
**Key elements to capture**:
- Progress bar actively showing progress
- Status messages (e.g., "Matching layers...", "Creating expressions...")
- Any percentage indicators
- Professional, reassuring interface

**Recommended size**: 1200px wide (retina quality)

---

### 5. download-ready.png
**Location in README**: "Your First Project" → Step 6
**What to show**: The completion screen with download ready
**Key elements to capture**:
- Green "Download" button prominently visible
- Success indicator (checkmark, "Complete" message, etc.)
- List of files that will be downloaded
- Clean, celebratory completion state

**Recommended size**: 1200px wide (retina quality)

---

## How to Capture Screenshots

### Preparation
1. Start the application: `python3 web_app.py`
2. Open browser to `http://localhost:5001`
3. Have a sample PSD file and template ready
4. Use browser DevTools to set consistent viewport size (1200px width)

### Capture Process
1. Use browser screenshot tools (Cmd+Shift+4 on Mac, or browser DevTools screenshot)
2. Capture at 2x resolution for retina displays if possible
3. Save as PNG format
4. Name exactly as shown above (dashboard.png, upload.png, etc.)

### Post-Processing
1. Crop to show relevant UI (remove browser chrome)
2. Ensure text is readable
3. Add subtle border if screenshot blends with white background
4. Optimize PNG file size (use ImageOptim or similar)
5. Verify final width is ~1200px (or 2400px for retina)

---

## Screenshot Quality Guidelines

✅ **DO:**
- Use clean, professional example data (e.g., "Player 01 - John Smith" not "test 123")
- Show successful states (green checkmarks, completed processes)
- Ensure good contrast and readability
- Capture at consistent window sizes
- Show realistic use cases (sports graphics, social media, etc.)

❌ **DON'T:**
- Include personal information or real client data
- Show error states or broken UI
- Use lorem ipsum or obviously fake placeholder text
- Capture at inconsistent sizes or aspect ratios
- Include browser UI elements (address bar, bookmarks, etc.)

---

## Testing Screenshots

After adding screenshots, verify:
1. All images load correctly in README.md preview
2. Images are clear and text is readable at display size
3. File sizes are reasonable (<500KB per image)
4. Images work on both light and dark GitHub themes

---

## Placeholder Images (Optional)

If you need placeholders while waiting for real screenshots, you can create simple placeholder images using:

```bash
# Create 1200x800 placeholder with text (requires ImageMagick)
convert -size 1200x800 xc:lightgray -pointsize 48 -fill black -gravity center -annotate +0+0 "Dashboard Screenshot\nComing Soon" dashboard.png
```

Or use online tools like:
- https://placeholder.com
- https://via.placeholder.com

But **replace with real screenshots as soon as possible** - they're critical for the README's effectiveness with non-technical users.
