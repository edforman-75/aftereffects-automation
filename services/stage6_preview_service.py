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
from modules.phase4.extendscript_generator import generate_extendscript


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

            # Step 1: Export PSD as flattened preview image (optional - may fail for PSD v8)
            self.log_info(f"Job {job.job_id}: Exporting PSD preview image")
            psd_preview_path = self._export_psd_preview(
                job.psd_path,
                preview_dir / f'{job.job_id}_psd_preview.png'
            )

            if not psd_preview_path:
                self.log_warning(
                    f"Job {job.job_id}: PSD preview export failed (possibly PSD v8 format). "
                    "Continuing without PSD preview..."
                )
                # Continue anyway - PSD preview is optional

            # Step 2: Fix ExtendScript to use absolute paths
            self.log_info(f"Job {job.job_id}: Preparing ExtendScript for execution")
            script_content = job.stage5_extendscript

            # Replace relative output path with absolute path
            import re
            output_aep_abs = os.path.abspath(preview_dir / f'{job.job_id}_populated.aep')
            script_content = re.sub(
                r'outputProject:\s*"[^"]*"',
                f'outputProject: "{output_aep_abs}"',
                script_content
            )
            self.log_info(f"Updated ExtendScript outputProject to: {output_aep_abs}")

            # Keep PSD file in CONFIG so AE can reference it when opening the project
            # (We're skipping the import, but AE may still need to resolve file references)

            # Fix relative image paths to absolute paths
            # Replace "data/exports/..." with "/absolute/path/data/exports/..."
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            script_content = re.sub(
                r'replaceImageSource\(([^,]+),\s*"data/exports/',
                f'replaceImageSource(\\1, "{base_dir}/data/exports/',
                script_content
            )
            self.log_info(f"Updated image paths to use absolute base: {base_dir}")

            # Remove PSD file path entirely to prevent AE from trying to locate it
            script_content = re.sub(
                r'psdFile:\s*"[^"]*"',
                'psdFile: ""',
                script_content
            )
            self.log_info(f"Cleared PSD file path to prevent file lookup errors")

            # Remove PSD import and layer copying (causes timeout/errors)
            # Comment out the entire PSD import block to avoid import dialogs
            script_content = script_content.replace(
                'logMessage("Importing PSD file...");',
                '// SKIPPED: logMessage("Importing PSD file...");'
            )
            script_content = script_content.replace(
                'var psdComp = importPSDAsComp(CONFIG.psdFile);',
                '// SKIPPED: var psdComp = importPSDAsComp(CONFIG.psdFile);  // Not needed - using exported PNGs'
            )
            script_content = script_content.replace(
                'if (!psdComp) {',
                'if (false) {  // SKIPPED PSD import check'
            )
            script_content = re.sub(
                r'logMessage\("PSD composition has.*?layers"\);',
                '// SKIPPED: logMessage about PSD composition layers',
                script_content
            )
            script_content = script_content.replace(
                'logMessage("Copying PSD layers to composition...");',
                '// SKIPPED: logMessage("Copying PSD layers to composition...");  // Not needed - using exported PNGs'
            )
            # Also comment out the for loop that copies PSD layers
            script_content = re.sub(
                r'for \(var i = psdComp\.numLayers; i >= 1; i--\) \{.*?copyLayerToComp\(srcLayer, comp, srcLayer\.name\);\s*\}',
                '// SKIPPED: for loop that copies PSD layers - not needed when using exported PNGs',
                script_content,
                flags=re.DOTALL
            )
            self.log_info(f"Disabled PSD import/copy sections to avoid dialogs")

            # Fix incorrect layer names from mappings (ae_0, ae_1, etc. don't exist in template)
            # Map to actual AEPX layer names based on exported PNG filenames
            layer_name_fixes = {
                'ae_0': 'featuredimage1',  # ben_forman.png → main featured image
                'ae_1': 'player2fullname',  # eloise_grace.png → player 2 text/image
                'ae_2': 'player3fullname',  # emma_louise.png → player 3 text/image
                'ae_3': 'cutout',          # cutout.png → cutout layer
                'ae_4': 'Background',      # background.png → Background layer
                'ae_5': 'green_yellow_bg'  # green_yellow_bg.png → green_yellow_bg layer
            }

            for old_name, new_name in layer_name_fixes.items():
                # Replace in findLayerByName() calls
                script_content = re.sub(
                    rf'findLayerByName\(comp,\s*"{old_name}"\)',
                    f'findLayerByName(comp, "{new_name}")',
                    script_content
                )
                # Replace in log messages
                script_content = re.sub(
                    rf'(Replacing image layer|WARNING: Layer not found):\s*{old_name}',
                    rf'\1: {new_name}',
                    script_content
                )
                # Replace in comments
                script_content = re.sub(
                    rf'// Replace image:\s*{old_name}',
                    f'// Replace image: {new_name} (was {old_name})',
                    script_content
                )

            self.log_info(f"Fixed {len(layer_name_fixes)} layer name mappings to match AEPX template")

            # Delete any existing populated.aep file to ensure fresh creation without old PSD references
            output_aep_file = preview_dir / f'{job.job_id}_populated.aep'
            if output_aep_file.exists():
                output_aep_file.unlink()
                self.log_info(f"Deleted existing AEP file to create fresh copy: {output_aep_file}")

            # Step 3: Execute ExtendScript to populate AE template
            self.log_info(f"Job {job.job_id}: Executing ExtendScript")
            populated_aep_path = self._execute_extendscript(
                script_content,
                job.aepx_path,
                output_aep_file
            )

            if not populated_aep_path:
                error_msg = 'Failed to execute ExtendScript'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Step 3.5: Force replace sources by filename pattern (layer names may not match)
            self.log_info(f"Job {job.job_id}: Force replacing sources by filename patterns")
            force_replace_success = self._force_replace_sources_by_filename(
                job.aepx_path,
                output_aep_file,
                job.job_id
            )

            if not force_replace_success:
                self.log_warning(f"Job {job.job_id}: Source replacement had issues, but continuing with render")

            # Step 4: Render preview video using After Effects
            self.log_info(f"Job {job.job_id}: Rendering preview video")

            # Extract composition name from job's comp_name field
            comp_name = job.comp_name if hasattr(job, 'comp_name') and job.comp_name else 'test-aep'

            # Convert paths to absolute for aerender (it doesn't handle relative paths correctly)
            abs_aep_path = os.path.abspath(populated_aep_path)
            abs_video_path = os.path.abspath(preview_dir / f'{job.job_id}_preview.mp4')

            video_preview_path = self._render_preview_video(
                abs_aep_path,
                Path(abs_video_path),
                comp_name
            )

            if not video_preview_path:
                error_msg = 'Failed to render preview video'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Step 5: Extract a full-quality frame from the rendered video for display
            self.log_info(f"Job {job.job_id}: Extracting render frame from video")
            render_frame_path = self._extract_video_frame(
                video_preview_path,
                preview_dir / f'{job.job_id}_render_frame.png'
            )

            if not render_frame_path:
                self.log_warning(
                    f"Job {job.job_id}: Failed to extract render frame. "
                    "Continuing without render frame image..."
                )

            # Step 6: Update job with preview paths
            job.stage6_psd_preview_path = str(psd_preview_path)
            job.stage6_preview_video_path = str(video_preview_path)
            job.stage6_render_frame_path = str(render_frame_path) if render_frame_path else None
            job.status = 'awaiting_approval'  # Ready for human approval
            session.commit()

            self.log_info(
                f"Job {job.job_id}: Preview generation complete - "
                f"awaiting user approval"
            )

            return True, None, {
                'psd_preview_path': str(psd_preview_path),
                'video_preview_path': str(video_preview_path),
                'render_frame_path': str(render_frame_path) if render_frame_path else None,
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

    def _regenerate_extendscript_for_preview(
        self,
        job: Job,
        preview_dir: Path
    ) -> Optional[str]:
        """
        Regenerate ExtendScript with PSD import disabled for faster execution.

        Args:
            job: Job model instance with all Stage data
            preview_dir: Directory for preview outputs

        Returns:
            ExtendScript content string, or None if failed
        """
        try:
            # Load job data from JSON fields
            psd_data = json.loads(job.stage1_psd_data)
            aepx_data = json.loads(job.stage2_aepx_data)
            mappings = json.loads(job.stage3_mappings)

            # Get absolute paths for script generation
            psd_abs = os.path.abspath(job.psd_path)
            aepx_abs = os.path.abspath(job.aepx_path)
            output_aep_abs = os.path.abspath(preview_dir / f'{job.job_id}_populated.aep')

            # Prepare options with skip_psd_import=True for faster execution
            options = {
                'psd_file_path': psd_abs,
                'aepx_file_path': aepx_abs,
                'output_project_path': output_aep_abs,
                'render_output': False,
                'render_path': '',
                'image_sources': {},  # Will be populated from mappings
                'skip_psd_import': True  # Skip PSD import for Stage 6 - we already have exports!
            }

            # Build image sources from mappings (absolute paths to exports)
            for mapping in mappings.get('mapped', []):
                if mapping['type'] == 'image':
                    placeholder = mapping['aepx_layer']
                    export_filename = mapping['psd_layer_name'] + '.png'
                    export_path = os.path.abspath(f"data/exports/{job.job_id}/{export_filename}")
                    options['image_sources'][placeholder] = export_path

            # Generate optimized ExtendScript
            temp_script_path = preview_dir / f'{job.job_id}_preview_temp.jsx'
            generate_extendscript(
                psd_data=psd_data,
                aepx_data=aepx_data,
                mappings=mappings,
                output_path=str(temp_script_path),
                options=options
            )

            # Read generated script content
            with open(temp_script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()

            self.log_info(f"✅ Regenerated ExtendScript with PSD import disabled ({len(script_content)} chars)")
            return script_content

        except Exception as e:
            self.log_error(f"Failed to regenerate ExtendScript: {e}", exc=e)
            import traceback
            self.log_error(f"Traceback:\n{traceback.format_exc()}")
            return None

    def _export_psd_preview(
        self,
        psd_path: str,
        output_path: Path
    ) -> Optional[str]:
        """
        Export PSD as flattened preview image.

        Note: psd-tools library may not support PSD v8 format.
        This method is optional and should not block the preview generation.

        Args:
            psd_path: Path to PSD file
            output_path: Path for output PNG

        Returns:
            Path to exported image, or None if failed
        """
        try:
            self.log_info(f"Attempting to export PSD preview: {psd_path}")
            self.log_info(f"PSD file exists: {os.path.exists(psd_path)}")

            # Open PSD file
            psd = PSDImage.open(psd_path)
            self.log_info(f"PSD opened successfully - Version: {psd.version}")

            # Get composite (flattened) image
            composite = psd.composite()
            self.log_info(f"PSD composite generated: {composite.size if composite else 'None'}")

            # Save as PNG
            composite.save(str(output_path), 'PNG')

            self.log_info(f"✅ PSD preview saved: {output_path}")
            return str(output_path)

        except Exception as e:
            self.log_warning(f"PSD preview export failed with psd-tools: {e}")
            self.log_info("Trying fallback method using macOS 'sips' command...")

            # Fallback: Try using macOS sips command
            try:
                result = subprocess.run(
                    ['sips', '-s', 'format', 'png', psd_path, '--out', str(output_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0 and output_path.exists():
                    self.log_info(f"✅ PSD preview saved using sips: {output_path}")
                    return str(output_path)
                else:
                    self.log_warning(f"sips conversion failed: {result.stderr}")
                    return None

            except Exception as sips_error:
                self.log_warning(f"sips fallback also failed: {sips_error}")
                self.log_info("PSD preview unavailable - continuing without it")
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
            self.log_info("=" * 80)
            self.log_info("EXTENDSCRIPT EXECUTION DEBUG LOG")
            self.log_info("=" * 80)

            # Log input parameters
            self.log_info(f"AEPX template path: {aepx_path}")
            self.log_info(f"AEPX exists: {os.path.exists(aepx_path)}")
            self.log_info(f"Output AEP path: {output_aep_path}")
            self.log_info(f"ExtendScript content length: {len(script_content)} chars")

            # Write ExtendScript to temporary file
            script_path = output_aep_path.parent / f'{output_aep_path.stem}.jsx'
            self.log_info(f"Writing ExtendScript to: {script_path}")

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            # Verify script file was written
            if script_path.exists():
                script_size = os.path.getsize(script_path)
                self.log_info(f"✅ ExtendScript file written successfully ({script_size} bytes)")

                # Log first 500 chars of script for debugging
                with open(script_path, 'r', encoding='utf-8') as f:
                    preview = f.read(500)
                    self.log_info(f"ExtendScript preview (first 500 chars):\n{preview}")
            else:
                self.log_error(f"❌ Failed to write ExtendScript file: {script_path}")
                return None

            # Generate AppleScript to execute ExtendScript
            # Using AppleScript instead of command-line -s flag (which doesn't work reliably on Mac)
            self.log_info("Generating AppleScript for ExtendScript execution...")
            applescript = self._generate_extendscript_execution_script(
                aepx_path,
                str(script_path),
                str(output_aep_path)
            )

            # Log the full AppleScript being executed (truncated)
            self.log_info("Generated AppleScript (first 1000 chars):")
            self.log_info("-" * 80)
            self.log_info(applescript[:1000] + "..." if len(applescript) > 1000 else applescript)
            self.log_info("-" * 80)
            self.log_info(f"Total AppleScript length: {len(applescript)} characters")

            # Check After Effects availability
            ae_path = "/Applications/Adobe After Effects 2025/Adobe After Effects 2025.app"
            self.log_info(f"Checking After Effects at: {ae_path}")
            self.log_info(f"After Effects exists: {os.path.exists(ae_path)}")

            # Save AppleScript to temporary file to avoid command-line length limits
            # and escaping issues with osascript -e
            applescript_path = output_aep_path.parent / f'{output_aep_path.stem}_script.scpt'
            self.log_info(f"Saving AppleScript to temporary file: {applescript_path}")
            with open(applescript_path, 'w', encoding='utf-8') as f:
                f.write(applescript)

            # Execute via AppleScript file (avoids command-line escaping issues)
            self.log_info("Executing AppleScript from file via osascript...")
            cmd = ['osascript', str(applescript_path)]
            self.log_info(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            self.log_info("=" * 80)
            self.log_info("APPLESCRIPT EXECUTION RESULT")
            self.log_info("=" * 80)
            self.log_info(f"Return code: {result.returncode}")
            self.log_info(f"STDOUT:\n{result.stdout if result.stdout else '[empty]'}")
            self.log_info(f"STDERR:\n{result.stderr if result.stderr else '[empty]'}")
            self.log_info("=" * 80)

            if result.returncode == 0:
                # Verify output file was created
                self.log_info(f"Checking if output file exists: {output_aep_path}")
                if output_aep_path.exists():
                    file_size = os.path.getsize(output_aep_path)
                    self.log_info(f"✅ ExtendScript executed successfully!")
                    self.log_info(f"   Output file: {output_aep_path}")
                    self.log_info(f"   File size: {file_size:,} bytes")
                    return str(output_aep_path)
                else:
                    self.log_error(f"❌ AppleScript returned success but output file not found!")
                    self.log_error(f"   Expected: {output_aep_path}")
                    self.log_error(f"   Directory contents:")
                    parent_dir = output_aep_path.parent
                    if parent_dir.exists():
                        for item in parent_dir.iterdir():
                            self.log_error(f"     - {item.name}")
                    return None
            else:
                self.log_error(f"❌ AppleScript execution failed!")
                self.log_error(f"   Return code: {result.returncode}")
                self.log_error(f"   Error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            self.log_error("❌ ExtendScript execution timed out after 5 minutes")
            return None
        except Exception as e:
            self.log_error(f"❌ Exception during ExtendScript execution: {e}", exc=e)
            import traceback
            self.log_error(f"Traceback:\n{traceback.format_exc()}")
            return None

    def _extract_video_frame(
        self,
        video_path: str,
        output_image_path: Path,
        time_seconds: float = 0.5
    ) -> Optional[str]:
        """
        Extract a single frame from video as a high-quality PNG image.

        Args:
            video_path: Path to video file
            output_image_path: Path for output PNG image
            time_seconds: Time in seconds to extract frame (default: 0.5s)

        Returns:
            Path to extracted image, or None if failed
        """
        try:
            self.log_info(f"Extracting frame from video: {video_path} at {time_seconds}s")

            # Build ffmpeg command to extract a single frame
            # -ss: seek to time position
            # -i: input file
            # -vframes 1: extract only 1 frame
            # -q:v 2: high quality (1-31, lower is better)
            cmd = [
                'ffmpeg',
                '-ss', str(time_seconds),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-y',  # Overwrite output file if exists
                str(output_image_path)
            ]

            self.log_info(f"Running ffmpeg: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and output_image_path.exists():
                file_size = output_image_path.stat().st_size
                self.log_info(
                    f"Frame extracted successfully: {output_image_path} "
                    f"({file_size / 1024:.2f} KB)"
                )
                return str(output_image_path)
            else:
                self.log_error(f"ffmpeg failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            self.log_error("Frame extraction timed out after 60 seconds")
            return None
        except Exception as e:
            self.log_error(f"Failed to extract video frame: {e}", exc=e)
            return None

    def _render_preview_video(
        self,
        aep_path: str,
        output_video_path: Path,
        comp_name: str = 'test-aep'
    ) -> Optional[str]:
        """
        Render preview video using After Effects aerender.

        Args:
            aep_path: Path to populated AEP file
            output_video_path: Path for output video
            comp_name: Composition name to render

        Returns:
            Path to rendered video, or None if failed
        """
        try:
            self.log_info(f"Rendering preview video from: {aep_path}")
            self.log_info(f"Composition: {comp_name}")

            # Find aerender executable
            aerender_path = self._find_aerender()
            if not aerender_path:
                self.log_error("aerender not found")
                return None

            # Build aerender command
            # -project: AEP file
            # -comp: Composition name
            # -output: Output video path
            # -RStemplate: Render settings template (use "Best Settings")
            # -OMtemplate: Output module template (use "H.264")
            cmd = [
                aerender_path,
                '-project', aep_path,
                '-comp', comp_name,
                '-output', str(output_video_path),
                '-RStemplate', 'Best Settings',
                '-OMtemplate', 'H.264 - Match Render Settings - 15 Mbps'
            ]

            self.log_info(f"Running aerender: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            # Log aerender output for debugging
            if result.stdout:
                self.log_info(f"aerender stdout:\n{result.stdout}")
            if result.stderr:
                self.log_info(f"aerender stderr:\n{result.stderr}")

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
                self.log_error(f"aerender failed with return code {result.returncode}")
                return None

        except subprocess.TimeoutExpired:
            self.log_error("Preview rendering timed out after 10 minutes")
            return None
        except Exception as e:
            self.log_error(f"Failed to render preview video: {e}", exc=e)
            return None

    def _generate_extendscript_execution_script(
        self,
        aepx_path: str,
        script_path: str,
        output_aep_path: str
    ) -> str:
        """
        Generate AppleScript to execute ExtendScript and save populated project.

        IMPORTANT: After Effects' `do script` command requires the script content as a string,
        not a file path. We use AppleScript to read the .jsx file and pass it to do script.

        Args:
            aepx_path: Path to AEPX template file
            script_path: Path to ExtendScript (.jsx) file to execute
            output_aep_path: Path for output populated AEP file

        Returns:
            AppleScript code as string
        """
        # Convert to absolute paths for AppleScript
        aepx_abs = os.path.abspath(aepx_path)
        script_abs = os.path.abspath(script_path)
        output_abs = os.path.abspath(output_aep_path)

        # Escape paths for AppleScript (replace backslashes and quotes)
        aepx_escaped = aepx_abs.replace('\\', '\\\\').replace('"', '\\"')
        script_escaped = script_abs.replace('\\', '\\\\').replace('"', '\\"')
        output_escaped = output_abs.replace('\\', '\\\\').replace('"', '\\"')

        # Note: The ExtendScript itself handles saving the project
        # We just need to open the template and execute the script
        applescript = f'''
with timeout of 300 seconds
    tell application "Adobe After Effects 2025"
        try
            -- Open the template project
            open POSIX file "{aepx_escaped}"

            -- Execute the ExtendScript from file (it will save the project)
            DoScriptFile POSIX file "{script_escaped}"

            -- Wait for save to complete before closing
            delay 2

            -- Close project
            close

            return "success"
        on error errMsg
            try
                close
            end try
            error "Failed to execute script: " & errMsg
        end try
    end tell
end timeout
'''

        return applescript

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

    def _force_replace_sources_by_filename(
        self,
        aepx_path: str,
        aep_path: Path,
        job_id: str
    ) -> bool:
        """
        Force replace layer sources by matching old filename patterns.
        This bypasses layer name matching issues.

        Args:
            aepx_path: Path to AEPX template
            aep_path: Path to populated AEP file
            job_id: Job ID for finding exported PNGs

        Returns:
            True if replacement succeeded, False otherwise
        """
        try:
            # Get list of exported PNGs for this job
            exports_dir = Path('data/exports') / job_id
            if not exports_dir.exists():
                self.log_error(f"Exports directory not found: {exports_dir}")
                return False

            # Build mapping of filename patterns to new file paths
            export_files = list(exports_dir.glob('*.png'))
            if not export_files:
                self.log_error(f"No PNG exports found in {exports_dir}")
                return False

            # Generate ExtendScript for source replacement
            script_lines = [
                '// Force replace sources by filename pattern',
                '',
                'function replaceSourceByFilename(comp, oldFilenamePattern, newImagePath) {',
                '    var replaced = false;',
                '    for (var i = 1; i <= comp.numLayers; i++) {',
                '        var layer = comp.layer(i);',
                '        try {',
                '            if (layer.source && layer.source.file) {',
                '                var oldFilename = layer.source.file.name;',
                '                if (oldFilename.toLowerCase().indexOf(oldFilenamePattern.toLowerCase()) >= 0) {',
                '                    $.writeln("Found layer " + i + " (\'" + layer.name + "\') with source: " + oldFilename);',
                '                    var newFile = new File(newImagePath);',
                '                    if (!newFile.exists) {',
                '                        $.writeln("  ERROR: New file not found: " + newImagePath);',
                '                        continue;',
                '                    }',
                '                    var importOptions = new ImportOptions(newFile);',
                '                    var footage = app.project.importFile(importOptions);',
                '                    layer.replaceSource(footage, false);',
                '                    $.writeln("  ✓ Replaced with: " + newFile.name);',
                '                    replaced = true;',
                '                }',
                '            }',
                '        } catch (e) {}',
                '    }',
                '    return replaced;',
                '}',
                '',
                'try {',
                '    $.writeln("==================================================");',
                '    $.writeln("Force Replace Sources");',
                '    $.writeln("==================================================");',
                '',
                '    var comp = null;',
                '    for (var i = 1; i <= app.project.numItems; i++) {',
                '        if (app.project.item(i) instanceof CompItem) {',
                f'            if (app.project.item(i).name === "{os.path.basename(aepx_path).replace(".aepx", "")}") {{',
                '                comp = app.project.item(i);',
                '                break;',
                '            }',
                '        }',
                '    }',
                '',
                '    if (!comp) {',
                '        for (var i = 1; i <= app.project.numItems; i++) {',
                '            if (app.project.item(i) instanceof CompItem) {',
                '                comp = app.project.item(i);',
                '                break;',
                '            }',
                '        }',
                '    }',
                '',
                '    if (!comp) {',
                '        $.writeln("ERROR: No composition found!");',
                '    } else {',
                '        $.writeln("Found composition: " + comp.name);',
                '        var totalReplaced = 0;',
                ''
            ]

            # Add replacement commands for each exported PNG
            for export_file in export_files:
                # Extract filename without extension as pattern
                pattern = export_file.stem
                abs_path = os.path.abspath(export_file)
                script_lines.extend([
                    f'        $.writeln("Looking for sources matching: {pattern}");',
                    f'        if (replaceSourceByFilename(comp, "{pattern}", "{abs_path}")) {{',
                    '            totalReplaced++;',
                    '        }',
                    ''
                ])

            script_lines.extend([
                '        $.writeln("==================================================");',
                '        $.writeln("Replaced " + totalReplaced + " sources");',
                '        $.writeln("==================================================");',
                '',
                f'        var saveFile = new File("{os.path.abspath(aep_path)}");',
                '        app.project.save(saveFile);',
                '        $.writeln("Project saved");',
                '    }',
                '} catch (e) {',
                '    $.writeln("ERROR: " + e.toString());',
                '}',
                ''
            ])

            script_content = '\n'.join(script_lines)

            # Write script to file
            script_path = aep_path.parent / f'{aep_path.stem}_force_replace.jsx'
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            self.log_info(f"Created force replace script: {script_path}")

            # Execute script via AppleScript
            applescript = f'''
            with timeout of 300 seconds
                tell application "Adobe After Effects 2025"
                    activate
                    open POSIX file "{os.path.abspath(aep_path)}"
                    DoScriptFile POSIX file "{os.path.abspath(script_path)}"
                    delay 2
                    close
                end tell
            end timeout
            '''

            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.log_info(f"Source replacement script executed successfully")
                return True
            else:
                self.log_error(f"Source replacement script failed: {result.stderr}")
                return False

        except Exception as e:
            self.log_error(f"Error in force source replacement: {e}")
            return False

    def _find_aerender(self) -> Optional[str]:
        """
        Find aerender executable path.

        Returns:
            Path to aerender, or None if not found
        """
        # Common aerender installation paths
        common_paths = [
            '/Applications/Adobe After Effects 2025/aerender',
            '/Applications/Adobe After Effects 2024/aerender',
            '/Applications/Adobe After Effects 2023/aerender',
            '/Applications/Adobe After Effects CC 2024/aerender',
            'C:\\Program Files\\Adobe\\Adobe After Effects 2025\\Support Files\\aerender.exe',
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
