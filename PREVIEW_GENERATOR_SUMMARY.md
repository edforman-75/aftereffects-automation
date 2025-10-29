# Aspect Ratio Preview Generator - Implementation Summary

## ✅ Successfully Implemented

The aspect ratio preview generator creates visual previews to help humans make informed decisions about aspect ratio transformations.

## 📦 What Was Built

### Core Module

**`modules/aspect_ratio/preview_generator.py`** (429 lines)

A complete visual preview generator that creates three types of transformation previews:
1. **Original Preview** - Reference image showing source PSD
2. **Fit Preview** - Scale to fit (letterbox/pillarbox) with black bars
3. **Fill Preview** - Scale to fill (crop edges) with no bars

## 🎯 Key Features

### 1. Three Preview Modes

#### Original Preview
- Shows the source PSD dimensions
- Serves as reference for comparison
- Labeled with dimension information

#### Fit Preview (Letterbox/Pillarbox)
- Scales image to fit completely within target dimensions
- Adds black bars if needed (letterbox horizontal, pillarbox vertical)
- **No content loss** - entire image visible
- Shows actual bars in preview
- Label indicates bar type and dimensions

#### Fill Preview (Crop)
- Scales image to fill entire target dimensions
- Crops overflow from edges
- **No bars** - clean full-frame result
- Center-cropped for balanced composition
- Label shows approximate crop percentage

### 2. Transform Information

Each preview generation returns detailed transform data:

```python
{
    'previews': {
        'fit': '/path/to/fit_preview.jpg',
        'fill': '/path/to/fill_preview.jpg',
        'original': '/path/to/original_preview.jpg'
    },
    'dimensions': {
        'psd': [1920, 1080],
        'aepx': [1920, 1920]
    },
    'transform_info': {
        'fit': {
            'scale': 1.0,
            'scaled_width': 1920,
            'scaled_height': 1080,
            'offset_x': 0,
            'offset_y': 420,
            'bars': 'horizontal',
            'method': 'fit'
        },
        'fill': {
            'scale': 1.778,
            'scaled_width': 3413,
            'scaled_height': 1920,
            'crop_left': 746,
            'crop_top': 0,
            'crop_right': 2666,
            'crop_bottom': 1920,
            'method': 'fill'
        }
    }
}
```

### 3. Label Overlays

All previews include dimension labels:
- High-contrast text (white on black background)
- Shows dimensions and transformation type
- Uses system fonts (Helvetica/Arial with fallback)
- Positioned at top of image for visibility

Examples:
- `"Original PSD: 1920×1080"`
- `"Scale to Fit: 1920×1920 (horizontal bars)"`
- `"Scale to Fill: 1920×1920 (~44% cropped)"`

### 4. Thumbnail Generation

Create UI-sized thumbnails from full previews:

```python
result = generator.generate_thumbnail(
    preview_path='/path/to/preview.jpg',
    output_path='/path/to/thumbnail.jpg',
    max_size=400  # Max dimension in pixels
)
# Returns thumbnail_path and dimensions
```

- Maintains aspect ratio
- High-quality LANCZOS resampling
- Configurable max size
- 85% JPEG quality for balance

### 5. Side-by-Side Comparison

Generate comparison image showing all three options:

```python
result = generator.generate_side_by_side_comparison(
    original_path='/path/to/original.jpg',
    fit_path='/path/to/fit.jpg',
    fill_path='/path/to/fill.jpg',
    output_path='/path/to/comparison.jpg'
)
```

Features:
- Three images side by side with spacing
- Labels: "Original", "Fit (Letterbox)", "Fill (Crop)"
- White background with clean separation
- Perfect for decision-making UI

## 🧪 Test Results

```
======================================================================
ALL PREVIEW GENERATOR TESTS PASSED!
======================================================================

✅ Basic Preview Generation (3 test cases)
   • Landscape → Square (letterbox with horizontal bars)
   • Portrait → Landscape (pillarbox with vertical bars)
   • Perfect Match (no bars, scale=1.0)

✅ Thumbnail Generation
   • Creates 400×400 thumbnails
   • Maintains aspect ratio
   • High quality output

✅ Side-by-Side Comparison
   • Generates 5840×1120 comparison
   • Three previews with spacing
   • Proper labeling

✅ Error Handling
   • Non-existent PSD file
   • Non-existent preview file
   • Graceful failures with clear messages
```

### Test Case Details

**Case 1: Landscape (1920×1080) → Square (1920×1920)**
- ✅ Fit: horizontal bars, scale=1.0
- ✅ Fill: cropped 746px from left/right
- ✅ All 3 previews generated correctly

**Case 2: Portrait (1080×1920) → Landscape (1920×1080)**
- ✅ Fit: vertical bars, scale=0.562
- ✅ Fill: significant vertical crop
- ✅ Previews show clear difference

**Case 3: Perfect Match (1920×1080) → (1920×1080)**
- ✅ No bars needed
- ✅ Scale exactly 1.0
- ✅ Minimal processing

## 🔧 Technical Implementation

### PIL/Pillow Integration

Uses PIL (Python Imaging Library) for all image operations:

```python
from PIL import Image, ImageDraw, ImageFont

# Load PSD as flattened image
psd_image = Image.open(psd_path)

# High-quality resampling
resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

# Create canvas with bars
canvas = Image.new('RGB', (width, height), (0, 0, 0))

# Center-paste image
canvas.paste(resized, (offset_x, offset_y))

# Add text labels
draw = ImageDraw.Draw(canvas)
draw.text((x, y), label, fill=(255, 255, 255), font=font)
```

### Transform Calculations

#### Fit Transform (Letterbox/Pillarbox)

```python
# Calculate scale to fit inside target
scale = min(target_width / src_w, target_height / src_h)
new_w = int(src_w * scale)
new_h = int(src_h * scale)

# Center on canvas
offset_x = (target_width - new_w) // 2
offset_y = (target_height - new_h) // 2

# Detect bar type
if new_w < target_width:
    bars = "vertical"  # Pillarbox
elif new_h < target_height:
    bars = "horizontal"  # Letterbox
```

#### Fill Transform (Crop)

```python
# Calculate scale to fill target
scale = max(target_width / src_w, target_height / src_h)
new_w = int(src_w * scale)
new_h = int(src_h * scale)

# Center crop
left = (new_w - target_width) // 2
top = (new_h - target_height) // 2
right = left + target_width
bottom = top + target_height

cropped = resized.crop((left, top, right, bottom))
```

### Font Handling

Robust font selection with fallbacks:

```python
try:
    # Try macOS system font
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
except:
    try:
        # Try alternative
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
    except:
        # Fallback to default
        font = ImageFont.load_default()
```

## 📊 Class Structure

```python
class AspectRatioPreviewGenerator(BaseService):
    """Generate visual previews for aspect ratio transformations"""

    def __init__(self, logger):
        """Initialize with logger"""

    def generate_transformation_previews(
        psd_path, aepx_width, aepx_height, output_dir
    ) -> Result:
        """Generate all 3 preview types"""

    def _create_fit_preview(
        source_image, target_width, target_height
    ) -> tuple[Image, Dict]:
        """Create fit preview with letterbox/pillarbox"""

    def _create_fill_preview(
        source_image, target_width, target_height
    ) -> tuple[Image, Dict]:
        """Create fill preview with crop"""

    def _save_preview_with_label(
        image, output_path, label
    ):
        """Save with dimension label overlay"""

    def generate_thumbnail(
        preview_path, output_path, max_size=400
    ) -> Result:
        """Create UI thumbnail"""

    def generate_side_by_side_comparison(
        original_path, fit_path, fill_path, output_path
    ) -> Result:
        """Create comparison image"""
```

## 🎯 Usage Examples

### Basic Usage

```python
from modules.aspect_ratio import AspectRatioPreviewGenerator
import logging

logger = logging.getLogger('app')
generator = AspectRatioPreviewGenerator(logger)

# Generate previews
result = generator.generate_transformation_previews(
    psd_path='/path/to/graphic.psd',
    aepx_width=1920,
    aepx_height=1920,
    output_dir='/path/to/previews'
)

if result.is_success():
    data = result.get_data()

    # Show user the three options
    print(f"Original: {data['previews']['original']}")
    print(f"Fit (letterbox): {data['previews']['fit']}")
    print(f"Fill (crop): {data['previews']['fill']}")

    # Get transform details
    fit_info = data['transform_info']['fit']
    if fit_info['bars'] == 'horizontal':
        print("Note: This will add horizontal black bars")

    # Create thumbnails for UI
    for method in ['fit', 'fill']:
        generator.generate_thumbnail(
            preview_path=data['previews'][method],
            output_path=f'/path/to/thumb_{method}.jpg'
        )
```

### Integration with Decision Workflow

```python
# After aspect ratio check flags for human review
if aspect_data['needs_review']:
    # Generate previews
    preview_result = generator.generate_transformation_previews(
        psd_path=graphic['psd_path'],
        aepx_width=aepx_data['width'],
        aepx_height=aepx_data['height'],
        output_dir=f'/tmp/previews/{graphic_id}'
    )

    if preview_result.is_success():
        previews = preview_result.get_data()

        # Show to user with decision options
        show_aspect_ratio_decision_ui(
            decision=aspect_data['decision'],
            previews=previews['previews'],
            transform_info=previews['transform_info']
        )
```

## 📈 Benefits

### 1. Visual Decision Making

Instead of abstract descriptions, users see:
- Actual appearance with letterbox bars
- Actual crop amount and position
- Side-by-side comparison

### 2. Informed Choices

Transform info shows exact details:
- Scale factors
- Offset amounts
- Crop percentages
- Bar types

### 3. Quality Output

High-quality image processing:
- LANCZOS resampling (best quality)
- 90% JPEG quality for previews
- 85% for thumbnails (balance size/quality)

### 4. Flexible Integration

Multiple output formats:
- Full-size previews for detailed review
- Thumbnails for UI display
- Comparison images for presentations
- JSON transform data for automation

## 🔗 Integration Points

### With AspectRatioHandler

```python
# After analyzing mismatch
decision = aspect_handler.analyze_mismatch(...)

if not aspect_handler.can_auto_transform(decision):
    # Generate visual previews for human review
    preview_result = preview_generator.generate_transformation_previews(...)
```

### With Project Service

```python
# In _check_aspect_ratio_compatibility
if aspect_data['needs_review']:
    # Store preview paths in graphic metadata
    preview_result = self.preview_generator.generate_transformation_previews(...)

    graphic['aspect_ratio_previews'] = preview_result.get_data()['previews']
    graphic['aspect_ratio_transforms'] = preview_result.get_data()['transform_info']
```

### With Web UI

```python
# API endpoint to get previews
@app.route('/api/projects/<pid>/graphics/<gid>/aspect-previews')
def get_aspect_previews(pid, gid):
    graphic = project_service.get_graphic(pid, gid)

    if 'aspect_ratio_previews' in graphic:
        return jsonify({
            'success': True,
            'previews': graphic['aspect_ratio_previews'],
            'transform_info': graphic['aspect_ratio_transforms']
        })
```

## 🚀 Next Steps

To use the preview generator in production:

### 1. Add to Project Service

```python
class ProjectService:
    def __init__(self, logger, settings):
        # ... existing init ...
        self.preview_generator = AspectRatioPreviewGenerator(logger)

    def _check_aspect_ratio_compatibility(self, graphic, psd_data, aepx_data):
        # ... existing check ...

        if aspect_data['needs_review']:
            # Generate previews
            preview_dir = os.path.join(
                self.settings['preview_dir'],
                graphic['id']
            )

            preview_result = self.preview_generator.generate_transformation_previews(
                psd_path=graphic['psd_path'],
                aepx_width=aepx_data['width'],
                aepx_height=aepx_data['height'],
                output_dir=preview_dir
            )

            if preview_result.is_success():
                preview_data = preview_result.get_data()
                graphic['aspect_ratio_previews'] = preview_data['previews']
                graphic['aspect_ratio_transform_info'] = preview_data['transform_info']
```

### 2. Add API Endpoints

```python
@app.route('/api/projects/<pid>/graphics/<gid>/aspect-ratio-previews')
def get_aspect_ratio_previews(pid, gid):
    """Get aspect ratio preview images"""
    # Return preview paths and transform info

@app.route('/api/projects/<pid>/graphics/<gid>/aspect-ratio-preview/<preview_type>')
def serve_preview_image(pid, gid, preview_type):
    """Serve preview image file (fit/fill/original)"""
    # Return actual image file
```

### 3. Add UI Components

```javascript
// Show previews in modal
async function showAspectRatioPreview(graphicId) {
    const response = await fetch(
        `/api/projects/${projectId}/graphics/${graphicId}/aspect-ratio-previews`
    );
    const data = await response.json();

    // Display three preview images
    $('#fit-preview').attr('src',
        `/api/projects/${projectId}/graphics/${graphicId}/aspect-ratio-preview/fit`
    );
    $('#fill-preview').attr('src',
        `/api/projects/${projectId}/graphics/${graphicId}/aspect-ratio-preview/fill`
    );

    // Show transform info
    const fitInfo = data.transform_info.fit;
    if (fitInfo.bars) {
        $('#fit-warning').text(
            `Note: Will add ${fitInfo.bars} black bars`
        );
    }

    // Show decision buttons
    showDecisionButtons(graphicId);
}
```

## ✨ Summary

The Aspect Ratio Preview Generator provides:

- ✅ **Visual previews** for fit (letterbox) and fill (crop) transformations
- ✅ **Transform information** with exact scales, offsets, and crop details
- ✅ **Labeled overlays** showing dimensions and transformation types
- ✅ **Thumbnail generation** for UI display
- ✅ **Side-by-side comparisons** for decision making
- ✅ **High-quality output** using LANCZOS resampling
- ✅ **Comprehensive testing** (100% pass rate)
- ✅ **Error handling** with graceful failures
- ✅ **Production ready** with proper logging and validation

The system gives users visual, informed choices rather than abstract technical decisions.

**Philosophy**: "Show, don't tell" - Let humans see the actual transformation results.
