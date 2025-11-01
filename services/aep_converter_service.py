"""
Service for converting AEP files to AEPX format using After Effects.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from services.base_service import BaseService, Result


class AepConverterService(BaseService):
    """Converts AEP (binary) files to AEPX (XML) format using After Effects automation."""

    def __init__(self, logger, after_effects_path: Optional[str] = None):
        super().__init__(logger)
        self.after_effects_path = after_effects_path or "/Applications/Adobe After Effects 2025/Adobe After Effects 2025.app"
        self.timeout = 120  # 2 minutes timeout for conversion

    def convert_aep_to_aepx(self, aep_path: str, output_path: Optional[str] = None) -> Result[str]:
        """
        Convert AEP file to AEPX format using After Effects.

        Args:
            aep_path: Path to the .aep file
            output_path: Optional output path for .aepx file (defaults to same location as .aep)

        Returns:
            Result containing the path to the generated .aepx file
        """
        self.log_info("=" * 70)
        self.log_info("AEP TO AEPX CONVERSION STARTED")
        self.log_info("=" * 70)
        self.log_info(f"AEP path: {aep_path}")
        self.log_info(f"AEP exists: {os.path.exists(aep_path)}")

        try:
            # Validate input file
            if not os.path.exists(aep_path):
                return Result.failure(f"AEP file not found: {aep_path}")

            if not aep_path.lower().endswith('.aep'):
                return Result.failure(f"File is not an AEP file: {aep_path}")

            # Determine output path
            if output_path is None:
                aep_file = Path(aep_path)
                output_path = str(aep_file.with_suffix('.aepx'))

            self.log_info(f"Output AEPX path: {output_path}")

            # Check if After Effects is available
            if not os.path.exists(self.after_effects_path):
                return Result.failure(
                    "After Effects not found. Please install After Effects or use .aepx files instead. "
                    f"Expected location: {self.after_effects_path}"
                )

            # Generate AppleScript to convert AEP to AEPX
            applescript = self._generate_conversion_script(aep_path, output_path)

            # Execute conversion
            self.log_info("Executing After Effects conversion script...")
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            self.log_info(f"AppleScript return code: {result.returncode}")
            self.log_info(f"AppleScript stdout: {result.stdout}")
            if result.stderr:
                self.log_warning(f"AppleScript stderr: {result.stderr}")

            if result.returncode != 0:
                return Result.failure(
                    f"AEP conversion failed: {result.stderr or 'Unknown error'}"
                )

            # Verify output file was created
            if not os.path.exists(output_path):
                return Result.failure(
                    "AEP conversion completed but AEPX file was not created. "
                    "The AEP file may be corrupted or use an unsupported format."
                )

            file_size = os.path.getsize(output_path)
            self.log_info(f"✅ Conversion successful! AEPX file created: {output_path} ({file_size:,} bytes)")
            self.log_info("=" * 70)

            return Result.success(output_path)

        except subprocess.TimeoutExpired:
            self.log_error("AEP conversion timed out after {self.timeout} seconds")
            return Result.failure(
                f"AEP conversion timed out. The file may be too large or complex. "
                f"Please try converting manually or use a smaller template."
            )
        except Exception as e:
            self.log_error(f"AEP conversion error: {e}", exc_info=True)
            return Result.failure(f"AEP conversion failed: {str(e)}")

    def _generate_conversion_script(self, aep_path: str, output_path: str) -> str:
        """Generate AppleScript to convert AEP to AEPX."""

        # Escape paths for AppleScript
        aep_path_escaped = aep_path.replace('\\', '\\\\').replace('"', '\\"')
        output_path_escaped = output_path.replace('\\', '\\\\').replace('"', '\\"')

        script = f'''
        tell application "Adobe After Effects 2025"
            -- Don't activate to keep AE in background
            try
                -- Open the AEP file
                open POSIX file "{aep_path_escaped}"

                -- Save as AEPX (XML format)
                set outputFile to POSIX file "{output_path_escaped}"
                save in outputFile

                -- Close project without saving again
                close

                return "success"
            on error errMsg
                -- Try to close if still open
                try
                    close
                end try
                error "Failed to convert AEP: " & errMsg
            end try
        end tell
        '''

        return script

    def check_after_effects_available(self) -> Result[bool]:
        """Check if After Effects is installed and accessible."""
        try:
            if os.path.exists(self.after_effects_path):
                self.log_info(f"After Effects found at: {self.after_effects_path}")
                return Result.success(True)
            else:
                self.log_warning(f"After Effects not found at: {self.after_effects_path}")
                return Result.success(False)
        except Exception as e:
            self.log_error(f"Error checking After Effects: {e}")
            return Result.failure(str(e))

    def get_supported_versions(self) -> list:
        """Get list of After Effects versions that support this conversion."""
        return [
            "Adobe After Effects 2025",
            "Adobe After Effects 2024",
            "Adobe After Effects 2023",
            "Adobe After Effects 2022"
        ]
