# Large File Handling

## Overview

This document describes the implementation of large file handling in the After Effects Automation system. The system now properly handles large content (ExtendScript files, Stage 1 results, Stage 2 matches) to avoid token limits in API responses.

## Problem

Previously, the system would return entire file contents or large data structures in JSON API responses. This caused issues when:
- ExtendScript (.jsx) files exceeded 44,000+ tokens
- Stage 1 PSD/AEPX parsing results were very large
- Stage 2 match data contained many matches

These large responses would fail with: "File content exceeds maximum allowed tokens"

## Solution

The system now implements three strategies for handling large content:

### 1. Summary Responses
Instead of returning full content, endpoints return summaries with links to fetch the full data:

```json
{
  "has_data": true,
  "data_size": 156000,
  "endpoint": "/api/job/123/extendscript",
  "supports_chunking": true
}
```

### 2. Chunked/Paginated Reading
Large content can be fetched in chunks using offset and limit parameters:

```bash
# Get first 10,000 characters
GET /api/job/123/extendscript?offset=0&limit=10000

# Get next chunk
GET /api/job/123/extendscript?offset=10000&limit=10000
```

Response includes metadata for pagination:
```json
{
  "success": true,
  "content": "... chunk of content ...",
  "metadata": {
    "offset": 0,
    "limit": 10000,
    "chunk_length": 10000,
    "total_length": 156000,
    "has_more": true,
    "next_offset": 10000
  }
}
```

### 3. File Downloads
Full content can be downloaded as files:

```bash
GET /api/job/123/extendscript/download
```

This returns the complete file as a download attachment.

## New API Endpoints

### ExtendScript Endpoints

#### GET /api/job/{job_id}/extendscript
Get ExtendScript content with optional chunking.

**Query Parameters:**
- `offset` (int): Starting position, default 0
- `limit` (int): Chunk size, default 10,000, max 50,000
- `full` (bool): Return full content (use with caution)

**Example:**
```bash
curl "http://localhost:5000/api/job/abc123/extendscript?offset=0&limit=10000"
```

#### GET /api/job/{job_id}/extendscript/download
Download the complete ExtendScript file.

**Example:**
```bash
curl -O "http://localhost:5000/api/job/abc123/extendscript/download"
# Downloads: abc123_script.jsx
```

### Stage 1 Results Endpoint

#### GET /api/job/{job_id}/stage1-results
Get Stage 1 parsing results with optional chunking.

**Query Parameters:**
- `offset` (int): Starting position, default 0
- `limit` (int): Chunk size, default 25,000, max 50,000
- `full` (bool): Return full results (use with caution)

**Example:**
```bash
curl "http://localhost:5000/api/job/abc123/stage1-results?limit=20000"
```

### Stage 2 Matches Endpoint

#### GET /api/job/{job_id}/stage2-matches
Get Stage 2 approved matches with optional chunking.

**Query Parameters:**
- `offset` (int): Starting position, default 0
- `limit` (int): Chunk size, default 25,000, max 50,000
- `full` (bool): Return full matches (use with caution)

**Example:**
```bash
curl "http://localhost:5000/api/job/abc123/stage2-matches?full=true"
```

## Changed Endpoints

### GET /api/job/{job_id}/preview-data
**Changed:** No longer includes `full_script` field in ExtendScript data.

**Before:**
```json
{
  "extendscript": {
    "full_script": "... entire 150KB script ...",
    "script_preview": "... first 1000 chars ..."
  }
}
```

**After:**
```json
{
  "extendscript": {
    "download_url": "/api/job/abc123/extendscript/download",
    "script_preview": "... first 1000 chars ...",
    "script_length": 156000
  }
}
```

### GET /api/job/{job_id}
**Changed:** Returns summaries for stage1_results and stage2_approved_matches.

**Before:**
```json
{
  "stage1_results": { /* large object */ },
  "stage2_approved_matches": { /* large object */ }
}
```

**After:**
```json
{
  "stage1_summary": {
    "has_results": true,
    "data_size": 45000,
    "endpoint": "/api/job/abc123/stage1-results"
  },
  "stage2_summary": {
    "has_matches": true,
    "data_size": 32000,
    "endpoint": "/api/job/abc123/stage2-matches"
  }
}
```

## Utility Class: LargeContentHandler

A new utility class provides reusable methods for handling large content:

```python
from utils import LargeContentHandler

# Create chunked response
response, status = LargeContentHandler.create_chunked_response(
    content=large_string,
    job_id='123',
    content_type='script'
)

# Create download response
return LargeContentHandler.create_download_response(
    content=script_content,
    filename='script.jsx'
)

# Create summary
summary = LargeContentHandler.create_summary_response(
    data=large_data,
    job_id='123',
    data_type='results',
    endpoint_path='/api/job/{job_id}/results'
)

# Check if content should be chunked
should_chunk = LargeContentHandler.should_chunk_content(content)

# Get content statistics
stats = LargeContentHandler.get_content_stats(data)
# Returns: {'size': 45000, 'type': 'dict', 'should_chunk': True}
```

## Configuration

Default chunk sizes can be adjusted in `utils/large_content_handler.py`:

```python
DEFAULT_CHUNK_SIZE = 25000  # Characters per chunk
MAX_CHUNK_SIZE = 50000      # Maximum allowed chunk size
```

## Frontend Integration

When integrating with the frontend:

1. **Check content size** before requesting full content
2. **Use chunking** for large files (> 25,000 characters)
3. **Use download endpoint** for files users need to save
4. **Display progress** when fetching multiple chunks

Example JavaScript:
```javascript
async function fetchLargeContent(jobId) {
  let offset = 0;
  let content = '';
  let hasMore = true;

  while (hasMore) {
    const response = await fetch(
      `/api/job/${jobId}/extendscript?offset=${offset}&limit=10000`
    );
    const data = await response.json();

    content += data.content;
    hasMore = data.metadata.has_more;
    offset = data.metadata.next_offset;

    // Update progress UI
    const progress = (offset / data.metadata.total_length) * 100;
    updateProgress(progress);
  }

  return content;
}
```

## Best Practices

1. **Always use summaries** in list/overview endpoints
2. **Provide download links** for files users need to save
3. **Implement chunking** for content > 25,000 characters
4. **Document chunk sizes** in API documentation
5. **Add progress indicators** in UI when fetching large content
6. **Cache chunked content** on client side to avoid re-fetching
7. **Use the LargeContentHandler utility** for consistent implementation

## Migration Guide

If you have existing code that fetches large content:

### Before:
```python
# Old way - returns full content
return jsonify({
    'full_script': job.stage5_extendscript
})
```

### After:
```python
# New way - return summary with link
from utils import LargeContentHandler

summary = LargeContentHandler.create_summary_response(
    data=job.stage5_extendscript,
    job_id=job.job_id,
    data_type='extendscript',
    endpoint_path='/api/job/{job_id}/extendscript'
)

return jsonify({
    'extendscript_summary': summary
})
```

Or for downloading:
```python
# Provide download endpoint
return LargeContentHandler.create_download_response(
    content=job.stage5_extendscript,
    filename=f'{job.job_id}_script.jsx'
)
```

## Testing

Test with large files:

```bash
# Create a test job with large ExtendScript
python -m pytest tests/test_large_content_handler.py

# Test chunked reading
curl "http://localhost:5000/api/job/test-job/extendscript?offset=0&limit=1000"

# Test download
curl -O "http://localhost:5000/api/job/test-job/extendscript/download"
```

## Performance Considerations

- **Database queries**: Large JSON fields are fetched in full from database. Consider storing very large content as files if needed.
- **Memory usage**: Chunking reduces memory usage on client but full content is still loaded in server memory.
- **Network**: Chunking can increase total network overhead due to multiple requests. Use appropriate chunk sizes.
- **Caching**: Consider implementing server-side caching for frequently accessed large content.

## Future Improvements

Potential enhancements:
- Stream large content directly from database to client
- Store very large files on disk instead of in database
- Implement compression for large JSON responses
- Add ETag/If-None-Match for caching
- Implement WebSocket streaming for real-time large content delivery
