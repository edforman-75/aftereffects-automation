/**
 * Stage 2: Layer Matching Review Interface
 *
 * Handles interactive layer matching review and approval workflow.
 */

// Global State
let jobId = null;
let jobData = null;
let psdLayers = [];
let aeLayers = [];
let currentMatches = [];
let originalMatches = [];
let currentEditingRowIndex = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Get job ID from URL path (/review-matching/JOB_ID)
    const pathParts = window.location.pathname.split('/');
    jobId = pathParts[pathParts.length - 1];

    if (!jobId) {
        alert('No job ID provided');
        window.location.href = '/dashboard';
        return;
    }

    // Load data
    loadJobData();

    // Set up event listeners
    setupEventListeners();
});

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Filter checkboxes
    document.getElementById('filter-unmatched').addEventListener('change', applyFilters);
    document.getElementById('filter-low-confidence').addEventListener('change', applyFilters);
}

/**
 * Setup drag and drop for layer matching
 */
function setupDragAndDrop() {
    console.log('setupDragAndDrop() called');

    // Make PSD layer rows draggable
    const rows = document.querySelectorAll('.matching-table tbody tr');
    console.log(`Found ${rows.length} table rows`);

    rows.forEach(row => {
        const rowIndex = parseInt(row.dataset.index);

        // Make PSD name cell draggable
        const psdCell = row.querySelector('td:nth-child(2)');
        if (psdCell) {
            psdCell.draggable = true;
            psdCell.style.cursor = 'grab';
            psdCell.title = 'Drag to swap matches';
            console.log(`Made PSD cell draggable for row ${rowIndex}`);

            psdCell.addEventListener('dragstart', (e) => {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', rowIndex.toString());
                row.classList.add('dragging');
                console.log(`Drag started from row ${rowIndex}`);
            });

            psdCell.addEventListener('dragend', (e) => {
                row.classList.remove('dragging');
                console.log(`Drag ended for row ${rowIndex}`);
            });
        }

        // Make BOTH AE cells (name AND preview) drop targets
        const aeCells = [
            row.querySelector('td:nth-child(5)'),  // AE name column
            row.querySelector('td:nth-child(6)')   // AE preview column
        ];

        aeCells.forEach((aeCell, cellIndex) => {
            if (aeCell) {
                aeCell.addEventListener('dragover', (e) => {
                    e.preventDefault();  // Critical - allows drop
                    e.dataTransfer.dropEffect = 'move';
                    aeCell.classList.add('drop-target');
                    // Also highlight the row
                    row.classList.add('drop-target-row');
                });

                aeCell.addEventListener('dragleave', (e) => {
                    // Only remove if we're actually leaving the cell
                    if (!aeCell.contains(e.relatedTarget)) {
                        aeCell.classList.remove('drop-target');
                        row.classList.remove('drop-target-row');
                    }
                });

                aeCell.addEventListener('drop', (e) => {
                    e.preventDefault();  // Critical - allows drop
                    aeCell.classList.remove('drop-target');
                    row.classList.remove('drop-target-row');

                    const draggedIndex = parseInt(e.dataTransfer.getData('text/plain'));
                    const targetIndex = rowIndex;

                    console.log(`Drop: Moving row ${draggedIndex} to row ${targetIndex}`);

                    if (draggedIndex !== targetIndex && !isNaN(draggedIndex)) {
                        // Swap the AE matches
                        const tempAeId = currentMatches[draggedIndex].ae_id;
                        currentMatches[draggedIndex].ae_id = currentMatches[targetIndex].ae_id;
                        currentMatches[targetIndex].ae_id = tempAeId;

                        console.log(`Swapped AE matches between rows ${draggedIndex} and ${targetIndex}`);

                        // Re-render table
                        renderMatchingTable();
                        updateMatchStats();

                        // Re-setup drag-and-drop
                        setTimeout(() => {
                            setupDragAndDrop();
                        }, 100);

                        // Show feedback
                        showToast('Matches swapped', 'success');
                    }
                });

                console.log(`Made AE cell ${cellIndex === 0 ? 'name' : 'preview'} a drop target for row ${rowIndex}`);
            }
        });
    });

    console.log('✅ Drag-and-drop setup complete');
}


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

        // Load matching data
        await loadMatchingData();

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
    const job = jobData.job || jobData; // Handle both response formats
    document.getElementById('job-id-display').textContent = job.job_id;
    document.getElementById('client-name').textContent = job.client_name || 'N/A';
    document.getElementById('project-name').textContent = job.project_name || 'N/A';
    document.getElementById('psd-filename').textContent = getFilename(job.psd_path);
    document.getElementById('aepx-filename').textContent = getFilename(job.aepx_path);
}

/**
 * Get filename from path
 */
function getFilename(path) {
    if (!path) return 'N/A';
    return path.split('/').pop();
}

/**
 * Load matching data from API
 */
async function loadMatchingData() {
    try {
        // Check if we have stage1_results
        if (!jobData.stage1_results) {
            console.error('No stage1_results in job data');
            generateSampleMatchingData(); // Fallback to sample data
            renderMatchingTable();
            updateMatchStats();
            setupDragAndDrop();
            return;
        }

        const stage1 = jobData.stage1_results;

        // Load PSD layers from stage1_results.psd.layers (object)
        if (stage1.psd && stage1.psd.layers) {
            psdLayers = Object.entries(stage1.psd.layers).map(([name, layer]) => ({
                id: `psd_${name.replace(/\s+/g, '_')}`,
                name: name,
                type: layer.type || layer.kind || 'Layer',
                bounds: layer.bounds || [0, 0, 100, 100],
                thumbnail: layer.thumbnail_path || null,
                size: layer.size || [0, 0],
                visible: layer.visible !== false
            }));
        } else {
            psdLayers = [];
        }

        // Load AE layers from stage1_results.aepx.layers (array)
        if (stage1.aepx && stage1.aepx.layers) {
            aeLayers = stage1.aepx.layers.map((layer, index) => ({
                id: `ae_${index}`,
                name: layer.name || `Layer ${index + 1}`,
                type: layer.type || 'Unknown'
            }));
        } else {
            aeLayers = [];
        }

        // Create match entries for ALL PSD layers
        // Start with all PSD layers as unmatched
        currentMatches = psdLayers.map(psdLayer => ({
            psd_id: psdLayer.id,
            ae_id: null,
            confidence: 0.0,
            method: 'no_match'
        }));

        // If we have existing matches from stage1, populate them
        if (stage1.matches && stage1.matches.matches && stage1.matches.matches.length > 0) {
            console.log('Processing', stage1.matches.matches.length, 'matches from stage1');
            console.log('Stage1 matches:', stage1.matches.matches);

            stage1.matches.matches.forEach(match => {
                const psd_id = `psd_${match.psd_layer.replace(/\s+/g, '_')}`;
                const matchIndex = currentMatches.findIndex(m => m.psd_id === psd_id);

                console.log(`Processing match: "${match.psd_layer}" → "${match.aepx_layer || match.ae_layer}"`);
                console.log(`  PSD ID: ${psd_id}, Match index: ${matchIndex}`);

                if (matchIndex >= 0) {
                    // API returns 'aepx_layer' not 'ae_layer'
                    const aeLayerName = match.aepx_layer || match.ae_layer;
                    const aeIndex = aeLayers.findIndex(l => l.name === aeLayerName);

                    console.log(`  AE layer name: "${aeLayerName}", AE index: ${aeIndex}`);

                    currentMatches[matchIndex] = {
                        psd_id: psd_id,
                        ae_id: aeIndex >= 0 ? `ae_${aeIndex}` : null,
                        confidence: match.confidence || 0.0,
                        method: match.match_type || match.method || 'auto'
                    };

                    console.log(`  ✓ Match updated:`, currentMatches[matchIndex]);
                } else {
                    console.warn(`  ✗ No PSD layer found with ID: ${psd_id}`);
                }
            });
        } else {
            console.log('No matches found in stage1 data');
        }

        // Keep original for reset
        originalMatches = JSON.parse(JSON.stringify(currentMatches));

        console.log('=== LOADED DATA SUMMARY ===');
        console.log('PSD Layers:', psdLayers.length);
        psdLayers.forEach((layer, i) => console.log(`  ${i + 1}. ${layer.id} - ${layer.name} (${layer.type})`));
        console.log('AE Layers:', aeLayers.length);
        aeLayers.forEach((layer, i) => console.log(`  ${i + 1}. ${layer.id} - ${layer.name} (${layer.type})`));
        console.log('Current Matches:', currentMatches.length);
        currentMatches.forEach((match, i) => {
            const psdLayer = psdLayers.find(l => l.id === match.psd_id);
            const aeLayer = aeLayers.find(l => l.id === match.ae_id);
            console.log(`  ${i + 1}. ${psdLayer?.name || 'Unknown'} → ${aeLayer?.name || 'No Match'} (${match.confidence * 100}%)`);
        });
        console.log('=========================');

        // Render the table
        renderMatchingTable();
        updateMatchStats();

        // Setup drag-and-drop with a small delay to ensure DOM is ready
        setTimeout(() => {
            console.log('Setting up drag-and-drop...');
            setupDragAndDrop();
        }, 100);
    } catch (error) {
        console.error('Error loading matching data:', error);
        throw error;
    }
}

/**
 * Generate sample matching data
 * In production, this would come from the backend
 */
function generateSampleMatchingData() {
    // Sample PSD layers
    psdLayers = [
        { id: 'psd_1', name: 'Background', type: 'Layer', bounds: [0, 0, 1920, 1080] },
        { id: 'psd_2', name: 'Logo', type: 'Smart Object', bounds: [100, 100, 400, 300] },
        { id: 'psd_3', name: 'Title Text', type: 'Text', bounds: [500, 200, 1400, 350] },
        { id: 'psd_4', name: 'Subtitle', type: 'Text', bounds: [500, 400, 1400, 500] },
        { id: 'psd_5', name: 'Product Image', type: 'Smart Object', bounds: [200, 600, 800, 1000] },
        { id: 'psd_6', name: 'Call to Action', type: 'Shape', bounds: [1000, 800, 1800, 1000] },
        { id: 'psd_7', name: 'Decorative Element', type: 'Layer', bounds: [1600, 100, 1900, 400] }
    ];

    // Sample AE layers
    aeLayers = [
        { id: 'ae_1', name: 'BG_Placeholder', type: 'Solid' },
        { id: 'ae_2', name: 'LOGO_REPLACE', type: 'Placeholder' },
        { id: 'ae_3', name: 'Main_Title', type: 'Text' },
        { id: 'ae_4', name: 'Sub_Title', type: 'Text' },
        { id: 'ae_5', name: 'Product_IMG', type: 'Placeholder' },
        { id: 'ae_6', name: 'CTA_Button', type: 'Shape' },
        { id: 'ae_7', name: 'Extra_Layer_1', type: 'Null' },
        { id: 'ae_8', name: 'Extra_Layer_2', type: 'Adjustment' }
    ];

    // Sample automatic matches with confidence scores
    currentMatches = [
        { psd_id: 'psd_1', ae_id: 'ae_1', confidence: 0.95, method: 'name_similarity' },
        { psd_id: 'psd_2', ae_id: 'ae_2', confidence: 0.88, method: 'name_similarity' },
        { psd_id: 'psd_3', ae_id: 'ae_3', confidence: 0.92, method: 'name_similarity' },
        { psd_id: 'psd_4', ae_id: 'ae_4', confidence: 0.85, method: 'name_similarity' },
        { psd_id: 'psd_5', ae_id: 'ae_5', confidence: 0.78, method: 'type_similarity' },
        { psd_id: 'psd_6', ae_id: 'ae_6', confidence: 0.65, method: 'type_similarity' },
        { psd_id: 'psd_7', ae_id: null, confidence: 0.0, method: 'no_match' }
    ];

    // Keep original for reset
    originalMatches = JSON.parse(JSON.stringify(currentMatches));
}

/**
 * Get layer icon based on type
 */
function getLayerIcon(type) {
    const typeStr = (type || 'unknown').toLowerCase();

    if (typeStr.includes('text')) return '📝';
    if (typeStr.includes('image') || typeStr.includes('footage')) return '🖼️';
    if (typeStr.includes('solid')) return '🟦';
    if (typeStr.includes('shape')) return '⭐';
    if (typeStr.includes('adjustment')) return '🎨';
    if (typeStr.includes('null')) return '🔗';
    return '❓';
}

/**
 * Render the matching table
 */
function renderMatchingTable() {
    const tbody = document.getElementById('matching-table-body');
    tbody.innerHTML = '';

    currentMatches.forEach((match, index) => {
        const psdLayer = psdLayers.find(l => l.id === match.psd_id);
        const aeLayer = aeLayers.find(l => l.id === match.ae_id);

        const tr = document.createElement('tr');
        tr.dataset.index = index;
        tr.dataset.psdId = match.psd_id;
        tr.dataset.aeId = match.ae_id || '';

        // Add class for styling
        if (match.confidence < 0.7 && match.confidence > 0) {
            tr.classList.add('low-confidence');
        } else if (!match.ae_id) {
            tr.classList.add('no-match');
        }

        tr.innerHTML = `
            <td>${index + 1}</td>
            <td>
                <span class="layer-name">${psdLayer.name}</span>
                <span class="layer-type">${psdLayer.type}</span>
            </td>
            <td>
                <div class="layer-preview">
                    ${psdLayer.thumbnail ? 
                        `<img src="/${psdLayer.thumbnail}" alt="${psdLayer.name}" class="thumbnail-img" />` :
                        '<span class="no-preview">No Preview</span>'
                    }
                </div>
            </td>
            <td class="arrow-cell">→</td>
            <td>
                ${aeLayer ? `
                    <span class="layer-name">${aeLayer.name}</span>
                    <span class="layer-type">${aeLayer.type}</span>
                ` : `
                    <span class="layer-name" style="color: #ef4444;">No Match</span>
                `}
            </td>
            <td>
                <div class="layer-preview" style="font-size: 48px;">
                    ${aeLayer ? getLayerIcon(aeLayer.type) : '-'}
                </div>
            </td>
            <td>
                ${getConfidenceBadge(match.confidence)}
            </td>
        `;

        tbody.appendChild(tr);
    });
}

/**
 * Get confidence badge HTML
 */
function getConfidenceBadge(confidence) {
    if (confidence === 0) {
        return '<span class="confidence-badge confidence-none">No Match</span>';
    } else if (confidence >= 0.8) {
        return `<span class="confidence-badge confidence-high">${Math.round(confidence * 100)}%</span>`;
    } else if (confidence >= 0.7) {
        return `<span class="confidence-badge confidence-medium">${Math.round(confidence * 100)}%</span>`;
    } else {
        return `<span class="confidence-badge confidence-low">${Math.round(confidence * 100)}%</span>`;
    }
}

/**
 * Update match statistics
 */
function updateMatchStats() {
    const matched = currentMatches.filter(m => m.ae_id !== null).length;
    const total = psdLayers.length;

    document.getElementById('matched-count').textContent = matched;
    document.getElementById('total-psd-layers').textContent = total;
}

/**
 * Apply filters to table
 */
function applyFilters() {
    const showOnlyUnmatched = document.getElementById('filter-unmatched').checked;
    const showOnlyLowConfidence = document.getElementById('filter-low-confidence').checked;

    const rows = document.querySelectorAll('#matching-table-body tr');

    rows.forEach(row => {
        let show = true;

        const index = parseInt(row.dataset.index);
        const match = currentMatches[index];

        if (showOnlyUnmatched && match.ae_id !== null) {
            show = false;
        }

        if (showOnlyLowConfidence && (match.confidence >= 0.7 || match.confidence === 0)) {
            show = false;
        }

        row.style.display = show ? '' : 'none';
    });
}

/**
 * Open change match modal
 */
function openChangeMatchModal(rowIndex) {
    currentEditingRowIndex = rowIndex;
    const match = currentMatches[rowIndex];
    const psdLayer = psdLayers.find(l => l.id === match.psd_id);
    const aeLayer = aeLayers.find(l => l.id === match.ae_id);

    // Update modal content
    document.getElementById('modal-psd-layer-name').textContent = psdLayer.name;
    document.getElementById('modal-current-match').textContent = aeLayer ? aeLayer.name : 'No Match';

    // Populate AE layer dropdown
    const select = document.getElementById('modal-ae-layer-select');
    select.innerHTML = '<option value="">-- No Match --</option>';

    aeLayers.forEach(ae => {
        const option = document.createElement('option');
        option.value = ae.id;
        option.textContent = `${ae.name} (${ae.type})`;
        if (ae.id === match.ae_id) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    // Show modal
    document.getElementById('change-match-modal').classList.add('active');
}

/**
 * Close change match modal
 */
function closeChangeMatchModal() {
    document.getElementById('change-match-modal').classList.remove('active');
    currentEditingRowIndex = null;
}

/**
 * Confirm change match
 */
function confirmChangeMatch() {
    if (currentEditingRowIndex === null) return;

    const select = document.getElementById('modal-ae-layer-select');
    const newAeId = select.value || null;

    // Update match
    currentMatches[currentEditingRowIndex].ae_id = newAeId;

    // Recalculate confidence (simplified)
    if (newAeId === null) {
        currentMatches[currentEditingRowIndex].confidence = 0.0;
        currentMatches[currentEditingRowIndex].method = 'manual_skip';
    } else {
        currentMatches[currentEditingRowIndex].confidence = 1.0;
        currentMatches[currentEditingRowIndex].method = 'manual_match';
    }

    // Re-render table
    renderMatchingTable();
    updateMatchStats();

    // Close modal
    closeChangeMatchModal();

    console.log('Match updated:', currentMatches[currentEditingRowIndex]);
}

/**
 * Reset matching to original auto-match
 */
function resetMatching() {
    if (confirm('Are you sure you want to reset all matches to the original auto-match results?')) {
        console.log('Resetting matches to original...');
        currentMatches = JSON.parse(JSON.stringify(originalMatches));
        renderMatchingTable();
        updateMatchStats();

        // Setup drag-and-drop with a small delay to ensure DOM is ready
        setTimeout(() => {
            console.log('Re-setting up drag-and-drop after reset...');
            setupDragAndDrop();
        }, 100);

        applyFilters();
    }
}

/**
 * Get current matches for saving
 */
function getCurrentMatches() {
    return currentMatches
        .filter(m => m.ae_id !== null)
        .map(m => ({
            psd_layer_id: m.psd_id,
            ae_layer_id: m.ae_id,
            confidence: m.confidence || 1.0,
            method: m.method || 'manual'
        }));
}

/**
 * Cancel review and return to dashboard
 */
function cancelReview() {
    if (confirm('Discard all changes and return to dashboard?')) {
        console.log('Canceling review, returning to dashboard');
        window.location.href = '/dashboard';
    }
}

/**
 * Save and load next Stage 2 job (or dashboard if none)
 */
async function saveAndNext() {
    console.log('Save and Next clicked');

    // Validate that all layers are either matched or explicitly skipped
    const unmatchedRequired = currentMatches.filter(m =>
        m.ae_id === null && m.method !== 'manual_skip'
    );

    if (unmatchedRequired.length > 0) {
        const proceed = confirm(
            `There are ${unmatchedRequired.length} layers with no match. ` +
            `Are you sure you want to proceed? These layers will be skipped.`
        );
        if (!proceed) return;
    }

    showLoading(true);

    try {
        const matchesToSubmit = getCurrentMatches();

        // Submit to API
        const response = await fetch(`/api/job/${jobId}/approve-stage2`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: 'demo_user',
                matches: matchesToSubmit,
                next_action: 'next_job'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to approve stage 2');
        }

        const result = await response.json();

        showLoading(false);

        // Check if validation is required (critical issues found)
        if (result.requires_validation) {
            showToast(`Critical validation issues found (${result.critical_count}). Redirecting...`, 'error');
            setTimeout(() => {
                window.location.href = result.validation_url;
            }, 1500);
            return;
        }

        // Validation passed - proceed with next job or dashboard
        if (result.next_job_id) {
            // Load next job
            const msg = result.warning_count > 0
                ? `Job saved with ${result.warning_count} warnings. Loading next job...`
                : `Job ${jobId} saved. Loading next job...`;
            showToast(msg, 'success');
            setTimeout(() => {
                window.location.href = `/review-matching/${result.next_job_id}`;
            }, 800);
        } else {
            // No more jobs - return to dashboard
            showToast('No more Stage 2 jobs. Great work!', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        }

    } catch (error) {
        console.error('Error approving stage 2:', error);
        showLoading(false);
        showToast('Failed to approve: ' + error.message, 'error');
    }
}

/**
 * Save and return to dashboard
 */
async function saveAndDashboard() {
    console.log('Save and Dashboard clicked');

    // Validate that all layers are either matched or explicitly skipped
    const unmatchedRequired = currentMatches.filter(m =>
        m.ae_id === null && m.method !== 'manual_skip'
    );

    if (unmatchedRequired.length > 0) {
        const proceed = confirm(
            `There are ${unmatchedRequired.length} layers with no match. ` +
            `Are you sure you want to proceed? These layers will be skipped.`
        );
        if (!proceed) return;
    }

    showLoading(true);

    try {
        const matchesToSubmit = getCurrentMatches();

        // Submit to API
        const response = await fetch(`/api/job/${jobId}/approve-stage2`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: 'demo_user',
                matches: matchesToSubmit,
                next_action: 'dashboard'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to approve stage 2');
        }

        const result = await response.json();

        showLoading(false);

        // Check if validation is required (critical issues found)
        if (result.requires_validation) {
            showToast(`Critical validation issues found (${result.critical_count}). Redirecting...`, 'error');
            setTimeout(() => {
                window.location.href = result.validation_url;
            }, 1500);
            return;
        }

        // Validation passed - return to dashboard
        const msg = result.warning_count > 0
            ? `Job saved with ${result.warning_count} warnings`
            : `Stage 2 approved for ${jobId}`;
        showToast(msg, 'success');
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 800);

    } catch (error) {
        console.error('Error approving stage 2:', error);
        showLoading(false);
        showToast('Failed to approve: ' + error.message, 'error');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    // Icon based on type
    let icon = '✓';
    if (type === 'error') icon = '✗';
    if (type === 'info') icon = 'ℹ';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <span class="toast-close" onclick="this.parentElement.remove()">×</span>
    `;

    container.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);

    console.log(`Toast: [${type}] ${message}`);
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
 * Handle escape key to close modal
 */
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('change-match-modal');
        if (modal.classList.contains('active')) {
            closeChangeMatchModal();
        }
    }
});
