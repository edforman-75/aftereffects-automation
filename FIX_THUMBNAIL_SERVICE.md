# Fix ThumbnailService to Match Working Test Script

## Problem
The standalone test script `test_photoshop_thumbnails.py` successfully generates all 6 thumbnails with NO errors.

However, the production code in `services/thumbnail_service.py` fails with:
```
Error: General Photoshop error occurred. This functionality may not be available in this version of Photoshop.
- <no additional information available>
```

## Task
1. Compare `test_photoshop_thumbnails.py` (working) with `services/thumbnail_service.py` (failing)
2. Identify the differences in the ExtendScript/JSX generation
3. Update `services/thumbnail_service.py` to match the exact working approach from the test script

## Key Areas to Compare
- How layer bounds are obtained
- The duplicate/flatten/crop sequence
- The resize operations (test does ONE resize, production does TWO)
- Any other ExtendScript API calls

## Success Criteria
- Production code generates thumbnails exactly like the test script
- All 6 layers produce valid PNG thumbnails
- No "General Photoshop error" messages

## Files
- Working: `test_photoshop_thumbnails.py`
- Broken: `services/thumbnail_service.py` (specifically the `_generate_thumbnail_script` method around lines 55-200)
