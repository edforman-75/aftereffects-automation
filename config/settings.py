"""
Application Settings Management

Provides configuration management with validation, save/load functionality,
and type-safe settings access.
"""

from dataclasses import dataclass, asdict
import json
import os
from typing import Optional


@dataclass
class DirectorySettings:
    """File location settings"""
    upload_dir: str = 'uploads'
    preview_dir: str = 'previews'
    renders_dir: str = 'renders'  # Final render output location
    output_dir: str = 'output'
    fonts_dir: str = 'fonts'
    footage_dir: str = 'sample_files/footage'  # Working footage location from successful test
    logs_dir: str = 'logs'


@dataclass
class ConflictThresholds:
    """Conflict detection thresholds - these worked well for UC Irvine test"""
    text_overflow_critical: int = 10  # % beyond bounds
    text_overflow_warning: int = 5
    aspect_ratio_critical: float = 0.2  # ratio difference
    aspect_ratio_warning: float = 0.1
    resolution_mismatch_warning: int = 100  # pixels


@dataclass
class PreviewDefaults:
    """Default preview generation settings - exactly what worked in our test"""
    duration: int = 5  # seconds - perfect length for preview
    resolution: str = 'half'  # Gives good quality without being slow
    fps: int = 15  # Good balance for preview
    format: str = 'mp4'
    quality: str = 'draft'  # draft, medium, high


@dataclass
class FileValidationSettings:
    """File upload validation settings"""
    allowed_psd_extensions: set = None
    allowed_aepx_extensions: set = None
    allowed_font_extensions: set = None
    max_psd_size_mb: int = 50
    max_aepx_size_mb: int = 10
    max_font_size_mb: int = 5

    def __post_init__(self):
        """Initialize sets with default values if not provided"""
        if self.allowed_psd_extensions is None:
            self.allowed_psd_extensions = {'psd'}
        if self.allowed_aepx_extensions is None:
            self.allowed_aepx_extensions = {'aepx', 'aep'}
        if self.allowed_font_extensions is None:
            self.allowed_font_extensions = {'ttf', 'otf', 'woff', 'woff2'}


@dataclass
class AdvancedSettings:
    """Advanced configuration"""
    ml_confidence_threshold: float = 0.7  # Our matching worked great at this level
    aerender_path: str = '/Applications/Adobe After Effects 2025/aerender'
    max_file_size_mb: int = 500
    auto_font_substitution: bool = False
    enable_debug_logging: bool = True  # Enable logs for production debugging
    cleanup_temp_files: bool = False  # Keep temp files for inspection
    cleanup_age_hours: int = 1  # Age in hours before cleaning up temp files


@dataclass
class Settings:
    """
    Application settings with validation and persistence.

    Provides:
    - Type-safe settings access
    - Validation before save
    - JSON persistence
    - Default values
    """

    directories: DirectorySettings
    conflict_thresholds: ConflictThresholds
    preview_defaults: PreviewDefaults
    file_validation: FileValidationSettings
    advanced: AdvancedSettings

    def __init__(self):
        self.directories = DirectorySettings()
        self.conflict_thresholds = ConflictThresholds()
        self.preview_defaults = PreviewDefaults()
        self.file_validation = FileValidationSettings()
        self.advanced = AdvancedSettings()

    @classmethod
    def load(cls, config_path='config.json') -> 'Settings':
        """
        Load settings from JSON file, preserving existing values.

        Strategy:
        1. Start with defaults from dataclasses
        2. Override with values from config file (existing values take precedence)
        3. Handle migration from old field names
        4. Save updated config if migration occurred

        Args:
            config_path: Path to JSON configuration file

        Returns:
            Settings instance with merged defaults and existing values
        """
        # Start with defaults
        instance = cls()

        if not os.path.exists(config_path):
            # Create default config file
            instance.save(config_path)
            return instance

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config.json, using defaults: {e}")
            instance.save(config_path)
            return instance

        # Track if migration occurred
        migrated = False

        # Load directories with migration from old format
        if 'directories' in data:
            dir_data = data['directories']
            # Start with defaults, then override with file values
            defaults = asdict(instance.directories)

            # Migrate old field names to new ones
            if 'psd_input' in dir_data or 'aepx_input' in dir_data:
                migrated = True
                defaults['upload_dir'] = dir_data.get('upload_dir',
                    dir_data.get('psd_input', dir_data.get('aepx_input', defaults['upload_dir'])))

            if 'output_previews' in dir_data:
                migrated = True
                defaults['preview_dir'] = dir_data.get('preview_dir',
                    dir_data.get('output_previews', defaults['preview_dir']))

            if 'output_scripts' in dir_data:
                migrated = True
                defaults['output_dir'] = dir_data.get('output_dir',
                    dir_data.get('output_scripts', defaults['output_dir']))

            if 'fonts' in dir_data:
                migrated = True
                defaults['fonts_dir'] = dir_data.get('fonts_dir',
                    dir_data.get('fonts', defaults['fonts_dir']))

            if 'footage' in dir_data:
                migrated = True
                defaults['footage_dir'] = dir_data.get('footage_dir',
                    dir_data.get('footage', defaults['footage_dir']))

            # Override defaults with any new-style fields from config
            for key in defaults:
                if key in dir_data:
                    defaults[key] = dir_data[key]

            instance.directories = DirectorySettings(**defaults)

        # Load conflict thresholds - preserve existing, use defaults for new fields
        if 'conflict_thresholds' in data:
            defaults = asdict(instance.conflict_thresholds)
            defaults.update(data['conflict_thresholds'])
            instance.conflict_thresholds = ConflictThresholds(**defaults)

        # Load preview defaults - preserve existing, use defaults for new fields
        if 'preview_defaults' in data:
            defaults = asdict(instance.preview_defaults)
            defaults.update(data['preview_defaults'])
            instance.preview_defaults = PreviewDefaults(**defaults)

        # Load file validation settings - preserve existing, use defaults for new fields
        if 'file_validation' in data:
            fv_data = data['file_validation']
            # Convert lists back to sets for extension fields
            if 'allowed_psd_extensions' in fv_data and isinstance(fv_data['allowed_psd_extensions'], list):
                fv_data['allowed_psd_extensions'] = set(fv_data['allowed_psd_extensions'])
            if 'allowed_aepx_extensions' in fv_data and isinstance(fv_data['allowed_aepx_extensions'], list):
                fv_data['allowed_aepx_extensions'] = set(fv_data['allowed_aepx_extensions'])
            if 'allowed_font_extensions' in fv_data and isinstance(fv_data['allowed_font_extensions'], list):
                fv_data['allowed_font_extensions'] = set(fv_data['allowed_font_extensions'])
            instance.file_validation = FileValidationSettings(**fv_data)

        # Load advanced settings - preserve existing, use defaults for new fields
        if 'advanced' in data:
            adv_data = data['advanced']
            defaults = asdict(instance.advanced)

            # Handle old field name migrations
            if 'max_psd_size_mb' in adv_data and 'max_file_size_mb' not in adv_data:
                migrated = True
                defaults['max_file_size_mb'] = adv_data['max_psd_size_mb']

            # Override defaults with values from config
            defaults.update(adv_data)
            instance.advanced = AdvancedSettings(**defaults)

        # Save if migration occurred to update file with new format
        if migrated:
            instance.save(config_path)

        return instance

    def save(self, config_path='config.json'):
        """
        Save settings to JSON file.

        Args:
            config_path: Path to JSON configuration file
        """
        # Convert file_validation dataclass, converting sets to lists for JSON
        fv_dict = asdict(self.file_validation)
        fv_dict['allowed_psd_extensions'] = list(fv_dict['allowed_psd_extensions'])
        fv_dict['allowed_aepx_extensions'] = list(fv_dict['allowed_aepx_extensions'])
        fv_dict['allowed_font_extensions'] = list(fv_dict['allowed_font_extensions'])

        data = {
            'directories': asdict(self.directories),
            'conflict_thresholds': asdict(self.conflict_thresholds),
            'preview_defaults': asdict(self.preview_defaults),
            'file_validation': fv_dict,
            'advanced': asdict(self.advanced)
        }

        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate settings and return (is_valid, error_message).

        Checks:
        - Directory paths are valid
        - Thresholds are in valid ranges
        - Preview settings are valid
        - After Effects path exists
        - ML threshold is valid

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """

        # Validate directories exist or can be created
        for dir_name in ['upload_dir', 'preview_dir', 'renders_dir', 'output_dir', 'fonts_dir', 'footage_dir', 'logs_dir']:
            dir_path = getattr(self.directories, dir_name)
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create directory '{dir_path}': {str(e)}"

        # Validate thresholds are in valid ranges
        if not (0 <= self.conflict_thresholds.text_overflow_critical <= 100):
            return False, "Text overflow critical threshold must be between 0-100%"

        if not (0 <= self.conflict_thresholds.text_overflow_warning <= 100):
            return False, "Text overflow warning threshold must be between 0-100%"

        if self.conflict_thresholds.text_overflow_warning > self.conflict_thresholds.text_overflow_critical:
            return False, "Warning threshold must be less than critical threshold"

        if not (0.0 <= self.conflict_thresholds.aspect_ratio_critical <= 1.0):
            return False, "Aspect ratio critical threshold must be between 0.0-1.0"

        if not (0.0 <= self.conflict_thresholds.aspect_ratio_warning <= 1.0):
            return False, "Aspect ratio warning threshold must be between 0.0-1.0"

        if self.conflict_thresholds.aspect_ratio_warning > self.conflict_thresholds.aspect_ratio_critical:
            return False, "Aspect ratio warning must be less than critical threshold"

        if self.conflict_thresholds.resolution_mismatch_warning < 0:
            return False, "Resolution mismatch warning must be positive"

        # Validate preview settings
        if self.preview_defaults.resolution not in ['full', 'half', 'quarter']:
            return False, "Preview resolution must be 'full', 'half', or 'quarter'"

        if not (1 <= self.preview_defaults.duration <= 60):
            return False, "Preview duration must be between 1-60 seconds"

        if not (10 <= self.preview_defaults.fps <= 60):
            return False, "Preview FPS must be between 10-60"

        if self.preview_defaults.format not in ['mp4', 'mov', 'avi']:
            return False, "Preview format must be 'mp4', 'mov', or 'avi'"

        if self.preview_defaults.quality not in ['draft', 'medium', 'high']:
            return False, "Preview quality must be 'draft', 'medium', or 'high'"

        # Validate After Effects path
        if not os.path.exists(self.advanced.aerender_path):
            return False, f"After Effects aerender not found at: {self.advanced.aerender_path}"

        # Validate ML threshold
        if not (0.0 <= self.advanced.ml_confidence_threshold <= 1.0):
            return False, "ML confidence threshold must be between 0.0-1.0"

        # Validate max file size
        if not (1 <= self.advanced.max_file_size_mb <= 5000):
            return False, "Max file size must be between 1-5000 MB"

        return True, None

    def to_dict(self) -> dict:
        """
        Convert settings to dictionary.

        Returns:
            Dictionary representation of all settings
        """
        # Convert file_validation, converting sets to lists for JSON compatibility
        fv_dict = asdict(self.file_validation)
        fv_dict['allowed_psd_extensions'] = list(fv_dict['allowed_psd_extensions'])
        fv_dict['allowed_aepx_extensions'] = list(fv_dict['allowed_aepx_extensions'])
        fv_dict['allowed_font_extensions'] = list(fv_dict['allowed_font_extensions'])

        return {
            'directories': asdict(self.directories),
            'conflict_thresholds': asdict(self.conflict_thresholds),
            'preview_defaults': asdict(self.preview_defaults),
            'file_validation': fv_dict,
            'advanced': asdict(self.advanced)
        }


# Global settings instance
settings = Settings.load()
