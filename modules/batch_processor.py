"""
Batch Processor Module

Processes multiple graphics in batch with progress tracking and error handling.
"""

import os
import time
from typing import List, Dict, Optional, Callable
from datetime import datetime
import logging


class BatchProcessor:
    """Process multiple graphics in batch with progress tracking"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.current_batch = None
        self.progress_callback = None

    def process_batch(
        self,
        project_id: str,
        graphics: List[Dict],
        psd_service,
        aepx_service,
        matching_service,
        preview_service,
        auto_process_threshold: float = 0.85,
        require_manual_review: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Process multiple graphics in batch

        Args:
            project_id: Project ID
            graphics: List of graphic objects to process
            psd_service: PSD service instance
            aepx_service: AEPX service instance
            matching_service: Matching service instance
            preview_service: Preview service instance
            auto_process_threshold: Confidence threshold for auto-processing
            require_manual_review: If True, all graphics need manual review
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with batch processing results
        """
        self.progress_callback = progress_callback

        results = {
            'project_id': project_id,
            'total': len(graphics),
            'processed': 0,
            'completed': 0,
            'needs_review': 0,
            'failed': 0,
            'started_at': datetime.now().isoformat(),
            'graphics': []
        }

        self.logger.info(f"Starting batch processing for project {project_id} - {len(graphics)} graphics")

        for i, graphic in enumerate(graphics):
            self._update_progress(i + 1, len(graphics), graphic['name'])

            try:
                result = self._process_single_graphic(
                    graphic=graphic,
                    psd_service=psd_service,
                    aepx_service=aepx_service,
                    matching_service=matching_service,
                    preview_service=preview_service,
                    auto_process_threshold=auto_process_threshold,
                    require_manual_review=require_manual_review
                )

                results['graphics'].append(result)
                results['processed'] += 1

                if result['status'] == 'complete':
                    results['completed'] += 1
                elif result['status'] == 'needs_review':
                    results['needs_review'] += 1
                elif result['status'] == 'error':
                    results['failed'] += 1

            except Exception as e:
                self.logger.error(f"Failed to process graphic {graphic['name']}: {e}", exc_info=True)
                results['graphics'].append({
                    'graphic_id': graphic['id'],
                    'name': graphic['name'],
                    'status': 'error',
                    'error': str(e)
                })
                results['failed'] += 1

        results['completed_at'] = datetime.now().isoformat()

        self.logger.info(f"Batch processing complete - {results['completed']} completed, "
                        f"{results['needs_review']} need review, {results['failed']} failed")

        return results

    def _process_single_graphic(
        self,
        graphic: Dict,
        psd_service,
        aepx_service,
        matching_service,
        preview_service,
        auto_process_threshold: float,
        require_manual_review: bool
    ) -> Dict:
        """Process a single graphic"""

        graphic_id = graphic['id']
        graphic_name = graphic['name']
        psd_path = graphic.get('psd_path')
        template_path = graphic.get('template_path')

        self.logger.info(f"Processing graphic: {graphic_name}")

        # Validate inputs
        if not psd_path or not os.path.exists(psd_path):
            return {
                'graphic_id': graphic_id,
                'name': graphic_name,
                'status': 'error',
                'error': 'PSD file not found'
            }

        if not template_path or not os.path.exists(template_path):
            return {
                'graphic_id': graphic_id,
                'name': graphic_name,
                'status': 'error',
                'error': 'Template file not found'
            }

        try:
            # Step 1: Parse PSD
            psd_result = psd_service.parse_psd(psd_path)
            if not psd_result.is_success():
                return {
                    'graphic_id': graphic_id,
                    'name': graphic_name,
                    'status': 'error',
                    'error': f'PSD parsing failed: {psd_result.get_error()}'
                }

            psd_data = psd_result.get_data()

            # Step 2: Parse AEPX
            aepx_result = aepx_service.parse_aepx(template_path)
            if not aepx_result.is_success():
                return {
                    'graphic_id': graphic_id,
                    'name': graphic_name,
                    'status': 'error',
                    'error': f'AEPX parsing failed: {aepx_result.get_error()}'
                }

            aepx_data = aepx_result.get_data()

            # Step 3: Match content
            match_result = matching_service.match_content(psd_data, aepx_data)
            if not match_result.is_success():
                return {
                    'graphic_id': graphic_id,
                    'name': graphic_name,
                    'status': 'error',
                    'error': f'Matching failed: {match_result.get_error()}'
                }

            mappings = match_result.get_data()

            # Step 4: Calculate confidence
            stats_result = matching_service.calculate_statistics(mappings)
            confidence_score = 0.0
            if stats_result.is_success():
                stats = stats_result.get_data()
                # Use average confidence as overall score
                if stats.get('total_mappings', 0) > 0:
                    confidence_score = stats.get('average_confidence', 0.0)

            # Step 5: Detect conflicts
            conflicts_result = matching_service.detect_conflicts(mappings, psd_data, aepx_data)
            conflicts = conflicts_result.get_data() if conflicts_result.is_success() else []

            # Step 6: Determine status based on confidence and settings
            if require_manual_review:
                status = 'needs_review'
            elif confidence_score < auto_process_threshold:
                status = 'needs_review'
            elif len(conflicts) > 0:
                # Check if there are critical conflicts
                has_critical = any(c.get('severity') == 'critical' for c in conflicts)
                status = 'needs_review' if has_critical else 'complete'
            else:
                status = 'complete'

            # Step 7: Generate preview (optional, can be done later)
            preview_path = None
            # We can skip preview in batch to speed things up
            # or generate it selectively

            return {
                'graphic_id': graphic_id,
                'name': graphic_name,
                'status': status,
                'mappings': mappings,
                'conflicts': conflicts,
                'confidence_score': confidence_score,
                'preview_path': preview_path,
                'processed_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error processing graphic {graphic_name}: {e}", exc_info=True)
            return {
                'graphic_id': graphic_id,
                'name': graphic_name,
                'status': 'error',
                'error': str(e)
            }

    def _update_progress(self, current: int, total: int, current_item: str):
        """Update progress callback"""
        if self.progress_callback:
            self.progress_callback({
                'current': current,
                'total': total,
                'percentage': (current / total) * 100,
                'current_item': current_item
            })
