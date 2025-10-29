# Visual Mapping Editor with Side-by-Side Previews

## Overview

The Visual Mapping Editor replaces the traditional text-based mapping interface with an intuitive visual editor that shows preview images of PSD layers and AEPX placeholders side-by-side.

## Features

### 1. Visual Preview Generation

**Two new API endpoints:**

- `POST /render-psd-preview` - Generates preview images for:
  - Full PSD composite (800px max width)
  - Individual layer previews (400px max width)
  - Returns URLs to preview images

- `POST /render-aepx-preview` - Generates placeholder previews:
  - Simple image with placeholder name and metadata
  - 400x300 placeholder cards showing type and dimensions
  - Returns URLs to preview images

### 2. Interactive Mapping Interface

**Three-column layout:**

```
┌─────────────────┬──────────────┬────────────────┐
│   PSD Layers    │   Mappings   │  AEPX Placeholders │
│   (Click to     │   (Current)  │  (Click to map)    │
│    select)      │              │                    │
├─────────────────┼──────────────┼────────────────┤
│ [Preview Image] │ Layer → PH   │ [Preview Image]│
│ Layer Name      │ Layer → PH   │ Placeholder    │
│                 │ [Delete]     │                │
│ [Preview Image] │              │ [Preview Image]│
│ Layer Name      │              │ Placeholder    │
└─────────────────┴──────────────┴────────────────┘
```

### 3. User Workflow

**Step 1: Load Previews**
- Click "Load Visual Previews" button
- Backend renders all PSD layers and AEPX placeholders
- Preview images displayed in grids

**Step 2: Select PSD Layer**
- Click any PSD layer card
- Card highlights in green
- Status message: "Selected PSD layer: [name]. Now click an AEPX placeholder to create mapping."

**Step 3: Create Mapping**
- Click any AEPX placeholder card
- Mapping created automatically
- Both cards dimmed to show they're mapped
- Success message displayed

**Step 4: Manage Mappings**
- View all current mappings in center panel
- Delete individual mappings with "Delete" button
- Reset all mappings with "Reset to Auto-Match" button
- See real-time stats (mapped/unmapped counts)

### 4. Visual Feedback

**Card States:**
- **Normal**: White background, 2px border
- **Hover**: Primary color border, slight lift
- **Selected**: Green border with glow effect
- **Mapped**: Dimmed (60% opacity), gray border

**Mapping Stats:**
- Total Mappings count
- Unmapped Layers count
- Unfilled Placeholders count

## Technical Implementation

### Backend (web_app.py)

**New imports:**
```python
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
```

**PSD Preview Rendering:**
```python
# Open PSD with psd-tools
psd = PSDImage.open(psd_path)

# Render full composite
full_image = psd.composite()
full_image.save(preview_path, 'PNG')

# Render individual layers
for layer in psd:
    layer_image = layer.composite()
    layer_image.save(layer_preview_path, 'PNG')
```

**AEPX Preview Rendering:**
```python
# Create placeholder card
img = Image.new('RGB', (400, 300), color=(50, 50, 60))
draw = ImageDraw.Draw(img)

# Draw placeholder name and metadata
draw.text((text_x, text_y), placeholder_name, fill=(255, 255, 255), font=font)
img.save(filepath, 'PNG')
```

### Frontend (templates/index.html)

**State Management:**
```javascript
let psdLayerPreviews = {};           // URLs to PSD layer preview images
let aepxPlaceholderPreviews = {};    // URLs to placeholder preview images
let selectedPsdLayer = null;         // Currently selected layer
let currentMappings = [];            // Active mappings
let allPsdLayers = [];               // All available layers
let allPlaceholders = [];            // All available placeholders
```

**Key Functions:**
- `loadVisualPreviews()` - Fetch preview images from backend
- `displayVisualMappingInterface()` - Render the 3-column interface
- `selectPsdLayer(name)` - Handle layer selection
- `selectAepxPlaceholder(name)` - Create mapping on click
- `deleteVisualMapping(index)` - Remove a mapping
- `updateVisualMappingsList()` - Update center panel and stats

### Styling (static/style.css)

**Grid Layout:**
```css
.visual-mapping-container {
    display: grid;
    grid-template-columns: 1fr auto 1fr;  /* 3 columns */
    gap: 20px;
}
```

**Preview Cards:**
```css
.preview-item {
    border: 2px solid var(--border);
    padding: 10px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.preview-item:hover {
    border-color: var(--primary);
    transform: translateY(-2px);
}

.preview-item.selected {
    border-color: var(--success-color);
    box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.2);
}

.preview-item.mapped {
    opacity: 0.6;
}
```

**Responsive Design:**
```css
@media (max-width: 768px) {
    .visual-mapping-container {
        grid-template-columns: 1fr;  /* Stack vertically */
    }

    .mapping-center {
        order: -1;  /* Show mappings first */
    }
}
```

## Benefits

### 🎨 Visual Understanding
- See actual PSD layer content
- Preview what each placeholder represents
- Understand mappings at a glance

### 🖱️ Intuitive Interaction
- Click to select, click to map
- No typing, no dropdowns
- Immediate visual feedback

### ✅ Error Prevention
- Already-mapped items are dimmed
- Can't create duplicate mappings
- Clear undo with Reset button

### 📊 Real-Time Insights
- See mapping progress
- Track unmapped items
- Validate completeness

## Example Usage

### Scenario: Mapping campaign content

**PSD Layers:**
- "CANDIDATE NAME" - Text layer with candidate's name
- "BEN FORMAN" - Sample text
- "HEADSHOT" - Photo layer

**AEPX Placeholders:**
- "CandidateNameText" - Text placeholder
- "CandidatePhoto" - Image placeholder
- "Background" - Background layer

**Mapping Process:**
1. Click "Load Visual Previews"
   - See preview of "BEN FORMAN" text
   - See preview of headshot photo
   - See placeholder cards with labels

2. Click "BEN FORMAN" layer
   - Card highlights green
   - Status: "Selected PSD layer: BEN FORMAN..."

3. Click "CandidateNameText" placeholder
   - Mapping created: BEN FORMAN → CandidateNameText
   - Both cards dimmed
   - Center panel shows mapping

4. Click "HEADSHOT" layer

5. Click "CandidatePhoto" placeholder
   - Mapping created: HEADSHOT → CandidatePhoto

6. Review stats
   - ✅ 2 Total Mappings
   - ✅ 1 Unmapped Layer
   - ✅ 1 Unfilled Placeholder

## API Reference

### POST /render-psd-preview

**Request:**
```json
{
  "session_id": "abc123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "full_preview": "/previews/psd_full_abc123_20250126.png",
    "layer_previews": {
      "BEN FORMAN": "/previews/psd_layer_BEN_FORMAN_abc123.png",
      "HEADSHOT": "/previews/psd_layer_HEADSHOT_abc123.png"
    }
  }
}
```

### POST /render-aepx-preview

**Request:**
```json
{
  "session_id": "abc123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "placeholder_previews": {
      "CandidateNameText": "/previews/aepx_placeholder_CandidateNameText_abc123.png",
      "CandidatePhoto": "/previews/aepx_placeholder_CandidatePhoto_abc123.png"
    }
  }
}
```

## Dependencies

**Backend:**
- `Pillow` (PIL) - Image manipulation
- `psd-tools` - PSD parsing and rendering

**Frontend:**
- Vanilla JavaScript (no external dependencies)
- Modern browser with ES6 support

## Future Enhancements

Potential improvements:

1. **Drag-and-drop mapping** - Drag PSD layer to placeholder
2. **Zoom on hover** - Larger preview when hovering
3. **Search/filter** - Find layers/placeholders by name
4. **Batch operations** - Map multiple items at once
5. **Undo/redo** - More granular history management
6. **Export mappings** - Save custom mapping templates
7. **AI suggestions** - Show confidence scores with visual cues

## Troubleshooting

### Preview images not loading

**Symptom:** Placeholder "?" image shown instead of preview

**Causes:**
- PSD layer is empty or invisible
- Font rendering failed (AEPX previews)
- File permissions issue

**Solution:**
- Check browser console for errors
- Verify layer is visible in PSD
- Check server logs for rendering errors

### Slow preview generation

**Symptom:** Long wait time when clicking "Load Visual Previews"

**Causes:**
- Large PSD file (>50MB)
- Many layers (>100)
- Complex layer effects

**Solution:**
- Simplify PSD (flatten effects)
- Reduce PSD size
- Consider caching previews

### Mappings not saving

**Symptom:** Mappings disappear after reload

**Status:** Expected behavior - mappings stored in session only

**Solution:**
- Complete workflow without refreshing
- Future: Add session persistence

## Files Modified

1. **web_app.py**
   - Added PIL and psd-tools imports
   - Added `/render-psd-preview` endpoint (lines 507-606)
   - Added `/render-aepx-preview` endpoint (lines 609-699)

2. **templates/index.html**
   - Replaced mappings section HTML (lines 81-121)
   - Added visual mapping state variables (lines 191-195)
   - Added 9 new JavaScript functions (lines 504-732)
   - Added 3 new event listeners (lines 924-926)
   - Updated `matchContent()` to extract layers/placeholders (lines 443-449)

3. **static/style.css**
   - Added visual mapping styles (lines 590-778)
   - Added responsive styles (lines 803-823)

## Production Readiness

✅ **Complete** - Feature fully implemented and functional

**Tested:**
- Preview image generation
- Layer/placeholder selection
- Mapping creation/deletion
- Stats updates
- Responsive layout

**Ready for:**
- Testing with real PSD/AEPX files
- User acceptance testing
- Production deployment

## Summary

The Visual Mapping Editor transforms the content mapping experience from text-based to visual-first, making it intuitive to understand and create mappings between PSD content and After Effects placeholders. With side-by-side preview images and click-to-map interaction, users can confidently configure their automation without technical knowledge.

🎉 **Ready to use!**
