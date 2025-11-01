"""
ExtendScript Generation Service

Handles ExtendScript (.jsx) generation from approved PSD-to-AEPX layer matches.
Provides a centralized service to avoid code duplication across route handlers.
"""

from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import json

from services.base_service import BaseService, Result
from database.models import Job


class ExtendScriptService(BaseService):
    """
    Service for generating ExtendScript files from approved matches.

    Centralizes ExtendScript generation logic that was previously duplicated
    across multiple route handlers.
    """

    def generate_for_job(
        self,
        job: Job,
        session
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Generate ExtendScript for a job and update job status.

        This method:
        1. Extracts approved matches and stage1 data from job
        2. Converts matches to mappings format
        3. Calls the ExtendScript generator
        4. Stores the generated script in the job
        5. Updates job timestamps and stage

        Args:
            job: Job model instance
            session: Database session (for committing changes)

        Returns:
            Tuple of (success: bool, error_message: Optional[str], result_data: Optional[Dict])

        Example:
            success, error, data = extendscript_service.generate_for_job(job, session)
            if success:
                # ExtendScript generated and job updated
                script_length = data['script_length']
            else:
                # Handle error
                logger.error(f"Generation failed: {error}")
        """
        try:
            self.log_info(f"Job {job.job_id}: Starting ExtendScript generation")

            # Get approved matches from Stage 2
            if not job.stage2_approved_matches:
                error_msg = 'No approved matches found'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            approved_matches_data = job.stage2_approved_matches
            if isinstance(approved_matches_data, str):
                approved_matches_data = json.loads(approved_matches_data)

            approved_matches = approved_matches_data.get('approved_matches', [])

            if not approved_matches:
                error_msg = 'No approved matches in data'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            # Get stage1 results for PSD/AEPX data
            if not job.stage1_results:
                error_msg = 'No Stage 1 results found'
                self.log_error(error_msg, job_id=job.job_id)
                return False, error_msg, None

            stage1_data = job.stage1_results
            if isinstance(stage1_data, str):
                stage1_data = json.loads(stage1_data)

            psd_data = stage1_data.get('psd_data', {})
            aepx_data = stage1_data.get('aepx_data', {})

            # Convert approved matches to mappings format
            mappings = self._convert_matches_to_mappings(approved_matches)

            # Generate ExtendScript
            with self.timer('extendscript_generation', job_id=job.job_id):
                script_content = self._generate_script(
                    job_id=job.job_id,
                    psd_data=psd_data,
                    aepx_data=aepx_data,
                    mappings=mappings,
                    psd_path=job.psd_path,
                    aepx_path=job.aepx_path
                )

            # Store generated script in job
            job.stage5_extendscript = script_content
            job.stage5_completed_at = datetime.utcnow()
            job.stage5_completed_by = 'system'
            job.current_stage = 6
            job.stage6_started_at = datetime.utcnow()
            job.status = 'awaiting_preview'  # Need to generate and approve preview first
            session.commit()

            self.log_info(
                f"Job {job.job_id}: ExtendScript generated successfully ({len(script_content)} chars)"
            )

            return True, None, {
                'script_length': len(script_content),
                'mappings_count': len(mappings['mappings']),
                'script_preview': script_content[:500] + '...' if len(script_content) > 500 else script_content
            }

        except Exception as e:
            error_msg = f'ExtendScript generation failed: {str(e)}'
            self.log_error_with_context(
                error_msg,
                exception=e,
                job_id=job.job_id
            )
            return False, error_msg, None

    def _convert_matches_to_mappings(self, approved_matches: list) -> Dict[str, list]:
        """
        Convert approved matches from Stage 2 format to mappings format.

        Args:
            approved_matches: List of match dictionaries from Stage 2

        Returns:
            Dictionary with 'mappings' key containing list of mapping dicts
        """
        mappings = {'mappings': []}

        for match in approved_matches:
            mappings['mappings'].append({
                'psd_layer': match.get('psd_layer_id', ''),
                'aepx_placeholder': match.get('ae_layer_id', ''),
                'type': match.get('type', 'text'),
                'confidence': match.get('confidence', 0),
                'method': match.get('method', 'manual')
            })

        return mappings

    def _generate_script(
        self,
        job_id: str,
        psd_data: Dict,
        aepx_data: Dict,
        mappings: Dict,
        psd_path: str,
        aepx_path: str
    ) -> str:
        """
        Generate ExtendScript using the extendscript_generator module.

        Args:
            job_id: Job identifier
            psd_data: PSD structure data from Stage 1
            aepx_data: AEPX structure data from Stage 1
            mappings: Converted mappings dictionary
            psd_path: Path to PSD file
            aepx_path: Path to AEPX file

        Returns:
            Generated ExtendScript content as string
        """
        from modules.phase4.extendscript_generator import generate_extendscript

        # Create output directory
        output_dir = Path('output') / 'extendscripts'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{job_id}.jsx'

        # Generate ExtendScript options
        options = {
            'psd_file_path': psd_path,
            'aepx_file_path': aepx_path,
            'output_project_path': f'output/{job_id}_populated.aep',
            'render_output': False,
            'render_path': '',
            'image_sources': {}
        }

        self.log_info(
            f"Generating ExtendScript with {len(mappings['mappings'])} mappings",
            job_id=job_id
        )

        # Generate the ExtendScript
        generated_path = generate_extendscript(
            psd_data=psd_data,
            aepx_data=aepx_data,
            mappings=mappings,
            output_path=str(output_path),
            options=options
        )

        # Read and return the generated script
        with open(generated_path, 'r', encoding='utf-8') as f:
            return f.read()
