/**
 * Projects List Page - JavaScript
 * Manages the display and creation of projects
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
    setupEventListeners();
});

function setupEventListeners() {
    // New project button
    const newProjectBtn = document.getElementById('new-project-btn');
    if (newProjectBtn) {
        newProjectBtn.addEventListener('click', showNewProjectModal);
    }

    // Modal close button
    const closeModal = document.querySelector('.modal-close');
    if (closeModal) {
        closeModal.addEventListener('click', hideNewProjectModal);
    }

    // Create project form
    const createForm = document.getElementById('create-project-form');
    if (createForm) {
        createForm.addEventListener('submit', handleCreateProject);
    }
}

// Load and display all projects
async function loadProjects() {
    const projectsGrid = document.getElementById('projects-grid');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error-message');

    try {
        // Show loading
        if (loadingDiv) loadingDiv.style.display = 'block';
        if (errorDiv) errorDiv.style.display = 'none';

        const response = await fetch('/api/projects');
        const data = await response.json();

        if (data.success) {
            displayProjects(data.projects);
        } else {
            showError(data.error || 'Failed to load projects');
        }
    } catch (error) {
        console.error('Failed to load projects:', error);
        showError('Error loading projects');
    } finally {
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
}

// Display projects in grid
function displayProjects(projects) {
    const projectsGrid = document.getElementById('projects-grid');

    if (!projectsGrid) return;

    if (!projects || projects.length === 0) {
        projectsGrid.innerHTML = `
            <div class="empty-state">
                <p>No projects yet. Create your first project to get started!</p>
            </div>
        `;
        return;
    }

    projectsGrid.innerHTML = projects.map(project => createProjectCard(project)).join('');

    // Add click handlers to project cards
    document.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('click', function() {
            const projectId = this.dataset.projectId;
            window.location.href = `/projects/${projectId}`;
        });
    });

    // Add delete button handlers (prevent navigation)
    document.querySelectorAll('.delete-project-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const projectId = this.dataset.projectId;
            const projectName = this.dataset.projectName;
            handleDeleteProject(projectId, projectName);
        });
    });
}

// Create HTML for a single project card
function createProjectCard(project) {
    const stats = project.stats || {};
    const totalGraphics = stats.total_graphics || 0;
    const completed = stats.completed || 0;
    const needsReview = stats.needs_review || 0;
    const approved = stats.approved || 0;

    const completionRate = totalGraphics > 0
        ? Math.round((completed / totalGraphics) * 100)
        : 0;

    const approvalRate = totalGraphics > 0
        ? Math.round((approved / totalGraphics) * 100)
        : 0;

    const createdDate = new Date(project.created_at).toLocaleDateString();
    const updatedDate = new Date(project.updated_at).toLocaleDateString();

    return `
        <div class="project-card" data-project-id="${project.id}">
            <div class="project-card-header">
                <h3 class="project-name">${escapeHtml(project.name)}</h3>
                <button class="delete-project-btn"
                        data-project-id="${project.id}"
                        data-project-name="${escapeHtml(project.name)}"
                        title="Delete project">
                    ×
                </button>
            </div>

            ${project.client ? `<p class="project-client">${escapeHtml(project.client)}</p>` : ''}
            ${project.description ? `<p class="project-description">${escapeHtml(project.description)}</p>` : ''}

            <div class="project-stats">
                <div class="stat-item">
                    <span class="stat-label">Total Graphics</span>
                    <span class="stat-value">${totalGraphics}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Completed</span>
                    <span class="stat-value">${completed}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Needs Review</span>
                    <span class="stat-value">${needsReview}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Approved</span>
                    <span class="stat-value">${approved}</span>
                </div>
            </div>

            <div class="project-progress">
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${completionRate}%"></div>
                </div>
                <span class="progress-text">${completionRate}% Complete</span>
            </div>

            ${approvalRate > 0 ? `
                <div class="project-approval">
                    <div class="progress-bar-container">
                        <div class="progress-bar approval" style="width: ${approvalRate}%"></div>
                    </div>
                    <span class="progress-text">${approvalRate}% Approved</span>
                </div>
            ` : ''}

            <div class="project-dates">
                <span>Created: ${createdDate}</span>
                <span>Updated: ${updatedDate}</span>
            </div>
        </div>
    `;
}

// Show new project modal
function showNewProjectModal() {
    const modal = document.getElementById('new-project-modal');
    if (modal) {
        modal.style.display = 'flex';
        // Focus on first input
        const firstInput = modal.querySelector('input');
        if (firstInput) firstInput.focus();
    }
}

// Hide new project modal
function hideNewProjectModal() {
    const modal = document.getElementById('new-project-modal');
    if (modal) {
        modal.style.display = 'none';
        // Reset form
        const form = document.getElementById('create-project-form');
        if (form) form.reset();
    }
}

// Handle create project form submission
async function handleCreateProject(e) {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');

    const projectData = {
        name: form.querySelector('#project-name').value.trim(),
        client: form.querySelector('#project-client').value.trim(),
        description: form.querySelector('#project-description').value.trim()
    };

    if (!projectData.name) {
        showError('Project name is required');
        return;
    }

    try {
        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';

        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(projectData)
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Project created successfully!', 'success');
            hideNewProjectModal();
            // Reload projects list
            await loadProjects();
        } else {
            showError(data.error || 'Failed to create project');
        }
    } catch (error) {
        console.error('Failed to create project:', error);
        showError('Error creating project');
    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Project';
    }
}

// Handle delete project
async function handleDeleteProject(projectId, projectName) {
    if (!confirm(`Are you sure you want to delete project "${projectName}"?\n\nThis will delete all graphics in the project. This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Project deleted successfully', 'success');
            // Reload projects list
            await loadProjects();
        } else {
            showError(data.error || 'Failed to delete project');
        }
    } catch (error) {
        console.error('Failed to delete project:', error);
        showError('Error deleting project');
    }
}

// Utility: Show error message
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

// Utility: Show success message
function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#4CAF50' : '#2196F3'};
        color: white;
        border-radius: 4px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(messageDiv);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        messageDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(messageDiv);
        }, 300);
    }, 3000);
}

// Utility: Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
