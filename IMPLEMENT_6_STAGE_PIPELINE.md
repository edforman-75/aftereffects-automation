# Implementation: 6-Stage Pipeline Structure

## Overview

Restructure the entire pipeline from 4 stages to 6 stages with proper separation between automatic validation and user review.

---

## Stage Definitions (Final)
```
Stage 0: Batch Upload & Ingestion
Stage 1: Automated Processing (PSD + AEPX extraction, auto-matching)
Stage 2: Manual Matching Review (user adjusts matches)
Stage 3: Automatic Validation (system checks, no user interaction)
Stage 4: Validation Review & Adjustment (user reviews issues, conditional)
Stage 5: ExtendScript Generation (automatic)
Stage 6: Preview & Download (user downloads final script)
```

---

## Database Schema Changes

### File: `database/models.py`

**Add new columns to Job model:**
```python
class Job(Base):
    __tablename__ = 'jobs'
    
    # ... existing columns ...
    
    # Stage completion timestamps
    stage1_completed_at = Column(DateTime)
    stage2_completed_at = Column(DateTime)
    stage3_completed_at = Column(DateTime)  # NEW: Auto-validation
    stage4_completed_at = Column(DateTime)  # NEW: User validation review
    stage5_completed_at = Column(DateTime)  # NEW: ExtendScript generation
    stage6_completed_at = Column(DateTime)  # NEW: Final download
    
    # Stage-specific data
    stage1_results = Column(Text)           # JSON: extraction results
    stage2_approved_matches = Column(Text)  # JSON: approved matches
    stage3_validation_results = Column(Text) # JSON: validation report
    stage4_override_reason = Column(Text)   # TEXT: override justification
    stage5_extendscript = Column(Text)      # TEXT: generated .jsx
    stage6_downloaded_at = Column(DateTime) # When user downloaded
```

**Create migration script:**
```sql
-- File: database/migrations/add_stage_4_5_6_columns.sql

ALTER TABLE jobs ADD COLUMN stage4_completed_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN stage4_override_reason TEXT;
ALTER TABLE jobs ADD COLUMN stage5_completed_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN stage5_extendscript TEXT;
ALTER TABLE jobs ADD COLUMN stage6_completed_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN stage6_downloaded_at TIMESTAMP;
```

---

## Stage Transition Manager Updates

### File: `services/stage_transition_manager.py`

**Update transition logic to handle 6 stages:**
```python
class StageTransitionManager:
    """
    Manages job transitions through 6 stages.
    
    Stage Flow:
    1 → 2: Extraction complete, ready for manual review
    2 → 3: Matches approved, trigger auto-validation
    3 → 4: Critical issues found, user must review
    3 → 5: No critical issues, skip Stage 4, generate ExtendScript
    4 → 2: User chose to return and fix matches
    4 → 5: User overrode issues, proceed to ExtendScript
    5 → 6: ExtendScript generated, ready for download
    6 → complete: User downloaded, job complete
    """
    
    def transition_to_stage(self, job_id: str, target_stage: int, user_id: str = 'system'):
        """
        Transition job to target stage with validation.
        
        Args:
            job_id: Job identifier
            target_stage: Target stage number (1-6)
            user_id: User performing transition
        """
        session = self.db_session()
        
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            
            current_stage = job.current_stage or 0
            
            # Validate transition is allowed
            if not self._is_valid_transition(current_stage, target_stage):
                raise ValueError(
                    f"Invalid transition from stage {current_stage} to {target_stage}"
                )
            
            # Update stage
            job.current_stage = target_stage
            
            # Set completion timestamp for previous stage
            if target_stage == 2:
                job.stage1_completed_at = datetime.utcnow()
                job.status = 'awaiting_review'
            elif target_stage == 3:
                job.stage2_completed_at = datetime.utcnow()
                job.status = 'validating'
            elif target_stage == 4:
                job.stage3_completed_at = datetime.utcnow()
                job.status = 'awaiting_validation_review'
            elif target_stage == 5:
                if current_stage == 3:
                    # Skipped Stage 4
                    job.stage3_completed_at = datetime.utcnow()
                    job.stage4_completed_at = datetime.utcnow()  # Mark as skipped
                elif current_stage == 4:
                    # Came from Stage 4
                    job.stage4_completed_at = datetime.utcnow()
                job.status = 'generating_extendscript'
            elif target_stage == 6:
                job.stage5_completed_at = datetime.utcnow()
                job.status = 'awaiting_download'
            
            session.commit()
            
            self.logger.info(
                f"Job {job_id}: Transitioned from Stage {current_stage} to {target_stage}"
            )
            
            return True
            
        finally:
            session.close()
    
    def _is_valid_transition(self, current: int, target: int) -> bool:
        """
        Check if stage transition is allowed.
        
        Valid transitions:
        0 → 1: Initial ingestion to processing
        1 → 2: Extraction complete
        2 → 3: Matches approved
        3 → 4: Critical validation issues
        3 → 5: No critical issues (skip Stage 4)
        4 → 2: Return to fix matches
        4 → 5: Override and continue
        5 → 6: ExtendScript generated
        """
        valid_transitions = {
            0: [1],           # Upload → Processing
            1: [2],           # Processing → Matching
            2: [3],           # Matching → Auto-validation
            3: [4, 5],        # Auto-validation → Review OR ExtendScript
            4: [2, 5],        # Review → Back to matching OR ExtendScript
            5: [6],           # ExtendScript → Download
            6: []             # Terminal stage
        }
        
        return target in valid_transitions.get(current, [])
```

---

## Web App Route Updates

### File: `web_app.py`

**Update approve_stage2 endpoint to handle Stage 3 → 4 transition:**
```python
@app.route('/api/job/<job_id>/approve-stage2', methods=['POST'])
def approve_stage2(job_id: str):
    """
    Approve Stage 2 matches and trigger Stage 3 validation.
    
    Flow:
    1. Save approved matches
    2. Transition to Stage 3 (auto-validation)
    3. Run validation checks
    4. If critical issues: Transition to Stage 4, return validation URL
    5. If no critical: Transition to Stage 5, proceed to ExtendScript
    """
    try:
        data = request.json
        approved_matches = data.get('approved_matches', [])
        user_id = data.get('user_id', 'anonymous')
        next_action = data.get('next_action', 'continue')
        
        session = db_session()
        
        try:
            # 1. Get job
            job = session.query(Job).filter_by(job_id=job_id).first()
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            # 2. Save approved matches
            job.stage2_approved_matches = json.dumps(approved_matches)
            session.commit()
            
            logger.info(f"Job {job_id}: Stage 2 approval by {user_id}, "
                       f"{len(approved_matches)} matches")
            
            # 3. Log approval
            log_service.add_log(
                job_id=job_id,
                stage=2,
                action='stage_approved',
                message=f'Stage 2 approved by {user_id}',
                user_id=user_id
            )
            
            # 4. Transition to Stage 3 (auto-validation)
            stage_transition_manager.transition_to_stage(job_id, 3, user_id)
            
            # 5. Run validation
            logger.info(f"Job {job_id}: Running validation checks...")
            validation_results = match_validator.validate_job(job_id)
            
            # 6. Store validation results
            job.stage3_validation_results = json.dumps(validation_results)
            session.commit()
            
            # 7. Check for critical issues
            has_critical = len(validation_results.get('critical_issues', [])) > 0
            
            if has_critical:
                # CRITICAL ISSUES FOUND
                logger.info(f"Job {job_id}: Critical validation issues found, "
                           f"transitioning to Stage 4")
                
                # Transition to Stage 4 (user review required)
                stage_transition_manager.transition_to_stage(job_id, 4, user_id)
                
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'requires_validation': True,
                    'validation_url': f'/validate/{job_id}',
                    'message': 'Critical validation issues found. Review required.',
                    'critical_count': len(validation_results.get('critical_issues', []))
                })
            
            else:
                # NO CRITICAL ISSUES
                logger.info(f"Job {job_id}: Validation passed, proceeding to Stage 5")
                
                # Skip Stage 4, go directly to Stage 5
                stage_transition_manager.transition_to_stage(job_id, 5, user_id)
                
                # Find next job if requested
                next_job_id = None
                if next_action == 'next_job':
                    next_jobs = job_service.get_jobs_for_stage(2, limit=1)
                    if next_jobs and len(next_jobs) > 0:
                        next_job_id = next_jobs[0].job_id
                
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'requires_validation': False,
                    'next_job_id': next_job_id,
                    'message': 'Validation passed - proceeding to ExtendScript generation'
                })
        
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error approving Stage 2: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

**Add Stage 4 → 2 return endpoint:**
```python
@app.route('/api/job/<job_id>/return-to-matching', methods=['POST'])
def return_to_matching(job_id: str):
    """
    User chose to return to Stage 2 to fix matches.
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        
        # Transition back to Stage 2
        stage_transition_manager.transition_to_stage(job_id, 2, user_id)
        
        log_service.add_log(
            job_id=job_id,
            stage=4,
            action='returned_to_matching',
            message=f'User {user_id} returned to Stage 2 to fix matches',
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'redirect_url': f'/review-matching/{job_id}',
            'message': 'Returned to matching review'
        })
        
    except Exception as e:
        logger.error(f"Error returning to matching: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

**Update Stage 4 override endpoint:**
```python
@app.route('/api/job/<job_id>/override-validation', methods=['POST'])
def override_validation(job_id: str):
    """
    User chose to override validation issues and proceed.
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        override_reason = data.get('override_reason', '')
        
        if not override_reason:
            return jsonify({
                'success': False,
                'error': 'Override reason is required'
            }), 400
        
        session = db_session()
        
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            # Store override reason
            job.stage4_override_reason = override_reason
            session.commit()
            
            # Log override
            log_service.add_log(
                job_id=job_id,
                stage=4,
                action='validation_overridden',
                message=f'User {user_id} overrode validation: {override_reason}',
                user_id=user_id
            )
            
            # Transition to Stage 5 (ExtendScript generation)
            stage_transition_manager.transition_to_stage(job_id, 5, user_id)
            
            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': 'Validation overridden - proceeding to ExtendScript generation'
            })
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error overriding validation: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

## Frontend Updates

### File: `static/js/stage2_review.js`

**Update saveAndNext() to handle validation redirect:**
```javascript
async function saveAndNext() {
    try {
        showLoading(true);
        
        const response = await fetch(`/api/job/${jobId}/approve-stage2`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                approved_matches: getCurrentMatches(),
                user_id: 'current_user',
                next_action: 'next_job'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.requires_validation) {
                // CRITICAL ISSUES FOUND - Redirect to Stage 4 validation review
                showToast(
                    `⚠️ ${result.critical_count} critical issue(s) found. Review required.`,
                    'warning'
                );
                setTimeout(() => {
                    window.location.href = result.validation_url;
                }, 1500);
                
            } else if (result.next_job_id) {
                // NO ISSUES - Load next Stage 2 job
                showToast(`✅ Job ${jobId} approved. Loading next job...`, 'success');
                setTimeout(() => {
                    window.location.href = `/review-matching/${result.next_job_id}`;
                }, 1000);
                
            } else {
                // NO MORE JOBS - Return to dashboard
                showToast('🎉 No more Stage 2 jobs. Excellent work!', 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            }
        } else {
            alert(`Error: ${result.error}`);
        }
        
    } catch (error) {
        alert(`Failed to approve: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

async function saveAndDashboard() {
    try {
        showLoading(true);
        
        const response = await fetch(`/api/job/${jobId}/approve-stage2`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                approved_matches: getCurrentMatches(),
                user_id: 'current_user',
                next_action: 'dashboard'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.requires_validation) {
                // Validation required - redirect there
                showToast('⚠️ Critical issues found. Redirecting to validation...', 'warning');
                setTimeout(() => {
                    window.location.href = result.validation_url;
                }, 1500);
            } else {
                // No issues - return to dashboard
                showToast(`✅ Stage 2 approved for ${jobId}`, 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            }
        } else {
            alert(`Error: ${result.error}`);
        }
        
    } catch (error) {
        alert(`Failed to approve: ${error.message}`);
    } finally {
        showLoading(false);
    }
}
```

### File: `static/js/stage3_validation.js`

**Update to use correct API endpoints:**
```javascript
async function returnToMatching() {
    if (!confirm('Return to Stage 2 to adjust matches?')) {
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch(`/api/job/${jobId}/return-to-matching`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: 'current_user'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Returning to Stage 2...', 'info');
            setTimeout(() => {
                window.location.href = result.redirect_url;
            }, 1000);
        } else {
            alert(`Error: ${result.error}`);
        }
        
    } catch (error) {
        alert(`Failed to return: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

async function overrideAndContinue() {
    const reason = document.getElementById('override-reason').value.trim();
    
    if (!reason) {
        alert('Please provide a reason for overriding validation issues.');
        return;
    }
    
    if (reason.length < 10) {
        alert('Reason must be at least 10 characters.');
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch(`/api/job/${jobId}/override-validation`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: 'current_user',
                override_reason: reason
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('✅ Proceeding to ExtendScript generation...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';  // Or next appropriate page
            }, 1500);
        } else {
            alert(`Error: ${result.error}`);
        }
        
    } catch (error) {
        alert(`Failed to override: ${error.message}`);
    } finally {
        showLoading(false);
    }
}
```

---

## Dashboard Updates

### File: `templates/dashboard.html`

**Update stage display to show 6 stages:**
```html
<div class="stage-progress">
    <div class="stage {% if job.current_stage >= 1 %}complete{% endif %}">
        Stage 1<br>Extract
    </div>
    <div class="stage {% if job.current_stage >= 2 %}complete{% endif %}">
        Stage 2<br>Match
    </div>
    <div class="stage {% if job.current_stage >= 3 %}complete{% endif %}">
        Stage 3<br>Validate
    </div>
    <div class="stage {% if job.current_stage >= 4 %}complete{% endif %}">
        Stage 4<br>Review
    </div>
    <div class="stage {% if job.current_stage >= 5 %}complete{% endif %}">
        Stage 5<br>Generate
    </div>
    <div class="stage {% if job.current_stage >= 6 %}complete{% endif %}">
        Stage 6<br>Download
    </div>
</div>
```

---

## Testing Checklist

After implementation, test the complete flow:

### Test 1: No Validation Issues (Happy Path)
1. Upload batch with good matches
2. Review in Stage 2, approve
3. Should skip Stage 4, go directly to Stage 5
4. No validation review page shown

### Test 2: Critical Validation Issues
1. Upload batch
2. Create aspect ratio mismatch in Stage 2
3. Approve matches
4. Should redirect to `/validate/{job_id}` (Stage 4)
5. See critical issues displayed
6. Test "Return to Matching" → goes back to Stage 2
7. Test "Override & Continue" → proceeds to Stage 5

### Test 3: Multiple Jobs Batch Processing
1. Upload batch with 3 jobs
2. Process Job 1 → has critical issues → Stage 4
3. Override Job 1 → proceeds to Stage 5
4. Click "Next Job" → loads Job 2 in Stage 2
5. Job 2 has no issues → skips Stage 4
6. Click "Next Job" → loads Job 3

---

## Documentation Updates

Update all documentation to reflect 6-stage pipeline:
- README.md
- ARCHITECTURE.md
- API documentation
- User guides

---

## Success Criteria

✅ Database has columns for all 6 stages
✅ Stage transition logic handles all valid transitions
✅ approve_stage2 endpoint redirects to Stage 4 when needed
✅ Stage 4 validation page loads correctly
✅ "Return to Matching" button works
✅ "Override & Continue" button works
✅ Dashboard shows all 6 stages
✅ End-to-end test passes through entire pipeline

---

## Implementation Order

1. **Database migration** (add Stage 4, 5, 6 columns)
2. **Stage transition manager** (update logic for 6 stages)
3. **approve_stage2 endpoint** (add redirect logic)
4. **Stage 4 endpoints** (return-to-matching, override)
5. **Frontend JavaScript** (handle validation redirect)
6. **Dashboard UI** (show 6 stages)
7. **Testing** (full end-to-end tests)

---

## Estimated Effort

- Database changes: 15 minutes
- Backend logic: 2 hours
- Frontend updates: 1 hour
- Testing: 1 hour
- **Total: ~4 hours**

