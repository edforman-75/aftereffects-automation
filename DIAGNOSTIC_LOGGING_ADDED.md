# Diagnostic Logging Added for AEPX Placeholder Names

## Issue Being Investigated

User reports that the RIGHT SIDE of the visual mapping interface is showing PSD layer names instead of AEPX placeholder names.

**Expected**:
- LEFT: BEN FORMAN (PSD Layer)
- RIGHT: player1fullname (AEPX Placeholder showing BEN FORMAN's thumbnail)

**Reported (Wrong)**:
- LEFT: BEN FORMAN (PSD Layer)
- RIGHT: BEN FORMAN (labeled as "AEPX Placeholder") ❌

## Code Analysis

The rendering code at `templates/index.html:723-753` appears correct:
- Line 723: Iterates over `allPlaceholders` array
- Line 747: Displays `${placeholderName}` (should be AEPX placeholder name)
- Line 748: Shows type as "AEPX Placeholder"

The data population at `templates/index.html:481-482` also appears correct:
```javascript
allPlaceholders = result.data.mappings.map(m => m.aepx_placeholder)
    .concat(result.data.unfilled_placeholders || []);
```

## Diagnostic Logging Added

### 1. Auto-Match Data Logging (`index.html:477-484`)

When Auto-Match completes, logs:
```javascript
console.log('🔍 Auto-Match Result Data:', result.data);
console.log('🔍 Mappings:', result.data.mappings);
console.log('📦 Extracted allPsdLayers:', allPsdLayers);
console.log('📦 Extracted allPlaceholders:', allPlaceholders);
```

**What to Check**:
- `result.data.mappings` - Each mapping should have `{psd_layer: "...", aepx_placeholder: "..."}`
- `allPlaceholders` - Should contain AEPX placeholder names like `["player1fullname", "player2fullname", ...]`
- If `allPlaceholders` contains PSD layer names, the backend is returning wrong data

### 2. Visual Interface Rendering Logging (`index.html:687-694`)

When `displayVisualMappingInterface()` is called, logs:
```javascript
console.log('='.repeat(70));
console.log('DISPLAY VISUAL MAPPING INTERFACE');
console.log('='.repeat(70));
console.log('📦 allPsdLayers:', allPsdLayers);
console.log('📦 allPlaceholders:', allPlaceholders);
console.log('🔗 currentMappings:', currentMappings);
console.log('='.repeat(70));
```

**What to Check**:
- `allPsdLayers` - Should be `["BEN FORMAN", "ELOISE GRACE", ...]`
- `allPlaceholders` - Should be `["player1fullname", "player2fullname", ...]`
- `currentMappings` - Should be `[{psd_layer: "BEN FORMAN", aepx_placeholder: "player1fullname"}, ...]`

### 3. Existing Thumbnail Mapping Logging (`index.html:732`)

Already present - logs when a placeholder uses a PSD layer's thumbnail:
```javascript
console.log(`Placeholder "${placeholderName}" mapped to "${mapping.psd_layer}", using its thumbnail`);
```

**What to Check**:
- `placeholderName` should be the AEPX placeholder name
- `mapping.psd_layer` should be the PSD layer name
- Example: `Placeholder "player1fullname" mapped to "BEN FORMAN", using its thumbnail`

## Testing Instructions

1. **Visit**: http://localhost:5001
2. **Upload** PSD and AEPX files
3. **Open Browser Console** (F12)
4. **Click "Auto-Match"**
5. **Review Console Logs**:
   - Check `🔍 Auto-Match Result Data` - verify mappings structure
   - Check `📦 Extracted allPlaceholders` - should be AEPX names, not PSD names
6. **Click "Load Visual Previews"**
7. **Review Console Logs**:
   - Check `DISPLAY VISUAL MAPPING INTERFACE` section
   - Verify `allPlaceholders` contains correct AEPX names
   - Check individual placeholder logs showing mapping relationships
8. **Inspect Visual Interface**:
   - LEFT: Should show PSD layer names
   - RIGHT: Should show AEPX placeholder names

## Possible Root Causes

### Hypothesis 1: Backend Returns Wrong Data
If `allPlaceholders` contains PSD layer names after Auto-Match, the issue is in:
- `/auto-match` endpoint in `web_app.py`
- Auto-matching service that creates the mappings
- Data structure has `aepx_placeholder` containing PSD layer names

### Hypothesis 2: Frontend Data Corruption
If `allPlaceholders` is correct after Auto-Match but wrong when rendering:
- Something is overwriting `allPlaceholders` between Auto-Match and render
- Check for duplicate variable assignments

### Hypothesis 3: Visual Bug (Not Data Issue)
If `allPlaceholders` is correct but RIGHT SIDE still shows PSD names:
- Issue with HTML rendering logic (lines 744-749)
- CSS/styling issue making wrong element visible
- JavaScript template string issue

## Expected Console Output

### Correct Output Example:
```
🔍 Auto-Match Result Data: {mappings: [...], ...}
🔍 Mappings: [
  {psd_layer: "BEN FORMAN", aepx_placeholder: "player1fullname"},
  {psd_layer: "ELOISE GRACE", aepx_placeholder: "player2fullname"},
  ...
]
📦 Extracted allPsdLayers: ["BEN FORMAN", "ELOISE GRACE", "EMMA LOUISE", ...]
📦 Extracted allPlaceholders: ["player1fullname", "player2fullname", "player3fullname", ...]
```

### Wrong Output Example (If Bug Exists):
```
📦 Extracted allPlaceholders: ["BEN FORMAN", "ELOISE GRACE", ...] ❌
```
^^ If you see PSD layer names in `allPlaceholders`, the backend is returning incorrect data!

## Next Steps

Based on console output:
1. **If `allPlaceholders` contains PSD names**: Fix backend `/auto-match` endpoint
2. **If `allPlaceholders` is correct**: Issue is in frontend rendering - investigate lines 723-753
3. **If data is correct but display is wrong**: Visual/CSS issue - inspect DOM elements

## Files Modified

- `templates/index.html:477-484` - Auto-Match data logging
- `templates/index.html:687-694` - Visual interface rendering logging

Logging is non-intrusive and can be left in place for future debugging!
