"""
Stage 6 Preview Generation Service

Handles complete preview generation workflow for Stage 6:
1. Export PSD as flattened preview image
2. Execute ExtendScript to populate After Effects template
3. Render preview video using After Effects
4. Update job with preview paths
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import json
import subprocess
import os

from services.base_service import BaseService
from services.preview_service import PreviewService
from database.models import Job
from psd_tools import PSDImage


class Stage6PreviewService(BaseService):
    """
    Service for generating Stage 6 previews.

    Orchestrates PSD export, ExtendScript execution, and video rendering
    to create side-by-side comparison previews for user approval.
    """

    def __init__(self, logger):
        super().__init__(logger)
        self.preview_service = PreviewService(logger)

    def generate_preview_for_job(
        self,
        job: Job,
        session
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Generate preview for a job in Stage 6.

        This method:
        1. Exports PSD as flattened preview image
        2. Executes ExtendScript to populate AE template
        3. Renders preview video
        4. Updates job with preview paths

        Args:
            job: Job model instance (must be in Stage 6)
            session: Database session for committing changes

        Returns:
            Tuple of (success: bool, error_message: Optional[str], result_data: Optional[Dict])
        """
        try:
            self.log_info(f"Job {job.job_id}: Starting Stage 6 preview generation")

            # Verify job is in Stage 6
            if job.current_stage != 6:
                error_msg = f'Job is in Stage {job.current_stage}, not Stage 6'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Verify ExtendScript exists
            if not job.stage5_extendscript:
                error_msg = 'No ExtendScript found - Stage 5 not completed'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Create preview output directory
            preview_dir = Path('output') / 'previews' / job.job_id
            preview_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: Export PSD as flattened preview image
            self.log_info(f"Job {job.job_id}: Exporting PSD preview image")
            psd_preview_path = self._export_psd_preview(
                job.psd_path,
                preview_dir / f'{job.job_id}_psd_preview.png'
            )

            if not psd_preview_path:
                error_msg = 'Failed to export PSD preview'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Step 2: Execute ExtendScript to populate AE template
            self.log_info(f"Job {job.job_id}: Executing ExtendScript")
            populated_aep_path = self._execute_extendscript(
                job.stage5_extendscript,
                job.aepx_path,
                preview_dir / f'{job.job_id}_populated.aep'
            )

            if not populated_aep_path:
                error_msg = 'Failed to execute ExtendScript'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Step 3: Render preview video using After Effects
            self.log_info(f"Job {job.job_id}: Rendering preview video")
            video_preview_path = self._render_preview_video(
                populated_aep_path,
                preview_dir / f'{job.job_id}_preview.mp4'
            )

            if not video_preview_path:
                error_msg = 'Failed to render preview video'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Step 4: Update job with preview paths
            job.stage6_psd_preview_path = str(psd_preview_path)
            job.stage6_preview_video_path = str(video_preview_path)
            job.status = 'awaiting_approval'  # Ready for human approval
            session.commit()

            self.log_info(
                f"Job {job.job_id}: Preview generation complete - "
                f"awaiting user approval"
            )

            return True, None, {
                'psd_preview_path': str(psd_preview_path),
                'video_preview_path': str(video_preview_path),
                'preview_url': f'/preview/{job.job_id}'
            }

        except Exception as e:
            error_msg = f'Preview generation failed: {str(e)}'
            self.log_error_with_context(
                error_msg,
                exception=e,
                job_id=job.job_id
            )
            return False, error_msg, None

    def _export_psd_preview(
        self,
        psd_path: str,
        output_path: Path
    ) -> Optional[str]:
        """
        Export PSD as flattened preview image.

        Args:
            psd_path: Path to PSD file
            output_path: Path for output PNG

        Returns:
            Path to exported image, or None if failed
        """
        try:
            self.log_info(f"Exporting PSD preview: {psd_path}")

            # Open PSD file
            psd = PSDImage.open(psd_path)

            # Get composite (flattened) image
            composite = psd.composite()

            # Save as PNG
            composite.save(str(output_path), 'PNG')

            self.log_info(f"PSD preview saved: {output_path}")
            return str(output_path)

        except Exception as e:
            self.log_error(f"Failed to export PSD preview: {e}", exc=e)
            return None

    def _execute_extendscript(
        self,
        script_content: str,
        aepx_path: str,
        output_aep_path: Path
    ) -> Optional[str]:
        """
        Execute ExtendScript to populate After Effects template.

        Args:
            script_content: ExtendScript code to execute
            aepx_path: Path to AEPX template
            output_aep_path: Path for populated AEP output

        Returns:
            Path to populated AEP file, or None if failed
        """
        try:
            self.log_info("Executing ExtendScript to populate template")

            # Write ExtendScript to temporary file
            script_path = output_aep_path.parent / f'{output_aep_path.stem}.jsx'
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            self.log_info(f"ExtendScript written to: {script_path}")

            # Generate AppleScript to execute the ExtendScript in After Effects
            applescript = self._generate_extendscript_execution_script(
                str(script_path),
                aepx_path,
                str(output_aep_path)
            )

            self.log_info("Generated AppleScript:")
            self.log_info(applescript)

            # Execute AppleScript
            self.log_info("Running osascript to execute ExtendScript in After Effects...")
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            self.log_info(f"osascript return code: {result.returncode}")
            self.log_info(f"osascript stdout: {result.stdout}")
            if result.stderr:
                self.log_warning(f"osascript stderr: {result.stderr}")

            if result.returncode != 0:
                self.log_error(f"ExtendScript execution failed: {result.stderr}")
                return None

            # Verify output file was created
            if output_aep_path.exists():
                file_size = output_aep_path.stat().st_size
                self.log_info(
                    f"ExtendScript executed successfully: {output_aep_path} "
                    f"({file_size / 1024:.2f} KB)"
                )
                return str(output_aep_path)
            else:
                self.log_error(f"ExtendScript ran but output file not found: {output_aep_path}")
                return None

        except subprocess.TimeoutExpired:
            self.log_error("ExtendScript execution timed out after 5 minutes")
            return None
        except Exception as e:
            self.log_error(f"Failed to execute ExtendScript: {e}", exc=e)
            return None

    def _generate_extendscript_execution_script(
        self,
        script_path: str,
        aepx_path: str,
        output_aep_path: str
    ) -> str:
        """
        Generate AppleScript to execute ExtendScript in After Effects.

        Args:
            script_path: Path to the ExtendScript (.jsx) file
            aepx_path: Path to the AEPX template to open
            output_aep_path: Path where the populated AEP should be saved

        Returns:
            AppleScript code as a string
        """
        # Escape paths for AppleScript (escape backslashes and quotes)
        script_path_escaped = script_path.replace('\\', '\\\\').replace('"', '\\"')
        aepx_path_escaped = aepx_path.replace('\\', '\\\\').replace('"', '\\"')
        output_aep_path_escaped = output_aep_path.replace('\\', '\\\\').replace('"', '\\"')

        applescript = f'''
        tell application "Adobe After Effects 2025"
            try
                -- Open the AEPX template
                open POSIX file "{aepx_path_escaped}"

                -- Execute the ExtendScript using DoScriptFile
                DoScriptFile "{script_path_escaped}"

                -- Wait for script to complete
                delay 2

                -- Save the populated project as AEP
                set outputFile to POSIX file "{output_aep_path_escaped}"
                save in outputFile

                -- Wait for save to complete
                delay 2

                -- Close the project
                close

                return "success"
            on error errMsg
                -- Try to close if still open
                try
                    close
                end try
                error "Failed to execute ExtendScript: " & errMsg
            end try
        end tell
        '''

        return applescript

    def _render_preview_video(
        self,
        aep_path: str,
        output_video_path: Path
    ) -> Optional[str]:
        """
        Render preview video using After Effects aerender.

        Args:
            aep_path: Path to populated AEP file
            output_video_path: Path for output video

        Returns:
            Path to rendered video, or None if failed
        """
        try:
            self.log_info(f"Rendering preview video from: {aep_path}")

            # Find aerender executable
            aerender_path = self._find_aerender()
            if not aerender_path:
                self.log_error("aerender not found")
                return None

            # Build aerender command
            # -project: AEP file
            # -comp: Composition name (use first comp)
            # -output: Output video path
            # -RStemplate: Render settings template (use "Best Settings")
            # -OMtemplate: Output module template (use "H.264")
            cmd = [
                aerender_path,
                '-project', aep_path,
                '-output', str(output_video_path),
                '-RStemplate', 'Best Settings',
                '-OMtemplate', 'H.264'
            ]

            self.log_info(f"Running aerender: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                # Verify output video was created
                if output_video_path.exists():
                    file_size = output_video_path.stat().st_size
                    self.log_info(
                        f"Preview video rendered successfully: {output_video_path} "
                        f"({file_size / 1024 / 1024:.2f} MB)"
                    )
                    return str(output_video_path)
                else:
                    self.log_error(f"aerender ran but output video not found: {output_video_path}")
                    return None
            else:
                self.log_error(f"aerender failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            self.log_error("Preview rendering timed out after 10 minutes")
            return None
        except Exception as e:
            self.log_error(f"Failed to render preview video: {e}", exc=e)
            return None

    def _find_after_effects(self) -> Optional[str]:
        """
        Find After Effects executable path.

        Returns:
            Path to After Effects, or None if not found
        """
        # Common After Effects installation paths
        common_paths = [
            '/Applications/Adobe After Effects 2024/Adobe After Effects 2024.app/Contents/MacOS/After Effects',
            '/Applications/Adobe After Effects 2023/Adobe After Effects 2023.app/Contents/MacOS/After Effects',
            '/Applications/Adobe After Effects CC 2024/Adobe After Effects CC 2024.app/Contents/MacOS/After Effects',
            'C:\\Program Files\\Adobe\\Adobe After Effects 2024\\Support Files\\AfterFX.exe',
            'C:\\Program Files\\Adobe\\Adobe After Effects 2023\\Support Files\\AfterFX.exe',
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

    def _find_aerender(self) -> Optional[str]:
        """
        Find aerender executable path.

        Returns:
            Path to aerender, or None if not found
        """
        # Common aerender installation paths
        common_paths = [
            '/Applications/Adobe After Effects 2024/aerender',
            '/Applications/Adobe After Effects 2023/aerender',
            '/Applications/Adobe After Effects CC 2024/aerender',
            'C:\\Program Files\\Adobe\\Adobe After Effects 2024\\Support Files\\aerender.exe',
            'C:\\Program Files\\Adobe\\Adobe After Effects 2023\\Support Files\\aerender.exe',
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        # Try using 'which' command on Unix-like systems
        try:
            result = subprocess.run(
                ['which', 'aerender'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        return None
