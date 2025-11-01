# Plainly AEP Requirements - Research Summary

## Date: October 30, 2025
## Sources: Plainly Videos Help Center & Documentation

---

## CRITICAL REQUIREMENTS (Must Fix - Will Cause Render Failures)

### 1. ❌ NO Non-English Characters
**Severity:** CRITICAL
**Requirement:** "Make sure that you don't add any non-English characters to layer/file names. This will cause failed renders."

**What to Check:**
- Layer names
- Composition names
- File names (assets)
- Folder names

**Invalid Examples:**
- `José_Player` ❌
- `背景层` ❌
- `Tëxt_Läyër` ❌
- `Café_Logo` ❌

**Valid Examples:**
- `Jose_Player` ✅
- `Background_Layer` ✅
- `Text_Layer` ✅
- `Cafe_Logo` ✅

**Validation Pattern:**
```regex
^[A-Za-z0-9_\-\s]+$
```

### 2. ❌ NO .mp3 Audio Files
**Severity:** CRITICAL
**Requirement:** "Use `.wav` files; avoid `.mp3` due to After Effects compatibility issues."

**What to Check:**
- All audio layer sources
- Imported audio files

**Invalid:** `background_music.mp3` ❌
**Valid:** `background_music.wav` ✅

---

## HIGH PRIORITY REQUIREMENTS (Strongly Recommended)

### 3. Layer Naming Conventions
**Severity:** WARNING
**Requirement:** "Put a prefix in front of the layer name when naming layers that are planned to be dynamic."

**Purpose:** Enables "Auto generate templates" feature

**Recommended Prefixes:**
- `txt_` - Text layers
- `img_` - Image layers
- `vid_` - Video layers
- `color_` - Color control layers
- `audio_` - Audio layers

**Examples:**
- `txt_player_name` ✅
- `img_team_logo` ✅
- `vid_background` ✅

### 4. Composition Naming for Renders
**Severity:** WARNING
**Requirement:** "Prefix rendering compositions with `render_` (example: `render_final`)."

**Purpose:** Identifies which composition Plainly uses for output

**Examples:**
- `render_final` ✅
- `render_main` ✅
- `render_output` ✅

### 5. Dynamic Elements in Containers
**Severity:** WARNING
**Requirement:** "Dynamic media must exist within dedicated composition containers."

**What This Means:**
- Images/videos should be in individual comp containers
- No effects/keyframes applied directly to assets
- Containers should reflect maximum display size

**Structure:**
```
Main Comp
├── render_final (output comp)
│   ├── txt_player1_name (text layer) ✅
│   ├── img_logo_container (pre-comp)
│   │   └── logo.png (in pre-comp) ✅
│   ├── vid_background_container (pre-comp)
│   │   └── background.mp4 (in pre-comp) ✅
```

**Invalid (don't do this):**
```
Main Comp
├── render_final
│   ├── logo.png (direct import with effects) ❌
│   ├── background.mp4 (direct import) ❌
```

### 6. Effects Minimization
**Severity:** WARNING
**Requirement:** "Effects destroy render times. If speed is important, try lowering the amount of effects/plugins to a minimum."

**What to Check:**
- Count of effects per layer
- Complexity of effect chains
- Use of third-party plugins

**Best Practice:**
- Pre-render heavy effects as .mp4
- Use native AE effects when possible
- Minimize effect stacking

### 7. Asset File Formats
**Severity:** WARNING
**Requirement:** "Convert Illustrator/Photoshop files to .png and .jpg formats."

**Supported Formats:**
- **Images:** `.png`, `.jpg`/`.jpeg` ✅
- **Video:** `.mp4`, `.mov` ✅
- **Audio:** `.wav` ✅

**Unsupported/Not Recommended:**
- `.ai` (Illustrator) - convert to .png
- `.psd` (Photoshop) - convert to .png/.jpg
- `.mp3` (Audio) - convert to .wav ❌

---

## PERFORMANCE BEST PRACTICES (Recommended)

### 8. Pre-Rendering
**Severity:** INFO
**Recommendation:** "Pre-render layers with effects or heavy processing as .mp4 files."

**When to Pre-Render:**
- Layers with multiple effects
- Particle systems
- Complex animations
- 3D elements

**How:**
- Render as .mp4
- For transparency: use green screen + key out

### 9. Asset Optimization
**Severity:** INFO
**Recommendations:**
- "Crop assets to composition dimensions rather than using oversized source files"
- "Avoid off-screen objects"
- Match output resolution to platform requirements
- "4K unnecessary for social media"

### 10. Expression Complexity
**Severity:** INFO
**Issue:** "Complex expressions reduce render speeds since After Effects recalculates them every frame."

**Best Practice:**
- Use simple expressions when possible
- Pre-calculate values when they don't change
- Avoid nested expression references

---

## TEXT LAYER SPECIFIC REQUIREMENTS

### Text Scaling Methods
**Two approaches based on text type:**

**1. Paragraph Text:**
- Use anchor point expression with `sourceRectAtTime()`
```javascript
top = sourceRectAtTime().top;
left = sourceRectAtTime().left;
x = left + sourceRectAtTime().width / 2;
y = top + sourceRectAtTime().height / 2;
[x, y];
```

**2. Point Text:**
- Create "boundingbox" solid layer
- Apply scale expressions

---

## VERSION COMPATIBILITY

**Supported Versions:**
- Plainly supports the latest 3 versions of After Effects
- Auto-upgrade process for unsupported versions
- Detection is automatic

**Current (2025):**
- After Effects 2025 ✅
- After Effects 2024 ✅
- After Effects 2023 ✅

---

## SUPPORTED DYNAMIC ELEMENTS

Plainly natively supports:
- ✅ Text (paragraph and point)
- ✅ Images
- ✅ Videos
- ✅ Audio
- ✅ Colors (solid layers, color control effects)
- ✅ Control effects

---

## VALIDATION CHECKLIST

Use this checklist to validate AEP files before Plainly deployment:

### Critical (Must Pass):
- [ ] No non-English characters in any layer/file/comp names
- [ ] All audio files are .wav format (no .mp3)
- [ ] All layer names use English characters only
- [ ] All composition names use English characters only
- [ ] All asset file names use English characters only

### High Priority (Strongly Recommended):
- [ ] Dynamic layers have proper prefixes (`txt_`, `img_`, etc.)
- [ ] Render compositions prefixed with `render_`
- [ ] Dynamic images/videos in composition containers
- [ ] No effects applied directly to dynamic media
- [ ] Minimal use of effects (pre-rendered when possible)
- [ ] Illustrator/Photoshop files converted to .png/.jpg

### Performance (Best Practices):
- [ ] Heavy effects pre-rendered as .mp4
- [ ] Assets cropped to composition size
- [ ] No off-screen objects
- [ ] Simple expressions used
- [ ] Resolution matches platform requirements
- [ ] Pre-compositions cleaned of unnecessary elements

---

## GRADING CRITERIA

**Grade A (90-100%):**
- All critical requirements met ✅
- All high priority requirements met ✅
- Most best practices followed ✅
- Ready for production deployment

**Grade B (80-89%):**
- All critical requirements met ✅
- Most high priority requirements met ✅
- Some best practices followed
- Safe for deployment with minor optimizations suggested

**Grade C (70-79%):**
- All critical requirements met ✅
- Some high priority requirements not met ⚠️
- Few best practices followed
- Deployable but needs optimization

**Grade D (60-69%):**
- Critical requirements met but barely ✅
- Many high priority issues ⚠️
- Poor best practices
- Needs significant work before deployment

**Grade F (<60%):**
- Critical requirements NOT met ❌
- Will likely fail in Plainly
- Cannot deploy - must fix critical issues

---

## COMMON FAILURE PATTERNS

Based on research, these are common issues:

1. **Non-English characters** - #1 cause of render failures
2. **Using .mp3 instead of .wav** - Compatibility issues
3. **Effects on dynamic media** - Performance/compatibility issues
4. **Oversized assets** - Slow render times
5. **Complex expression chains** - Performance degradation
6. **Missing prefixes** - Manual parametrization required

---

## IMPLEMENTATION NOTES

### Validation Order:
1. **Critical checks first** - Block deployment if failed
2. **High priority checks** - Warn but allow with confirmation
3. **Best practices** - Inform but don't block

### Scoring System:
- Critical issue: -20 points each
- Warning issue: -5 points each
- Info issue: -1 point each
- Start at 100, subtract for issues

### Report Format:
- Clear pass/fail for Plainly deployment
- Specific issues with line-by-line fixes
- Actionable suggestions
- Estimated render time impact

---

## RESEARCH SOURCES

1. **Plainly Help Center - Best Practices:**
   https://help.plainlyvideos.com/docs/user-guide/projects/project-creation/best-practices

2. **Plainly User Documentation:**
   https://api.plainlyvideos.com/asciidoc/plainly-manual.html

3. **After Effects Plugin Documentation:**
   https://help.plainlyvideos.com/docs/after-effects-plugin

4. **Blog: After Effects Template Tips:**
   https://www.plainlyvideos.com/blog/after-effects-template-tips

---

## STATUS: Research Complete ✅

Ready for implementation of validation module!
