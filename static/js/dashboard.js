// Production Dashboard JavaScript

// Global state
let allJobs = [];
let currentFilters = {
    stage: 'all',
    priority: 'all',
    search: ''
};
let autoRefreshInterval = null;

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    startAutoRefresh();
    setupUploadForm();
});

// Load all dashboard data
async function loadDashboard() {
    try {
        // Load statistics
        await loadStatistics();

        // Load all stages
        await loadAllStages();

        // Load recent batches
        await loadRecentBatches();

    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Failed to load dashboard data', 'error');
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch('/api/dashboard/stats');
        const data = await response.json();

        if (data.success) {
            document.getElementById('total-jobs').textContent = data.summary.total || 0;
            document.getElementById('in-progress-jobs').textContent = data.summary.in_progress || 0;
            document.getElementById('completed-jobs').textContent = data.summary.completed || 0;
            document.getElementById('failed-jobs').textContent = data.summary.failed || 0;
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load all stages
async function loadAllStages() {
    allJobs = [];

    for (let stage = 0; stage <= 4; stage++) {
        await loadStage(stage);
    }

    // Apply current filters
    applyFilters();
}

// Load jobs for a specific stage
async function loadStage(stage) {
    try {
        const response = await fetch(`/api/jobs/stage/${stage}`);
        const data = await response.json();

        if (data.success) {
            // Add stage info to each job
            const jobs = data.jobs.map(job => ({...job, current_stage: stage}));
            allJobs = allJobs.concat(jobs);

            // Update stage count
            document.getElementById(`stage-${stage}-count`).textContent = jobs.length;
        }
    } catch (error) {
        console.error(`Error loading stage ${stage}:`, error);
    }
}

// Render jobs in their respective stages
function renderJobs(jobs) {
    // Clear all stage containers
    for (let stage = 0; stage <= 4; stage++) {
        const container = document.getElementById(`stage-${stage}-jobs`);
        container.innerHTML = '';
    }

    // Group jobs by stage
    const jobsByStage = {};
    jobs.forEach(job => {
        const stage = job.current_stage;
        if (!jobsByStage[stage]) {
            jobsByStage[stage] = [];
        }
        jobsByStage[stage].push(job);
    });

    // Render each stage
    for (let stage = 0; stage <= 4; stage++) {
        const container = document.getElementById(`stage-${stage}-jobs`);
        const stageJobs = jobsByStage[stage] || [];

        if (stageJobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-text">No jobs in this stage</div>
                </div>
            `;
        } else {
            stageJobs.forEach(job => {
                container.appendChild(createJobCard(job));
            });
        }

        // Update count
        document.getElementById(`stage-${stage}-count`).textContent = stageJobs.length;
    }
}

// Create a job card element
function createJobCard(job) {
    const card = document.createElement('div');
    card.className = 'job-card';
    card.dataset.jobId = job.job_id;
    card.dataset.stage = job.current_stage;
    card.dataset.priority = job.priority || 'medium';
    card.onclick = () => showJobDetails(job.job_id);

    // Priority emoji
    const priorityEmoji = {
        'high': '🔴',
        'medium': '🟡',
        'low': '🟢'
    }[job.priority] || '🟡';

    // Action button based on status
    let actionButton = '';
    if (job.status === 'awaiting_review') {
        actionButton = '<button class="job-action-btn review" onclick="event.stopPropagation(); launchStageAction(\'' + job.job_id + '\', 2)">Review Matching</button>';
    } else if (job.status === 'awaiting_approval') {
        actionButton = '<button class="job-action-btn approve" onclick="event.stopPropagation(); launchStageAction(\'' + job.job_id + '\', 3)">Approve Preview</button>';
    } else if (job.status === 'completed') {
        actionButton = '<button class="job-action-btn download" onclick="event.stopPropagation(); downloadResult(\'' + job.job_id + '\')">Download</button>';
    }

    card.innerHTML = `
        <div class="job-card-header">
            <div class="job-id">${job.job_id}</div>
            <div class="job-priority">${priorityEmoji}</div>
        </div>
        <div class="job-info">
            ${job.client_name ? `Client: ${job.client_name}` : ''}
        </div>
        <div class="job-info">
            ${job.project_name ? `Project: ${job.project_name}` : ''}
        </div>
        <div class="job-status ${job.status}">
            ${formatStatus(job.status)}
        </div>
        ${actionButton}
    `;

    return card;
}

// Format status for display
function formatStatus(status) {
    const statusMap = {
        'pending': 'Pending',
        'processing': 'Processing',
        'awaiting_review': 'Awaiting Review',
        'awaiting_approval': 'Awaiting Approval',
        'ready_for_validation': 'Ready for Validation',
        'validation_failed': 'Validation Failed',
        'completed': 'Completed',
        'failed': 'Failed'
    };
    return statusMap[status] || status;
}

// Load recent batches
async function loadRecentBatches() {
    try {
        const response = await fetch('/api/dashboard/stats');
        const data = await response.json();

        if (data.success && data.recent_batches) {
            const container = document.getElementById('batches-list');
            container.innerHTML = '';

            if (data.recent_batches.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📦</div>
                        <div class="empty-state-text">No recent batches</div>
                    </div>
                `;
            } else {
                data.recent_batches.forEach(batch => {
                    container.appendChild(createBatchCard(batch));
                });
            }
        }
    } catch (error) {
        console.error('Error loading batches:', error);
    }
}

// Create a batch card element
function createBatchCard(batch) {
    const card = document.createElement('div');
    card.className = 'batch-card';

    const uploadDate = new Date(batch.uploaded_at).toLocaleString();

    card.innerHTML = `
        <div class="batch-header">
            <div class="batch-id">${batch.batch_id}</div>
            <div class="batch-status ${batch.status}">${formatStatus(batch.status)}</div>
        </div>
        <div class="batch-info">
            Total Jobs: ${batch.total_jobs} | Valid: ${batch.valid_jobs} | Uploaded by: ${batch.uploaded_by}
        </div>
        <div class="batch-info">
            ${uploadDate}
        </div>
    `;

    return card;
}

// Filter functions
function filterByStage(stage) {
    currentFilters.stage = stage;

    // Update active button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    applyFilters();
}

function filterByPriority(priority) {
    currentFilters.priority = priority;

    // Update active button
    document.querySelectorAll('.priority-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    applyFilters();
}

function filterJobs() {
    currentFilters.search = document.getElementById('search-input').value.toLowerCase();
    applyFilters();
}

function applyFilters() {
    let filtered = allJobs;

    // Stage filter
    if (currentFilters.stage !== 'all') {
        filtered = filtered.filter(job => job.current_stage == currentFilters.stage);
    }

    // Priority filter
    if (currentFilters.priority !== 'all') {
        filtered = filtered.filter(job => (job.priority || 'medium') === currentFilters.priority);
    }

    // Search filter
    if (currentFilters.search) {
        filtered = filtered.filter(job => {
            const searchStr = `${job.job_id} ${job.client_name || ''} ${job.project_name || ''}`.toLowerCase();
            return searchStr.includes(currentFilters.search);
        });
    }

    renderJobs(filtered);
}

// Show job details modal
async function showJobDetails(jobId) {
    try {
        const response = await fetch(`/api/job/${jobId}`);
        const data = await response.json();

        if (data.success) {
            const job = data.job;
            const warnings = data.warnings.list || [];
            const logs = data.recent_logs || [];

            const modalContent = `
                <div class="job-details-grid">
                    <div class="detail-item">
                        <div class="detail-label">Job ID</div>
                        <div class="detail-value">${job.job_id}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Current Stage</div>
                        <div class="detail-value">Stage ${job.current_stage}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Status</div>
                        <div class="detail-value">${formatStatus(job.status)}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Priority</div>
                        <div class="detail-value">${job.priority || 'medium'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Client</div>
                        <div class="detail-value">${job.client_name || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Project</div>
                        <div class="detail-value">${job.project_name || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">PSD Path</div>
                        <div class="detail-value">${job.psd_path}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">AEPX Path</div>
                        <div class="detail-value">${job.aepx_path}</div>
                    </div>
                </div>

                <div class="section-title">Stage Progress</div>
                <div class="job-details-grid">
                    ${[0, 1, 2, 3, 4].map(stage => `
                        <div class="detail-item">
                            <div class="detail-label">Stage ${stage}</div>
                            <div class="detail-value">
                                ${job[`stage${stage}_completed_at`]
                                    ? `✅ ${new Date(job[`stage${stage}_completed_at`]).toLocaleString()}`
                                    : '⏳ Not completed'
                                }
                            </div>
                        </div>
                    `).join('')}
                </div>

                ${warnings.length > 0 ? `
                    <div class="section-title">Warnings (${warnings.length})</div>
                    <div class="warning-list">
                        ${warnings.map(w => `
                            <div class="warning-item">
                                <strong>${w.warning_type}</strong>: ${w.message}
                                ${w.severity ? `<br><small>Severity: ${w.severity}</small>` : ''}
                            </div>
                        `).join('')}
                    </div>
                ` : '<div class="section-title">No warnings</div>'}

                ${logs.length > 0 ? `
                    <div class="section-title">Recent Activity</div>
                    <div class="log-list">
                        ${logs.map(log => `
                            <div class="log-item">
                                <div>${log.message}</div>
                                <div class="log-time">
                                    ${new Date(log.created_at).toLocaleString()} - ${log.user_id}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            `;

            document.getElementById('job-modal-title').textContent = `Job: ${job.job_id}`;
            document.getElementById('job-details-content').innerHTML = modalContent;
            document.getElementById('job-modal').classList.add('show');
        }
    } catch (error) {
        console.error('Error loading job details:', error);
        showNotification('Failed to load job details', 'error');
    }
}

function closeJobModal() {
    document.getElementById('job-modal').classList.remove('show');
}

// Upload modal functions
function showUploadModal() {
    document.getElementById('upload-modal').classList.add('show');
    document.getElementById('upload-form').reset();
    document.getElementById('upload-progress').style.display = 'none';
    document.getElementById('upload-result').style.display = 'none';
}

function closeUploadModal() {
    document.getElementById('upload-modal').classList.remove('show');
}

// Setup upload form
function setupUploadForm() {
    const form = document.getElementById('upload-form');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(form);
        const progressDiv = document.getElementById('upload-progress');
        const resultDiv = document.getElementById('upload-result');

        // Show progress
        progressDiv.style.display = 'block';
        resultDiv.style.display = 'none';
        document.getElementById('progress-fill').style.width = '30%';
        document.getElementById('progress-text').textContent = 'Uploading CSV...';

        try {
            const response = await fetch('/api/batch/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            // Update progress
            document.getElementById('progress-fill').style.width = '100%';
            document.getElementById('progress-text').textContent = 'Upload complete!';

            // Show result
            setTimeout(() => {
                progressDiv.style.display = 'none';
                resultDiv.style.display = 'block';

                if (data.success) {
                    resultDiv.className = 'upload-result success';
                    resultDiv.innerHTML = `
                        <strong>✅ Success!</strong><br>
                        Batch ID: ${data.batch_id}<br>
                        Valid Jobs: ${data.validation.valid_jobs}/${data.validation.total_jobs}
                        <br><br>
                        <button class="btn btn-primary" onclick="startBatchProcessing('${data.batch_id}')">
                            Start Processing
                        </button>
                    `;
                } else {
                    resultDiv.className = 'upload-result error';
                    resultDiv.innerHTML = `
                        <strong>❌ Error!</strong><br>
                        ${data.message || 'Upload failed'}
                        ${data.validation && data.validation.errors ?
                            '<br><br>' + data.validation.errors.map(e =>
                                `Row ${e.row}: ${e.errors.join(', ')}`
                            ).join('<br>')
                            : ''
                        }
                    `;
                }
            }, 500);

        } catch (error) {
            console.error('Upload error:', error);
            progressDiv.style.display = 'none';
            resultDiv.style.display = 'block';
            resultDiv.className = 'upload-result error';
            resultDiv.innerHTML = '<strong>❌ Error!</strong><br>Failed to upload CSV file';
        }
    });
}

// Start batch processing
async function startBatchProcessing(batchId) {
    try {
        const response = await fetch(`/api/batch/${batchId}/start-processing`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ max_jobs: 100 })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(`Processing started for ${batchId}!`, 'success');
            closeUploadModal();
            refreshDashboard();
        } else {
            showNotification('Failed to start processing', 'error');
        }
    } catch (error) {
        console.error('Error starting processing:', error);
        showNotification('Failed to start processing', 'error');
    }
}

// Launch stage-specific action
function launchStageAction(jobId, stage) {
    // Stage 2: Review matching
    if (stage === 2) {
        window.location.href = `/review-matching/${jobId}`;
    }
    // Stage 3: Approve preview
    else if (stage === 3) {
        window.location.href = `/approve-preview/${jobId}`;
    }
}

// Download result
function downloadResult(jobId) {
    window.location.href = `/download-result/${jobId}`;
}

// Refresh dashboard
async function refreshDashboard() {
    showNotification('Refreshing dashboard...', 'info');
    await loadDashboard();
    showNotification('Dashboard refreshed!', 'success');
}

// Auto-refresh
function startAutoRefresh() {
    // Refresh every 30 seconds
    autoRefreshInterval = setInterval(() => {
        loadDashboard();
    }, 30000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
}

// Show notification (toast)
function showNotification(message, type = 'info') {
    // Simple console notification for now
    // You can implement a toast library or custom toast later
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
};
