/**
 * Project Manager JavaScript
 * Handles project and graphic management with user identity tracking and audit trail
 */

// ============================================================================
// USER IDENTITY MANAGEMENT
// ============================================================================

/**
 * Get current user identity (prompts on first use and stores in localStorage)
 */
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

/**
 * Change current user identity
 */
function changeUser() {
    const newUser = prompt('Enter your name or email:', getCurrentUser() || '');
    if (newUser && newUser.trim()) {
        localStorage.setItem('ae_automation_user', newUser.trim());
        showMessage(`User changed to: ${newUser}`, 'success');
        // Refresh display
        updateUserDisplay();
    }
}

/**
 * Update user display in UI
 */
function updateUserDisplay() {
    const user = getCurrentUser();
    const userDisplay = document.getElementById('current-user');
    if (userDisplay && user) {
        userDisplay.textContent = `Signed in as: ${user}`;
    }
}

// ============================================================================
// PROJECT MANAGEMENT
// ============================================================================

/**
 * Create a new project
 */
async function createProject(name, client = '', description = '') {
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                client: client,
                description: description
            })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(`Project "${name}" created successfully`, 'success');
            return data.project;
        } else {
            showMessage(`Failed to create project: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Create project failed:', error);
        showMessage('Error creating project', 'error');
        return null;
    }
}

/**
 * List all projects
 */
async function listProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();

        if (data.success) {
            return data.projects;
        } else {
            showMessage(`Failed to load projects: ${data.error}`, 'error');
            return [];
        }
    } catch (error) {
        console.error('List projects failed:', error);
        showMessage('Error loading projects', 'error');
        return [];
    }
}

/**
 * Get a specific project
 */
async function getProject(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}`);
        const data = await response.json();

        if (data.success) {
            return data.project;
        } else {
            showMessage(`Failed to load project: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Get project failed:', error);
        showMessage('Error loading project', 'error');
        return null;
    }
}

/**
 * Delete a project
 */
async function deleteProject(projectId) {
    if (!confirm('Are you sure you want to delete this project? This cannot be undone.')) {
        return false;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Project deleted successfully', 'success');
            return true;
        } else {
            showMessage(`Failed to delete project: ${data.error}`, 'error');
            return false;
        }
    } catch (error) {
        console.error('Delete project failed:', error);
        showMessage('Error deleting project', 'error');
        return false;
    }
}

// ============================================================================
// GRAPHIC MANAGEMENT
// ============================================================================

/**
 * Create a new graphic in a project
 */
async function createGraphic(projectId, name, psdPath = null) {
    try {
        const response = await fetch(`/api/projects/${projectId}/graphics`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                psd_path: psdPath
            })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(`Graphic "${name}" created successfully`, 'success');
            return data.graphic;
        } else {
            showMessage(`Failed to create graphic: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Create graphic failed:', error);
        showMessage('Error creating graphic', 'error');
        return null;
    }
}

/**
 * Update a graphic
 */
async function updateGraphic(projectId, graphicId, updates) {
    const user = getCurrentUser();

    if (!user) {
        alert('User identity is required for updates');
        return null;
    }

    try {
        // Add user to the updates
        updates.user = user;

        const response = await fetch(`/api/projects/${projectId}/graphics/${graphicId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Graphic updated successfully', 'success');
            return data.graphic;
        } else {
            showMessage(`Failed to update graphic: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Update graphic failed:', error);
        showMessage('Error updating graphic', 'error');
        return null;
    }
}

// ============================================================================
// APPROVAL MANAGEMENT
// ============================================================================

/**
 * Approve a graphic for production
 */
async function approveGraphic(projectId, graphicId) {
    const user = getCurrentUser();

    if (!user) {
        alert('User identity is required to approve graphics');
        return null;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}/graphics/${graphicId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                approved_by: user
            })
        });

        const data = await response.json();

        if (data.success) {
            const approvalTime = new Date(data.graphic.approved_at).toLocaleString();
            showMessage(`✓ Approved by ${user} at ${approvalTime}`, 'success');
            return data.graphic;
        } else {
            showMessage(`Failed to approve: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Approve failed:', error);
        showMessage('Error approving graphic', 'error');
        return null;
    }
}

/**
 * Unapprove a graphic (unlock for editing)
 */
async function unapproveGraphic(projectId, graphicId) {
    const user = getCurrentUser();

    if (!user) {
        alert('User identity is required to unapprove graphics');
        return null;
    }

    if (!confirm('Are you sure you want to unapprove this graphic? This will unlock it for editing.')) {
        return null;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}/graphics/${graphicId}/unapprove`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                unapproved_by: user
            })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(`Unapproved by ${user} - graphic is now unlocked`, 'success');
            return data.graphic;
        } else {
            showMessage(`Failed to unapprove: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Unapprove failed:', error);
        showMessage('Error unapproving graphic', 'error');
        return null;
    }
}

// ============================================================================
// AUDIT TRAIL
// ============================================================================

/**
 * Get audit log for a graphic
 */
async function getAuditLog(projectId, graphicId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/graphics/${graphicId}/audit-log`);
        const data = await response.json();

        if (data.success) {
            return data.audit;
        } else {
            showMessage(`Failed to load audit log: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Get audit log failed:', error);
        showMessage('Error loading audit log', 'error');
        return null;
    }
}

/**
 * Display audit log in a modal or dedicated area
 */
function displayAuditLog(audit) {
    if (!audit || !audit.audit_log) {
        showMessage('No audit history available', 'info');
        return;
    }

    // Format audit log for display
    let html = `<div class="audit-log">`;
    html += `<h3>Audit History: ${audit.graphic_name}</h3>`;
    html += `<div class="audit-status">`;
    html += `<p><strong>Current Status:</strong> ${audit.current_status}</p>`;
    html += `<p><strong>Approved:</strong> ${audit.approved ? 'Yes' : 'No'}</p>`;
    if (audit.approved) {
        html += `<p><strong>Approved by:</strong> ${audit.approved_by}</p>`;
        html += `<p><strong>Approved at:</strong> ${new Date(audit.approved_at).toLocaleString()}</p>`;
    }
    html += `</div>`;

    html += `<h4>Activity Log:</h4>`;
    html += `<table class="audit-table">`;
    html += `<thead><tr><th>Time</th><th>Action</th><th>User</th><th>Details</th></tr></thead>`;
    html += `<tbody>`;

    // Sort by timestamp descending
    const sortedLog = [...audit.audit_log].sort((a, b) =>
        new Date(b.timestamp) - new Date(a.timestamp)
    );

    for (const entry of sortedLog) {
        html += `<tr>`;
        html += `<td>${new Date(entry.timestamp).toLocaleString()}</td>`;
        html += `<td>${entry.action}</td>`;
        html += `<td>${entry.user}</td>`;
        html += `<td>${JSON.stringify(entry.details, null, 2)}</td>`;
        html += `</tr>`;
    }

    html += `</tbody></table></div>`;

    // Display in modal or dedicated area
    const auditDisplay = document.getElementById('audit-display');
    if (auditDisplay) {
        auditDisplay.innerHTML = html;
    } else {
        // Create modal if doesn't exist
        alert('Audit log loaded - check console for details');
        console.log('Audit Log:', audit);
    }
}

/**
 * Export audit report for entire project
 */
async function exportAuditReport(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/audit-report`);
        const data = await response.json();

        if (data.success) {
            // Download as JSON file
            const blob = new Blob([JSON.stringify(data.report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit_report_${projectId}_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showMessage('Audit report exported successfully', 'success');
            return data.report;
        } else {
            showMessage(`Failed to export audit report: ${data.error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Export audit report failed:', error);
        showMessage('Error exporting audit report', 'error');
        return null;
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Show status message
 */
function showMessage(message, type = 'info') {
    const statusDiv = document.getElementById('status-message');
    if (statusDiv) {
        statusDiv.textContent = message;
        statusDiv.className = `status-message ${type}`;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            statusDiv.className = 'status-message hidden';
        }, 5000);
    } else {
        // Fallback to console
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
    // Update user display on page load
    updateUserDisplay();

    // Set up user change button if it exists
    const userChangeBtn = document.getElementById('change-user-btn');
    if (userChangeBtn) {
        userChangeBtn.addEventListener('click', changeUser);
    }
});
