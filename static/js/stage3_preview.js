/**
 * Stage 3: Preview & Approval Interface
 *
 * Handles video preview and approval workflow.
 */

// Global State
let jobId = null;
let jobData = null;
let videoElement = null;
let currentViewMode = 'side-by-side';

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
    showLoading(true);

    try {
        // Load job details
        const jobResponse = await fetch(`/api/job/${jobId}`);
        if (!jobResponse.ok) {
            throw new Error('Failed to load job data');
        }

        jobData = await jobResponse.json();

        // Update UI with job info
        updateJobInfo();

        // Load preview data
        loadPreviewData();

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
    document.getElementById('psd-filename').textContent = getFilename(jobData.psd_path);
    document.getElementById('aepx-filename').textContent = getFilename(jobData.aepx_template_path);

    // Get match count (would be from stored matches in production)
    document.getElementById('match-count').textContent = '5 matches';
}

/**
 * Get filename from path
 */
function getFilename(path) {
    if (!path) return 'N/A';
    return path.split('/').pop();
}

/**
 * Load preview data
 */
function loadPreviewData() {
    // In production, this would:
    // 1. Load preview video URL from job assets
    // 2. Initialize video player with the preview video
    // 3. Load render metrics (duration, resolution, render time)

    // For now, display placeholder and simulate data
    updateRenderDetails();
}

/**
 * Update render details
 */
function updateRenderDetails() {
    // Simulate render details
    document.getElementById('video-duration').textContent = '0:10';
    document.getElementById('video-resolution').textContent = '1920x1080';
    document.getElementById('video-framerate').textContent = '30 fps';
    document.getElementById('render-time').textContent = '2m 15s';
}

/**
 * Set view mode for video preview
 */
function setViewMode(mode) {
    currentViewMode = mode;

    // Update toggle buttons
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
        }
    });

    // In production, this would update the video source
    // For now, just log
    console.log('View mode changed to:', mode);
}

/**
 * Toggle play/pause for video
 */
function togglePlayPause() {
    if (!videoElement) {
        console.log('Video play/pause (placeholder)');
        return;
    }

    if (videoElement.paused) {
        videoElement.play();
    } else {
        videoElement.pause();
    }
}

/**
 * Toggle fullscreen
 */
function toggleFullscreen() {
    const wrapper = document.getElementById('video-wrapper');

    if (!document.fullscreenElement) {
        wrapper.requestFullscreen().catch(err => {
            console.error('Error entering fullscreen:', err);
        });
    } else {
        document.exitFullscreen();
    }
}

/**
 * Approve preview and continue to Stage 4
 */
async function approvePreview() {
    const notes = document.getElementById('approval-notes').value.trim();

    // Get checklist status
    const checklist = {
        timing: document.getElementById('check-timing').checked,
        layers: document.getElementById('check-layers').checked,
        effects: document.getElementById('check-effects').checked,
        quality: document.getElementById('check-quality').checked
    };

    // Confirm if not all checkboxes are checked
    const allChecked = Object.values(checklist).every(v => v);
    if (!allChecked) {
        const proceed = confirm(
            'Not all quality checks are marked as complete. ' +
            'Are you sure you want to approve this preview?'
        );
        if (!proceed) return;
    }

    showLoading(true);

    try {
        const response = await fetch(`/api/job/${jobId}/approve-stage3`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: 'demo_user',
                approval_notes: notes,
                checklist: checklist
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to approve stage 3');
        }

        const result = await response.json();

        showLoading(false);

        // Show success message
        alert('Stage 3 approved! Transitioning to Stage 4 (Validation & Deployment)...');

        // Redirect back to dashboard
        window.location.href = '/dashboard';

    } catch (error) {
        console.error('Error approving stage 3:', error);
        alert('Failed to approve: ' + error.message);
        showLoading(false);
    }
}

/**
 * Open reject modal
 */
function rejectPreview() {
    document.getElementById('reject-modal').classList.add('active');
}

/**
 * Close reject modal
 */
function closeRejectModal() {
    document.getElementById('reject-modal').classList.remove('active');
    document.getElementById('rejection-reason').value = '';
}

/**
 * Confirm rejection and send back to Stage 2
 */
async function confirmReject() {
    const reason = document.getElementById('rejection-reason').value.trim();

    if (!reason) {
        alert('Please provide a reason for rejection');
        return;
    }

    closeRejectModal();
    showLoading(true);

    try {
        // In production, this would call an API to:
        // 1. Log the rejection reason
        // 2. Transition job back to Stage 2
        // 3. Add warning/note about what needs to be fixed

        // For now, simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));

        // In a real implementation, you'd call something like:
        // POST /api/job/{jobId}/reject-stage3
        // with { user_id, reason }

        showLoading(false);

        alert('Preview rejected. Job sent back to Stage 2 for revision.');

        // Redirect back to dashboard
        window.location.href = '/dashboard';

    } catch (error) {
        console.error('Error rejecting preview:', error);
        alert('Failed to reject: ' + error.message);
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
 * Format time in seconds to MM:SS
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Handle escape key to close modals
 */
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const rejectModal = document.getElementById('reject-modal');
        if (rejectModal.classList.contains('active')) {
            closeRejectModal();
        }
    }
});

/**
 * Initialize video player (when video is available)
 */
function initializeVideoPlayer(videoUrl) {
    const wrapper = document.getElementById('video-wrapper');

    // Remove placeholder
    wrapper.innerHTML = '';

    // Create video element
    videoElement = document.createElement('video');
    videoElement.src = videoUrl;
    videoElement.controls = false; // Use custom controls

    wrapper.appendChild(videoElement);

    // Enable controls
    document.getElementById('play-pause-btn').disabled = false;
    document.getElementById('seek-bar').disabled = false;
    document.getElementById('fullscreen-btn').disabled = false;

    // Set up event listeners
    videoElement.addEventListener('loadedmetadata', () => {
        const duration = formatTime(videoElement.duration);
        document.getElementById('video-duration').textContent = duration;
    });

    videoElement.addEventListener('timeupdate', () => {
        const seekBar = document.getElementById('seek-bar');
        const currentTime = formatTime(videoElement.currentTime);
        const duration = formatTime(videoElement.duration);

        // Update seek bar
        seekBar.value = (videoElement.currentTime / videoElement.duration) * 100;

        // Update time display
        document.getElementById('time-display').textContent = `${currentTime} / ${duration}`;

        // Update play/pause button icon
        const playPauseBtn = document.getElementById('play-pause-btn');
        if (videoElement.paused) {
            playPauseBtn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
        } else {
            playPauseBtn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>';
        }
    });

    // Seek bar interaction
    const seekBar = document.getElementById('seek-bar');
    seekBar.addEventListener('input', (e) => {
        const time = (e.target.value / 100) * videoElement.duration;
        videoElement.currentTime = time;
    });
}
