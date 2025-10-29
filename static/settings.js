/**
 * Settings Page JavaScript
 * Handles loading, saving, validation, and UI interactions
 */

// Track if settings have been modified
let settingsModified = false;
let originalSettings = null;

// Load settings when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();

    // Track changes to mark as modified
    document.querySelectorAll('.setting-input, input[type="range"], input[type="checkbox"]').forEach(input => {
        input.addEventListener('change', function() {
            settingsModified = true;
        });
    });

    // Warn on page leave if unsaved changes
    window.addEventListener('beforeunload', function(e) {
        if (settingsModified) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
});

/**
 * Load settings from API
 */
async function loadSettings() {
    try {
        const response = await fetch('/settings');
        const data = await response.json();

        if (data.success) {
            originalSettings = JSON.parse(JSON.stringify(data.settings));
            populateSettings(data.settings);
            settingsModified = false;
        } else {
            showStatus('Failed to load settings: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Error loading settings: ' + error.message, 'error');
    }
}

/**
 * Populate form fields with settings data
 */
function populateSettings(settings) {
    // Directories
    document.getElementById('upload_dir').value = settings.directories.upload_dir || '';
    document.getElementById('preview_dir').value = settings.directories.preview_dir || '';
    document.getElementById('output_dir').value = settings.directories.output_dir || '';
    document.getElementById('fonts_dir').value = settings.directories.fonts_dir || '';
    document.getElementById('footage_dir').value = settings.directories.footage_dir || '';
    document.getElementById('logs_dir').value = settings.directories.logs_dir || '';

    // Conflict Thresholds
    setSliderValue('text_overflow_critical', settings.conflict_thresholds.text_overflow_critical, '%');
    setSliderValue('text_overflow_warning', settings.conflict_thresholds.text_overflow_warning, '%');
    setSliderValue('aspect_ratio_critical', settings.conflict_thresholds.aspect_ratio_critical, '');
    setSliderValue('aspect_ratio_warning', settings.conflict_thresholds.aspect_ratio_warning, '');
    setSliderValue('resolution_mismatch_warning', settings.conflict_thresholds.resolution_mismatch_warning, 'px');

    // Preview Defaults
    setSliderValue('preview_duration', settings.preview_defaults.duration, 's');
    document.getElementById('preview_resolution').value = settings.preview_defaults.resolution || 'half';
    setSliderValue('preview_fps', settings.preview_defaults.fps, ' fps');
    document.getElementById('preview_format').value = settings.preview_defaults.format || 'mp4';
    document.getElementById('preview_quality').value = settings.preview_defaults.quality || 'draft';

    // Advanced
    setSliderValue('ml_confidence_threshold', settings.advanced.ml_confidence_threshold, '');
    document.getElementById('aerender_path').value = settings.advanced.aerender_path || '';
    setSliderValue('max_file_size_mb', settings.advanced.max_file_size_mb, ' MB');
    document.getElementById('auto_font_substitution').checked = settings.advanced.auto_font_substitution || false;
    document.getElementById('enable_debug_logging').checked = settings.advanced.enable_debug_logging || false;
    document.getElementById('cleanup_temp_files').checked = settings.advanced.cleanup_temp_files || false;
}

/**
 * Set slider value and update display
 */
function setSliderValue(id, value, suffix) {
    const slider = document.getElementById(id);
    if (slider) {
        slider.value = value;
        const valueDisplay = document.getElementById(id + '_value');
        if (valueDisplay) {
            valueDisplay.textContent = value + suffix;
        }
    }
}

/**
 * Update slider value display
 */
function updateSliderValue(slider, valueId) {
    const valueDisplay = document.getElementById(valueId);
    if (!valueDisplay) return;

    let value = parseFloat(slider.value);
    let suffix = '';

    // Determine suffix based on slider ID
    if (slider.id.includes('overflow')) {
        suffix = '%';
    } else if (slider.id.includes('resolution_mismatch')) {
        suffix = 'px';
    } else if (slider.id.includes('fps')) {
        suffix = ' fps';
    } else if (slider.id.includes('duration')) {
        suffix = 's';
    } else if (slider.id.includes('max_file_size')) {
        suffix = ' MB';
    }

    valueDisplay.textContent = value + suffix;
}

/**
 * Collect settings from form
 */
function collectSettings() {
    return {
        directories: {
            upload_dir: document.getElementById('upload_dir').value,
            preview_dir: document.getElementById('preview_dir').value,
            output_dir: document.getElementById('output_dir').value,
            fonts_dir: document.getElementById('fonts_dir').value,
            footage_dir: document.getElementById('footage_dir').value,
            logs_dir: document.getElementById('logs_dir').value
        },
        conflict_thresholds: {
            text_overflow_critical: parseInt(document.getElementById('text_overflow_critical').value),
            text_overflow_warning: parseInt(document.getElementById('text_overflow_warning').value),
            aspect_ratio_critical: parseFloat(document.getElementById('aspect_ratio_critical').value),
            aspect_ratio_warning: parseFloat(document.getElementById('aspect_ratio_warning').value),
            resolution_mismatch_warning: parseInt(document.getElementById('resolution_mismatch_warning').value)
        },
        preview_defaults: {
            duration: parseInt(document.getElementById('preview_duration').value),
            resolution: document.getElementById('preview_resolution').value,
            fps: parseInt(document.getElementById('preview_fps').value),
            format: document.getElementById('preview_format').value,
            quality: document.getElementById('preview_quality').value
        },
        advanced: {
            ml_confidence_threshold: parseFloat(document.getElementById('ml_confidence_threshold').value),
            aerender_path: document.getElementById('aerender_path').value,
            max_file_size_mb: parseInt(document.getElementById('max_file_size_mb').value),
            auto_font_substitution: document.getElementById('auto_font_substitution').checked,
            enable_debug_logging: document.getElementById('enable_debug_logging').checked,
            cleanup_temp_files: document.getElementById('cleanup_temp_files').checked
        }
    };
}

/**
 * Save settings to API
 */
async function saveSettings() {
    const settings = collectSettings();

    // Validate before saving
    const validation = validateSettings(settings);
    if (!validation.valid) {
        showStatus('Validation error: ' + validation.error, 'error');
        return;
    }

    try {
        const response = await fetch('/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Settings saved successfully!', 'success');
            originalSettings = JSON.parse(JSON.stringify(data.settings));
            settingsModified = false;
        } else {
            showStatus('Failed to save settings: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showStatus('Error saving settings: ' + error.message, 'error');
    }
}

/**
 * Reset settings to defaults
 */
async function resetSettings() {
    if (!confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/settings/reset', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Settings reset to defaults!', 'success');
            populateSettings(data.settings);
            originalSettings = JSON.parse(JSON.stringify(data.settings));
            settingsModified = false;
        } else {
            showStatus('Failed to reset settings: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showStatus('Error resetting settings: ' + error.message, 'error');
    }
}

/**
 * Validate settings
 */
function validateSettings(settings) {
    // Validate directories are not empty
    for (const [key, value] of Object.entries(settings.directories)) {
        if (!value || value.trim() === '') {
            return { valid: false, error: `Directory "${key}" cannot be empty` };
        }
    }

    // Validate thresholds
    if (settings.conflict_thresholds.text_overflow_warning > settings.conflict_thresholds.text_overflow_critical) {
        return { valid: false, error: 'Text overflow warning must be less than critical threshold' };
    }

    if (settings.conflict_thresholds.aspect_ratio_warning > settings.conflict_thresholds.aspect_ratio_critical) {
        return { valid: false, error: 'Aspect ratio warning must be less than critical threshold' };
    }

    // Validate preview settings
    if (settings.preview_defaults.duration < 1 || settings.preview_defaults.duration > 60) {
        return { valid: false, error: 'Preview duration must be between 1-60 seconds' };
    }

    if (settings.preview_defaults.fps < 10 || settings.preview_defaults.fps > 60) {
        return { valid: false, error: 'Preview FPS must be between 10-60' };
    }

    // Validate advanced settings
    if (settings.advanced.ml_confidence_threshold < 0 || settings.advanced.ml_confidence_threshold > 1) {
        return { valid: false, error: 'ML confidence threshold must be between 0.0-1.0' };
    }

    if (!settings.advanced.aerender_path || settings.advanced.aerender_path.trim() === '') {
        return { valid: false, error: 'After Effects aerender path cannot be empty' };
    }

    return { valid: true };
}

/**
 * Show status message
 */
function showStatus(message, type) {
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = message;
    statusDiv.className = 'status-message ' + type;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusDiv.className = 'status-message hidden';
    }, 5000);
}

/**
 * Show/hide tabs
 */
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Activate corresponding button
    event.target.classList.add('active');
}
