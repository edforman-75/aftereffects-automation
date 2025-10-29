# API Documentation

This document describes the HTTP API endpoints for the After Effects Automation tool.

## Base URL

When running locally:
```
http://localhost:5001
```

## API Endpoints

### Projects

#### Create New Project
```
POST /api/projects
Content-Type: application/json

{
  "name": "My Project",
  "description": "Optional project description"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "proj_123",
    "name": "My Project",
    "created_at": "2025-01-28T10:30:00Z"
  }
}
```

#### Get Project Details
```
GET /api/projects/{project_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "proj_123",
    "name": "My Project",
    "graphics": [],
    "created_at": "2025-01-28T10:30:00Z"
  }
}
```

#### List All Projects
```
GET /api/projects
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "project_id": "proj_123",
      "name": "My Project",
      "graphics_count": 5,
      "created_at": "2025-01-28T10:30:00Z"
    }
  ]
}
```

---

### Graphics

#### Add Graphic to Project
```
POST /api/projects/{project_id}/graphics
Content-Type: application/json

{
  "name": "Player 01 - John Smith",
  "psd_path": "/path/to/design.psd",
  "template_path": "/path/to/template.aepx"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "graphic_id": "g1",
    "name": "Player 01 - John Smith",
    "status": "pending"
  }
}
```

#### Process Graphic
```
POST /api/graphics/{graphic_id}/process
Content-Type: application/json

{
  "aspect_ratio_mode": "fit"  // Optional: "fit", "fill", or "original"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "graphic_id": "g1",
    "status": "processing",
    "message": "Processing started"
  }
}
```

#### Get Graphic Status
```
GET /api/graphics/{graphic_id}/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "graphic_id": "g1",
    "status": "completed",
    "progress": 100,
    "current_step": "export_complete"
  }
}
```

#### Download Graphic Result
```
GET /api/graphics/{graphic_id}/download
```

**Response:**
- Content-Type: `application/zip`
- ZIP file containing:
  - `{name}.aepx` - After Effects project file
  - `Hard_Card.json` - Data file for expressions
  - Preview images

---

### File Upload

#### Upload PSD File
```
POST /api/upload/psd
Content-Type: multipart/form-data

psd_file: [binary file data]
```

**Response:**
```json
{
  "success": true,
  "data": {
    "file_id": "psd_abc123",
    "filename": "design.psd",
    "size_bytes": 1234567,
    "dimensions": {
      "width": 1080,
      "height": 1920
    }
  }
}
```

#### Upload Template File
```
POST /api/upload/template
Content-Type: multipart/form-data

template_file: [binary file data]
```

**Response:**
```json
{
  "success": true,
  "data": {
    "file_id": "aepx_def456",
    "filename": "template.aepx",
    "size_bytes": 234567
  }
}
```

---

### Performance Monitoring

#### Get Performance Summary
```
GET /api/performance-summary
```

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "psd_parse": {
        "count": 45,
        "avg_ms": 1234.5,
        "min_ms": 890.2,
        "max_ms": 2134.7,
        "p50_ms": 1200.1,
        "p95_ms": 1895.3,
        "p99_ms": 2050.7,
        "total_ms": 55552.5
      }
    },
    "total_operations": 2,
    "note": "Performance data collected since server start"
  }
}
```

**Requirements:**
- Enhanced logging must be enabled (`USE_ENHANCED_LOGGING=true`)
- Returns 400 error if enhanced logging is not enabled

---

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong",
  "error_code": "ERROR_CODE",  // Optional
  "details": {}  // Optional additional context
}
```

### Common Error Codes

- `400 Bad Request` - Invalid input data
- `404 Not Found` - Resource not found (project, graphic, etc.)
- `500 Internal Server Error` - Server-side processing error

---

## Rate Limiting

Currently no rate limiting is enforced. This is a local application running on your machine.

---

## Authentication

Currently no authentication is required. This is a local application.

**Security Note:** Do not expose this application to the internet without adding proper authentication and security measures.

---

## Python Client Example

Here's a simple Python client example:

```python
import requests
import json

BASE_URL = "http://localhost:5001"

# Create a project
response = requests.post(f"{BASE_URL}/api/projects", json={
    "name": "Sports Graphics Project"
})
project = response.json()["data"]
project_id = project["project_id"]

# Add a graphic
response = requests.post(f"{BASE_URL}/api/projects/{project_id}/graphics", json={
    "name": "Player 01",
    "psd_path": "/path/to/player01.psd",
    "template_path": "/path/to/template.aepx"
})
graphic = response.json()["data"]
graphic_id = graphic["graphic_id"]

# Process the graphic
response = requests.post(f"{BASE_URL}/api/graphics/{graphic_id}/process", json={
    "aspect_ratio_mode": "fit"
})

# Check status
import time
while True:
    response = requests.get(f"{BASE_URL}/api/graphics/{graphic_id}/status")
    status_data = response.json()["data"]

    if status_data["status"] == "completed":
        break
    elif status_data["status"] == "failed":
        print("Processing failed!")
        break

    time.sleep(2)  # Check every 2 seconds

# Download result
response = requests.get(f"{BASE_URL}/api/graphics/{graphic_id}/download")
with open(f"{graphic['name']}.zip", "wb") as f:
    f.write(response.content)

print("Done!")
```

---

## JavaScript/Node.js Client Example

```javascript
const axios = require('axios');
const fs = require('fs');

const BASE_URL = 'http://localhost:5001';

async function processGraphic() {
  // Create project
  const projectRes = await axios.post(`${BASE_URL}/api/projects`, {
    name: 'Sports Graphics Project'
  });
  const projectId = projectRes.data.data.project_id;

  // Add graphic
  const graphicRes = await axios.post(
    `${BASE_URL}/api/projects/${projectId}/graphics`,
    {
      name: 'Player 01',
      psd_path: '/path/to/player01.psd',
      template_path: '/path/to/template.aepx'
    }
  );
  const graphicId = graphicRes.data.data.graphic_id;

  // Process
  await axios.post(`${BASE_URL}/api/graphics/${graphicId}/process`, {
    aspect_ratio_mode: 'fit'
  });

  // Wait for completion
  let status;
  do {
    const statusRes = await axios.get(
      `${BASE_URL}/api/graphics/${graphicId}/status`
    );
    status = statusRes.data.data.status;

    if (status === 'failed') {
      throw new Error('Processing failed');
    }

    await new Promise(resolve => setTimeout(resolve, 2000));
  } while (status !== 'completed');

  // Download
  const downloadRes = await axios.get(
    `${BASE_URL}/api/graphics/${graphicId}/download`,
    { responseType: 'arraybuffer' }
  );

  fs.writeFileSync('Player_01.zip', downloadRes.data);
  console.log('Done!');
}

processGraphic().catch(console.error);
```

---

## Batch Processing

For processing multiple graphics, you can make parallel requests:

```python
import requests
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:5001"

def process_graphic(psd_path, template_path, name):
    # Create project (or reuse existing)
    response = requests.post(f"{BASE_URL}/api/projects", json={
        "name": "Batch Project"
    })
    project_id = response.json()["data"]["project_id"]

    # Add graphic
    response = requests.post(
        f"{BASE_URL}/api/projects/{project_id}/graphics",
        json={
            "name": name,
            "psd_path": psd_path,
            "template_path": template_path
        }
    )
    graphic_id = response.json()["data"]["graphic_id"]

    # Process
    requests.post(f"{BASE_URL}/api/graphics/{graphic_id}/process")

    return graphic_id

# Process 10 graphics in parallel
graphics_data = [
    ("/path/to/player01.psd", "/path/to/template.aepx", "Player 01"),
    ("/path/to/player02.psd", "/path/to/template.aepx", "Player 02"),
    # ... more graphics
]

with ThreadPoolExecutor(max_workers=5) as executor:
    graphic_ids = list(executor.map(
        lambda g: process_graphic(g[0], g[1], g[2]),
        graphics_data
    ))

print(f"Processing {len(graphic_ids)} graphics...")
```

---

## WebSocket Support (Future)

WebSocket support for real-time progress updates is planned for a future release.

---

## API Versioning

Currently the API is unversioned. Future versions may use URL-based versioning:
- `/api/v1/...`
- `/api/v2/...`

---

## Need Help?

- See the [main README](../README.md) for general usage
- See [ENHANCED_LOGGING.md](ENHANCED_LOGGING.md) for monitoring and debugging
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

---

**Last Updated:** January 2025
**API Version:** 1.0 (unversioned)
