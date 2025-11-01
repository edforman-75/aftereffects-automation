/**
 * Stage 4: Validation Review JavaScript (6-Stage Pipeline)
 *
 * Handles loading and displaying validation results,
 * user interactions for critical issues:
 * - Return to Stage 2 (Matching) to fix issues
 * - Override and proceed to Stage 5 (ExtendScript Generation)
 */

// Global state
let validationData = null;
let jobId = null;

/**
 * Initialize page on load
 */
document.addEventListener('DOMContentLoaded', () => {
    // Extract job_id from URL path: /validate/{job_id}
    const pathParts = window.location.pathname.split('/');
    jobId = pathParts[pathParts.length - 1];

    if (!jobId) {
        showToast('Error: No job ID found', 'error');
        return;
    }

    console.log('Loading validation for job:', jobId);
    loadValidationResults();
});

/**
 * Load validation results from API
 */
async function loadValidationResults() {
    try {
        showLoading(true);

        const response = await fetch(`/api/job/${jobId}/validation-results`);

        if (!response.ok) {
            throw new Error(`Failed to load validation results: ${response.status}`);
        }

        const data = await response.json();
        console.log('Validation data loaded:', data);

        validationData = data;

        // Update UI
        updateJobInfo(data);
        updateSummary(data);
        renderIssues(data);
        updateActionButtons(data);

        showLoading(false);

    } catch (error) {
        console.error('Error loading validation:', error);
        showToast('Failed to load validation results', 'error');
        showLoading(false);
    }
}

/**
 * Update job information bar
 */
function updateJobInfo(data) {
    document.getElementById('job-id-display').textContent = `Job: ${data.job_id}`;
    document.getElementById('client-name').textContent = data.client_name || '-';
    document.getElementById('project-name').textContent = data.project_name || '-';

    if (data.validated_at) {
        const date = new Date(data.validated_at);
        document.getElementById('validated-at').textContent = date.toLocaleString();
    }
}

/**
 * Update validation summary stats
 */
function updateSummary(data) {
    const results = data.validation_results || {};

    const validCount = data.total_matches - (results.critical_issues?.length || 0) - (results.warnings?.length || 0);
    const warningCount = results.warnings?.length || 0;
    const criticalCount = results.critical_issues?.length || 0;

    document.getElementById('valid-count').textContent = validCount;
    document.getElementById('warning-count').textContent = warningCount;
    document.getElementById('critical-count').textContent = criticalCount;
}

/**
 * Render issues by severity
 */
function renderIssues(data) {
    const results = data.validation_results || {};

    // Render critical issues
    renderIssueSection(
        results.critical_issues || [],
        'critical-section',
        'critical-issues-list',
        'critical'
    );

    // Render warnings
    renderIssueSection(
        results.warnings || [],
        'warning-section',
        'warning-issues-list',
        'warning'
    );

    // Render info
    renderIssueSection(
        results.info || [],
        'info-section',
        'info-issues-list',
        'info'
    );
}

/**
 * Render a specific issue section
 */
function renderIssueSection(issues, sectionId, listId, severity) {
    const section = document.getElementById(sectionId);
    const list = document.getElementById(listId);

    if (!issues || issues.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    list.innerHTML = '';

    issues.forEach(issue => {
        const card = createIssueCard(issue, severity);
        list.appendChild(card);
    });
}

/**
 * Create an issue card element
 */
function createIssueCard(issue, severity) {
    const card = document.createElement('div');
    card.className = `issue-card ${severity}`;

    // Header
    const header = document.createElement('div');
    header.className = 'issue-header';

    const title = document.createElement('div');
    title.className = 'issue-title';
    title.textContent = issue.psd_layer || 'Unknown Layer';

    const badge = document.createElement('span');
    badge.className = `issue-badge ${severity}`;
    badge.textContent = severity.toUpperCase();

    header.appendChild(title);
    header.appendChild(badge);
    card.appendChild(header);

    // Message
    const message = document.createElement('div');
    message.className = 'issue-message';
    message.textContent = issue.message || 'No description provided';
    card.appendChild(message);

    // Details
    if (hasDetails(issue)) {
        const details = createIssueDetails(issue);
        card.appendChild(details);
    }

    // Suggestion
    if (issue.suggestion) {
        const suggestion = document.createElement('div');
        suggestion.className = 'issue-suggestion';
        suggestion.textContent = `💡 Suggestion: ${issue.suggestion}`;
        card.appendChild(suggestion);
    }

    return card;
}

/**
 * Check if issue has detail fields
 */
function hasDetails(issue) {
    return issue.psd_dimensions || issue.comp_dimensions ||
           issue.difference_percent !== undefined || issue.scale_percent !== undefined;
}

/**
 * Create issue details grid
 */
function createIssueDetails(issue) {
    const details = document.createElement('div');
    details.className = 'issue-details';

    if (issue.psd_dimensions) {
        details.appendChild(createDetailItem('PSD Dimensions', issue.psd_dimensions));
    }

    if (issue.comp_dimensions) {
        details.appendChild(createDetailItem('Composition', issue.comp_dimensions));
    }

    if (issue.psd_orientation) {
        details.appendChild(createDetailItem('PSD Orientation', issue.psd_orientation));
    }

    if (issue.comp_orientation) {
        details.appendChild(createDetailItem('Comp Orientation', issue.comp_orientation));
    }

    if (issue.difference_percent !== undefined) {
        details.appendChild(createDetailItem('Difference', `${issue.difference_percent}%`));
    }

    if (issue.scale_percent !== undefined) {
        details.appendChild(createDetailItem('Scale', `${issue.scale_percent}%`));
    }

    return details;
}

/**
 * Create a single detail item
 */
function createDetailItem(label, value) {
    const item = document.createElement('div');
    item.className = 'detail-item';

    const labelEl = document.createElement('div');
    labelEl.className = 'detail-label';
    labelEl.textContent = label;

    const valueEl = document.createElement('div');
    valueEl.className = 'detail-value';
    valueEl.textContent = value;

    item.appendChild(labelEl);
    item.appendChild(valueEl);

    return item;
}

/**
 * Update action buttons - Stage 4 is only shown for critical issues
 * Users can either return to fix matches or override and continue
 */
function updateActionButtons(data) {
    const actionButtons = document.getElementById('action-buttons');
    actionButtons.innerHTML = '';

    // Return to Matching button
    const returnBtn = document.createElement('button');
    returnBtn.className = 'btn btn-secondary btn-lg';
    returnBtn.textContent = '← Return to Stage 2 (Matching)';
    returnBtn.onclick = returnToMatching;
    actionButtons.appendChild(returnBtn);

    // Override & Continue button
    const overrideBtn = document.createElement('button');
    overrideBtn.className = 'btn btn-danger btn-lg';
    overrideBtn.textContent = 'Override & Continue to Stage 5 →';
    overrideBtn.onclick = showOverrideModal;
    actionButtons.appendChild(overrideBtn);
}

/**
 * Return to Stage 2 matching to fix issues
 */
async function returnToMatching() {
    if (!confirm('Return to Stage 2 to adjust matches? Validation results will be cleared.')) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch(`/api/job/${jobId}/return-to-matching`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: 'current_user' // TODO: Get from session
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to return to matching: ${response.status}`);
        }

        const data = await response.json();

        showToast('Returning to Stage 2 matching...', 'success');

        // Redirect to matching page
        setTimeout(() => {
            window.location.href = data.redirect_url || `/review-matching/${jobId}`;
        }, 1000);

    } catch (error) {
        console.error('Error returning to matching:', error);
        showToast('Failed to return to matching', 'error');
        showLoading(false);
    }
}

/**
 * Show override modal
 */
function showOverrideModal() {
    const results = validationData.validation_results || {};
    const criticalCount = results.critical_issues?.length || 0;

    document.getElementById('override-issue-count').textContent = criticalCount;
    document.getElementById('override-reason').value = '';

    const modal = document.getElementById('override-modal');
    modal.classList.add('active');
}

/**
 * Close override modal
 */
function closeOverrideModal() {
    const modal = document.getElementById('override-modal');
    modal.classList.remove('active');
}

/**
 * Confirm override and proceed
 */
async function confirmOverride() {
    const reason = document.getElementById('override-reason').value.trim();

    if (!reason) {
        showToast('Please provide a reason for override', 'error');
        return;
    }

    try {
        showLoading(true);
        closeOverrideModal();

        const response = await fetch(`/api/job/${jobId}/override-validation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                override_reason: reason,
                user_id: 'current_user' // TODO: Get from session
            })
        });

        if (!response.ok) {
            throw new Error(`Override failed: ${response.status}`);
        }

        const data = await response.json();

        showToast('Validation overridden. Proceeding to Stage 5...', 'success');

        // Redirect to Stage 5 (ExtendScript Generation)
        setTimeout(() => {
            window.location.href = data.redirect_url || '/dashboard';
        }, 1500);

    } catch (error) {
        console.error('Error overriding validation:', error);
        showToast('Failed to override validation', 'error');
        showLoading(false);
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.add('active');
    } else {
        overlay.classList.remove('active');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = document.createElement('span');
    icon.className = 'toast-icon';
    icon.textContent = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';

    const messageEl = document.createElement('span');
    messageEl.className = 'toast-message';
    messageEl.textContent = message;

    const closeBtn = document.createElement('span');
    closeBtn.className = 'toast-close';
    closeBtn.textContent = '×';
    closeBtn.onclick = () => removeToast(toast);

    toast.appendChild(icon);
    toast.appendChild(messageEl);
    toast.appendChild(closeBtn);

    container.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => removeToast(toast), 4000);
}

/**
 * Remove toast with animation
 */
function removeToast(toast) {
    toast.classList.add('removing');
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

// Close modal on background click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        closeOverrideModal();
    }
});
