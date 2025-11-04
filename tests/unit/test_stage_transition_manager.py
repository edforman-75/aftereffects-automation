"""
Unit tests for StageTransitionManager.

Tests the StageTransitionManager class methods in isolation using mocks.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import threading
import time

from services.stage_transition_manager import StageTransitionManager


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def mock_job_service():
    """Create a mock JobService."""
    service = Mock()
    service.get_job.return_value = Mock(
        job_id='test-job-1',
        current_stage=1,
        psd_path='/path/to/test.psd',
        aepx_path='/path/to/test.aepx'
    )
    return service


@pytest.fixture
def mock_log_service():
    """Create a mock LogService."""
    return Mock()


@pytest.fixture
def mock_warning_service():
    """Create a mock WarningService."""
    return Mock()


@pytest.fixture
def transition_manager(
    mock_logger,
    mock_job_service,
    mock_log_service,
    mock_warning_service
):
    """Create a StageTransitionManager instance with mocked dependencies."""
    with patch('services.stage_transition_manager.JobService', return_value=mock_job_service):
        with patch('services.stage_transition_manager.LogService', return_value=mock_log_service):
            with patch('services.stage_transition_manager.WarningService', return_value=mock_warning_service):
                manager = StageTransitionManager(mock_logger)
                manager.job_service = mock_job_service
                manager.log_service = mock_log_service
                manager.warning_service = mock_warning_service
                return manager


class TestStageTransitionManagerTransitionStage:
    """Test transition_stage method."""

    @pytest.mark.unit
    def test_transition_stage_success(
        self,
        transition_manager,
        mock_job_service,
        mock_log_service
    ):
        """Test successful stage transition."""
        result = transition_manager.transition_stage(
            job_id='test-job-1',
            from_stage=1,
            to_stage=2,
            user_id='user-123'
        )

        assert result['success'] is True
        assert result['job_id'] == 'test-job-1'
        assert result['from_stage'] == 1
        assert result['to_stage'] == 2
        assert result['status'] == 'processing'

        # Verify stage was completed
        mock_job_service.complete_stage.assert_called_once_with('test-job-1', 1, 'user-123')

        # Verify status was updated
        mock_job_service.update_job_status.assert_called_once_with(
            'test-job-1',
            status='processing',
            current_stage=2
        )

        # Verify logging
        mock_log_service.log_stage_completed.assert_called_once()
        mock_log_service.log_action.assert_called_once()

    @pytest.mark.unit
    def test_transition_stage_job_not_found(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test transition when job not found."""
        mock_job_service.get_job.return_value = None

        result = transition_manager.transition_stage(
            job_id='nonexistent',
            from_stage=1,
            to_stage=2,
            user_id='user-123'
        )

        assert result['success'] is False
        assert 'not found' in result['error'].lower()
        mock_job_service.complete_stage.assert_not_called()

    @pytest.mark.unit
    def test_transition_stage_wrong_current_stage(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test transition when job is in wrong stage."""
        mock_job = Mock(job_id='test-job-1', current_stage=3)
        mock_job_service.get_job.return_value = mock_job

        result = transition_manager.transition_stage(
            job_id='test-job-1',
            from_stage=1,
            to_stage=2,
            user_id='user-123'
        )

        assert result['success'] is False
        assert 'stage 3' in result['error'].lower()
        mock_job_service.complete_stage.assert_not_called()

    @pytest.mark.unit
    def test_transition_stage_with_approved_data(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test transition with approved data."""
        approved_data = {
            'matches': [
                {'psd_layer': 'Layer1', 'aepx_layer': 'Placeholder1'}
            ]
        }

        # Set current stage to 2 for this test
        mock_job = Mock(job_id='test-job-1', current_stage=2)
        mock_job_service.get_job.return_value = mock_job

        result = transition_manager.transition_stage(
            job_id='test-job-1',
            from_stage=2,
            to_stage=3,
            user_id='user-123',
            approved_data=approved_data
        )

        assert result['success'] is True

        # Verify approved matches were stored
        mock_job_service.store_approved_matches.assert_called_once_with(
            'test-job-1',
            approved_data['matches']
        )

    @pytest.mark.unit
    def test_transition_stage_starts_preprocessing(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test that transition starts background preprocessing."""
        with patch.object(transition_manager, '_start_preprocessing') as mock_preprocess:
            result = transition_manager.transition_stage(
                job_id='test-job-1',
                from_stage=1,
                to_stage=2,
                user_id='user-123'
            )

            assert result['success'] is True
            mock_preprocess.assert_called_once_with('test-job-1', 2, 'user-123')

    @pytest.mark.unit
    def test_transition_stage_exception_handling(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test exception handling during transition."""
        mock_job_service.complete_stage.side_effect = Exception("Database error")

        result = transition_manager.transition_stage(
            job_id='test-job-1',
            from_stage=1,
            to_stage=2,
            user_id='user-123'
        )

        assert result['success'] is False
        assert 'database error' in result['error'].lower()


class TestStageTransitionManagerPreprocessing:
    """Test preprocessing methods."""

    @pytest.mark.unit
    def test_start_preprocessing_creates_thread(self, transition_manager):
        """Test that preprocessing starts a background thread."""
        with patch.object(transition_manager, '_preprocess_for_stage'):
            transition_manager._start_preprocessing('test-job-1', 2, 'user-123')

            # Check that thread was created and started
            thread_key = 'test-job-1_stage2'
            assert thread_key in transition_manager.active_threads
            assert isinstance(transition_manager.active_threads[thread_key], threading.Thread)

    @pytest.mark.unit
    def test_start_preprocessing_does_not_duplicate(self, transition_manager):
        """Test that preprocessing doesn't start duplicate threads."""
        with patch.object(transition_manager, '_preprocess_for_stage'):
            # Start first thread
            transition_manager._start_preprocessing('test-job-1', 2, 'user-123')

            # Create a mock alive thread
            mock_thread = Mock()
            mock_thread.is_alive.return_value = True
            transition_manager.active_threads['test-job-1_stage2'] = mock_thread

            # Try to start again
            transition_manager._start_preprocessing('test-job-1', 2, 'user-123')

            # Should not create a new thread
            assert transition_manager.active_threads['test-job-1_stage2'] == mock_thread

    @pytest.mark.unit
    def test_preprocess_for_stage_stage2(self, transition_manager, mock_job_service):
        """Test preprocessing for stage 2."""
        with patch.object(transition_manager, '_preprocess_stage2') as mock_stage2:
            mock_stage2.return_value = {'success': True, 'message': 'Complete'}

            with patch.object(transition_manager, '_mark_preprocessing_complete') as mock_complete:
                transition_manager._preprocess_for_stage('test-job-1', 2, 'user-123')

                mock_stage2.assert_called_once_with('test-job-1')
                mock_complete.assert_called_once_with('test-job-1', 2)

    @pytest.mark.unit
    def test_preprocess_for_stage_stage3(self, transition_manager, mock_job_service):
        """Test preprocessing for stage 3."""
        with patch.object(transition_manager, '_preprocess_stage3_validation') as mock_stage3:
            mock_stage3.return_value = {'success': True, 'message': 'Complete'}

            with patch.object(transition_manager, '_mark_preprocessing_complete') as mock_complete:
                transition_manager._preprocess_for_stage('test-job-1', 3, 'user-123')

                mock_stage3.assert_called_once_with('test-job-1')
                mock_complete.assert_called_once_with('test-job-1', 3)

    @pytest.mark.unit
    def test_preprocess_for_stage_stage4_no_preprocessing(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test that stage 4 has no preprocessing."""
        with patch.object(transition_manager, '_mark_preprocessing_complete') as mock_complete:
            transition_manager._preprocess_for_stage('test-job-1', 4, 'user-123')

            # Stage 4 should complete immediately
            mock_complete.assert_called_once_with('test-job-1', 4)

    @pytest.mark.unit
    def test_preprocess_for_stage_stage5(self, transition_manager, mock_job_service):
        """Test preprocessing for stage 5."""
        with patch.object(transition_manager, '_preprocess_stage5_extendscript') as mock_stage5:
            mock_stage5.return_value = {'success': True, 'message': 'Complete'}

            with patch.object(transition_manager, '_mark_preprocessing_complete') as mock_complete:
                transition_manager._preprocess_for_stage('test-job-1', 5, 'user-123')

                mock_stage5.assert_called_once_with('test-job-1')
                mock_complete.assert_called_once_with('test-job-1', 5)

    @pytest.mark.unit
    def test_preprocess_for_stage_failure(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test preprocessing failure handling."""
        with patch.object(transition_manager, '_preprocess_stage2') as mock_stage2:
            mock_stage2.return_value = {'success': False, 'error': 'Processing failed'}

            with patch.object(transition_manager, '_mark_preprocessing_failed') as mock_failed:
                transition_manager._preprocess_for_stage('test-job-1', 2, 'user-123')

                mock_failed.assert_called_once_with('test-job-1', 2, 'Processing failed')

    @pytest.mark.unit
    def test_preprocess_for_stage_exception(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test preprocessing exception handling."""
        with patch.object(transition_manager, '_preprocess_stage2') as mock_stage2:
            mock_stage2.side_effect = Exception("Unexpected error")

            with patch.object(transition_manager, '_mark_preprocessing_failed') as mock_failed:
                transition_manager._preprocess_for_stage('test-job-1', 2, 'user-123')

                mock_failed.assert_called_once()
                assert 'Unexpected error' in str(mock_failed.call_args[0][2])


class TestStageTransitionManagerStatusUpdates:
    """Test status update methods."""

    @pytest.mark.unit
    def test_mark_preprocessing_complete_stage2(
        self,
        transition_manager,
        mock_job_service,
        mock_log_service
    ):
        """Test marking stage 2 preprocessing complete."""
        transition_manager._mark_preprocessing_complete('test-job-1', 2)

        mock_job_service.update_job_status.assert_called_once_with(
            'test-job-1',
            'awaiting_review'
        )
        mock_log_service.log_action.assert_called_once()

    @pytest.mark.unit
    def test_mark_preprocessing_complete_stage3(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test marking stage 3 preprocessing complete."""
        transition_manager._mark_preprocessing_complete('test-job-1', 3)

        mock_job_service.update_job_status.assert_called_once_with(
            'test-job-1',
            'ready_for_validation'
        )

    @pytest.mark.unit
    def test_mark_preprocessing_complete_stage4(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test marking stage 4 preprocessing complete."""
        transition_manager._mark_preprocessing_complete('test-job-1', 4)

        mock_job_service.update_job_status.assert_called_once_with(
            'test-job-1',
            'awaiting_approval'
        )

    @pytest.mark.unit
    def test_mark_preprocessing_complete_stage5(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test marking stage 5 preprocessing complete."""
        transition_manager._mark_preprocessing_complete('test-job-1', 5)

        mock_job_service.update_job_status.assert_called_once_with(
            'test-job-1',
            'awaiting_download'
        )

    @pytest.mark.unit
    def test_mark_preprocessing_complete_stage6(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test marking stage 6 preprocessing complete."""
        transition_manager._mark_preprocessing_complete('test-job-1', 6)

        mock_job_service.update_job_status.assert_called_once_with(
            'test-job-1',
            'completed'
        )

    @pytest.mark.unit
    def test_mark_preprocessing_failed(
        self,
        transition_manager,
        mock_job_service,
        mock_warning_service,
        mock_log_service
    ):
        """Test marking preprocessing as failed."""
        transition_manager._mark_preprocessing_failed(
            'test-job-1',
            2,
            'Processing error'
        )

        mock_job_service.update_job_status.assert_called_once_with(
            'test-job-1',
            'failed'
        )

        mock_warning_service.add_warning.assert_called_once()
        call_args = mock_warning_service.add_warning.call_args[1]
        assert call_args['job_id'] == 'test-job-1'
        assert call_args['stage'] == 2
        assert call_args['warning_type'] == 'preprocessing_failed'
        assert call_args['severity'] == 'critical'

        mock_log_service.log_error.assert_called_once()


class TestStageTransitionManagerStageSpecificPreprocessing:
    """Test stage-specific preprocessing methods."""

    @pytest.mark.unit
    def test_preprocess_stage2_success(self, transition_manager, mock_job_service):
        """Test stage 2 preprocessing."""
        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            result = transition_manager._preprocess_stage2('test-job-1')

            assert result['success'] is True
            assert 'prep_dir' in result

    @pytest.mark.unit
    def test_preprocess_stage2_job_not_found(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test stage 2 preprocessing when job not found."""
        mock_job_service.get_job.return_value = None

        result = transition_manager._preprocess_stage2('test-job-1')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    @pytest.mark.unit
    def test_preprocess_stage3_validation_success(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test stage 3 validation preprocessing."""
        with patch('time.sleep'):
            result = transition_manager._preprocess_stage3_validation('test-job-1')

            assert result['success'] is True

    @pytest.mark.unit
    def test_preprocess_stage3_validation_job_not_found(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test stage 3 validation when job not found."""
        mock_job_service.get_job.return_value = None

        result = transition_manager._preprocess_stage3_validation('test-job-1')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    @pytest.mark.unit
    def test_preprocess_stage5_extendscript_success(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test stage 5 ExtendScript preprocessing."""
        with patch('time.sleep'):
            result = transition_manager._preprocess_stage5_extendscript('test-job-1')

            assert result['success'] is True
            assert 'prep_dir' in result

    @pytest.mark.unit
    def test_preprocess_stage5_extendscript_job_not_found(
        self,
        transition_manager,
        mock_job_service
    ):
        """Test stage 5 preprocessing when job not found."""
        mock_job_service.get_job.return_value = None

        result = transition_manager._preprocess_stage5_extendscript('test-job-1')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()


class TestStageTransitionManagerHelperMethods:
    """Test helper methods."""

    @pytest.mark.unit
    def test_get_preprocessing_status_active(self, transition_manager):
        """Test getting status of active preprocessing."""
        # Create a mock running thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        transition_manager.active_threads['test-job-1_stage2'] = mock_thread

        status = transition_manager.get_preprocessing_status('test-job-1', 2)

        assert status['job_id'] == 'test-job-1'
        assert status['stage'] == 2
        assert status['preprocessing_active'] is True
        assert status['status'] == 'processing'

    @pytest.mark.unit
    def test_get_preprocessing_status_completed(self, transition_manager):
        """Test getting status of completed preprocessing."""
        # Create a mock completed thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        transition_manager.active_threads['test-job-1_stage2'] = mock_thread

        status = transition_manager.get_preprocessing_status('test-job-1', 2)

        assert status['preprocessing_active'] is False
        assert status['status'] == 'completed'

    @pytest.mark.unit
    def test_get_preprocessing_status_not_started(self, transition_manager):
        """Test getting status when preprocessing not started."""
        status = transition_manager.get_preprocessing_status('test-job-1', 2)

        assert status['preprocessing_active'] is False
        assert status['status'] == 'not_started'

    @pytest.mark.unit
    def test_cleanup_completed_threads(self, transition_manager):
        """Test cleaning up completed threads."""
        # Create mock threads
        active_thread = Mock()
        active_thread.is_alive.return_value = True

        completed_thread1 = Mock()
        completed_thread1.is_alive.return_value = False

        completed_thread2 = Mock()
        completed_thread2.is_alive.return_value = False

        transition_manager.active_threads = {
            'job1_stage2': active_thread,
            'job2_stage3': completed_thread1,
            'job3_stage4': completed_thread2
        }

        transition_manager.cleanup_completed_threads()

        # Only active thread should remain
        assert 'job1_stage2' in transition_manager.active_threads
        assert 'job2_stage3' not in transition_manager.active_threads
        assert 'job3_stage4' not in transition_manager.active_threads
        assert len(transition_manager.active_threads) == 1

    @pytest.mark.unit
    def test_cleanup_completed_threads_no_completed(self, transition_manager):
        """Test cleanup when no threads are completed."""
        # Create mock active threads
        thread1 = Mock()
        thread1.is_alive.return_value = True

        thread2 = Mock()
        thread2.is_alive.return_value = True

        transition_manager.active_threads = {
            'job1_stage2': thread1,
            'job2_stage3': thread2
        }

        transition_manager.cleanup_completed_threads()

        # All threads should remain
        assert len(transition_manager.active_threads) == 2


class TestStageTransitionManagerStoreStageData:
    """Test _store_stage_data method."""

    @pytest.mark.unit
    def test_store_stage_data_stage2(self, transition_manager, mock_job_service):
        """Test storing stage 2 data."""
        data = {
            'matches': [
                {'psd_layer': 'Layer1', 'aepx_layer': 'Placeholder1'}
            ]
        }

        transition_manager._store_stage_data('test-job-1', 2, data)

        mock_job_service.store_approved_matches.assert_called_once_with(
            'test-job-1',
            data['matches']
        )

    @pytest.mark.unit
    def test_store_stage_data_stage3(self, transition_manager, mock_job_service):
        """Test storing stage 3 data (currently a no-op)."""
        data = {'some': 'data'}

        transition_manager._store_stage_data('test-job-1', 3, data)

        # Stage 3 doesn't store data currently, just verify no errors
        mock_job_service.store_approved_matches.assert_not_called()

    @pytest.mark.unit
    def test_store_stage_data_no_matches(self, transition_manager, mock_job_service):
        """Test storing stage 2 data with no matches."""
        data = {}

        transition_manager._store_stage_data('test-job-1', 2, data)

        mock_job_service.store_approved_matches.assert_called_once_with(
            'test-job-1',
            []
        )
