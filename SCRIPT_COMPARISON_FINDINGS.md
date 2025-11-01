# ExtendScript Comparison: Test vs Production

## Critical Difference Found!

### Issue: `app.activeDocument` Placement

**Test Script (WORKING) - Line 73-74:**
```javascript
// Hide all layers
for (var j = 0; j < doc.layers.length; j++) {
    doc.layers[j].visible = false;
}

// Show only current layer
layer.visible = true;

// CRITICAL: Re-confirm active document AFTER visibility changes
app.activeDocument = doc;

// Get layer bounds
var bounds = layer.bounds;
```

**Production Script (BROKEN) - Line 92:**
```javascript
for (var i = 0; i < doc.layers.length; i++) {
    var layer = doc.layers[i];

        app.activeDocument = doc;  // ⚠️ WRONG PLACEMENT - Before visibility operations!

    try {
        if (layer.typename === "LayerSet") {
            // Skip groups...
        }

        // Hide all layers
        for (var j = 0; j < doc.layers.length; j++) {
            doc.layers[j].visible = false;
        }

        // Show only current layer
        layer.visible = true;

        // Get layer bounds - NO app.activeDocument call here!
        var bounds = layer.bounds;
```

## The Problem

The production script calls `app.activeDocument = doc;` at line 92, which is:
1. **Before** the layer visibility operations
2. **Outside** the inner try block
3. **Before** getting layer bounds

The test script calls it **after** the visibility operations and **before** getting bounds, which is the correct placement.

## Why This Matters

Setting the active document AFTER changing visibility ensures that Photoshop is working with the correct document state when it calculates layer bounds. The "General Photoshop error" is likely caused by the bounds calculation happening with the wrong document context.

## Additional Weird Indentation

Line 92 in production has strange indentation (extra spaces), suggesting it was added in the wrong location during a previous fix attempt.

## The Fix

Move line 92 from its current position to AFTER the visibility operations (line 111) and BEFORE the bounds calculation (line 113):

```javascript
try {
    // Skip groups
    if (layer.typename === "LayerSet") {
        results.push({
            layer: layer.name,
            skipped: true,
            reason: "Layer group"
        });
        continue;
    }

    // Hide all layers
    for (var j = 0; j < doc.layers.length; j++) {
        doc.layers[j].visible = false;
    }

    // Show only current layer
    layer.visible = true;

    // MOVE IT HERE - After visibility, before bounds
    app.activeDocument = doc;

    // Get layer bounds
    var bounds = layer.bounds;
    var layerWidth = bounds[2].value - bounds[0].value;
    var layerHeight = bounds[3].value - bounds[1].value;

    // ... rest of logic
```

## Other Differences (Not Critical)

1. **Variable names**: Test uses `safeName`, production uses `safeLayerName` - OK, just naming
2. **Results array**: Production builds a results array for JSON output - OK, this is additional functionality
3. **Logging**: Test uses `$.writeln()`, production uses `results.push()` - OK, different output methods

## Summary

There's ONE critical fix needed:
- **Move** `app.activeDocument = doc;` from line 92 to after line 111 (after visibility operations, before bounds)

This should make the production code work exactly like the test script.
