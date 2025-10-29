/**
 * Project Dashboard - JavaScript
 * Manages individual project view and graphics operations
 */

let currentProject = null;
let currentUser = null;
let availableTemplates = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Get project ID from URL or data attribute
    const projectId = document.getElementById('project-dashboard')?.dataset.projectId;

    if (!projectId) {
        showError('Project ID not found');
        return;
    }

    // Initialize user
    currentUser = getCurrentUser();
    updateUserDisplay();

    // Load templates
    loadTemplates();

    // Load project
    loadProject(projectId);

    // Setup event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Add graphic button
    const addGraphicBtn = document.getElementById('add-graphic-btn');
    if (addGraphicBtn) {
        addGraphicBtn.addEventListener('click', showAddGraphicModal);
    }

    // Batch process button
    const batchProcessBtn = document.getElementById('batch-process-btn');
    if (batchProcessBtn) {
        batchProcessBtn.addEventListener('click', handleBatchProcess);
    }

    // Bulk approve button
    const bulkApproveBtn = document.getElementById('bulk-approve-btn');
    if (bulkApproveBtn) {
        bulkApproveBtn.addEventListener('click', handleBulkApprove);
    }

    // Export project button
    const exportBtn = document.getElementById('export-project-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportProject);
    }

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filter = this.dataset.filter;
            applyFilter(filter);
        });
    });

    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });

    // Add graphic form
    const addGraphicForm = document.getElementById('add-graphic-form');
    if (addGraphicForm) {
        addGraphicForm.addEventListener('submit', handleAddGraphic);
    }

    // PSD file upload
    const psdUpload = document.getElementById('psd-upload');
    if (psdUpload) {
        psdUpload.addEventListener('change', handlePSDUpload);
    }

    // Template select change
    const templateSelect = document.getElementById('template-select');
    if (templateSelect) {
        templateSelect.addEventListener('change', updateTemplatePreview);
    }

    // Change user button
    const changeUserBtn = document.getElementById('change-user-btn');
    if (changeUserBtn) {
        changeUserBtn.addEventListener('click', changeUser);
    }

    // Back to projects button
    const backBtn = document.getElementById('back-to-projects-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            window.location.href = '/projects-page';
        });
    }
}

// User management
function getCurrentUser() {
    let user = localStorage.getItem('ae_automation_user');

    if (!user) {
        user = prompt('Enter your name or email for audit tracking:');
        if (user && user.trim()) {
            user = user.trim();
            localStorage.setItem('ae_automation_user', user);
        } else {
            return null;
        }
    }

    return user;
}

function changeUser() {
    const newUser = prompt('Enter your name or email:', currentUser || '');
    if (newUser && newUser.trim()) {
        currentUser = newUser.trim();
        localStorage.setItem('ae_automation_user', currentUser);
        updateUserDisplay();
        showMessage('User changed to: ' + currentUser, 'success');
    }
}

function updateUserDisplay() {
    const userDisplay = document.getElementById('current-user-display');
    if (userDisplay && currentUser) {
        userDisplay.textContent = currentUser;
    }
}

// Load available templates
async function loadTemplates() {
    try {
        const response = await fetch('/api/templates');
        const data = await response.json();

        if (data.success) {
            availableTemplates = data.templates;
            console.log(`Loaded ${availableTemplates.length} templates`);
        } else {
            console.error('Failed to load templates:', data.error);
            availableTemplates = [];
        }
    } catch (error) {
        console.error('Error loading templates:', error);
        availableTemplates = [];
    }
}

// Load project details
async function loadProject(projectId) {
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error-message');

    try {
        // Show loading
        if (loadingDiv) loadingDiv.style.display = 'block';
        if (errorDiv) errorDiv.style.display = 'none';

        const response = await fetch(`/api/projects/${projectId}`);
        const data = await response.json();

        if (data.success) {
            currentProject = data.project;
            displayProjectDetails();
            loadGraphics();
            loadHardCardInfo();  // Load Hard Card information
        } else {
            showError(data.error || 'Failed to load project');
        }
    } catch (error) {
        console.error('Failed to load project:', error);
        showError('Error loading project');
    } finally {
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
}

// Display project header details
function displayProjectDetails() {
    if (!currentProject) return;

    // Project name
    const nameElement = document.getElementById('project-name');
    if (nameElement) {
        nameElement.textContent = currentProject.name;
    }

    // Client
    const clientElement = document.getElementById('project-client');
    if (clientElement && currentProject.client) {
        clientElement.textContent = currentProject.client;
        clientElement.style.display = 'block';
    }

    // Description
    const descElement = document.getElementById('project-description');
    if (descElement && currentProject.description) {
        descElement.textContent = currentProject.description;
        descElement.style.display = 'block';
    }

    // Stats
    displayProjectStats();

    // Update export button state
    updateExportButton();
}

// Display project statistics
function displayProjectStats() {
    if (!currentProject || !currentProject.stats) return;

    const stats = currentProject.stats;

    updateStatValue('total-graphics', stats.total_graphics || 0);
    updateStatValue('completed-graphics', stats.completed || 0);
    updateStatValue('needs-review-graphics', stats.needs_review || 0);
    updateStatValue('approved-graphics', stats.approved || 0);

    // Progress bar
    const progressBar = document.getElementById('project-progress-bar');
    if (progressBar && stats.total_graphics > 0) {
        const completionRate = Math.round((stats.completed / stats.total_graphics) * 100);
        progressBar.style.width = completionRate + '%';
        progressBar.textContent = completionRate + '%';
    }
}

function updateStatValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

// Load and display graphics
async function loadGraphics() {
    if (!currentProject) return;

    const graphicsGrid = document.getElementById('graphics-grid');
    const emptyState = document.getElementById('empty-state');

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/graphics`);
        const data = await response.json();

        if (data.success) {
            if (data.graphics && data.graphics.length > 0) {
                displayGraphics(data.graphics);
                if (emptyState) emptyState.style.display = 'none';
                if (graphicsGrid) graphicsGrid.style.display = 'grid';
            } else {
                if (emptyState) emptyState.style.display = 'block';
                if (graphicsGrid) graphicsGrid.style.display = 'none';
            }
            // Update export button after loading graphics
            updateExportButton();
        } else {
            showError(data.error || 'Failed to load graphics');
        }
    } catch (error) {
        console.error('Failed to load graphics:', error);
        showError('Error loading graphics');
    }
}

// Display graphics in grid
function displayGraphics(graphics) {
    const graphicsGrid = document.getElementById('graphics-grid');
    if (!graphicsGrid) return;

    graphicsGrid.innerHTML = graphics.map(graphic => createGraphicCard(graphic)).join('');

    // Add event listeners to cards
    setupGraphicCardListeners();
}

// Create HTML for a single graphic card
function createGraphicCard(graphic) {
    const statusClass = getStatusClass(graphic.status);
    const statusLabel = getStatusLabel(graphic.status);

    const confidenceScore = graphic.confidence_score !== null && graphic.confidence_score !== undefined
        ? Math.round(graphic.confidence_score * 100)
        : null;

    const hasConflicts = graphic.conflicts && graphic.conflicts.length > 0;
    const conflictCount = hasConflicts ? graphic.conflicts.length : 0;

    return `
        <div class="graphic-card ${statusClass}" data-graphic-id="${graphic.id}">
            <div class="graphic-card-header">
                <h4 class="graphic-name">${escapeHtml(graphic.name)}</h4>
                <span class="graphic-status ${statusClass}">${statusLabel}</span>
            </div>

            ${graphic.template_name ? `<p class="template-name">Template: ${escapeHtml(graphic.template_name)}</p>` : ''}

            ${confidenceScore !== null ? `
                <div class="confidence-meter">
                    <div class="confidence-bar" style="width: ${confidenceScore}%; background-color: ${getConfidenceColor(confidenceScore)}"></div>
                    <span class="confidence-text">${confidenceScore}% confidence</span>
                </div>
            ` : ''}

            ${hasConflicts ? `
                <div class="conflicts-warning">
                    <span>⚠️ ${conflictCount} conflict${conflictCount > 1 ? 's' : ''}</span>
                </div>
            ` : ''}

            ${graphic.has_expressions ? `
                <div class="expression-stats" style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span class="badge bg-info" style="font-size: 0.75rem;">
                            <i class="fas fa-code"></i> ${graphic.expression_count || 0} Expressions
                        </span>
                        <span class="badge bg-success" style="font-size: 0.75rem;">
                            ${Math.round((graphic.expression_confidence || 0) * 100)}% Confidence
                        </span>
                    </div>
                </div>
            ` : graphic.status === 'complete' ? `
                <div class="expression-stats" style="margin-top: 8px;">
                    <span class="badge bg-secondary" style="font-size: 0.75rem;">
                        <i class="fas fa-file-alt"></i> Static Template
                    </span>
                </div>
            ` : ''}

            ${graphic.approved ? `
                <div class="approval-badge">
                    ✓ Approved by ${escapeHtml(graphic.approved_by || 'Unknown')}
                    <br>
                    <small>${new Date(graphic.approved_at).toLocaleString()}</small>
                </div>
            ` : ''}

            <div class="graphic-actions">
                ${!graphic.approved ? `
                    <button class="btn btn-sm btn-approve" data-action="approve">Approve</button>
                ` : `
                    <button class="btn btn-sm btn-unapprove" data-action="unapprove">Unapprove</button>
                `}
                <button class="btn btn-sm btn-view" data-action="view">View Details</button>
                <button class="btn btn-sm btn-audit" data-action="audit">Audit Log</button>
                ${graphic.has_expressions ? `
                    <button class="btn btn-sm btn-outline-info" data-action="expressions">
                        <i class="fas fa-code"></i> Expressions
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

// Setup event listeners for graphic cards
function setupGraphicCardListeners() {
    document.querySelectorAll('.graphic-card').forEach(card => {
        const graphicId = card.dataset.graphicId;

        card.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.stopPropagation();
                const action = this.dataset.action;

                switch (action) {
                    case 'approve':
                        await handleApproveGraphic(graphicId);
                        break;
                    case 'unapprove':
                        await handleUnapproveGraphic(graphicId);
                        break;
                    case 'view':
                        await showGraphicDetails(graphicId);
                        break;
                    case 'audit':
                        await showAuditLog(graphicId);
                        break;
                    case 'expressions':
                        await showExpressionInfo(graphicId);
                        break;
                }
            });
        });
    });
}

// Handle approve graphic
async function handleApproveGraphic(graphicId) {
    if (!currentUser) {
        showError('Please set your user identity first');
        changeUser();
        return;
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/graphics/${graphicId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                approved_by: currentUser
            })
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Graphic approved successfully', 'success');
            await loadProject(currentProject.id);
        } else {
            showError(data.error || 'Failed to approve graphic');
        }
    } catch (error) {
        console.error('Failed to approve graphic:', error);
        showError('Error approving graphic');
    }
}

// Handle unapprove graphic
async function handleUnapproveGraphic(graphicId) {
    if (!currentUser) {
        showError('Please set your user identity first');
        changeUser();
        return;
    }

    if (!confirm('Are you sure you want to unapprove this graphic? It will be unlocked for editing.')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/graphics/${graphicId}/unapprove`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                unapproved_by: currentUser
            })
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Graphic unapproved successfully', 'success');
            await loadProject(currentProject.id);
        } else {
            showError(data.error || 'Failed to unapprove graphic');
        }
    } catch (error) {
        console.error('Failed to unapprove graphic:', error);
        showError('Error unapproving graphic');
    }
}

// Show graphic details modal
async function showGraphicDetails(graphicId) {
    // TODO: Implement detailed view modal
    showMessage('Graphic details view coming soon', 'info');
}

// Show audit log modal
async function showAuditLog(graphicId) {
    try {
        const response = await fetch(`/api/projects/${currentProject.id}/graphics/${graphicId}/audit-log`);
        const data = await response.json();

        if (data.success) {
            displayAuditLogModal(data);
        } else {
            showError(data.error || 'Failed to load audit log');
        }
    } catch (error) {
        console.error('Failed to load audit log:', error);
        showError('Error loading audit log');
    }
}

// Display audit log in modal
function displayAuditLogModal(auditData) {
    const modal = document.getElementById('audit-log-modal');
    if (!modal) return;

    const graphicName = document.getElementById('audit-graphic-name');
    const auditContent = document.getElementById('audit-log-content');

    if (graphicName) {
        graphicName.textContent = auditData.graphic_name || 'Graphic';
    }

    if (auditContent) {
        if (auditData.audit_log && auditData.audit_log.length > 0) {
            auditContent.innerHTML = auditData.audit_log.map(entry => `
                <div class="audit-entry">
                    <div class="audit-timestamp">${new Date(entry.timestamp).toLocaleString()}</div>
                    <div class="audit-action">${escapeHtml(entry.action)}</div>
                    <div class="audit-user">By: ${escapeHtml(entry.user)}</div>
                    ${entry.details ? `<div class="audit-details"><pre>${JSON.stringify(entry.details, null, 2)}</pre></div>` : ''}
                </div>
            `).join('');
        } else {
            auditContent.innerHTML = '<p>No audit log entries</p>';
        }
    }

    modal.style.display = 'flex';
}

// Handle batch processing
async function handleBatchProcess() {
    if (!currentUser) {
        showError('Please set your user identity first');
        changeUser();
        return;
    }

    if (!confirm('Start batch processing for all ready graphics in this project?')) {
        return;
    }

    const batchBtn = document.getElementById('batch-process-btn');
    if (batchBtn) {
        batchBtn.disabled = true;
        batchBtn.textContent = 'Processing...';
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/process-batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user: currentUser,
                auto_process_threshold: 0.85,
                require_manual_review: false
            })
        });

        const data = await response.json();

        if (data.success) {
            const results = data.batch_results;
            showMessage(
                `Batch complete: ${results.completed} completed, ${results.needs_review} need review, ${results.failed} failed`,
                'success'
            );
            await loadProject(currentProject.id);
        } else {
            showError(data.error || 'Batch processing failed');
        }
    } catch (error) {
        console.error('Batch processing failed:', error);
        showError('Error during batch processing');
    } finally {
        if (batchBtn) {
            batchBtn.disabled = false;
            batchBtn.textContent = 'Batch Process';
        }
    }
}

// Handle bulk approve
async function handleBulkApprove() {
    if (!currentUser) {
        showError('Please set your user identity first');
        changeUser();
        return;
    }

    // Get all completed graphics that aren't approved
    const graphicsToApprove = currentProject.graphics.filter(g =>
        g.status === 'complete' && !g.approved
    );

    if (graphicsToApprove.length === 0) {
        showMessage('No graphics ready for approval', 'info');
        return;
    }

    if (!confirm(`Approve ${graphicsToApprove.length} completed graphic(s)?`)) {
        return;
    }

    let approvedCount = 0;
    let failedCount = 0;

    for (const graphic of graphicsToApprove) {
        try {
            const response = await fetch(`/api/projects/${currentProject.id}/graphics/${graphic.id}/approve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    approved_by: currentUser
                })
            });

            const data = await response.json();

            if (data.success) {
                approvedCount++;
            } else {
                failedCount++;
            }
        } catch (error) {
            console.error('Failed to approve graphic:', error);
            failedCount++;
        }
    }

    showMessage(`Bulk approval complete: ${approvedCount} approved, ${failedCount} failed`, 'success');
    await loadProject(currentProject.id);
}

// Export project
async function exportProject() {
    const user = getCurrentUser();
    if (!user) {
        showError('Please set your user identity first');
        changeUser();
        return;
    }

    // Check if all graphics are approved
    const approvedGraphics = currentProject.graphics.filter(g => g.approved);
    const unapprovedCount = currentProject.graphics.length - approvedGraphics.length;

    if (unapprovedCount > 0) {
        if (!confirm(`${unapprovedCount} graphic(s) are not approved and will not be included in the export. Continue?`)) {
            return;
        }
    }

    if (approvedGraphics.length === 0) {
        showError('No approved graphics to export');
        return;
    }

    const exportBtn = document.getElementById('export-project-btn');
    if (exportBtn) {
        exportBtn.disabled = true;
        exportBtn.textContent = 'Exporting...';
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user: user
            })
        });

        const data = await response.json();

        if (data.success) {
            showExportDetailsModal(data);
        } else {
            showError(data.error || 'Export failed');
        }
    } catch (error) {
        console.error('Export failed:', error);
        showError('Error during export');
    } finally {
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.textContent = '📦 Export All';
        }
    }
}

// Show export details modal
function showExportDetailsModal(exportData) {
    const modal = document.getElementById('export-success-modal');
    if (!modal) return;

    // Update modal content
    const filename = document.getElementById('export-filename');
    const filesize = document.getElementById('export-filesize');
    const graphicsCount = document.getElementById('export-graphics-count');
    const downloadLink = document.getElementById('export-download-link');

    if (filename) {
        filename.textContent = exportData.zip_filename;
    }

    if (filesize) {
        const sizeMB = (exportData.file_size / (1024 * 1024)).toFixed(2);
        filesize.textContent = `${sizeMB} MB`;
    }

    if (graphicsCount) {
        graphicsCount.textContent = exportData.graphics_count;
    }

    if (downloadLink) {
        downloadLink.href = `/exports/${exportData.zip_filename}`;
        downloadLink.download = exportData.zip_filename;
    }

    modal.style.display = 'flex';
}

// Update export button state based on approved graphics
function updateExportButton() {
    const exportBtn = document.getElementById('export-project-btn');
    if (!exportBtn || !currentProject) return;

    const approvedCount = currentProject.graphics.filter(g => g.approved).length;

    if (approvedCount > 0) {
        exportBtn.disabled = false;
        exportBtn.title = `Export ${approvedCount} approved graphic(s)`;
    } else {
        exportBtn.disabled = true;
        exportBtn.title = 'No approved graphics to export';
    }
}

// Show add graphic modal
function showAddGraphicModal() {
    const modal = document.getElementById('add-graphic-modal');
    if (modal) {
        // Populate template dropdown
        const templateSelect = document.getElementById('template-select');
        if (templateSelect) {
            templateSelect.innerHTML = '<option value="">Select template...</option>' +
                availableTemplates.map(template =>
                    `<option value="${escapeHtml(template.path)}">${escapeHtml(template.name)}</option>`
                ).join('');
        }
        modal.style.display = 'flex';
    }
}

// Handle PSD file upload
async function handlePSDUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload-file', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // Store uploaded file path
            document.getElementById('add-graphic-form').dataset.psdPath = data.file_path;
            showMessage('PSD file uploaded successfully', 'success');
        } else {
            showError(data.error || 'Failed to upload PSD file');
        }
    } catch (error) {
        console.error('Failed to upload PSD:', error);
        showError('Error uploading PSD file');
    }
}

// Handle add graphic form submission
async function handleAddGraphic(e) {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');

    const graphicName = form.querySelector('#graphic-name').value.trim();
    const templateSelect = form.querySelector('#template-select');
    const psdPath = form.dataset.psdPath;

    if (!graphicName) {
        showError('Graphic name is required');
        return;
    }

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';

        // Create graphic
        const response = await fetch(`/api/projects/${currentProject.id}/graphics`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: graphicName,
                psd_path: psdPath || null
            })
        });

        const data = await response.json();

        if (data.success) {
            const graphicId = data.graphic.id;

            // If template is selected, update graphic with template
            if (templateSelect && templateSelect.value) {
                await fetch(`/api/projects/${currentProject.id}/graphics/${graphicId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        user: currentUser || 'system',
                        updates: {
                            template_path: templateSelect.value,
                            template_name: templateSelect.selectedOptions[0].text,
                            status: 'ready_for_processing'
                        }
                    })
                });
            }

            showMessage('Graphic created successfully', 'success');

            // Close modal and reset form
            const modal = document.getElementById('add-graphic-modal');
            if (modal) modal.style.display = 'none';
            form.reset();
            delete form.dataset.psdPath;

            // Reload project
            await loadProject(currentProject.id);
        } else {
            showError(data.error || 'Failed to create graphic');
        }
    } catch (error) {
        console.error('Failed to create graphic:', error);
        showError('Error creating graphic');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Graphic';
    }
}

// Apply filter to graphics display
function applyFilter(filter) {
    const cards = document.querySelectorAll('.graphic-card');

    // Update filter button states
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.dataset.filter === filter) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Filter cards
    cards.forEach(card => {
        if (filter === 'all') {
            card.style.display = '';
        } else {
            if (card.classList.contains(filter)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        }
    });
}

// Utility functions
function getStatusClass(status) {
    const statusMap = {
        'not_started': 'status-not-started',
        'ready_for_processing': 'status-ready',
        'processing': 'status-processing',
        'complete': 'status-complete',
        'needs_review': 'status-needs-review',
        'error': 'status-error'
    };
    return statusMap[status] || '';
}

function getStatusLabel(status) {
    const labelMap = {
        'not_started': 'Not Started',
        'ready_for_processing': 'Ready',
        'processing': 'Processing',
        'complete': 'Complete',
        'needs_review': 'Needs Review',
        'error': 'Error'
    };
    return labelMap[status] || status;
}

function getConfidenceColor(score) {
    if (score >= 85) return '#4CAF50'; // Green
    if (score >= 70) return '#FF9800'; // Orange
    return '#F44336'; // Red
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : '#2196F3'};
        color: white;
        border-radius: 4px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(messageDiv);
        }, 300);
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateTemplatePreview() {
    // TODO: Show template preview when selected
}

// Expression System Functions

async function showExpressionInfo(graphicId) {
    try {
        const response = await fetch(`/api/projects/${currentProject.id}/graphics/${graphicId}/expression-recommendations`);
        const data = await response.json();

        if (!data.success) {
            showMessage(data.error || 'Failed to load expression information', 'error');
            return;
        }

        const recommendations = data.recommendations || [];
        const stats = data.statistics || {};

        // Create modal
        const modalHtml = `
            <div class="modal fade" id="expressionInfoModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-code"></i> Expression Information
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Statistics -->
                            <div class="alert alert-info">
                                <h6><i class="fas fa-chart-bar"></i> Expression Statistics</h6>
                                <div class="row mt-2">
                                    <div class="col-md-3">
                                        <strong>Applied:</strong> ${stats.applied_count || 0}
                                    </div>
                                    <div class="col-md-3">
                                        <strong>Skipped:</strong> ${stats.skipped_count || 0}
                                    </div>
                                    <div class="col-md-3">
                                        <strong>Avg. Confidence:</strong> ${Math.round((stats.avg_confidence || 0) * 100)}%
                                    </div>
                                    <div class="col-md-3">
                                        <strong>Total:</strong> ${recommendations.length}
                                    </div>
                                </div>
                            </div>

                            <!-- Recommendations Table -->
                            <h6><i class="fas fa-lightbulb"></i> Expression Recommendations</h6>
                            ${recommendations.length > 0 ? `
                                <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                                    <table class="table table-sm table-hover">
                                        <thead class="table-light sticky-top">
                                            <tr>
                                                <th>Layer</th>
                                                <th>Type</th>
                                                <th>Variable</th>
                                                <th>Confidence</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${recommendations.map(rec => {
                                                const confidencePct = Math.round((rec.confidence || 0) * 100);
                                                const confidenceBadge = getConfidenceBadge(rec.confidence);
                                                const statusBadge = rec.applied ?
                                                    '<span class="badge bg-success">Applied</span>' :
                                                    '<span class="badge bg-secondary">Skipped</span>';

                                                return `
                                                    <tr>
                                                        <td>${escapeHtml(rec.layer_name || 'Unknown')}</td>
                                                        <td><span class="badge bg-light text-dark">${escapeHtml(rec.layer_type || 'N/A')}</span></td>
                                                        <td><code>${escapeHtml(rec.variable || 'N/A')}</code></td>
                                                        <td>
                                                            ${confidenceBadge}
                                                            <small class="text-muted">${confidencePct}%</small>
                                                        </td>
                                                        <td>${statusBadge}</td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : `
                                <p class="text-muted">No expression recommendations available.</p>
                            `}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('expressionInfoModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('expressionInfoModal'));
        modal.show();

        // Cleanup on close
        document.getElementById('expressionInfoModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });

    } catch (error) {
        console.error('Error loading expression info:', error);
        showMessage('Failed to load expression information', 'error');
    }
}

function getConfidenceBadge(confidence) {
    if (confidence >= 0.9) {
        return '<span class="badge bg-success">High</span>';
    } else if (confidence >= 0.75) {
        return '<span class="badge bg-info">Good</span>';
    } else if (confidence >= 0.6) {
        return '<span class="badge bg-warning">Medium</span>';
    } else {
        return '<span class="badge bg-danger">Low</span>';
    }
}

async function loadHardCardInfo() {
    try {
        const response = await fetch(`/api/projects/${currentProject.id}/expression-stats`);
        const data = await response.json();

        if (!data.success) {
            console.warn('Hard Card not available:', data.error);
            return;
        }

        const stats = data.statistics || {};

        // Only show if Hard Card exists
        if (!stats.has_hard_card) {
            return;
        }

        // Create Hard Card panel
        const panelHtml = `
            <div class="card mt-3" id="hardCardPanel">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-cube"></i> Hard Card Parametrization System
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-value">${stats.hard_card_variables || 185}</div>
                                <div class="stat-label">Variables</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-value">${stats.graphics_with_expressions || 0} / ${stats.total_graphics || 0}</div>
                                <div class="stat-label">Graphics w/ Expressions</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-value">${stats.total_expressions || 0}</div>
                                <div class="stat-label">Total Expressions</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-value">${Math.round((stats.average_confidence || 0) * 100)}%</div>
                                <div class="stat-label">Avg. Confidence</div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-primary" onclick="viewHardCardVariables()">
                            <i class="fas fa-list"></i> View Variables
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="downloadHardCard()">
                            <i class="fas fa-download"></i> Download Hard Card
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Add panel after project header
        const projectHeader = document.querySelector('.card.mb-4');
        if (projectHeader) {
            // Remove existing panel if present
            const existingPanel = document.getElementById('hardCardPanel');
            if (existingPanel) {
                existingPanel.remove();
            }

            projectHeader.insertAdjacentHTML('afterend', panelHtml);
        }

    } catch (error) {
        console.error('Error loading Hard Card info:', error);
    }
}

async function viewHardCardVariables() {
    try {
        const response = await fetch('/api/hard-card/info');
        const data = await response.json();

        if (!data.success) {
            showMessage(data.error || 'Failed to load Hard Card variables', 'error');
            return;
        }

        const hardCard = data.hard_card || {};
        const categories = hardCard.variables_by_category || {};

        // Create modal
        const modalHtml = `
            <div class="modal fade" id="hardCardVariablesModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-cube"></i> Hard Card Variables (${hardCard.total_variables || 0})
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                            <p class="text-muted mb-3">
                                Total: ${hardCard.total_variables || 0} variables across ${Object.keys(categories).length} categories
                            </p>
                            ${Object.entries(categories).sort().map(([category, vars]) => {
                                if (!vars || vars.length === 0) return '';

                                return `
                                    <div class="mb-4">
                                        <h6 class="text-uppercase text-muted mb-3">
                                            <i class="fas fa-folder"></i> ${category} (${vars.length})
                                        </h6>
                                        <div class="table-responsive">
                                            <table class="table table-sm table-hover">
                                                <thead class="table-light">
                                                    <tr>
                                                        <th>Variable Name</th>
                                                        <th>Hard Card Name</th>
                                                        <th>Default Value</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    ${vars.map(v => `
                                                        <tr>
                                                            <td><code>${escapeHtml(v.display_name || v.name)}</code></td>
                                                            <td><small class="text-muted">${escapeHtml(v.name)}</small></td>
                                                            <td><small>${escapeHtml(v.default_value || 'N/A')}</small></td>
                                                        </tr>
                                                    `).join('')}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="downloadHardCard()">
                                <i class="fas fa-download"></i> Download Hard Card
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('hardCardVariablesModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('hardCardVariablesModal'));
        modal.show();

        // Cleanup on close
        document.getElementById('hardCardVariablesModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });

    } catch (error) {
        console.error('Error loading Hard Card variables:', error);
        showMessage('Failed to load Hard Card variables', 'error');
    }
}

function downloadHardCard() {
    window.location.href = '/api/hard-card/download';
    showMessage('Downloading Hard Card...', 'success');
}

// ============================================================================
// ASPECT RATIO REVIEW SYSTEM
// ============================================================================

// Track selected transformation method
let selectedTransformMethod = null;

async function showAspectRatioReview(graphicId) {
    try {
        showLoading('Loading aspect ratio review...');

        // Fetch review data
        const response = await fetch(
            `/api/projects/${currentProject.id}/graphics/${graphicId}/aspect-ratio-review`
        );
        const result = await response.json();

        hideLoading();

        if (!result.success) {
            showMessage(result.error || 'Failed to load aspect ratio review', 'error');
            return;
        }

        // Build modal HTML
        const modalHtml = buildAspectRatioModal(graphicId, result);

        // Remove existing modal
        const existingModal = document.getElementById('aspectRatioModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add and show modal
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('aspectRatioModal'));
        modal.show();

        // Reset selection
        selectedTransformMethod = null;

        // Cleanup on close
        document.getElementById('aspectRatioModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });

    } catch (error) {
        hideLoading();
        console.error('Aspect ratio review error:', error);
        showMessage('Failed to load aspect ratio review', 'error');
    }
}

function buildAspectRatioModal(graphicId, data) {
    const psdDims = data.psd_dimensions;
    const aepxDims = data.aepx_dimensions;
    const ratioDiff = (data.ratio_difference * 100).toFixed(1);

    // Determine if cross-category
    const isCrossCategory = data.psd_category !== data.aepx_category;
    const categoryText = isCrossCategory
        ? `<span class="text-danger"><strong>Cross-Category:</strong> ${data.psd_category} → ${data.aepx_category}</span>`
        : `<span class="text-success">Same category: ${data.psd_category}</span>`;

    return `
        <div class="modal fade" id="aspectRatioModal" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle"></i>
                            Aspect Ratio Review Required
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>

                    <div class="modal-body">
                        <!-- Mismatch Details -->
                        <div class="alert alert-info">
                            <h6><strong>Dimension Mismatch Detected</strong></h6>
                            <div class="row">
                                <div class="col-md-4">
                                    <strong>PSD:</strong> ${psdDims[0]} × ${psdDims[1]}<br>
                                    <small class="text-muted">(${data.psd_category})</small>
                                </div>
                                <div class="col-md-4">
                                    <strong>Template:</strong> ${aepxDims[0]} × ${aepxDims[1]}<br>
                                    <small class="text-muted">(${data.aepx_category})</small>
                                </div>
                                <div class="col-md-4">
                                    <strong>Difference:</strong> ${ratioDiff}%<br>
                                    ${categoryText}
                                </div>
                            </div>
                            <div class="mt-2">
                                <strong>AI Analysis:</strong> ${data.reasoning}
                            </div>
                        </div>

                        <!-- Visual Previews -->
                        <h6 class="mb-3">
                            <i class="fas fa-images"></i>
                            Choose Your Preferred Transformation:
                        </h6>

                        <div class="row">
                            <!-- Original (Reference) -->
                            <div class="col-md-4">
                                <div class="card preview-option" style="cursor: default;">
                                    <img src="${data.previews.original_url}"
                                         class="card-img-top"
                                         alt="Original PSD"
                                         style="border: 2px solid #ddd; height: 250px; object-fit: contain; background-color: #f8f9fa;">
                                    <div class="card-body">
                                        <h6 class="card-title">
                                            <i class="fas fa-file"></i> Original PSD
                                        </h6>
                                        <p class="card-text" style="font-size: 0.85rem;">
                                            <strong>For reference only</strong><br>
                                            Dimensions: ${psdDims[0]} × ${psdDims[1]}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <!-- Scale to Fit -->
                            <div class="col-md-4">
                                <div class="card preview-option selectable"
                                     onclick="selectTransformOption('fit')"
                                     id="option-fit"
                                     style="cursor: pointer; border: 3px solid transparent; transition: all 0.2s ease;">
                                    <img src="${data.previews.fit_url}"
                                         class="card-img-top"
                                         alt="Scale to Fit"
                                         style="height: 250px; object-fit: contain; background-color: #f8f9fa;">
                                    <div class="card-body">
                                        <h6 class="card-title">
                                            <i class="fas fa-compress-arrows-alt"></i>
                                            Scale to Fit
                                            <span class="badge bg-success ms-1">Recommended</span>
                                        </h6>
                                        <p class="card-text" style="font-size: 0.85rem;">
                                            <strong>Letterbox/Pillarbox</strong><br>
                                            ✓ Maintains all content<br>
                                            ✓ No cropping<br>
                                            ⚠ May have black bars
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <!-- Scale to Fill -->
                            <div class="col-md-4">
                                <div class="card preview-option selectable"
                                     onclick="selectTransformOption('fill')"
                                     id="option-fill"
                                     style="cursor: pointer; border: 3px solid transparent; transition: all 0.2s ease;">
                                    <img src="${data.previews.fill_url}"
                                         class="card-img-top"
                                         alt="Scale to Fill"
                                         style="height: 250px; object-fit: contain; background-color: #f8f9fa;">
                                    <div class="card-body">
                                        <h6 class="card-title">
                                            <i class="fas fa-expand-arrows-alt"></i>
                                            Scale to Fill
                                        </h6>
                                        <p class="card-text" style="font-size: 0.85rem;">
                                            <strong>Crop edges</strong><br>
                                            ✓ No black bars<br>
                                            ✓ Full frame<br>
                                            ⚠ May crop content at edges
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Selected method display -->
                        <div id="selectedMethod" class="alert alert-secondary mt-3" style="display: none;">
                            <strong>Selected:</strong> <span id="selectedMethodText"></span>
                        </div>

                        <!-- CSS for hover effects -->
                        <style>
                            .preview-option.selectable:hover {
                                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                                transform: translateY(-2px);
                            }
                        </style>
                    </div>

                    <div class="modal-footer">
                        <div class="flex-grow-1">
                            <button type="button" class="btn btn-secondary"
                                    onclick="submitAspectRatioDecision('${graphicId}', 'skip')">
                                <i class="fas fa-times"></i> Skip This Graphic
                            </button>
                            <button type="button" class="btn btn-outline-secondary"
                                    onclick="submitAspectRatioDecision('${graphicId}', 'manual_fix')">
                                <i class="fas fa-wrench"></i> Fix Manually in AE
                            </button>
                        </div>
                        <button type="button" class="btn btn-success"
                                id="proceedButton"
                                onclick="submitAspectRatioDecision('${graphicId}', 'proceed')"
                                disabled>
                            <i class="fas fa-check"></i> Proceed with Selected
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function selectTransformOption(method) {
    selectedTransformMethod = method;

    // Update UI to show selection
    document.querySelectorAll('.preview-option.selectable').forEach(el => {
        el.style.border = '3px solid transparent';
    });
    document.getElementById(`option-${method}`).style.border = '3px solid #28a745';

    // Show selected method
    const methodText = method === 'fit'
        ? 'Scale to Fit (Letterbox/Pillarbox)'
        : 'Scale to Fill (Crop Edges)';

    document.getElementById('selectedMethodText').textContent = methodText;
    document.getElementById('selectedMethod').style.display = 'block';

    // Enable proceed button
    document.getElementById('proceedButton').disabled = false;
}

async function submitAspectRatioDecision(graphicId, decision) {
    try {
        // Validate selection for 'proceed'
        if (decision === 'proceed' && !selectedTransformMethod) {
            showMessage('Please select a transformation option', 'error');
            return;
        }

        showLoading(`Processing decision: ${decision}...`);

        // Close modal
        const modalElement = document.getElementById('aspectRatioModal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) modal.hide();

        // Submit decision
        const response = await fetch(
            `/api/projects/${currentProject.id}/graphics/${graphicId}/aspect-ratio-decision`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    decision: decision,
                    method: selectedTransformMethod || 'fit'
                })
            }
        );

        const result = await response.json();

        hideLoading();

        if (result.success) {
            showMessage(result.message || 'Decision processed successfully', 'success');

            // Reset selection
            selectedTransformMethod = null;

            // Reload project to refresh status
            await loadProject(currentProject.id);

            // If proceeding, processing will continue automatically
            if (decision === 'proceed') {
                showMessage('Processing graphic with selected transformation...', 'info');
            }

        } else {
            showMessage(result.error || 'Failed to process decision', 'error');
        }

    } catch (error) {
        hideLoading();
        console.error('Submit decision error:', error);
        showMessage('Failed to submit decision', 'error');
    }
}