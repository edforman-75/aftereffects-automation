# Module 5: Video Preview Generation

Generate low-resolution video previews of populated After Effects templates using aerender.

## Overview

This module provides functionality to generate quick video previews of After Effects templates populated with content from PSD files. It uses Adobe After Effects' command-line rendering tool (`aerender`) to create draft-quality previews.

## Features

- **Fast Preview Rendering**: Generate low-res previews in 10-30 seconds
- **Configurable Quality**: Choose resolution (half/third/quarter), duration, and FPS
- **Multiple Formats**: Support for MP4, MOV, and GIF outputs
- **Thumbnail Generation**: Automatically extract thumbnail images from videos
- **Graceful Degradation**: Handles missing aerender with clear error messages

## Components

### 1. preview_generator.py

Main module with the following functions:

#### `check_aerender_available() -> Optional[str]`
Checks if Adobe After Effects' aerender tool is installed.

**Returns:**
- Path to aerender if found
- None if not available

**Search locations:**
- macOS: `/Applications/Adobe After Effects 2025/aerender`
- Windows: `C:\Program Files\Adobe\Adobe After Effects 2025\Support Files\aerender.exe`
- PATH environment variable

#### `generate_preview(aepx_path, mappings, output_path, options=None) -> Dict[str, Any]`
Generate a video preview of a populated template.

**Parameters:**
- `aepx_path`: Path to After Effects template file
- `mappings`: Content mappings from Module 3
- `output_path`: Where to save the preview video
- `options`: Optional rendering settings

**Options:**
```python
{
    'resolution': 'half',    # half, third, quarter of original
    'duration': 5.0,         # seconds to render (or 'full')
    'format': 'mp4',         # mp4, mov, gif
    'quality': 'draft',      # draft, medium, high
    'fps': 15                # frames per second
}
```

**Returns:**
```python
{
    'success': True/False,
    'video_path': '/path/to/preview.mp4',
    'thumbnail_path': '/path/to/preview.jpg',
    'duration': 5.0,
    'resolution': '960x540',
    'format': 'mp4',
    'error': 'error message if failed'
}
```

#### `prepare_temp_project(aepx_path, mappings, temp_dir) -> str`
Prepares a temporary project file with content mappings applied.

**Returns:** Path to prepared project file

#### `render_with_aerender(project_path, comp_name, output_path, options, aerender_path) -> bool`
Executes aerender command to render the composition.

**Returns:** True if successful, False otherwise

#### `generate_thumbnail(video_path, timestamp=0.5) -> Optional[str]`
Extracts a thumbnail frame from the video using ffmpeg.

**Returns:** Path to thumbnail JPEG, or None if ffmpeg unavailable

#### `get_video_info(video_path) -> Dict[str, Any]`
Gets metadata about the rendered video using ffprobe.

**Returns:**
```python
{
    'duration': 5.0,
    'resolution': '960x540',
    'fps': 30.0
}
```

## Usage Example

```python
from modules.phase5.preview_generator import generate_preview, check_aerender_available

# Check if aerender is available
if not check_aerender_available():
    print("After Effects not installed!")
    exit(1)

# Define mappings
mappings = {
    'composition_name': 'Main Comp',
    'mappings': [
        {
            'psd_layer': 'Title',
            'aepx_placeholder': 'title_text',
            'type': 'text'
        }
    ]
}

# Generate preview
result = generate_preview(
    aepx_path='templates/template.aepx',
    mappings=mappings,
    output_path='previews/preview.mp4',
    options={
        'resolution': 'half',
        'duration': 5.0,
        'format': 'mp4'
    }
)

if result['success']:
    print(f"Preview saved to: {result['video_path']}")
    print(f"Thumbnail: {result['thumbnail_path']}")
else:
    print(f"Error: {result['error']}")
```

## Web API Integration

### POST /generate-preview

Generate a video preview for the current session.

**Request:**
```json
{
    "session_id": "abc123",
    "options": {
        "resolution": "half",
        "duration": 5.0,
        "format": "mp4"
    }
}
```

**Response:**
```json
{
    "success": true,
    "message": "Preview generated successfully",
    "data": {
        "preview_url": "/previews/preview_123.mp4",
        "thumbnail_url": "/previews/preview_123.jpg",
        "duration": 5.0,
        "resolution": "960x540"
    }
}
```

### GET /previews/<filename>

Serve preview videos and thumbnails with appropriate content-type headers.

## User Workflow

1. **Upload Files**: User uploads PSD and AEPX files
2. **Check Fonts**: Optional font verification
3. **Review Mappings**: Check content-to-placeholder mappings
4. **Review Conflicts**: Address any detected issues
5. **Generate Preview**: Create low-res video preview
6. **Review Preview**: Watch the preview in browser
7. **Generate Script**: If satisfied, generate full ExtendScript

## Requirements

### Required:
- Adobe After Effects 2025 or 2024 (for aerender)
- Python 3.7+

### Optional:
- ffmpeg (for thumbnail generation)
- ffprobe (for video metadata)

Install ffmpeg on macOS:
```bash
brew install ffmpeg
```

## Technical Details

### aerender Command Format

```bash
/Applications/Adobe\ After\ Effects\ 2025/aerender \
    -project /path/to/project.aep \
    -comp "test-aep" \
    -output /path/to/output.mp4 \
    -RStemplate "Best Settings" \
    -s 0 \
    -e 75
```

**Parameters:**
- `-project`: Path to AE project file
- `-comp`: Composition name to render (from parsed AEPX)
- `-output`: Output video path (extension determines format)
- `-RStemplate`: Render settings template
- `-s`: Start frame
- `-e`: End frame

**Note:** We do NOT use `-OMtemplate` parameter because:
- Template names like "H.264" vary between After Effects versions
- After Effects automatically selects the appropriate encoder based on output file extension
- `.mp4` → Default MP4 encoder
- `.mov` → Default QuickTime encoder
- `.avi` → Default AVI encoder
- This approach is more reliable and compatible across all AE versions

### Resolution Mapping

- `full`: 1x (original resolution)
- `half`: 0.5x (960×540 for 1920×1080)
- `third`: 0.33x (640×360 for 1920×1080)
- `quarter`: 0.25x (480×270 for 1920×1080)

### Render Time Estimates

- **5 second preview at half resolution**: 10-20 seconds
- **10 second preview at full resolution**: 30-60 seconds
- **Complexity**: Text-heavy templates render faster than complex animations

## Error Handling

### aerender Not Found
```python
{
    'success': False,
    'error': 'aerender not found. After Effects must be installed.'
}
```

**User Action**: Install After Effects or skip preview generation

### Render Failed
```python
{
    'success': False,
    'error': 'Rendering failed'
}
```

**Possible Causes**:
- Invalid composition name
- Missing fonts in After Effects
- Corrupted template file
- Insufficient disk space

### Timeout
aerender has a 5-minute timeout. If rendering takes longer, the process is killed.

**User Action**: Reduce duration or resolution

## Testing

Run the test suite:
```bash
python tests/test_preview_generator.py
```

**Tests:**
1. Check aerender availability
2. Prepare temporary project
3. Handle missing aerender gracefully
4. Mock aerender rendering
5. Mock thumbnail generation
6. Mock video info extraction

All tests use mocking to avoid requiring actual After Effects installation.

## Performance Optimization

1. **Use Low Resolution**: `half` or `quarter` for fastest results
2. **Short Duration**: 3-5 seconds is usually sufficient
3. **Low FPS**: 15 FPS is adequate for preview
4. **Draft Quality**: Use draft settings for speed

## Security Notes

- Previews are auto-deleted after 1 hour
- Temporary project files are cleaned up immediately
- Video files are served with appropriate MIME types
- No user input is passed directly to shell commands

## Future Enhancements

- [ ] Progress tracking during render
- [ ] Cancel rendering in progress
- [ ] Multiple composition previews
- [ ] Side-by-side PSD vs rendered comparison
- [ ] Automatic quality adjustment based on template complexity
- [ ] Cloud rendering support (AWS/GCP)
