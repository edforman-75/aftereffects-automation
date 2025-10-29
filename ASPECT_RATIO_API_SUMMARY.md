# Aspect Ratio Review API - Summary

## ✅ Successfully Added

All aspect ratio review API endpoints have been added to `web_app.py` (lines 2265-2474).

## 📋 API Endpoints

### 1. Get Aspect Ratio Review Info

**Endpoint**: `GET /api/projects/<project_id>/graphics/<graphic_id>/aspect-ratio-review`

**Purpose**: Get aspect ratio review details including decision info and preview URLs

**Response**:
```json
{
  "success": true,
  "graphic_id": "graphic_123",
  "graphic_name": "Campaign Banner",
  "psd_category": "landscape",
  "aepx_category": "square",
  "psd_dimensions": [1920, 1080],
  "aepx_dimensions": [1920, 1920],
  "transformation_type": "human_review",
  "ratio_difference": 0.437,
  "confidence": 0.0,
  "reasoning": "Cross-category transformation detected (landscape → square). Content aspect differs significantly (44%). Human review recommended.",
  "recommended_action": "Review visual previews and choose transformation method",
  "needs_review": true,
  "has_previews": true,
  "previews": {
    "original_url": "/api/projects/proj_123/graphics/graphic_123/aspect-ratio-preview/original",
    "fit_url": "/api/projects/proj_123/graphics/graphic_123/aspect-ratio-preview/fit",
    "fill_url": "/api/projects/proj_123/graphics/graphic_123/aspect-ratio-preview/fill"
  }
}
```

**Error Responses**:
- `404`: Project not found, Graphic not found, No aspect ratio check data
- `500`: Server error

**Usage**:
```javascript
const response = await fetch(
  `/api/projects/${projectId}/graphics/${graphicId}/aspect-ratio-review`
);
const data = await response.json();

if (data.success && data.needs_review) {
  // Show decision UI with previews
  showAspectRatioDecisionModal(data);
}
```

---

### 2. Serve Preview Images

**Endpoint**: `GET /api/projects/<project_id>/graphics/<graphic_id>/aspect-ratio-preview/<preview_type>`

**Preview Types**:
- `original` - Original PSD for reference
- `fit` - Scale to fit (letterbox/pillarbox)
- `fill` - Scale to fill (crop edges)

**Purpose**: Serve preview images (thumbnails preferred for UI, 400px max)

**Response**: JPEG image file (image/jpeg)

**Error Responses**:
- `400`: Invalid preview type
- `404`: Project not found, Graphic not found, Preview not found
- `500`: Server error

**Smart Serving**:
- Automatically serves thumbnail if available (400px, optimized for UI)
- Falls back to full-size preview if thumbnail not found
- Checks file existence before serving

**Usage**:
```html
<!-- Display preview images -->
<div class="preview-grid">
  <div class="preview-option">
    <h4>Fit (Letterbox)</h4>
    <img src="/api/projects/proj_123/graphics/g1/aspect-ratio-preview/fit"
         alt="Fit Preview">
    <p>Maintain all content, add bars</p>
    <button onclick="chooseFit()">Use Fit</button>
  </div>

  <div class="preview-option">
    <h4>Fill (Crop)</h4>
    <img src="/api/projects/proj_123/graphics/g1/aspect-ratio-preview/fill"
         alt="Fill Preview">
    <p>Full frame, crop edges</p>
    <button onclick="chooseFill()">Use Fill</button>
  </div>
</div>
```

---

### 3. Submit Human Decision

**Endpoint**: `POST /api/projects/<project_id>/graphics/<graphic_id>/aspect-ratio-decision`

**Purpose**: Submit human decision on aspect ratio transformation

**Request Body**:
```json
{
  "decision": "proceed",  // "proceed", "skip", or "manual_fix"
  "method": "fit"         // "fit" or "fill" (only used if decision is "proceed")
}
```

**Decision Types**:
1. **`proceed`** - Apply transformation and continue processing
   - Requires `method` ('fit' or 'fill')
   - Records decision for learning
   - Calculates and stores transform
   - Updates graphic status to 'pending'

2. **`skip`** - Skip this graphic
   - Marks graphic as 'skipped'
   - Records decision for learning
   - Graphic excluded from processing

3. **`manual_fix`** - Flag for manual handling
   - Marks graphic as 'needs_manual_fix'
   - Records decision for learning
   - Requires human intervention

**Response (Success)**:
```json
{
  "success": true,
  "status": "approved",  // or "skipped", "needs_manual_fix"
  "message": "Decision 'proceed' processed successfully"
}
```

**Error Responses**:
- `400`: Invalid decision, Invalid method, Processing error
- `500`: Server error

**Usage**:
```javascript
async function submitAspectRatioDecision(graphicId, decision, method = 'fit') {
  const response = await fetch(
    `/api/projects/${projectId}/graphics/${graphicId}/aspect-ratio-decision`,
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({decision, method})
    }
  );

  const data = await response.json();

  if (data.success) {
    showMessage(data.message, 'success');
    refreshGraphicList();
  } else {
    showMessage(data.error, 'error');
  }
}

// Example calls
submitAspectRatioDecision('g1', 'proceed', 'fit');   // Apply fit transform
submitAspectRatioDecision('g2', 'proceed', 'fill');  // Apply fill transform
submitAspectRatioDecision('g3', 'skip');              // Skip graphic
submitAspectRatioDecision('g4', 'manual_fix');        // Flag for manual work
```

---

### 4. Get Learning Statistics

**Endpoint**: `GET /api/aspect-ratio/learning-stats`

**Purpose**: Get aspect ratio learning system statistics

**Response**:
```json
{
  "success": true,
  "statistics": {
    "total_decisions": 45,
    "auto_apply_accuracy": 0.95,
    "agreement_rate": 0.87,
    "by_category": {
      "landscape": {
        "count": 25,
        "accuracy": 0.92
      },
      "square": {
        "count": 12,
        "accuracy": 0.83
      },
      "portrait": {
        "count": 8,
        "accuracy": 0.88
      }
    },
    "by_transformation_type": {
      "none": {"count": 10, "agreed": 10},
      "minor_scale": {"count": 15, "agreed": 14},
      "moderate": {"count": 12, "agreed": 10},
      "human_review": {"count": 8, "agreed": 6}
    }
  }
}
```

**Metrics Explained**:
- **total_decisions**: Total number of human decisions recorded
- **auto_apply_accuracy**: % of auto-applied cases humans would have agreed with
- **agreement_rate**: Overall % AI and human decisions agreed
- **by_category**: Breakdown by aspect ratio category
- **by_transformation_type**: Breakdown by transformation type

**Error Responses**:
- `500`: Server error

**Usage**:
```javascript
async function showLearningStats() {
  const response = await fetch('/api/aspect-ratio/learning-stats');
  const data = await response.json();

  if (data.success) {
    const stats = data.statistics;

    console.log(`Total Decisions: ${stats.total_decisions}`);
    console.log(`Auto-Apply Accuracy: ${(stats.auto_apply_accuracy * 100).toFixed(1)}%`);
    console.log(`Agreement Rate: ${(stats.agreement_rate * 100).toFixed(1)}%`);

    // Display stats in UI
    displayStatsChart(stats);
  }
}
```

---

### 5. Export Learning Data

**Endpoint**: `GET /api/aspect-ratio/learning-data/export`

**Purpose**: Download all aspect ratio learning data as JSON file

**Response**: JSON file download (`aspect_ratio_learning_data.json`)

**File Contents**:
```json
{
  "decisions": [
    {
      "timestamp": "2025-01-26T10:15:00",
      "psd_dimensions": [1920, 1080],
      "aepx_dimensions": [1920, 1161],
      "psd_category": "landscape",
      "aepx_category": "landscape",
      "ratio_difference": 0.070,
      "ai_recommendation": "minor_scale",
      "human_choice": "proceed",
      "agreed": true
    },
    // ... more decisions
  ]
}
```

**Error Responses**:
- `500`: Server error

**Usage**:
```html
<!-- Direct download link -->
<a href="/api/aspect-ratio/learning-data/export" download>
  Download Learning Data (JSON)
</a>

<!-- Or via JavaScript -->
<script>
async function downloadLearningData() {
  window.location.href = '/api/aspect-ratio/learning-data/export';
  showMessage('Downloading learning data...', 'info');
}
</script>
```

---

## 🔄 Complete Workflow Example

### UI Implementation

```javascript
// ============================================================================
// Aspect Ratio Review Modal
// ============================================================================

async function checkForAspectRatioReview(graphicId) {
  const response = await fetch(
    `/api/projects/${currentProject.id}/graphics/${graphicId}/aspect-ratio-review`
  );
  const data = await response.json();

  if (data.success && data.needs_review) {
    showAspectRatioDecisionModal(data);
  }
}

function showAspectRatioDecisionModal(reviewData) {
  const modal = `
    <div class="modal" id="aspectRatioModal">
      <div class="modal-content">
        <h2>Aspect Ratio Review Required</h2>

        <!-- Decision Info -->
        <div class="review-info">
          <p><strong>Graphic:</strong> ${reviewData.graphic_name}</p>
          <p><strong>PSD:</strong> ${reviewData.psd_category} (${reviewData.psd_dimensions.join('×')})</p>
          <p><strong>AEPX:</strong> ${reviewData.aepx_category} (${reviewData.aepx_dimensions.join('×')})</p>
          <p><strong>Difference:</strong> ${(reviewData.ratio_difference * 100).toFixed(1)}%</p>
          <p><strong>Confidence:</strong> ${(reviewData.confidence * 100).toFixed(0)}%</p>
        </div>

        <div class="reasoning-box">
          <h3>Analysis</h3>
          <p>${reviewData.reasoning}</p>
          <p><em>${reviewData.recommended_action}</em></p>
        </div>

        <!-- Preview Images -->
        <div class="preview-grid">
          <div class="preview-option">
            <h4>Fit (Letterbox)</h4>
            <img src="${reviewData.previews.fit_url}" alt="Fit Preview">
            <p>✓ All content visible<br>± Black bars if needed</p>
            <button onclick="applyDecision('${reviewData.graphic_id}', 'proceed', 'fit')"
                    class="btn-primary">
              Use Fit
            </button>
          </div>

          <div class="preview-option">
            <h4>Fill (Crop)</h4>
            <img src="${reviewData.previews.fill_url}" alt="Fill Preview">
            <p>✓ Full frame<br>± Some content cropped</p>
            <button onclick="applyDecision('${reviewData.graphic_id}', 'proceed', 'fill')"
                    class="btn-primary">
              Use Fill
            </button>
          </div>
        </div>

        <!-- Other Options -->
        <div class="modal-actions">
          <button onclick="applyDecision('${reviewData.graphic_id}', 'skip')"
                  class="btn-warning">
            Skip This Graphic
          </button>
          <button onclick="applyDecision('${reviewData.graphic_id}', 'manual_fix')"
                  class="btn-danger">
            Needs Manual Fix
          </button>
          <button onclick="closeModal()" class="btn-secondary">
            Cancel
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modal);
}

async function applyDecision(graphicId, decision, method = 'fit') {
  const response = await fetch(
    `/api/projects/${currentProject.id}/graphics/${graphicId}/aspect-ratio-decision`,
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({decision, method})
    }
  );

  const data = await response.json();

  if (data.success) {
    showMessage(`Decision applied: ${decision}`, 'success');
    closeModal();
    refreshGraphics();
  } else {
    showMessage(`Error: ${data.error}`, 'error');
  }
}
```

---

## 📊 Testing the Endpoints

### Using curl

```bash
# 1. Get aspect ratio review info
curl http://localhost:5001/api/projects/proj_123/graphics/g1/aspect-ratio-review

# 2. View preview image in browser
open http://localhost:5001/api/projects/proj_123/graphics/g1/aspect-ratio-preview/fit

# 3. Submit decision (proceed with fit)
curl -X POST http://localhost:5001/api/projects/proj_123/graphics/g1/aspect-ratio-decision \
  -H "Content-Type: application/json" \
  -d '{"decision":"proceed","method":"fit"}'

# 4. Submit decision (skip)
curl -X POST http://localhost:5001/api/projects/proj_123/graphics/g2/aspect-ratio-decision \
  -H "Content-Type: application/json" \
  -d '{"decision":"skip"}'

# 5. Get learning stats
curl http://localhost:5001/api/aspect-ratio/learning-stats

# 6. Download learning data
curl -O http://localhost:5001/api/aspect-ratio/learning-data/export
```

### Using JavaScript Fetch API

```javascript
// Get review info
const reviewInfo = await fetch(`/api/projects/${pid}/graphics/${gid}/aspect-ratio-review`)
  .then(r => r.json());

// Submit decision
const result = await fetch(`/api/projects/${pid}/graphics/${gid}/aspect-ratio-decision`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({decision: 'proceed', method: 'fit'})
}).then(r => r.json());

// Get learning stats
const stats = await fetch('/api/aspect-ratio/learning-stats')
  .then(r => r.json());
```

---

## 🔒 Error Handling

All endpoints return proper HTTP status codes:

- **200 OK**: Success
- **400 Bad Request**: Invalid input (wrong decision type, method, etc.)
- **404 Not Found**: Resource not found (project, graphic, preview)
- **500 Internal Server Error**: Server-side error

### Error Response Format

```json
{
  "success": false,
  "error": "Error description"
}
```

### Common Errors

**Get Review Info**:
- "Project not found" (404)
- "Graphic not found" (404)
- "No aspect ratio check data available" (404)

**Serve Preview**:
- "Invalid preview type" (400)
- "Preview not found" (404)
- "Preview file not found" (404)

**Submit Decision**:
- "Invalid decision. Must be: proceed, skip, or manual_fix" (400)
- "Invalid method. Must be: fit or fill" (400)
- "Project not found" / "Graphic not found" (from service layer)

---

## ✨ Key Features

### 1. Smart Image Serving

The preview image endpoint automatically:
- Serves thumbnails (400px) for UI performance
- Falls back to full-size if thumbnail unavailable
- Validates file existence
- Returns proper MIME type (image/jpeg)

### 2. Comprehensive Validation

- Decision validation (proceed/skip/manual_fix)
- Method validation (fit/fill)
- Parameter presence checks
- Type checking

### 3. Learning System Integration

- Every decision automatically recorded
- Statistics updated in real-time
- Full audit trail
- Exportable for analysis

### 4. RESTful Design

- Proper HTTP methods (GET for reads, POST for writes)
- Logical URL structure
- JSON request/response
- HTTP status codes

---

## 📝 Summary

All 5 aspect ratio review API endpoints have been successfully added:

1. ✅ **GET** `/api/projects/<pid>/graphics/<gid>/aspect-ratio-review` - Get review info
2. ✅ **GET** `/api/projects/<pid>/graphics/<gid>/aspect-ratio-preview/<type>` - Serve images
3. ✅ **POST** `/api/projects/<pid>/graphics/<gid>/aspect-ratio-decision` - Submit decision
4. ✅ **GET** `/api/aspect-ratio/learning-stats` - Get statistics
5. ✅ **GET** `/api/aspect-ratio/learning-data/export` - Export learning data

**Location**: `web_app.py` lines 2265-2474

**Status**: Production ready with:
- ✅ Proper error handling (400, 404, 500)
- ✅ Input validation
- ✅ JSON responses
- ✅ Image serving with correct MIME types
- ✅ Learning system integration
- ✅ Comprehensive logging

**Next Step**: Add UI components to consume these endpoints and display aspect ratio decisions to users.
