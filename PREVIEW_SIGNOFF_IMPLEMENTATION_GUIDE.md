# Preview & Sign-off Workflow - Implementation Guide

## Phase 2: Remaining Implementation

This document provides complete implementation details for the remaining components of the dual-workflow preview/sign-off system.

---

## 1. BACKEND ENDPOINTS TO ADD

### A. `/previews/generate` Endpoint

**Location**: `web_app.py` (before PROJECT MANAGEMENT API section, ~line 2326)

```python
# ============================================================================
# PREVIEW & SIGN-OFF WORKFLOW
# ============================================================================

@app.route('/previews/generate', methods=['POST'])
def previews_generate():
    """Generate PSD PNG and AE MP4 preview renders"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({'success': False, 'error': 'Invalid session'}), 400

        session = sessions[session_id]

        # Guard: Check validation requirement (Mode A)
        if VALIDATE_BEFORE_PREVIEW:
            validation = session.get('validation')
            if not (validation and validation.get('ok')):
                return jsonify({
                    'success': False,
                    'error': 'Validation must pass before generating previews (Mode A).'
                }), 400

        psd_path = session.get('psd_path')
        aepx_path = session.get('aepx_path')

        # Create preview directory for this session
        preview_dir = PREVIEWS_FOLDER / "session_previews" / session_id
        preview_dir.mkdir(parents=True, exist_ok=True)

        # Generate PSD PNG (left preview)
        psd_png_path = str(preview_dir / f"psd_preview_{session_id}.png")
        from services.thumbnail_service import ThumbnailService
        thumb_service = ThumbnailService(container.main_logger)

        # Render full PSD as flattened PNG
        psd_result = thumb_service.render_psd_to_png(psd_path, psd_png_path)

        if not psd_result.is_success():
            return jsonify({
                'success': False,
                'error': f'PSD preview generation failed: {psd_result.get_error()}'
            }), 500

        # Generate AE MP4 (right preview)
        ae_mp4_path = str(preview_dir / f"ae_preview_{session_id}.mp4")

        # Use existing preview generator with draft settings
        from modules.phase5.preview_generator import generate_preview
        preview_result = generate_preview(
            aepx_path=aepx_path,
            output_path=ae_mp4_path,
            options={
                'resolution': 'half',  # Draft quality
                'duration': 5.0,
                'format': 'mp4',
                'quality': 'draft',
                'fps': 15
            }
        )

        if not preview_result['success']:
            return jsonify({
                'success': False,
                'error': f'AE preview generation failed: {preview_result.get("message")}'
            }), 500

        # Store preview info in session
        session['preview'] = {
            'psd_png': psd_png_path,
            'ae_mp4': ae_mp4_path,
            'generated_at': now_iso()
        }

        # Update state
        update_job_state(session_id, 'PREVIEW_READY')

        return jsonify({
            'success': True,
            'message': 'Previews generated successfully',
            'state': session['state'],
            'preview': {
                'psd_png_url': f'/preview-file/{session_id}/psd',
                'ae_mp4_url': f'/preview-file/{session_id}/ae',
                'generated_at': session['preview']['generated_at']
            }
        })

    except Exception as e:
        container.main_logger.error(f"Preview generation error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/preview-file/<session_id>/<file_type>')
def serve_preview_file(session_id, file_type):
    """Serve preview files (psd or ae)"""
    try:
        if session_id not in sessions:
            return "Session not found", 404

        preview = sessions[session_id].get('preview')
        if not preview:
            return "Preview not generated", 404

        if file_type == 'psd':
            file_path = preview.get('psd_png')
        elif file_type == 'ae':
            file_path = preview.get('ae_mp4')
        else:
            return "Invalid file type", 400

        if not file_path or not Path(file_path).exists():
            return "File not found", 404

        return send_file(file_path)

    except Exception as e:
        container.main_logger.error(f"Error serving preview: {e}")
        return "Error serving file", 500
```

---

### B. `/signoff/approve` Endpoint

```python
@app.route('/signoff/approve', methods=['POST'])
def signoff_approve():
    """Approve previews and kick off final render"""
    try:
        data = request.json
        session_id = data.get('session_id')
        notes = data.get('notes', '')
        user = data.get('user', 'user')  # Could integrate with auth system

        if not session_id or session_id not in sessions:
            return jsonify({'success': False, 'error': 'Invalid session'}), 400

        session = sessions[session_id]

        # Guards
        if REQUIRE_SIGNOFF_FOR_RENDER:
            # Check validation (Mode A only)
            if VALIDATE_BEFORE_PREVIEW:
                validation = session.get('validation')
                if not (validation and validation.get('ok')):
                    return jsonify({
                        'success': False,
                        'error': 'Validation must pass before sign-off (Mode A).'
                    }), 400

            # Check previews exist
            preview = session.get('preview')
            if not (preview and preview.get('psd_png') and preview.get('ae_mp4')):
                return jsonify({
                    'success': False,
                    'error': 'Generate previews before sign-off.'
                }), 400

        # Calculate hashes for audit trail
        preview = session.get('preview', {})
        hashes = {
            'psd_png_sha256': sha256_file(preview.get('psd_png')) if preview.get('psd_png') else None,
            'ae_mp4_sha256': sha256_file(preview.get('ae_mp4')) if preview.get('ae_mp4') else None
        }

        # Store signoff
        session['signoff'] = {
            'approved': True,
            'approved_by': user,
            'notes': notes,
            'timestamp': now_iso(),
            'hashes': hashes
        }

        # Update state
        update_job_state(session_id, 'APPROVED', user=user)

        # Kick off final render (async)
        # For now, just prepare - actual render would be background task
        session['final_render'] = {
            'status': 'queued',
            'queued_at': now_iso()
        }

        container.main_logger.info(
            f"Sign-off approved for session {session_id} by {user}. Final render queued."
        )

        return jsonify({
            'success': True,
            'message': 'Approved! Final render queued.',
            'state': session['state'],
            'signoff': {
                'approved': True,
                'approved_by': user,
                'timestamp': session['signoff']['timestamp']
            }
        })

    except Exception as e:
        container.main_logger.error(f"Sign-off error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

### C. Modify `/validate-plainly` to Update State

**Find the existing `/validate-plainly` endpoint (~line 2052) and update it:**

After successful validation, update the session state:

```python
# At the end of successful validation, add:
session['validation'] = {
    'ok': report.is_valid and report.plainly_ready,
    'score': report.score,
    'grade': report.grade,
    'report': session['validation_report'],
    'generated_at': now_iso()
}

# Update state based on result
new_state = 'VALIDATED_OK' if (report.is_valid and report.plainly_ready) else 'VALIDATED_FAIL'
update_job_state(session_id, new_state)
```

---

## 2. MISSING UTILITY: PSD to PNG Renderer

**Add to `services/thumbnail_service.py`:**

```python
def render_psd_to_png(self, psd_path: str, output_path: str) -> Result:
    """
    Render full PSD as flattened PNG for preview

    Args:
        psd_path: Path to PSD file
        output_path: Where to save PNG

    Returns:
        Result with output path
    """
    try:
        from psd_tools import PSDImage
        from PIL import Image

        # Open PSD
        psd = PSDImage.open(psd_path)

        # Convert to PIL Image (flattened)
        img = psd.compose()

        # Save as PNG
        img.save(output_path, 'PNG')

        self.log_info(f"Rendered PSD to PNG: {output_path}")
        return Result.success({'output_path': output_path})

    except Exception as e:
        self.log_error(f"PSD to PNG render failed: {e}", exc_info=True)
        return Result.failure(f"Render failed: {str(e)}")
```

---

## 3. FRONTEND UI SECTION

**Add to `templates/index.html` after the validation section (~line 238):**

```html
<!-- Preview & Sign-off Section -->
<section class="card preview-signoff-section" id="previewSignoffSection" style="display: none;">
    <h2>7. Preview & Sign-off</h2>

    <!-- Mode Badge -->
    <div class="mode-badge">
        {% if VALIDATE_BEFORE_PREVIEW %}
            <span class="badge badge-green">Mode A: Validate → Preview → Sign-off → Render</span>
        {% else %}
            <span class="badge badge-blue">Mode B: Preview → Validate → Sign-off → Render</span>
        {% endif %}
    </div>

    <!-- Generate Previews Button -->
    <div class="preview-controls">
        <button id="generatePreviewsBtn" class="btn btn-primary btn-large">
            🎬 Generate Side-by-Side Previews
        </button>
        <div class="status-message" id="previewGenStatus"></div>
    </div>

    <!-- Side-by-Side Preview -->
    <div id="previewContainer" class="two-col" style="display: none;">
        <!-- Left: PSD Reference -->
        <div class="panel">
            <div class="panel-header">
                <h3>PSD Reference</h3>
                <div class="btn-row">
                    <a id="openPsdBtn" class="btn btn-secondary" download>📄 Download PSD</a>
                    <button id="regeneratePsdBtn" class="btn btn-secondary">🔄 Regenerate</button>
                </div>
            </div>
            <div class="panel-body">
                <img id="psdPreviewImg" class="media-box" alt="PSD preview" />
            </div>
        </div>

        <!-- Right: AE Preview -->
        <div class="panel">
            <div class="panel-header">
                <h3>After Effects Preview</h3>
                <div class="btn-row">
                    <a id="openAepxBtn" class="btn btn-secondary" download>🎬 Download AEPX</a>
                    <button id="regenerateAeBtn" class="btn btn-secondary">🔄 Regenerate</button>
                </div>
            </div>
            <div class="panel-body">
                <video id="aePreviewVideo" class="media-box" controls preload="metadata"></video>
            </div>
        </div>
    </div>

    <!-- Validation Summary Strip -->
    <div id="validationStrip" class="validation-strip" style="display: none;">
        <span class="strip-label">Validation Status:</span>
        <span id="validationBadge" class="badge"></span>
        <a id="viewReportLink" class="link" href="#validationSection">View Full Report</a>
    </div>

    <!-- Sign-off Card -->
    <div id="signoffCard" class="signoff-card" style="display: none;">
        <h3>✍️ Sign-off</h3>
        <p class="signoff-description">
            I confirm the PSD render (left) and AE preview (right) match expectations and are ready for final production render.
        </p>
        <textarea id="signoffNotes" class="signoff-textarea" placeholder="Optional notes (e.g., 'Approved for client delivery')"></textarea>
        <label class="signoff-checkbox">
            <input type="checkbox" id="signoffCheckbox">
            <span>I approve this preview for final high-quality render</span>
        </label>
        <button id="approveBtn" class="btn btn-success btn-large" disabled>
            ✅ Approve & Start Final Render
        </button>
        <div id="signoffStatus" class="status-message"></div>
    </div>
</section>
```

---

## 4. JAVASCRIPT WIRING

**Add to bottom of `<script>` section in `index.html`:**

```javascript
// Preview & Sign-off Workflow
const workflowSettings = {
    validateBeforePreview: {{ 'true' if VALIDATE_BEFORE_PREVIEW else 'false' }},
    requireSignoff: {{ 'true' if REQUIRE_SIGNOFF_FOR_RENDER else 'false' }}
};

// Event listeners
document.getElementById('generatePreviewsBtn')?.addEventListener('click', generatePreviews);
document.getElementById('regeneratePsdBtn')?.addEventListener('click', generatePreviews);
document.getElementById('regenerateAeBtn')?.addEventListener('click', generatePreviews);
document.getElementById('approveBtn')?.addEventListener('click', approveSignoff);
document.getElementById('signoffCheckbox')?.addEventListener('change', updateApproveButton);

async function generatePreviews() {
    const btn = document.getElementById('generatePreviewsBtn');
    const status = document.getElementById('previewGenStatus');

    btn.disabled = true;
    btn.textContent = '🎬 Generating Previews...';
    status.innerHTML = '<div class="status-message info">Generating side-by-side previews...</div>';

    try {
        const response = await fetch('/previews/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });

        const result = await response.json();

        if (result.success) {
            status.innerHTML = '<div class="status-message success">✅ Previews generated!</div>';

            // Show preview container
            const container = document.getElementById('previewContainer');
            container.style.display = 'grid';

            // Load images/videos
            document.getElementById('psdPreviewImg').src = result.preview.psd_png_url;
            document.getElementById('aePreviewVideo').src = result.preview.ae_mp4_url;

            // Show sign-off card
            document.getElementById('signoffCard').style.display = 'block';

            // Update validation strip if validation exists
            updateValidationStrip();

            btn.textContent = '✅ Previews Ready';
        } else {
            status.innerHTML = `<div class="status-message error">❌ ${result.error}</div>`;
            btn.disabled = false;
            btn.textContent = '🎬 Generate Side-by-Side Previews';
        }
    } catch (error) {
        status.innerHTML = `<div class="status-message error">❌ Error: ${error.message}</div>`;
        btn.disabled = false;
        btn.textContent = '🎬 Generate Side-by-Side Previews';
    }
}

async function approveSignoff() {
    const btn = document.getElementById('approveBtn');
    const status = document.getElementById('signoffStatus');
    const notes = document.getElementById('signoffNotes').value;

    btn.disabled = true;
    btn.textContent = '✅ Approving...';
    status.innerHTML = '<div class="status-message info">Processing sign-off...</div>';

    try {
        const response = await fetch('/signoff/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                notes: notes,
                user: 'current_user'  // Replace with actual user from auth
            })
        });

        const result = await response.json();

        if (result.success) {
            status.innerHTML = '<div class="status-message success">✅ Approved! Final render started.</div>';
            btn.textContent = '✅ Approved';
            document.getElementById('signoffCheckbox').disabled = true;
            document.getElementById('signoffNotes').disabled = true;
        } else {
            status.innerHTML = `<div class="status-message error">❌ ${result.error}</div>`;
            btn.disabled = false;
            btn.textContent = '✅ Approve & Start Final Render';
        }
    } catch (error) {
        status.innerHTML = `<div class="status-message error">❌ Error: ${error.message}</div>`;
        btn.disabled = false;
        btn.textContent = '✅ Approve & Start Final Render';
    }
}

function updateApproveButton() {
    const approve = document.getElementById('approveBtn');
    const checkbox = document.getElementById('signoffCheckbox');

    // Enable only if checked AND (in Mode A, validation passed)
    let enabled = checkbox.checked;

    if (workflowSettings.validateBeforePreview) {
        // Mode A: Need validation to pass
        const validationOk = sessions[sessionId]?.validation?.ok || false;
        enabled = enabled && validationOk;
    }

    approve.disabled = !enabled;
}

function updateValidationStrip() {
    const strip = document.getElementById('validationStrip');
    const badge = document.getElementById('validationBadge');

    // This would come from session data in practice
    // For now, show if validation section is visible
    if (document.getElementById('validationReport').style.display !== 'none') {
        strip.style.display = 'flex';
        const grade = document.getElementById('scoreGrade').textContent;
        const score = document.getElementById('scoreNumber').textContent;
        badge.textContent = `${grade} (${score}%)`;
        badge.className = grade === 'A' || grade === 'B' ? 'badge badge-ok' : 'badge badge-warn';
    }
}

// Auto-show preview section after script generation
const originalDisplayDownload = displayDownload;
displayDownload = function(data) {
    originalDisplayDownload(data);
    document.getElementById('previewSignoffSection').style.display = 'block';
    document.getElementById('previewSignoffSection').scrollIntoView({ behavior: 'smooth' });
};
```

---

## 5. CSS STYLES

**Add to `static/style.css`:**

```css
/* Preview & Sign-off Section */
.preview-signoff-section {
    margin-top: 30px;
}

.mode-badge {
    margin-bottom: 20px;
}

.badge-green {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
}

.badge-blue {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
}

.preview-controls {
    margin-bottom: 30px;
}

.two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin: 30px 0;
}

.panel {
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    overflow: hidden;
}

.panel-header {
    background: #f9fafb;
    padding: 15px 20px;
    border-bottom: 2px solid #e5e7eb;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.panel-header h3 {
    margin: 0;
    font-size: 18px;
    color: #1e293b;
}

.btn-row {
    display: flex;
    gap: 10px;
}

.panel-body {
    padding: 15px;
    background: #f9fafb;
}

.media-box {
    width: 100%;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.validation-strip {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 15px 20px;
    background: #f0f9ff;
    border: 2px solid #3b82f6;
    border-radius: 8px;
    margin: 20px 0;
}

.strip-label {
    font-weight: 600;
    color: #1e40af;
}

.badge-ok {
    background: #10b981;
    color: white;
    padding: 4px 12px;
    border-radius: 4px;
    font-weight: 600;
}

.badge-warn {
    background: #f59e0b;
    color: white;
    padding: 4px 12px;
    border-radius: 4px;
    font-weight: 600;
}

.signoff-card {
    margin-top: 30px;
    padding: 25px;
    border: 2px solid #10b981;
    border-radius: 12px;
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
}

.signoff-card h3 {
    margin: 0 0 15px 0;
    color: #065f46;
}

.signoff-description {
    color: #047857;
    margin-bottom: 15px;
}

.signoff-textarea {
    width: 100%;
    min-height: 80px;
    padding: 12px;
    border: 2px solid #d1d5db;
    border-radius: 8px;
    font-family: inherit;
    font-size: 14px;
    margin-bottom: 15px;
}

.signoff-checkbox {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
    cursor: pointer;
    font-weight: 600;
}

.signoff-checkbox input[type="checkbox"] {
    width: 20px;
    height: 20px;
    cursor: pointer;
}

/* Responsive */
@media (max-width: 768px) {
    .two-col {
        grid-template-columns: 1fr;
    }

    .btn-row {
        flex-direction: column;
    }

    .panel-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }
}
```

---

## 6. FINAL INTEGRATION CHECKLIST

- [ ] Add all endpoints to `web_app.py`
- [ ] Add `render_psd_to_png` method to `ThumbnailService`
- [ ] Add UI section to `index.html`
- [ ] Add JavaScript wiring to `index.html`
- [ ] Add CSS styles to `style.css`
- [ ] Update `/validate-plainly` to set state
- [ ] Test Mode A workflow (Validate → Preview → Sign-off)
- [ ] Test Mode B workflow (Preview → Validate → Sign-off)
- [ ] Test state guards (preview blocked without validation in Mode A)
- [ ] Test sign-off hashing and audit trail
- [ ] Verify responsive design

---

## 7. TESTING SCENARIOS

### Mode A (VALIDATE_BEFORE_PREVIEW=true):
1. Upload files → Try generate previews → **Should block** (no validation yet)
2. Run validation → Pass validation → Generate previews → **Should succeed**
3. View side-by-side → Check checkbox → Approve → **Should succeed**

### Mode B (VALIDATE_BEFORE_PREVIEW=false):
1. Upload files → Generate previews → **Should succeed** (no validation check)
2. View side-by-side → Run validation → Check checkbox → Approve → **Should succeed**

---

## STATUS: Ready for Implementation

All code is provided above. Implementation estimated at 2-3 hours for a developer familiar with the codebase.
