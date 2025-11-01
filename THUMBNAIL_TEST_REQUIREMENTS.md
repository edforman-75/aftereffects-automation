# Photoshop Thumbnail Generation - Minimal Test

## Goal
Create a simple Python script that generates PNG thumbnails from each layer in a PSD file using Photoshop 2026.

## Requirements
1. **Input**: Hardcoded path to test PSD file: `/Users/edf/aftereffects-automation/uploads/1761779221_6cda6f4d_psd_test-photoshop-doc.psd`
2. **Output**: PNG thumbnails (200px width) saved to `/tmp/thumb_test/`
3. **Process**:
   - Open PSD in Photoshop 2026
   - For each layer:
     - Hide all other layers
     - Show only current layer
     - Export as 200px wide PNG thumbnail
     - Save to output folder with layer name
   - Close PSD without saving

## Technical Details
- Use AppleScript to control Photoshop 2026
- Use ExtendScript (JavaScript) for Photoshop operations
- Handle the "frontmost document" issue we've been encountering
- Print progress to console
- Handle errors gracefully

## Success Criteria
- Script runs without errors
- Generates 6 PNG files (one per layer)
- Each PNG is valid and ~200px wide
- Console shows clear progress messages

## Known Issues to Solve
- "The requested action requires that the target document is the frontmost document" error
- Need to ensure document stays active throughout layer iteration

Please create a standalone Python script called `test_photoshop_thumbnails.py` that accomplishes this.
