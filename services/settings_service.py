"""
Settings Service

Provides settings management operations using the service layer pattern.
Handles loading, saving, validation, and reset of application settings.
"""

from services.base_service import BaseService, Result
from config.settings import Settings
import os
from typing import Dict, Any


class SettingsService(BaseService):
    """
    Handle settings operations.

    Provides:
    - Get current settings
    - Update settings with validation
    - Reset to defaults
    - Validate settings
    """

    def __init__(self, logger, config_path='config.json'):
        """
        Initialize settings service.

        Args:
            logger: Logger instance
            config_path: Path to configuration file
        """
        super().__init__(logger)
        self.config_path = config_path
        self.settings = Settings.load(config_path)

    def get_settings(self) -> Result[Dict[str, Any]]:
        """
        Get current settings.

        Returns:
            Result containing settings dictionary or error
        """
        try:
            self.log_info("Retrieved current settings")
            return Result.success(self.settings.to_dict())
        except Exception as e:
            self.log_error("Failed to get settings", exc=e)
            return Result.failure(str(e))

    def update_settings(self, settings_data: Dict[str, Any]) -> Result[Dict[str, Any]]:
        """
        Update settings and save to file.

        Validates settings before saving. If validation fails,
        settings are not updated.

        Args:
            settings_data: Dictionary with settings updates

        Returns:
            Result containing updated settings or error
        """
        try:
            # Load current settings
            self.settings = Settings.load(self.config_path)

            # Update with new data
            if 'directories' in settings_data:
                for key, value in settings_data['directories'].items():
                    if hasattr(self.settings.directories, key):
                        setattr(self.settings.directories, key, value)
                    else:
                        self.log_warning(f"Unknown directory setting: {key}")

            if 'conflict_thresholds' in settings_data:
                for key, value in settings_data['conflict_thresholds'].items():
                    if hasattr(self.settings.conflict_thresholds, key):
                        setattr(self.settings.conflict_thresholds, key, value)
                    else:
                        self.log_warning(f"Unknown conflict threshold: {key}")

            if 'preview_defaults' in settings_data:
                for key, value in settings_data['preview_defaults'].items():
                    if hasattr(self.settings.preview_defaults, key):
                        setattr(self.settings.preview_defaults, key, value)
                    else:
                        self.log_warning(f"Unknown preview default: {key}")

            if 'advanced' in settings_data:
                for key, value in settings_data['advanced'].items():
                    if hasattr(self.settings.advanced, key):
                        setattr(self.settings.advanced, key, value)
                    else:
                        self.log_warning(f"Unknown advanced setting: {key}")

            # Validate settings
            is_valid, error = self.settings.validate()
            if not is_valid:
                self.log_error(f"Settings validation failed: {error}")
                return Result.failure(f"Invalid settings: {error}")

            # Save to file
            self.settings.save(self.config_path)
            self.log_info("Settings updated successfully")

            return Result.success(self.settings.to_dict())

        except Exception as e:
            self.log_error("Failed to update settings", exc=e)
            return Result.failure(str(e))

    def reset_to_defaults(self) -> Result[Dict[str, Any]]:
        """
        Reset settings to defaults.

        Creates new default settings and saves to file.

        Returns:
            Result containing default settings or error
        """
        try:
            self.settings = Settings()
            self.settings.save(self.config_path)
            self.log_info("Settings reset to defaults")
            return Result.success(self.settings.to_dict())
        except Exception as e:
            self.log_error("Failed to reset settings", exc=e)
            return Result.failure(str(e))

    def validate_settings(self) -> Result[Dict[str, bool]]:
        """
        Validate current settings.

        Returns:
            Result containing validation status or error
        """
        try:
            is_valid, error = self.settings.validate()
            if not is_valid:
                self.log_error(f"Settings validation failed: {error}")
                return Result.failure(error)

            self.log_info("Settings validation passed")
            return Result.success({"valid": True})
        except Exception as e:
            self.log_error("Settings validation error", exc=e)
            return Result.failure(str(e))

    def get_section(self, section_name: str) -> Result[Dict[str, Any]]:
        """
        Get a specific settings section.

        Args:
            section_name: Name of section ('directories', 'conflict_thresholds', etc.)

        Returns:
            Result containing section data or error
        """
        try:
            if section_name == 'directories':
                from dataclasses import asdict
                return Result.success(asdict(self.settings.directories))
            elif section_name == 'conflict_thresholds':
                from dataclasses import asdict
                return Result.success(asdict(self.settings.conflict_thresholds))
            elif section_name == 'preview_defaults':
                from dataclasses import asdict
                return Result.success(asdict(self.settings.preview_defaults))
            elif section_name == 'advanced':
                from dataclasses import asdict
                return Result.success(asdict(self.settings.advanced))
            else:
                return Result.failure(f"Unknown section: {section_name}")
        except Exception as e:
            self.log_error(f"Failed to get section {section_name}", exc=e)
            return Result.failure(str(e))

    def update_section(self, section_name: str, section_data: Dict[str, Any]) -> Result[Dict[str, Any]]:
        """
        Update a specific settings section.

        Args:
            section_name: Name of section
            section_data: Dictionary with section updates

        Returns:
            Result containing updated settings or error
        """
        try:
            # Reload to get latest
            self.settings = Settings.load(self.config_path)

            # Update the specific section
            if section_name == 'directories':
                for key, value in section_data.items():
                    if hasattr(self.settings.directories, key):
                        setattr(self.settings.directories, key, value)
            elif section_name == 'conflict_thresholds':
                for key, value in section_data.items():
                    if hasattr(self.settings.conflict_thresholds, key):
                        setattr(self.settings.conflict_thresholds, key, value)
            elif section_name == 'preview_defaults':
                for key, value in section_data.items():
                    if hasattr(self.settings.preview_defaults, key):
                        setattr(self.settings.preview_defaults, key, value)
            elif section_name == 'advanced':
                for key, value in section_data.items():
                    if hasattr(self.settings.advanced, key):
                        setattr(self.settings.advanced, key, value)
            else:
                return Result.failure(f"Unknown section: {section_name}")

            # Validate
            is_valid, error = self.settings.validate()
            if not is_valid:
                return Result.failure(f"Invalid settings: {error}")

            # Save
            self.settings.save(self.config_path)
            self.log_info(f"Updated section: {section_name}")

            return Result.success(self.settings.to_dict())

        except Exception as e:
            self.log_error(f"Failed to update section {section_name}", exc=e)
            return Result.failure(str(e))
