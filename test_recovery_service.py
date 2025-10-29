"""
Tests for Error Recovery Service

Tests retry mechanisms, error diagnostics, and state management.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.recovery_service import RecoveryService
from services.base_service import Result


class TestRecoveryService(unittest.TestCase):
    """Test RecoveryService functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.logger = MagicMock()
        self.project_service = MagicMock()
        self.recovery_service = RecoveryService(self.logger, self.project_service)

        # Sample project data
        self.project = {
            'id': 'proj_123',
            'name': 'Test Project',
            'graphics': [
                {
                    'id': 'g1',
                    'name': 'Graphic 1',
                    'status': 'error',
                    'error': 'File not found',
                    'psd_data': None,
                    'aepx_data': None,
                    'matches': None,
                    'aspect_ratio_check': None,
                    'has_expressions': False
                },
                {
                    'id': 'g2',
                    'name': 'Graphic 2',
                    'status': 'error',
                    'error': 'Failed to parse file - invalid format',
                    'psd_data': {'width': 1920, 'height': 1080},
                    'aepx_data': None,
                    'matches': None,
                    'aspect_ratio_check': None,
                    'has_expressions': False
                },
                {
                    'id': 'g3',
                    'name': 'Graphic 3',
                    'status': 'error',
                    'error': 'Timeout during processing',
                    'psd_data': {'width': 1920, 'height': 1080},
                    'aepx_data': {'width': 1920, 'height': 1920},
                    'matches': [{'psd_layer': 'Layer1', 'aepx_layer': 'Layer1'}],
                    'aspect_ratio_check': None,
                    'has_expressions': False
                },
                {
                    'id': 'g4',
                    'name': 'Graphic 4',
                    'status': 'completed',
                    'has_expressions': True
                }
            ]
        }

    def test_determine_restart_step_start(self):
        """Test restart step detection - full restart"""
        graphic = {
            'id': 'g1',
            'matches': None,
            'aspect_ratio_check': None,
            'has_expressions': False
        }

        step = self.recovery_service._determine_restart_step(graphic)
        self.assertEqual(step, 'start')

    def test_determine_restart_step_aspect_ratio(self):
        """Test restart step detection - from aspect ratio"""
        graphic = {
            'id': 'g1',
            'matches': [{'psd_layer': 'Layer1'}],
            'aspect_ratio_check': None,
            'has_expressions': False
        }

        step = self.recovery_service._determine_restart_step(graphic)
        self.assertEqual(step, 'aspect_ratio')

    def test_determine_restart_step_expressions(self):
        """Test restart step detection - from expressions"""
        graphic = {
            'id': 'g1',
            'matches': [{'psd_layer': 'Layer1'}],
            'aspect_ratio_check': {'can_auto_apply': True},
            'has_expressions': False
        }

        step = self.recovery_service._determine_restart_step(graphic)
        self.assertEqual(step, 'expressions')

    def test_determine_restart_step_matching(self):
        """Test restart step detection - from matching"""
        graphic = {
            'id': 'g1',
            'matches': [{'psd_layer': 'Layer1'}],
            'aspect_ratio_check': None,
            'has_expressions': False
        }

        step = self.recovery_service._determine_restart_step(graphic)
        self.assertEqual(step, 'aspect_ratio')  # Has matches but no aspect check

    def test_clear_processing_data(self):
        """Test clearing all processing data"""
        graphic = {
            'id': 'g1',
            'status': 'error',
            'psd_data': {'width': 1920},
            'aepx_data': {'width': 1920},
            'matches': ['match1'],
            'aspect_ratio_check': {'check': True},
            'has_expressions': True,
            'preview_path': '/path/to/preview.jpg'
        }

        self.recovery_service._clear_processing_data(graphic)

        # All processing data should be cleared
        self.assertNotIn('psd_data', graphic)
        self.assertNotIn('aepx_data', graphic)
        self.assertNotIn('matches', graphic)
        self.assertNotIn('aspect_ratio_check', graphic)
        self.assertNotIn('has_expressions', graphic)
        self.assertNotIn('preview_path', graphic)
        self.assertEqual(graphic['status'], 'pending')

    @patch('services.recovery_service.datetime')
    def test_retry_graphic_from_start(self, mock_datetime):
        """Test retry with full restart"""
        mock_datetime.now.return_value.isoformat.return_value = '2025-01-26T10:00:00'

        self.project_service.get_project.return_value = Result.success(self.project)
        self.project_service.process_graphic.return_value = Result.success({'status': 'processing'})
        self.project_service._save_project.return_value = None

        result = self.recovery_service.retry_graphic(
            project_id='proj_123',
            graphic_id='g1',
            from_step='start'
        )

        self.assertTrue(result.is_success())

        # Verify graphic was updated
        graphic = self.project['graphics'][0]
        # Status is 'pending' because _clear_processing_data was called for full restart
        self.assertEqual(graphic['status'], 'pending')
        self.assertIsNone(graphic['error'])
        self.assertEqual(graphic['retry_count'], 1)
        self.assertEqual(graphic['retry_from_step'], 'start')

    def test_retry_graphic_project_not_found(self):
        """Test retry when project doesn't exist"""
        self.project_service.get_project.return_value = Result.failure("Project not found")

        result = self.recovery_service.retry_graphic(
            project_id='invalid_id',
            graphic_id='g1'
        )

        self.assertFalse(result.is_success())
        self.assertIn('Project not found', result.get_error())

    def test_retry_graphic_graphic_not_found(self):
        """Test retry when graphic doesn't exist"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.retry_graphic(
            project_id='proj_123',
            graphic_id='invalid_id'
        )

        self.assertFalse(result.is_success())
        self.assertIn('Graphic not found', result.get_error())

    def test_reset_graphic_state_to_pending(self):
        """Test resetting graphic to pending state"""
        self.project_service.get_project.return_value = Result.success(self.project)
        self.project_service._save_project.return_value = None

        result = self.recovery_service.reset_graphic_state(
            project_id='proj_123',
            graphic_id='g3',
            to_state='pending'
        )

        self.assertTrue(result.is_success())

        # Verify all data was cleared
        graphic = self.project['graphics'][2]
        self.assertEqual(graphic['status'], 'pending')
        self.assertIsNone(graphic['error'])
        self.assertNotIn('psd_data', graphic)
        self.assertNotIn('matches', graphic)

    def test_reset_graphic_state_to_matched(self):
        """Test resetting graphic to matched state"""
        self.project_service.get_project.return_value = Result.success(self.project)
        self.project_service._save_project.return_value = None

        result = self.recovery_service.reset_graphic_state(
            project_id='proj_123',
            graphic_id='g3',
            to_state='matched'
        )

        self.assertTrue(result.is_success())

        # Verify partial data was cleared
        graphic = self.project['graphics'][2]
        self.assertEqual(graphic['status'], 'matched')
        self.assertNotIn('aspect_ratio_check', graphic)
        self.assertNotIn('has_expressions', graphic)

    def test_reset_graphic_state_invalid_state(self):
        """Test reset with invalid state"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.reset_graphic_state(
            project_id='proj_123',
            graphic_id='g1',
            to_state='invalid_state'
        )

        self.assertFalse(result.is_success())
        self.assertIn('Unknown state', result.get_error())

    def test_diagnose_error_file_not_found(self):
        """Test error diagnosis - file not found"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.diagnose_error(
            project_id='proj_123',
            graphic_id='g1'
        )

        self.assertTrue(result.is_success())
        diagnosis = result.get_data()

        self.assertEqual(diagnosis['error_type'], 'file_not_found')
        self.assertEqual(diagnosis['error_step'], 'file_access')
        self.assertFalse(diagnosis['can_retry'])
        self.assertFalse(diagnosis['retry_recommended'])
        self.assertIn('Re-upload', diagnosis['suggested_fixes'][0])

    def test_diagnose_error_parsing(self):
        """Test error diagnosis - parsing error"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.diagnose_error(
            project_id='proj_123',
            graphic_id='g2'
        )

        self.assertTrue(result.is_success())
        diagnosis = result.get_data()

        self.assertEqual(diagnosis['error_type'], 'parsing_error')
        self.assertTrue(diagnosis['can_retry'])
        self.assertFalse(diagnosis['retry_recommended'])

    def test_diagnose_error_timeout(self):
        """Test error diagnosis - timeout"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.diagnose_error(
            project_id='proj_123',
            graphic_id='g3'
        )

        self.assertTrue(result.is_success())
        diagnosis = result.get_data()

        self.assertEqual(diagnosis['error_type'], 'timeout')
        self.assertTrue(diagnosis['can_retry'])
        self.assertTrue(diagnosis['retry_recommended'])
        self.assertIn('Retry', diagnosis['suggested_fixes'][0])

    def test_diagnose_error_not_in_error_state(self):
        """Test diagnosis of graphic not in error state"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.diagnose_error(
            project_id='proj_123',
            graphic_id='g4'  # Completed graphic
        )

        self.assertFalse(result.is_success())
        self.assertIn('not in error state', result.get_error())

    def test_analyze_error_memory(self):
        """Test analyzing memory error"""
        graphic = {'id': 'g1'}
        error_msg = "Out of memory during processing"

        diagnosis = self.recovery_service._analyze_error_message(error_msg, graphic)

        self.assertEqual(diagnosis['error_type'], 'memory_error')
        self.assertTrue(diagnosis['can_retry'])
        self.assertTrue(diagnosis['retry_recommended'])

    def test_analyze_error_aspect_ratio(self):
        """Test analyzing aspect ratio review error"""
        graphic = {'id': 'g1'}
        error_msg = "Aspect ratio review required"

        diagnosis = self.recovery_service._analyze_error_message(error_msg, graphic)

        self.assertEqual(diagnosis['error_type'], 'requires_human_review')
        self.assertFalse(diagnosis['can_retry'])
        self.assertFalse(diagnosis['retry_recommended'])

    def test_analyze_error_matching(self):
        """Test analyzing matching error"""
        graphic = {'id': 'g1'}
        error_msg = "No matches found between PSD and AEPX"

        diagnosis = self.recovery_service._analyze_error_message(error_msg, graphic)

        self.assertEqual(diagnosis['error_type'], 'matching_error')
        self.assertTrue(diagnosis['can_retry'])
        self.assertFalse(diagnosis['retry_recommended'])

    def test_bulk_retry_all_failed(self):
        """Test bulk retry of all failed graphics"""
        self.project_service.get_project.return_value = Result.success(self.project)
        self.project_service.process_graphic.return_value = Result.success({'status': 'processing'})
        self.project_service._save_project.return_value = None

        result = self.recovery_service.bulk_retry(
            project_id='proj_123',
            graphic_ids=None  # Retry all failed
        )

        self.assertTrue(result.is_success())
        data = result.get_data()

        # Should retry 3 error graphics (g1, g2, g3)
        self.assertEqual(data['total'], 3)
        self.assertGreater(data['successful'], 0)

    def test_bulk_retry_specific_graphics(self):
        """Test bulk retry of specific graphics"""
        self.project_service.get_project.return_value = Result.success(self.project)
        self.project_service.process_graphic.return_value = Result.success({'status': 'processing'})
        self.project_service._save_project.return_value = None

        result = self.recovery_service.bulk_retry(
            project_id='proj_123',
            graphic_ids=['g1', 'g2']
        )

        self.assertTrue(result.is_success())
        data = result.get_data()

        # Should retry only 2 specified graphics
        self.assertEqual(data['total'], 2)

    def test_bulk_retry_no_failed_graphics(self):
        """Test bulk retry when no graphics failed"""
        # Project with no error graphics
        project = {
            'id': 'proj_123',
            'graphics': [
                {'id': 'g1', 'status': 'completed'}
            ]
        }

        self.project_service.get_project.return_value = Result.success(project)

        result = self.recovery_service.bulk_retry(
            project_id='proj_123',
            graphic_ids=None
        )

        self.assertTrue(result.is_success())
        data = result.get_data()

        self.assertEqual(data['total'], 0)
        self.assertEqual(data['message'], 'No graphics to retry')

    def test_get_retry_stats(self):
        """Test getting retry statistics"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.get_retry_stats(project_id='proj_123')

        self.assertTrue(result.is_success())
        stats = result.get_data()

        self.assertEqual(stats['total_graphics'], 4)
        self.assertEqual(stats['error_count'], 3)
        self.assertIsInstance(stats['avg_retries'], float)
        self.assertIsInstance(stats['most_common_errors'], list)

    def test_get_retry_stats_with_retries(self):
        """Test retry stats with retry counts"""
        # Add retry counts to graphics
        self.project['graphics'][0]['retry_count'] = 2
        self.project['graphics'][1]['retry_count'] = 1
        self.project['graphics'][2]['retry_count'] = 3

        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.get_retry_stats(project_id='proj_123')

        self.assertTrue(result.is_success())
        stats = result.get_data()

        self.assertEqual(stats['retry_count'], 6)  # 2 + 1 + 3
        self.assertEqual(stats['avg_retries'], 1.5)  # 6 / 4 graphics

    def test_get_retry_stats_error_type_categorization(self):
        """Test error type categorization in stats"""
        self.project_service.get_project.return_value = Result.success(self.project)

        result = self.recovery_service.get_retry_stats(project_id='proj_123')

        self.assertTrue(result.is_success())
        stats = result.get_data()

        # Should have categorized the 3 different error types
        error_types = [e['error_type'] for e in stats['most_common_errors']]
        self.assertIn('file_not_found', error_types)
        self.assertIn('parsing_error', error_types)
        self.assertIn('timeout', error_types)


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Recovery Service")
    print("=" * 70)
    print()

    # Run tests
    unittest.main(verbosity=2)
