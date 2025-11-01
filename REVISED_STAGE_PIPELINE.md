# Revised Stage Pipeline - Proper Separation of Concerns

## Current Problem

We conflated two distinct phases into "Stage 3":
1. **Automatic validation** (system checks for issues)
2. **User review/adjustment** (user decides what to do)

These should be separate stages!

---

## Proposed Corrected Pipeline

### Stage 0: Batch Upload & Ingestion
**Status:** ✅ Complete
- CSV upload and validation
- File existence checks
- Batch creation

### Stage 1: Automated Processing
**Status:** ✅ Complete
- PSD layer extraction with thumbnails
- AEPX parsing with namespace support
- Automatic fuzzy name matching
- Warnings detection (missing assets, etc.)

### Stage 2: Manual Matching Review
**Status:** ✅ Complete
- User reviews auto-matches
- Drag-and-drop to adjust matches
- Add/remove/swap matches
- Mark layers as "skip" if needed
**Output:** Approved match list

### Stage 3: Automatic Validation ⭐ NEW DEFINITION
**Status:** ✅ System built, needs stage separation
**Type:** Automatic (no user interaction)
**What Happens:**
- System automatically validates approved matches
- Checks aspect ratios
- Checks resolution scaling
- Checks for missing assets
- Generates validation report
**Output:** Validation report with severity levels
**Duration:** 1-2 seconds (instant)

### Stage 4: Validation Review & Adjustment ⭐ NEW STAGE
**Status:** ⚠️ UI built, needs integration
**Type:** Manual (conditional - only if issues found)
**What Happens:**
- **IF critical issues:** User must review at `/validate/{job_id}`
  - Shows all critical issues, warnings, info
  - User chooses:
    - Option A: "Back to Stage 2" → Fix matches
    - Option B: "Override & Continue" → Provide reason, proceed
- **IF no critical issues:** Skip this stage entirely, auto-advance
**Output:** Override decision or return to Stage 2

### Stage 5: ExtendScript Generation ⭐ RENAMED (was Stage 4)
**Status:** ⏳ Not yet implemented
**Type:** Automatic
**What Happens:**
- Generate ExtendScript (.jsx) from approved matches
- Create replacement commands for each match
- Handle text layers, image layers, solids
- Generate preview of script
**Output:** Downloadable .jsx file

### Stage 6: Final Review & Download ⭐ NEW
**Status:** ⏳ Not yet implemented
**Type:** Manual
**What Happens:**
- User reviews generated ExtendScript
- Preview shows what will be replaced
- Download button for .jsx file
- Option to regenerate if issues
**Output:** Final .jsx file downloaded

---

## Stage Transition Logic

### From Stage 2 (Manual Matching):
```
User clicks "Save & Next Job"
  ↓
Save matches to database
  ↓
TRANSITION TO STAGE 3 (auto-validation)
  ↓
Validation runs (1-2 seconds)
  ↓
Check results:
  ├─ Critical Issues Found?
  │    ↓
  │  TRANSITION TO STAGE 4 (validation review)
  │    ↓
  │  Redirect user to /validate/{job_id}
  │    ↓
  │  User reviews and decides:
  │    ├─ "Back to Matching" → STAGE 2
  │    └─ "Override & Continue" → STAGE 5
  │
  └─ No Critical Issues?
       ↓
     SKIP STAGE 4
       ↓
     TRANSITION TO STAGE 5 (ExtendScript generation)
       ↓
     Load next job or go to dashboard
```

---

## Database Schema Update

**Current `jobs` table:**
```sql
current_stage INTEGER  -- Values: 1, 2, 3, 4
```

**Updated `jobs` table:**
```sql
current_stage INTEGER  -- Values: 1, 2, 3, 4, 5, 6

-- Stage completion tracking
stage1_completed_at TIMESTAMP
stage2_completed_at TIMESTAMP
stage3_completed_at TIMESTAMP  -- Auto-validation
stage4_completed_at TIMESTAMP  -- User validation review (if needed)
stage5_completed_at TIMESTAMP  -- ExtendScript generation
stage6_completed_at TIMESTAMP  -- Final download

-- Stage-specific data
stage1_results TEXT            -- JSON: PSD/AEPX extraction results
stage2_approved_matches TEXT   -- JSON: User-approved match list
stage3_validation_results TEXT -- JSON: Validation report
stage4_override_reason TEXT    -- TEXT: Why user overrode validation
stage5_extendscript TEXT       -- TEXT: Generated .jsx script
```

---

## Stage Status Values

Each stage can have these statuses:

**Stage 1:**
- `pending` - Waiting to start
- `processing` - Currently extracting
- `complete` - Extraction done
- `failed` - Errors occurred

**Stage 2:**
- `awaiting_review` - Waiting for user to review matches
- `in_review` - User actively reviewing
- `complete` - User approved matches

**Stage 3:**
- `validating` - Auto-validation running
- `complete` - Validation finished

**Stage 4:**
- `skipped` - No critical issues, skipped this stage
- `awaiting_review` - User needs to review validation issues
- `overridden` - User chose to override issues
- `returned_to_stage2` - User went back to fix matches

**Stage 5:**
- `generating` - Creating ExtendScript
- `complete` - Script generated
- `failed` - Generation errors

**Stage 6:**
- `awaiting_download` - Ready for user to download
- `complete` - User downloaded file

---

## API Endpoints by Stage

### Stage 0
- `POST /api/batch/upload` - Upload CSV
- `GET /api/batch/{batch_id}` - Get batch details

### Stage 1
- `POST /api/batch/{batch_id}/start-processing` - Trigger Stage 1
- `GET /api/job/{job_id}` - Get job with Stage 1 results

### Stage 2
- `GET /review-matching/{job_id}` - Manual matching UI
- `POST /api/job/{job_id}/approve-stage2` - Save matches → Trigger Stage 3

### Stage 3 (Auto-validation)
- `GET /api/job/{job_id}/validation-status` - Check if validation complete
- *(No user endpoint - automatic)*

### Stage 4 (Validation Review)
- `GET /validate/{job_id}` - Validation review UI
- `GET /api/job/{job_id}/validation-results` - Get validation report
- `POST /api/job/{job_id}/override-validation` - Override with reason
- `POST /api/job/{job_id}/return-to-matching` - Go back to Stage 2

### Stage 5 (ExtendScript Generation)
- `POST /api/job/{job_id}/generate-extendscript` - Trigger generation
- `GET /api/job/{job_id}/extendscript-status` - Check generation status

### Stage 6 (Final Review & Download)
- `GET /preview/{job_id}` - Preview and download UI
- `GET /api/job/{job_id}/download-extendscript` - Download .jsx file
- `POST /api/job/{job_id}/complete` - Mark job as complete

---

## Implementation Priority

### Phase 1: Stage Separation (High Priority)
1. Update stage numbers throughout codebase
2. Fix stage transition logic in `approve_stage2`
3. Ensure Stage 4 (validation review) UI loads correctly
4. Test full flow: Stage 2 → 3 → 4 → back to 2 or → 5

### Phase 2: Stage 5 Implementation (High Priority)
1. Implement ExtendScript generation
2. Create generation service
3. Test with various match types

### Phase 3: Stage 6 Implementation (Medium Priority)
1. Create preview UI
2. Add download functionality
3. Job completion tracking

---

## Migration Plan

### Step 1: Database Migration
```sql
-- No schema changes needed for stage numbers
-- Just update the logic and documentation

-- Add new columns for Stage 4
ALTER TABLE jobs ADD COLUMN stage4_completed_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN stage4_override_reason TEXT;

-- Add new columns for Stage 5
ALTER TABLE jobs ADD COLUMN stage5_completed_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN stage5_extendscript TEXT;

-- Add new columns for Stage 6
ALTER TABLE jobs ADD COLUMN stage6_completed_at TIMESTAMP;
```

### Step 2: Update Stage Transition Manager
```python
# /services/stage_transition_manager.py

def transition_to_stage(self, job_id: str, target_stage: int, user_id: str):
    """
    Stage transitions:
    1 → 2: Extraction complete, ready for manual review
    2 → 3: Matches approved, trigger auto-validation
    3 → 4: Critical issues found, needs user review
    3 → 5: No critical issues, skip Stage 4, generate ExtendScript
    4 → 2: User chose to go back and fix matches
    4 → 5: User overrode issues, proceed to ExtendScript
    5 → 6: ExtendScript generated, ready for download
    6 → complete: User downloaded, job complete
    """
```

### Step 3: Update Web App Routes
- Update all stage references in comments/logs
- Ensure validation redirect goes to Stage 4
- Update dashboard to show all 6 stages

### Step 4: Update UI
- Dashboard shows stages 1-6
- Progress indicators show all stages
- Breadcrumbs reflect new stage names

---

## Visual Stage Flow Diagram
```
┌─────────────┐
│  Stage 0    │  Batch Upload
│  Upload CSV │
└──────┬──────┘
       ↓
┌─────────────┐
│  Stage 1    │  Automated Processing
│  Extract    │  • PSD layers
│  & Match    │  • AEPX parsing
│             │  • Auto-matching
└──────┬──────┘
       ↓
┌─────────────┐
│  Stage 2    │  Manual Matching Review
│  User       │  • Review matches
│  Adjusts    │  • Drag & drop
│             │  • Approve
└──────┬──────┘
       ↓
┌─────────────┐
│  Stage 3    │  Automatic Validation
│  System     │  • Aspect ratio check
│  Validates  │  • Resolution check
│  (1-2 sec)  │  • Generate report
└──────┬──────┘
       ↓
    ┌──┴───┐
    │      │
Critical? No?
    │      │
   Yes     └─────────────┐
    ↓                    ↓
┌─────────────┐   ┌─────────────┐
│  Stage 4    │   │  Stage 5    │
│  Validation │   │  ExtendScript│
│  Review     │   │  Generation  │
│  (User)     │   │  (Auto)      │
└──────┬──────┘   └──────┬───────┘
       │                 │
   ┌───┴───┐            │
   │       │            │
Back?  Override?        │
   │       │            │
   ↓       └────────────┘
Stage 2           │
                  ↓
            ┌─────────────┐
            │  Stage 6    │
            │  Preview &  │
            │  Download   │
            └─────────────┘
```

---

## Benefits of This Structure

### Clear Separation
- ✅ Automatic vs Manual stages clearly defined
- ✅ Each stage has single responsibility
- ✅ Easy to understand workflow

### Conditional Logic
- ✅ Stage 4 only runs when needed (critical issues)
- ✅ No wasted time for jobs without issues
- ✅ Users only intervene when necessary

### Extensibility
- ✅ Easy to add Stage 7, 8, etc. in future
- ✅ Each stage is self-contained
- ✅ Can parallelize automatic stages

### Better UX
- ✅ Users see clear progress through 6 stages
- ✅ Can bookmark/share specific stage URLs
- ✅ Clear indication of where job is blocked

---

## Next Steps

1. **Approve this structure** - Confirm 6-stage model
2. **Update stage transition logic** - Fix Stage 2→3→4 flow
3. **Test validation redirect** - Ensure Stage 4 UI loads
4. **Implement Stage 5** - ExtendScript generation
5. **Implement Stage 6** - Preview & download

---

## Summary

**Correct Pipeline:**
```
Stage 0: Upload
Stage 1: Extract & Auto-match (automatic)
Stage 2: User reviews matches (manual)
Stage 3: Auto-validation (automatic, always runs)
Stage 4: User reviews validation (manual, conditional)
Stage 5: Generate ExtendScript (automatic)
Stage 6: Preview & download (manual)
```

**Key Insight:** Stage 3 and Stage 4 are DIFFERENT phases:
- Stage 3 = System checks (always happens)
- Stage 4 = User reviews (only if issues found)

This is cleaner and more maintainable! ✅

