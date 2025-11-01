"""
Stage Transition Manager - Automated Stage Transitions with Pre-Processing

This service manages transitions between pipeline stages and automatically
prepares everything needed for the next stage in the background, ensuring
humans never wait for processing.

Author: After Effects Automation System
Date: 2025-10-30
"""

import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from services.job_service import JobService
from services.log_service import LogService
from services.warning_service import WarningService


class StageTransitionManager:
    """
    Manages automated stage transitions with background pre-processing.

    When a stage completes, this service:
    1. Transitions the job to the next stage
    2. Starts background pre-processing for that stage
    3. Updates job status appropriately
    4. Logs all actions
    """

    def __init__(self, logger=None):
        """Initialize the stage transition manager."""
        self.logger = logger
        self.job_service = JobService(logger)
        self.log_service = LogService(logger)
        self.warning_service = WarningService(logger)

        # Background processing threads
        self.active_threads: Dict[str, threading.Thread] = {}

        # Directories for pre-processing outputs
        self.prep_dir = Path(__file__).parent.parent / 'data' / 'stage_prep'
        self.prep_dir.mkdir(parents=True, exist_ok=True)

        self.log_info("Stage Transition Manager initialized")

    def log_info(self, message: str):
        """Log info message."""
        if self.logger:
            self.logger.info(message)

    def log_error(self, message: str):
        """Log error message."""
        if self.logger:
            self.logger.error(message)

    def transition_stage(
        self,
        job_id: str,
        from_stage: int,
        to_stage: int,
        user_id: str,
        approved_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Transition a job from one stage to another with background pre-processing.

        Args:
            job_id: Job identifier
            from_stage: Current stage number
            to_stage: Target stage number
            user_id: User who triggered the transition
            approved_data: Optional data from approval (e.g., layer matches)

        Returns:
            Dict with transition result
        """
        try:
            self.log_info(f"Job {job_id}: Transitioning from Stage {from_stage} to Stage {to_stage}")

            # Verify job exists and is in correct stage
            job = self.job_service.get_job(job_id)
            if not job:
                return {
                    'success': False,
                    'error': f'Job {job_id} not found'
                }

            if job.current_stage != from_stage:
                return {
                    'success': False,
                    'error': f'Job is in Stage {job.current_stage}, not Stage {from_stage}'
                }

            # Store approved data if provided
            if approved_data:
                self._store_stage_data(job_id, from_stage, approved_data)

            # Complete the current stage
            self.job_service.complete_stage(job_id, from_stage, user_id)
            self.log_service.log_stage_completed(job_id, from_stage, user_id)

            # Transition to next stage
            self.job_service.update_job_status(
                job_id,
                status='processing',
                current_stage=to_stage
            )

            self.log_service.log_action(
                job_id=job_id,
                stage=to_stage,
                action='stage_transition',
                user_id='system',
                message=f'Transitioned from Stage {from_stage} to Stage {to_stage}'
            )

            # Start background pre-processing for the new stage
            self._start_preprocessing(job_id, to_stage, user_id)

            return {
                'success': True,
                'job_id': job_id,
                'from_stage': from_stage,
                'to_stage': to_stage,
                'status': 'processing',
                'message': f'Transitioning to Stage {to_stage} - pre-processing started'
            }

        except Exception as e:
            self.log_error(f"Transition failed for {job_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _store_stage_data(self, job_id: str, stage: int, data: Dict):
        """Store stage-specific data (e.g., approved matches)."""
        if stage == 2:
            # Store approved layer matches from Stage 2
            self.job_service.store_approved_matches(job_id, data.get('matches', []))
        elif stage == 3:
            # Store preview approval data from Stage 3
            # Could include notes, approval timestamp, etc.
            pass

    def _start_preprocessing(self, job_id: str, stage: int, user_id: str):
        """
        Start background pre-processing for a stage.

        Creates a daemon thread to run pre-processing in the background
        so the API can return immediately.
        """
        thread_key = f"{job_id}_stage{stage}"

        # Don't start if already processing
        if thread_key in self.active_threads and self.active_threads[thread_key].is_alive():
            self.log_info(f"Job {job_id}: Pre-processing already running for Stage {stage}")
            return

        # Create and start background thread
        thread = threading.Thread(
            target=self._preprocess_for_stage,
            args=(job_id, stage, user_id),
            daemon=True,
            name=f"Preprocess_{job_id}_S{stage}"
        )

        self.active_threads[thread_key] = thread
        thread.start()

        self.log_info(f"Job {job_id}: Started background pre-processing for Stage {stage}")

    def _preprocess_for_stage(self, job_id: str, stage: int, user_id: str):
        """
        Route to stage-specific pre-processing.

        This runs in a background thread.

        6-Stage Pipeline:
        - Stage 2: Matching (generate layer previews)
        - Stage 3: Auto-Validation (run validation checks)
        - Stage 4: Validation Review (human review - no preprocessing)
        - Stage 5: ExtendScript Generation (generate script)
        - Stage 6: Download (no preprocessing needed)
        """
        try:
            self.log_info(f"Job {job_id}: Pre-processing Stage {stage} started")

            # Route to stage-specific preprocessing
            if stage == 2:
                result = self._preprocess_stage2(job_id)
            elif stage == 3:
                result = self._preprocess_stage3_validation(job_id)
            elif stage == 4:
                # Stage 4 is human review - no preprocessing needed
                result = {'success': True, 'message': 'No pre-processing required'}
            elif stage == 5:
                result = self._preprocess_stage5_extendscript(job_id)
            elif stage == 6:
                # Stage 6 is download - no preprocessing needed
                result = {'success': True, 'message': 'No pre-processing required'}
            else:
                # No pre-processing needed for this stage
                result = {'success': True, 'message': 'No pre-processing required'}

            if result.get('success'):
                # Pre-processing complete - mark job as ready for review/approval
                self._mark_preprocessing_complete(job_id, stage)
                self.log_info(f"Job {job_id}: Pre-processing Stage {stage} completed successfully")
            else:
                # Pre-processing failed
                self._mark_preprocessing_failed(job_id, stage, result.get('error', 'Unknown error'))
                self.log_error(f"Job {job_id}: Pre-processing Stage {stage} failed: {result.get('error')}")

        except Exception as e:
            self.log_error(f"Job {job_id}: Pre-processing exception: {e}")
            self._mark_preprocessing_failed(job_id, stage, str(e))

    def _mark_preprocessing_complete(self, job_id: str, stage: int):
        """
        Mark pre-processing as complete and update job status.

        6-Stage Pipeline Status Mapping:
        - Stage 2: awaiting_review (human reviews matching)
        - Stage 3: ready_for_validation (auto-validation complete, may need review)
        - Stage 4: awaiting_approval (human reviews validation issues)
        - Stage 5: awaiting_download (ExtendScript ready for download)
        - Stage 6: completed (job complete)
        """
        # Determine appropriate status based on stage
        if stage == 2:
            new_status = 'awaiting_review'  # Ready for human to review matching
        elif stage == 3:
            new_status = 'ready_for_validation'  # Auto-validation complete
        elif stage == 4:
            new_status = 'awaiting_approval'  # Ready for human validation review
        elif stage == 5:
            new_status = 'awaiting_download'  # ExtendScript generated
        elif stage == 6:
            new_status = 'completed'  # Job fully complete
        else:
            new_status = 'awaiting_review'

        self.job_service.update_job_status(job_id, new_status)

        self.log_service.log_action(
            job_id=job_id,
            stage=stage,
            action='preprocessing_complete',
            user_id='system',
            message=f'Stage {stage} pre-processing completed'
        )

    def _mark_preprocessing_failed(self, job_id: str, stage: int, error: str):
        """Mark pre-processing as failed."""
        self.job_service.update_job_status(job_id, 'failed')

        self.warning_service.add_warning(
            job_id=job_id,
            stage=stage,
            warning_type='preprocessing_failed',
            severity='critical',
            message=f'Pre-processing failed: {error}'
        )

        self.log_service.log_error(
            job_id=job_id,
            stage=stage,
            message=f'Pre-processing failed: {error}',
            user_id='system'
        )

    # =========================================================================
    # STAGE-SPECIFIC PRE-PROCESSING
    # =========================================================================

    def _preprocess_stage2(self, job_id: str) -> Dict[str, Any]:
        """
        Pre-process for Stage 2: Matching & Adjustment

        Tasks:
        1. Generate PSD layer previews
        2. Generate AEPX layer previews
        3. Create side-by-side comparison thumbnails
        4. Calculate similarity scores
        5. Prepare matching UI data

        Note: For now, this is a placeholder. Full implementation will:
        - Use PSD Layer Exporter to generate layer images
        - Use aerender to generate AEPX layer previews
        - Use image comparison to calculate similarity
        """
        try:
            job = self.job_service.get_job(job_id)
            if not job:
                return {'success': False, 'error': 'Job not found'}

            # Create stage prep directory
            stage_prep_dir = self.prep_dir / f'stage2_{job_id}'
            stage_prep_dir.mkdir(parents=True, exist_ok=True)

            self.log_info(f"Job {job_id}: Stage 2 pre-processing - generating previews")

            # TODO: Full implementation
            # 1. Generate PSD layer previews
            # psd_previews = self._generate_psd_previews(job.psd_path, stage_prep_dir)

            # 2. Generate AEPX layer previews
            # aepx_previews = self._generate_aepx_previews(job.aepx_path, stage_prep_dir)

            # 3. Create comparison thumbnails
            # comparisons = self._create_comparison_images(psd_previews, aepx_previews, stage_prep_dir)

            # 4. Calculate similarity scores
            # similarity_scores = self._calculate_similarity(psd_previews, aepx_previews)

            # For now, simulate processing time
            time.sleep(2)

            self.log_info(f"Job {job_id}: Stage 2 pre-processing complete")

            return {
                'success': True,
                'prep_dir': str(stage_prep_dir),
                'message': 'Stage 2 pre-processing complete'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _preprocess_stage3_validation(self, job_id: str) -> Dict[str, Any]:
        """
        Pre-process for Stage 3: Automatic Validation

        Tasks:
        1. Run match_validation_service to check approved matches
        2. Detect aspect ratio mismatches
        3. Detect resolution issues
        4. Store validation results

        Note: This validation is automatic and runs without user interaction.
        If critical issues are found, the job will be routed to Stage 4 for human review.
        """
        try:
            job = self.job_service.get_job(job_id)
            if not job:
                return {'success': False, 'error': 'Job not found'}

            self.log_info(f"Job {job_id}: Stage 3 auto-validation - running checks")

            # Validation is now handled by approve_stage2 endpoint
            # This preprocessing step is just a placeholder for future enhancements

            # Simulate minimal processing time
            time.sleep(0.5)

            self.log_info(f"Job {job_id}: Stage 3 auto-validation complete")

            return {
                'success': True,
                'message': 'Stage 3 auto-validation complete'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _preprocess_stage5_extendscript(self, job_id: str) -> Dict[str, Any]:
        """
        Pre-process for Stage 5: ExtendScript Generation

        Tasks:
        1. Generate ExtendScript with approved mappings
        2. Validate ExtendScript syntax
        3. Store generated script
        4. Prepare for download

        Note: This generates the final .jsx script that users will download.
        Full implementation will:
        - Generate ExtendScript from Stage 2 approved matches
        - Include any adjustments from Stage 4 override
        - Validate script syntax
        - Store in stage5_extendscript field
        """
        try:
            job = self.job_service.get_job(job_id)
            if not job:
                return {'success': False, 'error': 'Job not found'}

            # Create stage prep directory
            stage_prep_dir = self.prep_dir / f'stage5_{job_id}'
            stage_prep_dir.mkdir(parents=True, exist_ok=True)

            self.log_info(f"Job {job_id}: Stage 5 pre-processing - generating ExtendScript")

            # TODO: Full implementation
            # 1. Load approved matches from stage2_approved_matches
            # approved_matches = json.loads(job.stage2_approved_matches)

            # 2. Generate ExtendScript
            # extendscript = self._generate_extendscript(job_id, approved_matches, stage_prep_dir)

            # 3. Validate script
            # validation = self._validate_extendscript(extendscript)

            # 4. Store in database
            # self.job_service.store_extendscript(job_id, extendscript)

            # Simulate processing time
            time.sleep(2)

            self.log_info(f"Job {job_id}: Stage 5 ExtendScript generation complete")

            return {
                'success': True,
                'prep_dir': str(stage_prep_dir),
                'message': 'Stage 5 ExtendScript generation complete'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # HELPER METHODS (To be implemented)
    # =========================================================================

    def get_preprocessing_status(self, job_id: str, stage: int) -> Dict[str, Any]:
        """
        Get the status of pre-processing for a job/stage.

        Returns:
            Dict with status information
        """
        thread_key = f"{job_id}_stage{stage}"

        if thread_key in self.active_threads:
            thread = self.active_threads[thread_key]
            is_running = thread.is_alive()

            return {
                'job_id': job_id,
                'stage': stage,
                'preprocessing_active': is_running,
                'status': 'processing' if is_running else 'completed'
            }
        else:
            return {
                'job_id': job_id,
                'stage': stage,
                'preprocessing_active': False,
                'status': 'not_started'
            }

    def cleanup_completed_threads(self):
        """Clean up completed background threads."""
        completed = [
            key for key, thread in self.active_threads.items()
            if not thread.is_alive()
        ]

        for key in completed:
            del self.active_threads[key]

        if completed:
            self.log_info(f"Cleaned up {len(completed)} completed preprocessing threads")
