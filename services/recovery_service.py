"""
Error Recovery Service

Provides retry mechanisms and error state management for failed graphics.
Enables selective retries, checkpoint resets, and error diagnostics.
"""

from typing import Dict, Optional, List
from datetime import datetime
from services.base_service import BaseService, Result


class RecoveryService(BaseService):
    """
    Service for recovering from processing errors

    Features:
    - Retry individual graphics from specific steps
    - Auto-detect optimal restart points
    - Reset graphics to checkpoints
    - Diagnose errors with actionable suggestions
    - Bulk retry operations
    - Retry statistics and tracking
    """

    def __init__(self, logger, project_service):
        """
        Initialize recovery service

        Args:
            logger: Logger instance
            project_service: ProjectService instance for accessing projects
        """
        super().__init__(logger)
        self.project_service = project_service

    def retry_graphic(
        self,
        project_id: str,
        graphic_id: str,
        from_step: Optional[str] = None
    ) -> Result:
        """
        Retry processing a failed graphic

        Args:
            project_id: Project ID
            graphic_id: Graphic ID
            from_step: Optional step to resume from:
                - 'start': Full restart from beginning
                - 'matching': Resume from layer matching
                - 'aspect_ratio': Resume from aspect ratio check
                - 'expressions': Resume from expression generation
                - None (default): Auto-detect best restart point

        Auto-detection logic:
        - If has matches but no aspect_ratio_check → 'aspect_ratio'
        - If has aspect_ratio_check but no expressions → 'expressions'
        - Otherwise → 'start'

        Returns:
            Result with retry outcome
        """
        try:
            self.log_info(f"Retrying graphic {graphic_id}, from_step={from_step}")

            # Get project and graphic
            project_result = self.project_service.get_project(project_id)
            if not project_result.is_success():
                return Result.failure("Project not found")

            project = project_result.get_data()
            graphic = next((g for g in project['graphics'] if g['id'] == graphic_id), None)

            if not graphic:
                return Result.failure("Graphic not found")

            # Determine restart point
            restart_step = from_step or self._determine_restart_step(graphic)
            self.log_info(f"Auto-detected restart step: {restart_step}")

            # Clear error state
            graphic['status'] = 'retrying'
            graphic['error'] = None
            graphic['retry_count'] = graphic.get('retry_count', 0) + 1
            graphic['last_retry_time'] = datetime.now().isoformat()

            # Store restart step
            graphic['retry_from_step'] = restart_step

            self.project_service._save_project(project)

            # Execute retry based on step
            if restart_step == 'start':
                # Full restart
                self.log_info("Full restart - clearing all processing data")
                self._clear_processing_data(graphic)
                self.project_service._save_project(project)
                return self.project_service.process_graphic(project_id, graphic_id)

            elif restart_step == 'matching':
                # Has PSD/AEPX data, redo matching
                self.log_info("Restarting from matching")
                graphic['matches'] = None
                graphic['aspect_ratio_check'] = None
                graphic['has_expressions'] = False
                self.project_service._save_project(project)
                return self.project_service.process_graphic(project_id, graphic_id)

            elif restart_step == 'aspect_ratio':
                # Has matches, redo aspect ratio check
                self.log_info("Restarting from aspect ratio check")
                graphic['aspect_ratio_check'] = None
                graphic['aspect_ratio_review_pending'] = False
                graphic['has_expressions'] = False
                self.project_service._save_project(project)
                return self.project_service.process_graphic(project_id, graphic_id)

            elif restart_step == 'expressions':
                # Has aspect ratio approved, redo expressions
                self.log_info("Restarting from expression generation")
                graphic['has_expressions'] = False
                graphic['expression_count'] = 0
                graphic['expression_confidence'] = 0
                self.project_service._save_project(project)
                return self.project_service.process_graphic(project_id, graphic_id)

            else:
                return Result.failure(f"Unknown restart step: {restart_step}")

        except Exception as e:
            self.log_error(f"Retry failed: {e}", e)
            return Result.failure(str(e))

    def _determine_restart_step(self, graphic: Dict) -> str:
        """
        Auto-detect best restart point based on graphic state

        Logic:
        - If has matches and aspect_ratio_check: restart from expressions
        - If has matches but no aspect_ratio_check: restart from aspect_ratio
        - Otherwise: full restart

        Args:
            graphic: Graphic dict

        Returns:
            Step name ('start', 'matching', 'aspect_ratio', 'expressions')
        """
        has_matches = graphic.get('matches') is not None
        has_aspect_check = graphic.get('aspect_ratio_check') is not None
        has_expressions = graphic.get('has_expressions', False)

        if has_matches and has_aspect_check and not has_expressions:
            return 'expressions'
        elif has_matches and not has_aspect_check:
            return 'aspect_ratio'
        elif has_matches:
            return 'matching'
        else:
            return 'start'

    def _clear_processing_data(self, graphic: Dict):
        """
        Clear all processing artifacts for full restart

        Args:
            graphic: Graphic dict to clear
        """
        graphic.pop('psd_data', None)
        graphic.pop('aepx_data', None)
        graphic.pop('matches', None)
        graphic.pop('aspect_ratio_check', None)
        graphic.pop('aspect_ratio_review_pending', None)
        graphic.pop('aspect_ratio_transform_applied', None)
        graphic.pop('has_expressions', None)
        graphic.pop('expression_count', None)
        graphic.pop('expression_confidence', None)
        graphic.pop('preview_path', None)
        graphic['status'] = 'pending'

    def reset_graphic_state(
        self,
        project_id: str,
        graphic_id: str,
        to_state: str = 'pending'
    ) -> Result:
        """
        Reset graphic to initial or specific checkpoint

        Args:
            project_id: Project ID
            graphic_id: Graphic ID
            to_state: State to reset to:
                - 'pending': Initial state, ready for full processing
                - 'matched': After matching, before aspect ratio
                - 'aspect_approved': After aspect ratio, before expressions

        Returns:
            Result with reset confirmation
        """
        try:
            self.log_info(f"Resetting graphic {graphic_id} to state: {to_state}")

            project_result = self.project_service.get_project(project_id)
            if not project_result.is_success():
                return Result.failure("Project not found")

            project = project_result.get_data()
            graphic = next((g for g in project['graphics'] if g['id'] == graphic_id), None)

            if not graphic:
                return Result.failure("Graphic not found")

            # Clear error state
            graphic['error'] = None
            graphic['status'] = to_state

            # Clear data based on target state
            if to_state == 'pending':
                # Full reset
                self._clear_processing_data(graphic)

            elif to_state == 'matched':
                # Keep PSD/AEPX/matches, clear rest
                graphic.pop('aspect_ratio_check', None)
                graphic.pop('aspect_ratio_review_pending', None)
                graphic.pop('aspect_ratio_transform_applied', None)
                graphic.pop('has_expressions', None)
                graphic.pop('expression_count', None)
                graphic.pop('expression_confidence', None)

            elif to_state == 'aspect_approved':
                # Keep everything up to aspect ratio, clear expressions
                graphic.pop('has_expressions', None)
                graphic.pop('expression_count', None)
                graphic.pop('expression_confidence', None)

            else:
                return Result.failure(f"Unknown state: {to_state}")

            self.project_service._save_project(project)
            self.log_info(f"Reset complete: {graphic_id} → {to_state}")

            return Result.success({
                'graphic_id': graphic_id,
                'state': to_state,
                'message': f"Reset to {to_state}"
            })

        except Exception as e:
            self.log_error(f"Reset failed: {e}", e)
            return Result.failure(str(e))

    def diagnose_error(
        self,
        project_id: str,
        graphic_id: str
    ) -> Result:
        """
        Diagnose why a graphic failed

        Returns detailed error analysis:
        {
            'error_type': str,           # Category of error
            'error_step': str,           # Which step failed
            'error_message': str,        # Original error
            'possible_causes': List[str], # Why it happened
            'suggested_fixes': List[str], # How to fix
            'can_retry': bool,           # Safe to retry?
            'retry_recommended': bool,   # Should retry?
            'from_step': str            # Best restart point
        }

        Args:
            project_id: Project ID
            graphic_id: Graphic ID

        Returns:
            Result with diagnosis dict
        """
        try:
            self.log_info(f"Diagnosing error for graphic {graphic_id}")

            project_result = self.project_service.get_project(project_id)
            if not project_result.is_success():
                return Result.failure("Project not found")

            project = project_result.get_data()
            graphic = next((g for g in project['graphics'] if g['id'] == graphic_id), None)

            if not graphic:
                return Result.failure("Graphic not found")

            if graphic.get('status') != 'error':
                return Result.failure("Graphic is not in error state")

            error_msg = graphic.get('error', 'Unknown error')

            # Analyze error
            diagnosis = self._analyze_error_message(error_msg, graphic)

            # Add restart recommendation
            diagnosis['from_step'] = self._determine_restart_step(graphic)

            return Result.success(diagnosis)

        except Exception as e:
            self.log_error(f"Diagnosis failed: {e}", e)
            return Result.failure(str(e))

    def _analyze_error_message(self, error_msg: str, graphic: Dict) -> Dict:
        """
        Analyze error message to categorize and suggest fixes

        Uses pattern matching on error messages

        Args:
            error_msg: Error message text
            graphic: Graphic dict for context

        Returns:
            Diagnosis dict with error info and suggestions
        """
        error_lower = error_msg.lower()

        # File not found
        if 'not found' in error_lower or 'no such file' in error_lower:
            return {
                'error_type': 'file_not_found',
                'error_step': 'file_access',
                'error_message': error_msg,
                'possible_causes': [
                    'File was moved or deleted after upload',
                    'Incorrect file path in project data',
                    'File system permission issue'
                ],
                'suggested_fixes': [
                    'Re-upload the PSD or AEPX file',
                    'Verify file exists at expected location',
                    'Check file permissions'
                ],
                'can_retry': False,
                'retry_recommended': False
            }

        # Parsing/format errors
        elif 'parse' in error_lower or 'invalid' in error_lower or 'corrupt' in error_lower:
            return {
                'error_type': 'parsing_error',
                'error_step': 'file_parsing',
                'error_message': error_msg,
                'possible_causes': [
                    'File is corrupted or incomplete',
                    'Unsupported file format or version',
                    'File contains invalid data'
                ],
                'suggested_fixes': [
                    'Re-save file in compatible format',
                    'Try opening and re-saving in Photoshop/After Effects',
                    'Use a different version of the file'
                ],
                'can_retry': True,
                'retry_recommended': False
            }

        # Memory/resource errors
        elif 'memory' in error_lower or 'out of' in error_lower:
            return {
                'error_type': 'memory_error',
                'error_step': 'processing',
                'error_message': error_msg,
                'possible_causes': [
                    'File is too large or complex',
                    'Too many layers or effects',
                    'System running out of memory'
                ],
                'suggested_fixes': [
                    'Simplify PSD (flatten layers, reduce size)',
                    'Process fewer graphics simultaneously',
                    'Increase system memory'
                ],
                'can_retry': True,
                'retry_recommended': True
            }

        # Timeout errors
        elif 'timeout' in error_lower or 'timed out' in error_lower:
            return {
                'error_type': 'timeout',
                'error_step': 'processing',
                'error_message': error_msg,
                'possible_causes': [
                    'Processing took too long',
                    'System performance issue',
                    'Very complex file'
                ],
                'suggested_fixes': [
                    'Retry - may succeed on second attempt',
                    'Simplify file if possible',
                    'Check system performance'
                ],
                'can_retry': True,
                'retry_recommended': True
            }

        # Aspect ratio review pending
        elif 'aspect ratio' in error_lower and 'review' in error_lower:
            return {
                'error_type': 'requires_human_review',
                'error_step': 'aspect_ratio_check',
                'error_message': error_msg,
                'possible_causes': [
                    'Aspect ratio mismatch requires human decision',
                    'Cross-category transformation detected',
                    'Large dimension difference'
                ],
                'suggested_fixes': [
                    'Review aspect ratio options in UI',
                    'Choose fit or fill transformation',
                    'Or skip this graphic'
                ],
                'can_retry': False,
                'retry_recommended': False
            }

        # Matching errors
        elif 'match' in error_lower or 'no matches' in error_lower:
            return {
                'error_type': 'matching_error',
                'error_step': 'layer_matching',
                'error_message': error_msg,
                'possible_causes': [
                    'Layer names don\'t match between PSD and AEPX',
                    'No compatible layers found',
                    'Naming convention mismatch'
                ],
                'suggested_fixes': [
                    'Check layer names in PSD and AEPX match',
                    'Use consistent naming convention',
                    'Verify template is correct for this PSD'
                ],
                'can_retry': True,
                'retry_recommended': False
            }

        # Generic/unknown
        else:
            return {
                'error_type': 'unknown',
                'error_step': 'unknown',
                'error_message': error_msg,
                'possible_causes': [
                    'Unknown or unexpected error',
                    'Check application logs for details'
                ],
                'suggested_fixes': [
                    'Try full restart',
                    'Check application logs',
                    'Contact support if issue persists'
                ],
                'can_retry': True,
                'retry_recommended': True
            }

    def bulk_retry(
        self,
        project_id: str,
        graphic_ids: Optional[List[str]] = None,
        from_step: Optional[str] = None
    ) -> Result:
        """
        Retry multiple graphics or all failed graphics

        Args:
            project_id: Project ID
            graphic_ids: Optional specific graphic IDs
                        If None, retries all error/failed graphics
            from_step: Optional restart step for all graphics

        Returns:
            Result with bulk retry statistics:
            {
                'total': int,
                'successful': int,
                'failed': int,
                'results': List[Dict]
            }
        """
        try:
            project_result = self.project_service.get_project(project_id)
            if not project_result.is_success():
                return Result.failure("Project not found")

            project = project_result.get_data()

            # Determine which graphics to retry
            if graphic_ids:
                graphics_to_retry = [
                    g for g in project['graphics']
                    if g['id'] in graphic_ids
                ]
            else:
                # Retry all failed/error graphics
                graphics_to_retry = [
                    g for g in project['graphics']
                    if g.get('status') in ['error', 'failed']
                ]

            if not graphics_to_retry:
                return Result.success({
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'results': [],
                    'message': 'No graphics to retry'
                })

            self.log_info(f"Bulk retry: {len(graphics_to_retry)} graphics")

            # Retry each
            results = []
            for graphic in graphics_to_retry:
                retry_result = self.retry_graphic(
                    project_id=project_id,
                    graphic_id=graphic['id'],
                    from_step=from_step
                )

                results.append({
                    'graphic_id': graphic['id'],
                    'graphic_name': graphic.get('name', 'Unknown'),
                    'success': retry_result.is_success(),
                    'error': retry_result.get_error() if not retry_result.is_success() else None
                })

            # Calculate statistics
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful

            self.log_info(f"Bulk retry complete: {successful} successful, {failed} failed")

            return Result.success({
                'total': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            })

        except Exception as e:
            self.log_error(f"Bulk retry failed: {e}", e)
            return Result.failure(str(e))

    def get_retry_stats(self, project_id: str) -> Result:
        """
        Get retry statistics for a project

        Args:
            project_id: Project ID

        Returns:
            Result with statistics dict:
            {
                'total_graphics': int,
                'error_count': int,
                'retry_count': int,
                'avg_retries': float,
                'most_common_errors': List[Dict]
            }
        """
        try:
            project_result = self.project_service.get_project(project_id)
            if not project_result.is_success():
                return Result.failure("Project not found")

            project = project_result.get_data()
            graphics = project['graphics']

            # Count errors
            error_graphics = [g for g in graphics if g.get('status') == 'error']

            # Count retries
            retry_counts = [g.get('retry_count', 0) for g in graphics]
            total_retries = sum(retry_counts)
            avg_retries = total_retries / len(graphics) if graphics else 0

            # Count error types
            error_types = {}
            for graphic in error_graphics:
                error_msg = graphic.get('error', 'Unknown')
                diagnosis = self._analyze_error_message(error_msg, graphic)
                error_type = diagnosis['error_type']
                error_types[error_type] = error_types.get(error_type, 0) + 1

            # Sort by frequency
            most_common = [
                {'error_type': k, 'count': v}
                for k, v in sorted(error_types.items(), key=lambda x: x[1], reverse=True)
            ]

            return Result.success({
                'total_graphics': len(graphics),
                'error_count': len(error_graphics),
                'retry_count': total_retries,
                'avg_retries': round(avg_retries, 2),
                'most_common_errors': most_common[:5]  # Top 5
            })

        except Exception as e:
            self.log_error(f"Get retry stats failed: {e}", e)
            return Result.failure(str(e))
