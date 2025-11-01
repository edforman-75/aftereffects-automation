/**
 * Stage 4: Validation & Deployment Interface
 *
 * Handles validation results display and deployment to Plainly.
 */

// Global State
let jobId = null;
let jobData = null;
let validationResults = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Get job ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    jobId = urlParams.get('job_id');

    if (!jobId) {
        alert('No job ID provided');
        window.location.href = '/dashboard';
        return;
    }

    // Load data
    loadJobData();
});

/**
 * Load job data from API
 */
async function loadJobData() {
    showLoading(true, 'Loading job data...');

    try {
        // Load job details
        const jobResponse = await fetch(`/api/job/${jobId}`);
        if (!jobResponse.ok) {
            throw new Error('Failed to load job data');
        }

        jobData = await jobResponse.json();

        // Update UI with job info
        updateJobInfo();

        // Load validation results
        await loadValidationResults();

        showLoading(false);
    } catch (error) {
        console.error('Error loading job data:', error);
        alert('Failed to load job data: ' + error.message);
        showLoading(false);
    }
}

/**
 * Update job info display
 */
function updateJobInfo() {
    document.getElementById('job-id-display').textContent = jobData.job_id;
    document.getElementById('client-name').textContent = jobData.client_name || 'N/A';
    document.getElementById('project-name').textContent = jobData.project_name || 'N/A';
    document.getElementById('output-filename').textContent = jobData.output_name || 'N/A';

    // Pre-fill template name
    document.getElementById('template-name').value =
        `${jobData.client_name || 'Unknown'} - ${jobData.project_name || 'Project'}`;
}

/**
 * Load validation results
 */
async function loadValidationResults() {
    try {
        // In production, this would load from:
        // GET /api/job/{jobId}/validation-results

        // For now, generate sample validation results
        generateSampleValidationResults();

        // Render validation UI
        renderValidationResults();
        updateFileInfo();

    } catch (error) {
        console.error('Error loading validation results:', error);
        throw error;
    }
}

/**
 * Generate sample validation results
 */
function generateSampleValidationResults() {
    validationResults = {
        passed: true,
        checks: [
            { name: 'Project Structure', status: 'pass', message: 'Project structure is valid' },
            { name: 'Layer Names', status: 'pass', message: 'All layer names are valid' },
            { name: 'Comp Duration', status: 'pass', message: 'Composition duration is acceptable' },
            { name: 'Missing Fonts', status: 'pass', message: 'No missing fonts detected' },
            { name: 'Missing Effects', status: 'pass', message: 'All effects are available' },
            { name: 'Expressions', status: 'pass', message: 'Expressions are valid' },
            { name: 'Render Settings', status: 'warning', message: 'Output module uses default settings' }
        ],
        errors: [],
        warnings: [
            'Output module uses default settings - consider customizing for better quality'
        ],
        file_size: '45.2 MB',
        created_at: new Date().toISOString()
    };
}

/**
 * Render validation results
 */
function renderValidationResults() {
    const passed = validationResults.checks.filter(c => c.status === 'pass').length;
    const warnings = validationResults.checks.filter(c => c.status === 'warning').length;
    const errors = validationResults.checks.filter(c => c.status === 'fail').length;

    // Update summary
    document.getElementById('checks-passed').textContent = passed;
    document.getElementById('warnings-count').textContent = warnings;
    document.getElementById('errors-count').textContent = errors;

    // Update validation status badge
    const statusBadge = document.getElementById('validation-status');
    if (validationResults.passed) {
        statusBadge.textContent = 'Passed';
        statusBadge.className = 'status-badge';
    } else {
        statusBadge.textContent = 'Failed';
        statusBadge.className = 'status-badge failed';
    }

    // Render checks list
    const checksList = document.getElementById('checks-list');
    checksList.innerHTML = '';

    validationResults.checks.forEach(check => {
        const item = document.createElement('div');
        item.className = 'check-item';

        let icon = '';
        let iconClass = '';

        if (check.status === 'pass') {
            icon = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            iconClass = 'pass';
        } else if (check.status === 'warning') {
            icon = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
            iconClass = 'warning';
        } else {
            icon = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
            iconClass = 'fail';
        }

        item.innerHTML = `
            <div class="check-icon ${iconClass}">
                ${icon}
            </div>
            <div class="check-content">
                <div class="check-name">${check.name}</div>
                <div class="check-message">${check.message}</div>
            </div>
        `;

        checksList.appendChild(item);
    });

    // Show/hide issues section
    if (errors > 0 || warnings > 0) {
        const issuesSection = document.getElementById('issues-section');
        issuesSection.style.display = 'block';

        const issuesList = document.getElementById('issues-list');
        issuesList.innerHTML = '';

        validationResults.warnings.forEach(warning => {
            const issue = document.createElement('div');
            issue.className = 'issue-item';
            issue.innerHTML = `
                <div class="issue-title">⚠️ Warning</div>
                <div class="issue-description">${warning}</div>
            `;
            issuesList.appendChild(issue);
        });
    }

    // Show/hide sign-off button if there are errors
    if (errors > 0) {
        document.getElementById('sign-off-btn').style.display = 'inline-block';
    }
}

/**
 * Update file info
 */
function updateFileInfo() {
    document.getElementById('file-size').textContent =
        `Size: ${validationResults.file_size || '-'}`;

    const date = new Date(validationResults.created_at);
    document.getElementById('file-date').textContent =
        `Created: ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

/**
 * Run validation
 */
async function runValidation() {
    showLoading(true, 'Running validation...');

    try {
        // In production, this would call:
        // POST /api/job/{jobId}/validate

        // Simulate validation time
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Reload results
        await loadValidationResults();

        showLoading(false);

        alert('Validation complete!');

    } catch (error) {
        console.error('Error running validation:', error);
        alert('Failed to run validation: ' + error.message);
        showLoading(false);
    }
}

/**
 * Download final AEP file
 */
function downloadFinalAEP() {
    // In production, this would:
    // window.location.href = `/api/job/${jobId}/download-aep`;

    alert('Download would start here. In production, this downloads the final AEP file.');
    console.log('Downloading final AEP for job:', jobId);
}

/**
 * Deploy to Plainly
 */
function deployToPlainly() {
    const templateName = document.getElementById('template-name').value.trim();

    if (!templateName) {
        alert('Please enter a template name');
        return;
    }

    // Open confirmation modal
    document.getElementById('deploy-template-name').textContent = templateName;
    document.getElementById('deploy-project-name').textContent = jobData.project_name || 'N/A';
    document.getElementById('deploy-auto-publish').textContent =
        document.getElementById('auto-publish').checked ? 'Yes' : 'No';

    document.getElementById('deploy-modal').classList.add('active');
}

/**
 * Close deploy modal
 */
function closeDeployModal() {
    document.getElementById('deploy-modal').classList.remove('active');
}

/**
 * Confirm deployment
 */
async function confirmDeploy() {
    closeDeployModal();
    showLoading(true, 'Deploying to Plainly...');

    try {
        const templateName = document.getElementById('template-name').value.trim();
        const description = document.getElementById('template-description').value.trim();
        const autoPublish = document.getElementById('auto-publish').checked;

        // In production, this would call:
        // POST /api/job/{jobId}/deploy
        // with { template_name, description, auto_publish }

        // Simulate deployment time
        await new Promise(resolve => setTimeout(resolve, 3000));

        showLoading(false);

        alert('Successfully deployed to Plainly!');

        // Return to dashboard
        window.location.href = '/dashboard';

    } catch (error) {
        console.error('Error deploying:', error);
        alert('Failed to deploy: ' + error.message);
        showLoading(false);
    }
}

/**
 * Sign off with errors
 */
async function signOffWithErrors() {
    const proceed = confirm(
        'This job has validation errors. Are you sure you want to sign off and mark it as complete? ' +
        'The errors will be logged but the job will be marked as completed.'
    );

    if (!proceed) return;

    showLoading(true, 'Signing off...');

    try {
        // In production, this would call:
        // POST /api/job/{jobId}/sign-off-with-errors

        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));

        showLoading(false);

        alert('Job signed off with errors. Marked as completed with warnings.');

        // Return to dashboard
        window.location.href = '/dashboard';

    } catch (error) {
        console.error('Error signing off:', error);
        alert('Failed to sign off: ' + error.message);
        showLoading(false);
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show, message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    const messageEl = document.getElementById('loading-message');

    if (show) {
        messageEl.textContent = message;
        overlay.classList.add('active');
    } else {
        overlay.classList.remove('active');
    }
}

/**
 * Handle escape key to close modals
 */
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const deployModal = document.getElementById('deploy-modal');
        if (deployModal.classList.contains('active')) {
            closeDeployModal();
        }
    }
});
