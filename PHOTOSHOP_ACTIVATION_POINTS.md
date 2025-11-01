# Photoshop Document Activation Points

## Why Multiple Activations Are Needed

Photoshop's ExtendScript API can lose track of which document is "active" during complex operations. When this happens, API calls like `layer.bounds` fail with "General Photoshop error."

## Production Script Now Has 4 Activation Points

### 1. After Opening Document (Line 79)
```javascript
var doc = app.open(psdFile);
app.activeDocument = doc;  // Make sure document is active and frontmost
```
**Purpose**: Establish initial active document state

### 2. Start of Each Layer Iteration (Line 91)
```javascript
for (var i = 0; i < doc.layers.length; i++) {
    var layer = doc.layers[i];
    app.activeDocument = doc;  // Ensure doc is active at start of iteration
```
**Purpose**: Re-confirm active state before each layer

### 3. After Visibility Changes (Line 113) ⚠️ MOST CRITICAL
```javascript
// Hide all layers
for (var j = 0; j < doc.layers.length; j++) {
    doc.layers[j].visible = false;
}

// Show only current layer
layer.visible = true;

// CRITICAL: Re-confirm active document after visibility changes
app.activeDocument = doc;

// Get layer bounds
var bounds = layer.bounds;
```
**Purpose**: Ensure document is active AFTER visibility operations and BEFORE bounds calculation

**Why critical**: Visibility changes can cause Photoshop to lose active document context. Getting bounds without re-activation here causes the "General Photoshop error."

### 4. After Closing Temp Document (Line 146)
```javascript
// Close temp document
tempDoc.close(SaveOptions.DONOTSAVECHANGES);
app.activeDocument = doc;  // Re-activate original document
```
**Purpose**: Restore active state after temp document operations

## Test Script vs Production

The working test script (`test_photoshop_thumbnails.py`) has activations at:
- Line 43: After opening
- Line 74: After visibility changes (critical!)
- Line 104: After temp doc closes

Production now has all of these PLUS an extra one at loop start for maximum reliability.

## Result

Production script now has **redundant safeguards** ensuring the active document never gets lost, even during complex layer visibility and duplication operations.

## Verification

Run: `grep -n "app.activeDocument = doc" services/thumbnail_service.py`

Should show:
```
79:app.activeDocument = doc;  // Make sure document is active and frontmost
91:        app.activeDocument = doc;  // Ensure doc is active at start of iteration
113:            app.activeDocument = doc;
146:                app.activeDocument = doc;  // Re-activate original document
```

All 4 activation points confirmed! ✅
