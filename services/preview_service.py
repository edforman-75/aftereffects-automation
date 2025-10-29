"""
Preview Service

Handles video preview generation operations, including rendering with After Effects,
thumbnail generation, and video metadata extraction.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from services.base_service import BaseService, Result
from core.exceptions import (
    PreviewError,
    PreviewGenerationError,
    AERenderError
)

# Import existing modules (these will remain unchanged)
from modules.phase5 import preview_generator


class PreviewService(BaseService):
    """
    Service for handling preview generation operations.

    This service wraps the existing preview_generator module and provides
    a clean API with proper error handling and logging.
    """

    def generate_preview(
        self,
        aepx_path: str,
        mappings: Dict[str, Any],
        output_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Result[Dict[str, Any]]:
        """
        Generate video preview of populated After Effects template.

        Args:
            aepx_path: Path to AEPX/AEP template file
            mappings: Content mappings from MatchingService
            output_path: Path for output video
            options: Optional rendering options (resolution, duration, format, etc.)

        Returns:
            Result containing preview info dict with:
            - success: True if successful
            - video_path: Path to generated video
            - thumbnail_path: Path to thumbnail (or None)
            - duration: Video duration in seconds
            - resolution: Video resolution (e.g., "1920x1080")
            - format: Video format
            - error: Error message (if failed)
        """
        self.log_info(f"Generating preview for: {aepx_path}")

        # Validate inputs
        validation = self._validate_preview_inputs(aepx_path, mappings, output_path)
        if not validation.is_success():
            return validation

        # Log options
        if options:
            self.log_info(f"Preview options: {options}")

        try:
            # Call existing preview generator module
            result = preview_generator.generate_preview(
                aepx_path=aepx_path,
                mappings=mappings,
                output_path=output_path,
                options=options
            )

            # Validate result structure
            if not isinstance(result, dict):
                return Result.failure("Invalid preview result structure")

            # Check if generation was successful
            success = result.get('success', False)

            if success:
                video_path = result.get('video_path')
                thumbnail_path = result.get('thumbnail_path')
                duration = result.get('duration')

                self.log_info(
                    f"Preview generated successfully: {video_path} "
                    f"({duration}s)"
                )

                return Result.success(result)
            else:
                error_msg = result.get('error', 'Unknown error')
                self.log_error(f"Preview generation failed: {error_msg}")
                return Result.failure(error_msg)

        except Exception as e:
            self.log_error(f"Preview generation exception: {aepx_path}", exc=e)
            return Result.failure(f"Preview generation failed: {str(e)}")

    def check_aerender_available(self) -> Result[str]:
        """
        Check if After Effects aerender is available on the system.

        Returns:
            Result containing path to aerender if found, or error message
        """
        self.log_info("Checking for aerender availability")

        try:
            aerender_path = preview_generator.check_aerender_available()

            if aerender_path:
                self.log_info(f"aerender found at: {aerender_path}")
                return Result.success(aerender_path)
            else:
                self.log_error("aerender not found on system")
                return Result.failure(
                    "After Effects aerender not found. "
                    "After Effects must be installed."
                )

        except Exception as e:
            self.log_error("Error checking aerender availability", exc=e)
            return Result.failure(f"Error checking aerender: {str(e)}")

    def validate_preview_output(self, video_path: str) -> Result[bool]:
        """
        Validate that a preview video was generated successfully.

        Args:
            video_path: Path to preview video

        Returns:
            Result containing True if valid, or error message
        """
        self.log_info(f"Validating preview output: {video_path}")

        # Check if file exists
        if not os.path.exists(video_path):
            return Result.failure(f"Preview video not found: {video_path}")

        # Check file size
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            return Result.failure("Preview video is empty (0 bytes)")

        size_kb = file_size / 1024
        size_mb = size_kb / 1024

        self.log_info(f"Preview video valid: {size_mb:.2f}MB")
        return Result.success(True)

    def get_video_info(self, video_path: str) -> Result[Dict[str, Any]]:
        """
        Get metadata about a video file.

        Args:
            video_path: Path to video file

        Returns:
            Result containing video info dict with:
            - duration: Duration in seconds
            - resolution: Resolution string (e.g., "1920x1080")
            - fps: Frames per second
        """
        self.log_info(f"Getting video info: {video_path}")

        # Validate file exists
        if not os.path.exists(video_path):
            return Result.failure(f"Video file not found: {video_path}")

        try:
            info = preview_generator.get_video_info(video_path)

            self.log_info(
                f"Video info: duration={info.get('duration')}s, "
                f"resolution={info.get('resolution')}, "
                f"fps={info.get('fps')}"
            )

            return Result.success(info)

        except Exception as e:
            self.log_error("Failed to get video info", exc=e)
            return Result.failure(f"Failed to get video info: {str(e)}")

    def generate_thumbnail(
        self,
        video_path: str,
        timestamp: float = 0.5
    ) -> Result[Optional[str]]:
        """
        Generate a thumbnail from a video file.

        Args:
            video_path: Path to video file
            timestamp: Time in seconds to extract frame

        Returns:
            Result containing path to thumbnail JPEG, or None if ffmpeg unavailable
        """
        self.log_info(f"Generating thumbnail from: {video_path} at {timestamp}s")

        # Validate file exists
        if not os.path.exists(video_path):
            return Result.failure(f"Video file not found: {video_path}")

        try:
            thumbnail_path = preview_generator.generate_thumbnail(
                video_path=video_path,
                timestamp=timestamp
            )

            if thumbnail_path:
                self.log_info(f"Thumbnail generated: {thumbnail_path}")
                return Result.success(thumbnail_path)
            else:
                self.log_info("Thumbnail generation skipped (ffmpeg not available)")
                return Result.success(None)

        except Exception as e:
            self.log_error("Thumbnail generation failed", exc=e)
            return Result.failure(f"Thumbnail generation failed: {str(e)}")

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default rendering options.

        Returns:
            Dictionary with default options
        """
        return preview_generator.DEFAULT_OPTIONS.copy()

    def validate_options(self, options: Dict[str, Any]) -> Result[bool]:
        """
        Validate preview rendering options.

        Args:
            options: Options dict to validate

        Returns:
            Result containing True if valid, or error message
        """
        try:
            # Valid resolution options
            valid_resolutions = ['full', 'half', 'third', 'quarter']
            resolution = options.get('resolution')
            if resolution and resolution not in valid_resolutions:
                return Result.failure(
                    f"Invalid resolution: {resolution}. "
                    f"Must be one of: {', '.join(valid_resolutions)}"
                )

            # Valid format options
            valid_formats = ['mp4', 'mov', 'gif']
            format_opt = options.get('format')
            if format_opt and format_opt not in valid_formats:
                return Result.failure(
                    f"Invalid format: {format_opt}. "
                    f"Must be one of: {', '.join(valid_formats)}"
                )

            # Valid quality options
            valid_qualities = ['draft', 'medium', 'high']
            quality = options.get('quality')
            if quality and quality not in valid_qualities:
                return Result.failure(
                    f"Invalid quality: {quality}. "
                    f"Must be one of: {', '.join(valid_qualities)}"
                )

            # Validate duration
            duration = options.get('duration')
            if duration and duration != 'full':
                if not isinstance(duration, (int, float)) or duration <= 0:
                    return Result.failure(
                        f"Invalid duration: {duration}. "
                        "Must be positive number or 'full'"
                    )

            # Validate FPS
            fps = options.get('fps')
            if fps:
                if not isinstance(fps, (int, float)) or fps <= 0 or fps > 120:
                    return Result.failure(
                        f"Invalid fps: {fps}. Must be between 1 and 120"
                    )

            self.log_info("Preview options validation passed")
            return Result.success(True)

        except Exception as e:
            self.log_error("Options validation failed", exc=e)
            return Result.failure(f"Options validation failed: {str(e)}")

    def _validate_preview_inputs(
        self,
        aepx_path: str,
        mappings: Dict[str, Any],
        output_path: str
    ) -> Result[bool]:
        """
        Validate inputs for preview generation.

        Args:
            aepx_path: AEPX file path to validate
            mappings: Mappings dict to validate
            output_path: Output path to validate

        Returns:
            Result with True if valid, or error message
        """
        # Validate AEPX path
        if not os.path.exists(aepx_path):
            return Result.failure(f"AEPX file not found: {aepx_path}")

        if not aepx_path.lower().endswith('.aepx'):
            return Result.failure("File must have .aepx extension")

        # Validate mappings
        if not isinstance(mappings, dict):
            return Result.failure("Invalid mappings: expected dict")

        # Validate output path
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            return Result.failure(f"Output directory does not exist: {output_dir}")

        # Check output format
        valid_extensions = ['.mp4', '.mov', '.gif']
        output_ext = Path(output_path).suffix.lower()
        if output_ext not in valid_extensions:
            return Result.failure(
                f"Invalid output format: {output_ext}. "
                f"Must be one of: {', '.join(valid_extensions)}"
            )

        self.log_info("Preview input validation passed")
        return Result.success(True)
