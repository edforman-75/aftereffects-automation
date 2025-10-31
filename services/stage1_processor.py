"""
Stage 1 Automated Processor

Processes jobs through automated ingestion:
- Extract PSD layers headlessly
- Process AEPX structure headlessly
- Auto-match layers
- Detect fonts and check installation
- Generate thumbnails
- Identify warnings (missing fonts, missing assets, etc.)
- Transition to Stage 2 (ready for human review)

This stage runs completely automated with no human intervention.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from services.psd_layer_exporter import PSDLayerExporter
from services.aepx_processor import AEPXProcessor
from services.job_service import JobService
from services.warning_service import WarningService
from services.log_service import LogService


class Stage1Processor:
    """
    Automated processor for Stage 1 (Ingestion).

    Takes jobs in stage 0 and processes them completely automated.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.psd_exporter = PSDLayerExporter(logger)
        self.aepx_processor = AEPXProcessor(logger)
        self.job_service = JobService(logger)
        self.warning_service = WarningService(logger)
        self.log_service = LogService(logger)

    def log_info(self, message: str):
        """Log info message."""
        if self.logger:
            self.logger.info(message)
        print(f"ℹ️  {message}")

    def log_error(self, message: str):
        """Log error message."""
        if self.logger:
            self.logger.error(message)
        print(f"❌ {message}")

    def process_batch(self, batch_id: str, max_jobs: int = 100):
        """
        Process all jobs in a batch through Stage 1.

        Args:
            batch_id: Batch identifier
            max_jobs: Maximum jobs to process in one call
        """
        print(f"\n{'='*70}")
        print(f"🏭 STAGE 1: BATCH AUTOMATED PROCESSING")
        print(f"{'='*70}")
        print(f"Batch ID: {batch_id}")
        print(f"{'='*70}\n")

        self.log_info(f"Starting Stage 1 batch processing for {batch_id}")

        # Get all jobs in stage 0 for this batch
        jobs = self.job_service.get_jobs_for_stage(
            stage=0,
            batch_id=batch_id,
            limit=max_jobs
        )

        if not jobs:
            print(f"⚠️  No jobs found in stage 0 for batch {batch_id}")
            return {
                'processed': 0,
                'succeeded': 0,
                'failed': 0
            }

        print(f"Found {len(jobs)} jobs to process\n")

        results = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'job_results': {}
        }

        for idx, job in enumerate(jobs, 1):
            print(f"{'─'*70}")
            print(f"Job [{idx}/{len(jobs)}]: {job.job_id}")
            print(f"{'─'*70}")

            try:
                # Process this job
                job_result = self.process_job(job.job_id)

                results['processed'] += 1

                if job_result['success']:
                    results['succeeded'] += 1
                else:
                    results['failed'] += 1

                results['job_results'][job.job_id] = job_result

            except Exception as e:
                self.log_error(f"Failed to process job {job.job_id}: {e}")
                results['processed'] += 1
                results['failed'] += 1
                results['job_results'][job.job_id] = {
                    'success': False,
                    'error': str(e)
                }

            print()

        # Summary
        print(f"\n{'='*70}")
        print(f"📊 STAGE 1 BATCH PROCESSING COMPLETE")
        print(f"{'='*70}")
        print(f"Total processed: {results['processed']}")
        print(f"✅ Succeeded: {results['succeeded']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"{'='*70}\n")

        self.log_info(f"Stage 1 batch processing complete: {results['succeeded']}/{results['processed']} succeeded")

        return results

    def process_job(self, job_id: str) -> Dict[str, Any]:
        """
        Process a single job through Stage 1.

        Args:
            job_id: Job identifier

        Returns:
            {
                'success': True/False,
                'psd_result': {...},
                'aepx_result': {...},
                'matches': {...},
                'warnings': [...],
                'error': 'error message' (if failed)
            }
        """
        print(f"\n🔄 Processing job: {job_id}")

        # Get job
        job = self.job_service.get_job(job_id)
        if not job:
            return {
                'success': False,
                'error': f'Job not found: {job_id}'
            }

        # Start stage 1
        self.job_service.start_stage(job_id, stage=1, user_id='system')
        self.job_service.update_job_status(job_id, 'processing', current_stage=1)
        self.log_service.log_stage_started(job_id, stage=1, user_id='system')

        result = {
            'success': False,
            'psd_result': None,
            'aepx_result': None,
            'matches': None,
            'warnings': []
        }

        try:
            # Step 1: Process PSD
            print(f"\n  📄 Step 1: Processing PSD...")
            psd_result = self._process_psd(job)
            result['psd_result'] = psd_result

            # Step 2: Process AEPX
            print(f"\n  🎬 Step 2: Processing AEPX...")
            aepx_result = self._process_aepx(job)
            result['aepx_result'] = aepx_result

            # Step 3: Auto-match layers
            print(f"\n  🔗 Step 3: Auto-matching layers...")
            matches = self._auto_match_layers(psd_result, aepx_result)
            result['matches'] = matches

            # Step 4: Check for warnings
            print(f"\n  ⚠️  Step 4: Checking for warnings...")
            warnings = self._check_warnings(job_id, psd_result, aepx_result, matches)
            result['warnings'] = warnings

            # Step 5: Store results
            print(f"\n  💾 Step 5: Storing results...")
            self.job_service.store_stage1_results(
                job_id=job_id,
                psd_result=psd_result,
                aepx_result=aepx_result,
                match_result=matches
            )

            # Complete stage 1
            self.job_service.complete_stage(job_id, stage=1, user_id='system')
            self.job_service.update_job_status(job_id, 'awaiting_review', current_stage=2)
            self.log_service.log_stage_completed(job_id, stage=1, user_id='system')

            result['success'] = True

            print(f"\n✅ Job {job_id} completed Stage 1 successfully")
            if warnings:
                print(f"   ⚠️  {len(warnings)} warnings detected")

            self.log_info(f"Job {job_id} completed Stage 1 - {len(warnings)} warnings")

        except Exception as e:
            self.log_error(f"Job {job_id} failed in Stage 1: {e}")
            result['error'] = str(e)

            # Log error
            self.log_service.log_error(
                job_id=job_id,
                stage=1,
                error_message=str(e),
                error_details={'exception_type': type(e).__name__}
            )

            # Update job status to failed
            self.job_service.update_job_status(job_id, 'failed', current_stage=1)

            import traceback
            traceback.print_exc()

        return result

    def _process_psd(self, job) -> Dict[str, Any]:
        """Process PSD file and extract layers."""
        # Create output directory for this job
        exports_dir = Path('data/exports') / job.job_id
        exports_dir.mkdir(parents=True, exist_ok=True)

        # Extract all layers
        export_result = self.psd_exporter.extract_all_layers(
            psd_path=job.psd_path,
            output_dir=str(exports_dir),
            generate_thumbnails=True
        )

        return {
            'layers': export_result.get('layers', {}),
            'fonts': export_result.get('fonts', []),
            'dimensions': export_result.get('dimensions', {}),
            'flattened_preview': export_result.get('flattened_preview'),
            'metadata': export_result.get('metadata', {})
        }

    def _process_aepx(self, job) -> Dict[str, Any]:
        """Process AEPX file and analyze structure."""
        aepx_result = self.aepx_processor.process_aepx(
            aepx_path=job.aepx_path,
            session_id=job.job_id,
            generate_thumbnails=False  # Keep headless
        )

        return {
            'compositions': aepx_result.get('compositions', []),
            'layers': aepx_result.get('layers', []),
            'placeholders': aepx_result.get('placeholders', []),
            'layer_categories': aepx_result.get('layer_categories', {}),
            'missing_footage': aepx_result.get('missing_footage', [])
        }

    def _auto_match_layers(
        self,
        psd_result: Dict[str, Any],
        aepx_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Auto-match PSD layers to AEPX placeholders.

        Simple name-based matching for now.
        Can be enhanced with ML in the future.
        """
        psd_layers = psd_result.get('layers', {})
        aepx_placeholders = aepx_result.get('placeholders', [])

        matches = []
        unmatched_psd = []
        unmatched_aepx = []

        matched_psd_names = set()
        matched_aepx_names = set()

        # Try exact name matching first
        for placeholder in aepx_placeholders:
            aepx_name = placeholder['name'].lower().replace(' ', '_')
            matched = False

            for psd_name, psd_layer in psd_layers.items():
                psd_name_clean = psd_name.lower().replace(' ', '_')

                if psd_name_clean == aepx_name or aepx_name in psd_name_clean or psd_name_clean in aepx_name:
                    matches.append({
                        'psd_layer': psd_name,
                        'aepx_layer': placeholder['name'],
                        'match_type': 'exact',
                        'confidence': 1.0
                    })
                    matched_psd_names.add(psd_name)
                    matched_aepx_names.add(placeholder['name'])
                    matched = True
                    break

            if not matched:
                unmatched_aepx.append(placeholder['name'])

        # Track unmatched PSD layers
        for psd_name in psd_layers.keys():
            if psd_name not in matched_psd_names:
                unmatched_psd.append(psd_name)

        print(f"    ✅ Matched: {len(matches)} layer pairs")
        print(f"    ⚠️  Unmatched PSD layers: {len(unmatched_psd)}")
        print(f"    ⚠️  Unmatched AEPX placeholders: {len(unmatched_aepx)}")

        return {
            'matches': matches,
            'unmatched_psd': unmatched_psd,
            'unmatched_aepx': unmatched_aepx,
            'match_count': len(matches),
            'match_rate': len(matches) / max(len(aepx_placeholders), 1) if aepx_placeholders else 0
        }

    def _check_warnings(
        self,
        job_id: str,
        psd_result: Dict[str, Any],
        aepx_result: Dict[str, Any],
        matches: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check for warnings and add them to the job.

        Returns list of warnings added.
        """
        warnings = []

        # Check for missing fonts
        fonts = psd_result.get('fonts', [])
        for font in fonts:
            if not font.get('is_installed'):
                warning_id = self.warning_service.add_missing_font_warning(
                    job_id=job_id,
                    stage=1,
                    font_name=f"{font['family']} {font['style']}",
                    layer_name=font.get('layer_name')
                )
                warnings.append({
                    'id': warning_id,
                    'type': 'missing_font',
                    'font': font
                })

        # Check for missing footage in AEPX
        missing_footage = aepx_result.get('missing_footage', [])
        for footage in missing_footage:
            warning_id = self.warning_service.add_missing_asset_warning(
                job_id=job_id,
                stage=1,
                asset_path=footage.get('path', 'Unknown'),
                asset_type='footage'
            )
            warnings.append({
                'id': warning_id,
                'type': 'missing_footage',
                'footage': footage
            })

        # Check for unmatched placeholders
        unmatched_aepx = matches.get('unmatched_aepx', [])
        for placeholder_name in unmatched_aepx:
            warning_id = self.warning_service.add_placeholder_not_matched_warning(
                job_id=job_id,
                stage=1,
                placeholder_name=placeholder_name
            )
            warnings.append({
                'id': warning_id,
                'type': 'placeholder_not_matched',
                'placeholder': placeholder_name
            })

        # Log warnings
        for warning in warnings:
            self.log_service.log_warning_added(
                job_id=job_id,
                stage=1,
                warning_type=warning['type'],
                severity='warning'
            )

        print(f"    ⚠️  Total warnings: {len(warnings)}")

        return warnings
