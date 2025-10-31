# Automated Stage Transitions with Pre-Processing - Specification

**Date**: 2025-10-30
**Status**: 📋 **Specification Complete** | ⚠️ **Implementation Pending**
**Builds On**: Core batch processing backend (Stages 0-1 complete)

---

## 🎯 Concept

When a human approves a stage, the system **immediately begins preparing everything needed for the next stage** in the background. By the time the human is ready to review the next stage, all processing is already complete.

**Key Benefit**: Humans never wait for processing - they only review what's already been prepared.

---

## 🔄 Complete Stage Flow with Pre-Processing

### **STAGE 0 → STAGE 1**
**Trigger**: Human clicks "Start Ingestion"

**Processing** (Automated):
- Process PSD headlessly (extract layers, detect fonts)
- Process AEPX headlessly (parse structure, detect placeholders)
- Auto-match layers using name similarity
- Detect warnings (missing fonts, missing footage, unmatched placeholders)

**Status Change**: `pending` → `processing` → `awaiting_review` (Stage 2)

**Pre-Processing for Stage 2** (Background Thread):
1. Generate high-quality preview renders of all PSD layers
2. Generate preview renders of all AEPX layers
3. Create side-by-side comparison thumbnails
4. Calculate similarity scores for better matching
5. Prepare matching UI with all assets ready

**Result**: When human opens Stage 2, everything is already rendered

---

### **STAGE 2 → STAGE 3**
**Trigger**: Human clicks "Approve Matching"

**Processing** (Human):
- Review auto-matched layers
- Adjust incorrect matches
- Resolve warnings if possible

**Status Change**: `awaiting_review` → `awaiting_approval` (Stage 3)

**Pre-Processing for Stage 3** (Background Thread):
1. Generate ExtendScript with approved layer mappings
2. Render side-by-side preview video (PSD flat vs AE render)
3. Create preview thumbnails
4. Calculate render metrics (time, quality)
5. Prepare approval UI with preview ready to play

**Result**: When human opens Stage 3, preview video is already rendered and ready to watch

---

### **STAGE 3 → STAGE 4**
**Trigger**: Human clicks "Approve for Deployment"

**Processing** (Human):
- Watch side-by-side preview
- Can approve WITH warnings (logged)
- Final approval decision

**Status Change**: `awaiting_approval` → `ready_for_validation` (Stage 4)

**Pre-Processing for Stage 4** (Background Thread):
1. Generate final AEP with unique output name
2. Run Plainly validator on final AEP
3. Check for validation errors
4. Prepare validation report
5. If no errors: Mark as ready for deployment
6. If errors: Mark as needs sign-off

**Result**: Validation already complete when human checks status

---

### **STAGE 4 COMPLETION**
**Two Paths**:

**Path A: Validation Passed** (Automated):
- Auto-deploy to output directory
- Status: `completed`
- Human sees: "Download" button

**Path B: Validation Failed** (Needs Human):
- Human reviews validation errors
- Human decides: Fix and re-process OR Force approve
- Status: `validation_failed` → manual approval → `completed`

---

## 🔧 Implementation: Stage Transition Manager

### **New Service**: `services/stage_transition_manager.py`

**Core Methods**:
1. `transition_stage(job_id, from_stage, to_stage, user_id)` - Handle transitions
2. `_preprocess_for_stage(job_id, stage)` - Route to stage-specific preprocessing
3. `_preprocess_stage2(job_id)` - Prepare matching UI
4. `_preprocess_stage3(job_id)` - Prepare preview approval
5. `_preprocess_stage4(job_id)` - Validate and deploy

**Dependencies**:
- JobService (already implemented ✅)
- LogService (already implemented ✅)
- WarningService (already implemented ✅)
- PSD Layer Exporter (already implemented ✅)
- AEPX Processor (already implemented ✅)
- Matcher Service (needs implementation ⚠️)
- Preview Generator (partially implemented ⚠️)
- Plainly Validator (needs implementation ⚠️)

---

## 📊 Stage 2 Pre-Processing Details

### **Tasks**:
1. **Generate PSD Layer Previews**
   - Use exported PNG files from Stage 1
   - For text layers, render text as image
   - Store in `data/stage2_prep/<job_id>/psd_previews/`

2. **Generate AEPX Layer Previews**
   - Use aerender to export single frame of each layer
   - Store in `data/stage2_prep/<job_id>/aepx_previews/`

3. **Create Side-by-Side Comparison Thumbnails**
   - For each potential match pair, create comparison image
   - Store in `data/stage2_prep/<job_id>/comparisons/`

4. **Calculate Similarity Scores**
   - Image similarity (using PIL/OpenCV)
   - Name similarity (Levenshtein distance)
   - Create similarity matrix for UI

5. **Prepare Matching UI Data Structure**
   ```python
   matching_data = {
       'psd_previews': {layer_name: preview_path},
       'aepx_previews': {layer_name: preview_path},
       'comparisons': {pair_id: comparison_path},
       'similarity_scores': [[score_matrix]],
       'auto_matches': [...]  # From Stage 1
   }
   ```

---

## 📊 Stage 3 Pre-Processing Details

### **Tasks**:
1. **Generate ExtendScript**
   - Use approved layer mappings from Stage 2
   - Generate populate.jsx script
   - Store in `data/stage3_prep/<job_id>/`

2. **Render Side-by-Side Preview Video**
   - PSD flat video (export all layers as video)
   - AE render video (execute ExtendScript + render)
   - Combined side-by-side video
   - Store in `data/stage3_prep/<job_id>/`

3. **Create Video Thumbnail**
   - Extract frame from preview video
   - Store as preview thumbnail

4. **Calculate Render Metrics**
   ```python
   metrics = {
       'render_time': seconds,
       'psd_duration': seconds,
       'ae_duration': seconds,
       'file_sizes': {
           'psd': bytes,
           'ae': bytes,
           'combined': bytes
       }
   }
   ```

5. **Prepare Approval UI Data**
   ```python
   approval_data = {
       'preview_video': path,
       'thumbnail': path,
       'psd_video': path,
       'ae_video': path,
       'metrics': {},
       'extendscript_path': path
   }
   ```

---

## 📊 Stage 4 Pre-Processing Details

### **Tasks**:
1. **Generate Final AEP**
   - Execute ExtendScript on AEPX
   - Save as AEP with unique output name
   - Store in `data/stage4_prep/<job_id>/`

2. **Run Plainly Validator**
   - Execute Plainly CLI on final AEP
   - Parse validation results
   - Categorize errors vs warnings

3. **Handle Validation Results**

   **If Passed**:
   - Auto-deploy to `output/deployed/`
   - Mark job as `completed`
   - Log deployment

   **If Failed**:
   - Log errors as warnings in database
   - Mark job as `validation_failed`
   - Require human sign-off

---

## 🔌 Integration with Existing System

### **Update Approval Endpoints in `web_app.py`**:

```python
from services.stage_transition_manager import StageTransitionManager

# Initialize
transition_manager = StageTransitionManager(...)

# Stage 1 completion
@app.route('/api/stage1-complete/<job_id>', methods=['POST'])
def stage1_complete(job_id):
    transition_manager.transition_stage(job_id, 1, 2, 'system')
    return jsonify({'success': True})

# Stage 2 approval
@app.route('/approve-matching/<job_id>', methods=['POST'])
def approve_matching(job_id):
    data = request.json
    job_service.store_approved_matches(job_id, data['matches'])
    transition_manager.transition_stage(job_id, 2, 3, current_user.id)
    return jsonify({'success': True})

# Stage 3 approval
@app.route('/approve-final/<job_id>', methods=['POST'])
def approve_final(job_id):
    transition_manager.transition_stage(job_id, 3, 4, current_user.id)
    return jsonify({'success': True})
```

---

## 📋 Implementation Checklist

### **Phase 1: Stage Transition Manager Core**
- [ ] Create `services/stage_transition_manager.py`
- [ ] Implement `transition_stage()` method
- [ ] Implement background thread handling
- [ ] Add error handling for failed pre-processing
- [ ] Test basic stage transitions

### **Phase 2: Stage 2 Pre-Processing**
- [ ] Implement PSD layer preview generation
- [ ] Implement AEPX layer preview generation (aerender)
- [ ] Implement comparison thumbnail creation
- [ ] Implement similarity score calculation
- [ ] Test Stage 1→2 transition with real data

### **Phase 3: Stage 3 Pre-Processing**
- [ ] Integrate ExtendScript generator
- [ ] Implement side-by-side video rendering
- [ ] Implement video thumbnail extraction
- [ ] Calculate render metrics
- [ ] Test Stage 2→3 transition with real data

### **Phase 4: Stage 4 Pre-Processing**
- [ ] Implement final AEP generation
- [ ] Integrate Plainly validator
- [ ] Implement validation result parsing
- [ ] Implement auto-deployment
- [ ] Test Stage 3→4 transition with real data

### **Phase 5: Error Handling**
- [ ] Handle pre-processing failures gracefully
- [ ] Retry logic for transient failures
- [ ] User notifications for failures
- [ ] Ability to manually retry failed pre-processing

### **Phase 6: Dashboard Integration**
- [ ] Show pre-processing progress in dashboard
- [ ] Display "Processing" vs "Ready for Review" states
- [ ] Enable/disable action buttons based on pre-processing status

---

## 💡 Expected User Experience

### **Scenario: User Approves Stage 2 Matching**

**What User Does**:
1. Reviews layer matches in Stage 2 UI
2. Makes adjustments to incorrect matches
3. Clicks "Approve Matching" button

**What System Does** (Immediate):
1. Shows toast: "Matching approved! Generating preview..."
2. Updates job status to "Processing"
3. Returns user to dashboard

**What System Does** (Background - 30-60 seconds):
1. Generates ExtendScript with approved mappings
2. Renders PSD flat video
3. Renders After Effects video
4. Creates side-by-side comparison
5. Extracts thumbnail
6. Updates job status to "Awaiting Approval" (Stage 3)

**Dashboard Updates**:
1. Job moves from Stage 2 card to Stage 3 card
2. Stage 3 card shows "1 job needs approval"
3. Action button changes to "Approve Preview"

**When User Clicks "Approve Preview"**:
1. Preview video loads instantly (already rendered!)
2. User can watch side-by-side comparison immediately
3. No "please wait" messages

---

## 🎯 Benefits

### **1. No Waiting for Humans** ⚡
- Everything pre-rendered before human sees it
- Instant feedback and review
- Smooth, professional workflow

### **2. Efficient Resource Usage** 💪
- Background threads don't block UI
- Multiple jobs process in parallel
- Better CPU utilization

### **3. Clear Status Tracking** 📊
- Dashboard shows exact stage and state
- "Processing" vs "Ready" indicators
- Users know what needs attention

### **4. Error Recovery** 🛡️
- Failed pre-processing logged
- Jobs don't get stuck
- Manual retry capability

---

## 📈 Performance Expectations

### **Typical Timeline** (per job):

**Stage 1 → Stage 2 Transition**:
- Pre-processing time: 10-30 seconds
- Tasks: Generate previews, create comparisons
- User can review other jobs while waiting

**Stage 2 → Stage 3 Transition**:
- Pre-processing time: 30-90 seconds
- Tasks: Generate ExtendScript, render videos
- Most time-consuming stage

**Stage 3 → Stage 4 Transition**:
- Pre-processing time: 10-20 seconds
- Tasks: Generate AEP, run validator
- If validation passes: Auto-deploy (instant)

**Total Pipeline Time** (with pre-processing):
- ~2-3 minutes per job (all automated stages)
- Human review time: Variable (0-5 minutes per stage)

---

## 🔧 Dependencies Needed

### **Already Implemented** ✅:
- JobService
- LogService
- WarningService
- PSD Layer Exporter
- AEPX Processor
- Database infrastructure

### **Needs Implementation** ⚠️:
- Stage Transition Manager (new)
- Matcher Service (similarity scoring)
- Enhanced Preview Generator (side-by-side video)
- Plainly Validator integration
- Final AEP generator

---

## 📝 Notes for Implementation

### **Threading Considerations**:
- Use `threading.Thread` for background pre-processing
- Mark threads as daemon to allow clean shutdown
- Use try/except to catch and log errors
- Update database from background threads (thread-safe)

### **Progress Tracking**:
- Log start/end of each pre-processing step
- Store progress in job metadata
- Dashboard can poll for progress updates

### **Resource Management**:
- Limit concurrent background threads (e.g., max 5 at once)
- Clean up temp files after successful deployment
- Monitor disk space for preview videos

---

## 🎉 Summary

This automated stage transition system transforms the batch processing pipeline from a **wait-heavy workflow** into a **smooth, instant-review experience**.

When combined with the production dashboard, it creates a **professional production system** where:
- Humans focus on review and approval
- System handles all processing in background
- Everything is pre-rendered and ready
- No waiting, no bottlenecks

**Status**: Specification complete and ready for implementation
**Builds On**: Existing Stage 0-1 backend (already implemented)
**Next**: Implement Stage Transition Manager + required services
