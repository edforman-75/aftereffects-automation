# After Effects Automation - Web UI

A modern web interface for the After Effects automation pipeline.

## Features

- **Drag-and-Drop Upload**: Easy file upload for PSD and AEPX/AEP files
- **Intelligent Matching**: Automatic content-to-placeholder mapping
- **Conflict Detection**: Real-time warnings about dimension mismatches, font issues, etc.
- **Script Generation**: One-click ExtendScript (.jsx) generation
- **Modern UI**: Beautiful purple/pink gradient theme with responsive design

## Prerequisites

Install the required Python packages:

```bash
pip install flask flask-cors
```

Or if using the virtual environment:

```bash
source venv/bin/activate
pip install flask flask-cors
```

## Quick Start

### 1. Start the Server

From the project root directory:

```bash
python web_app.py
```

You should see:

```
======================================================================
After Effects Automation - Web Interface
======================================================================

🌐 Starting server at http://localhost:5000

📝 Instructions:
   1. Open http://localhost:5000 in your browser
   2. Upload your PSD and AEPX files
   3. Review mappings and conflicts
   4. Generate and download ExtendScript

⚠️  Press Ctrl+C to stop the server
======================================================================
```

### 2. Open in Browser

Navigate to: **http://localhost:5000**

### 3. Use the Interface

#### Step 1: Upload Files

1. **PSD File**: Drag and drop or click to select your Photoshop document
2. **AEPX/AEP File**: Drag and drop or click to select your After Effects template
3. Click **"Upload & Analyze"**

The system will:
- Parse both files
- Extract layers and placeholders
- Check fonts for compatibility

#### Step 2: Review Mappings

After upload, you'll see:
- **File Information**: Details about your PSD and template
- **Font Check**: List of fonts used and any uncommon fonts
- Click **"Match Content"** to proceed

The matcher will:
- Automatically map PSD layers to template placeholders
- Calculate confidence scores for each mapping
- Identify unmapped content and unfilled placeholders

#### Step 3: Check Conflicts

Review the conflicts section for:
- **Critical Issues**: Problems that may prevent the script from working
- **Warnings**: Issues that may affect quality (dimension mismatches, etc.)
- **Info Messages**: Helpful information about the automation

Conflict types include:
- Dimension mismatches
- Aspect ratio differences
- Resolution warnings (upscaling/downscaling)
- Font availability issues

#### Step 4: Generate Script

1. Click **"Generate ExtendScript"**
2. Wait for generation to complete
3. Click **"Download Script"** to save the .jsx file

#### Step 5: Use in After Effects

1. Open After Effects
2. Open your template file manually
3. Go to: **File → Scripts → Run Script File**
4. Select the downloaded .jsx file
5. The script will update your composition!

## File Structure

```
aftereffects-automation/
├── web_app.py              # Flask backend
├── templates/
│   └── index.html          # Web UI frontend
├── static/
│   └── style.css           # Stylesheet
├── uploads/                # Uploaded files (auto-created)
└── output/                 # Generated scripts (auto-created)
```

## API Endpoints

### POST /upload

Upload PSD and AEPX files.

**Request:**
- Form data with `psd_file` and `aepx_file`

**Response:**
```json
{
  "success": true,
  "message": "Files uploaded successfully",
  "data": {
    "session_id": "1234567890_abcd1234",
    "psd": {
      "filename": "design.psd",
      "width": 1200,
      "height": 1500,
      "layers": 6
    },
    "aepx": {
      "filename": "template.aepx",
      "composition": "Main Comp",
      "placeholders": 4
    },
    "fonts": {
      "total": 3,
      "uncommon": 1,
      "uncommon_list": ["Custom Font"]
    }
  }
}
```

### POST /match

Match content to placeholders.

**Request:**
```json
{
  "session_id": "1234567890_abcd1234"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Content matched successfully",
  "data": {
    "mappings": [...],
    "unmapped_psd": [...],
    "unfilled_placeholders": [...],
    "conflicts": {...}
  }
}
```

### POST /generate

Generate ExtendScript file.

**Request:**
```json
{
  "session_id": "1234567890_abcd1234",
  "mappings": [...]  // Optional: custom mappings
}
```

**Response:**
```json
{
  "success": true,
  "message": "Script generated successfully",
  "data": {
    "filename": "script.jsx",
    "download_url": "/download/script.jsx"
  }
}
```

### GET /download/<filename>

Download generated script file.

## Configuration

Edit `web_app.py` to customize:

```python
# File size limits
MAX_PSD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_AEPX_SIZE = 10 * 1024 * 1024  # 10MB

# Cleanup age
CLEANUP_AGE = timedelta(hours=1)  # Delete files after 1 hour

# Server settings
app.run(debug=True, host='0.0.0.0', port=5000)
```

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, change the port in `web_app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use port 5001
```

Then access at: http://localhost:5001

### Module Not Found Errors

Make sure you're in the project root directory and the virtual environment is activated:

```bash
cd /path/to/aftereffects-automation
source venv/bin/activate
python web_app.py
```

### Files Not Uploading

Check the console for error messages. Common issues:
- File too large (increase MAX_PSD_SIZE or MAX_AEPX_SIZE)
- Invalid file format (must be .psd, .aepx, or .aep)
- Permissions issue (ensure write access to uploads/ and output/ folders)

### CORS Errors

CORS is enabled by default for development. For production, configure CORS properly:

```python
CORS(app, origins=['https://yourdomain.com'])
```

### Session Not Found

Sessions are stored in memory and will be lost if the server restarts. For production, use:
- Redis for session storage
- Database for persistent sessions
- File-based session storage

## Production Deployment

For production use:

1. **Disable Debug Mode**:
   ```python
   app.run(debug=False, host='0.0.0.0', port=5000)
   ```

2. **Use Production Server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
   ```

3. **Add Session Storage**:
   - Use Redis or database instead of in-memory sessions
   - Implement proper session cleanup

4. **Configure HTTPS**:
   - Use nginx or Apache as reverse proxy
   - Enable SSL certificates

5. **File Storage**:
   - Consider using cloud storage (S3, etc.) for uploaded files
   - Implement proper file cleanup and retention policies

## Security Notes

- The current implementation stores sessions in memory (not suitable for production)
- File uploads are limited to 50MB for PSD and 10MB for AEPX
- Files are automatically cleaned up after 1 hour
- No authentication is implemented (add for production use)
- CORS is enabled for all origins (restrict in production)

## Support

For issues or questions:
1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure you're using Python 3.7+
4. Review the main project README.md for general setup

## License

Same as the main After Effects Automation project.
