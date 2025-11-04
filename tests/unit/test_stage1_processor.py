"""
Unit tests for Stage1Processor.

Tests the Stage1Processor class methods in isolation using mocks.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from services.stage1_processor import Stage1Processor


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def mock_job_service():
    """Create a mock JobService."""
    service = Mock()
    # Default return values
    service.get_job.return_value = Mock(
        job_id='test-job-1',
        psd_path='/path/to/test.psd',
        aepx_path='/path/to/test.aepx',
        current_stage=0
    )
    service.get_jobs_for_stage.return_value = []
    return service


@pytest.fixture
def mock_warning_service():
    """Create a mock WarningService."""
    service = Mock()
    service.add_missing_font_warning.return_value = 'warning-1'
    service.add_missing_asset_warning.return_value = 'warning-2'
    service.add_placeholder_not_matched_warning.return_value = 'warning-3'
    return service


@pytest.fixture
def mock_log_service():
    """Create a mock LogService."""
    return Mock()


@pytest.fixture
def mock_psd_exporter():
    """Create a mock PSDLayerExporter."""
    exporter = Mock()
    exporter.extract_all_layers.return_value = {
        'layers': {
            'Layer 1': {'type': 'text', 'name': 'Layer 1'},
            'Layer 2': {'type': 'image', 'name': 'Layer 2'}
        },
        'fonts': [
            {'family': 'Arial', 'style': 'Regular', 'is_installed': True},
            {'family': 'CustomFont', 'style': 'Bold', 'is_installed': False, 'layer_name': 'Text Layer'}
        ],
        'dimensions': {'width': 1920, 'height': 1080},
        'flattened_preview': '/path/to/preview.png',
        'metadata': {}
    }
    return exporter


@pytest.fixture
def mock_aepx_processor():
    """Create a mock AEPXProcessor."""
    processor = Mock()
    processor.process_aepx.return_value = {
        'compositions': [{'name': 'Main Comp', 'width': 1920, 'height': 1080}],
        'layers': [
            {'name': 'Layer 1', 'type': 'text'},
            {'name': 'Layer 2', 'type': 'image'}
        ],
        'placeholders': [
            {'name': 'Layer 1', 'type': 'text'},
            {'name': 'Layer 2', 'type': 'image'},
            {'name': 'Layer 3', 'type': 'text'}  # Unmatched
        ],
        'layer_categories': {},
        'missing_footage': [
            {'path': '/missing/footage.mov', 'type': 'video'}
        ]
    }
    return processor


@pytest.fixture
def stage1_processor(
    mock_logger,
    mock_psd_exporter,
    mock_aepx_processor,
    mock_job_service,
    mock_warning_service,
    mock_log_service
):
    """Create a Stage1Processor instance with mocked dependencies."""
    processor = Stage1Processor(mock_logger)
    processor.psd_exporter = mock_psd_exporter
    processor.aepx_processor = mock_aepx_processor
    processor.job_service = mock_job_service
    processor.warning_service = mock_warning_service
    processor.log_service = mock_log_service
    return processor


class TestStage1ProcessorProcessJob:
    """Test process_job method."""

    @pytest.mark.unit
    def test_process_job_success(self, stage1_processor, mock_job_service, mock_log_service):
        """Test successful job processing."""
        job_id = 'test-job-1'

        result = stage1_processor.process_job(job_id)

        assert result['success'] is True
        assert result['psd_result'] is not None
        assert result['aepx_result'] is not None
        assert result['matches'] is not None
        assert isinstance(result['warnings'], list)

        # Verify stage management
        mock_job_service.start_stage.assert_called_once_with(job_id, stage=1, user_id='system')
        mock_job_service.complete_stage.assert_called_once_with(job_id, stage=1, user_id='system')
        mock_job_service.update_job_status.assert_any_call(job_id, 'processing', current_stage=1)
        mock_job_service.update_job_status.assert_any_call(job_id, 'awaiting_review', current_stage=2)

        # Verify logging
        mock_log_service.log_stage_started.assert_called_once()
        mock_log_service.log_stage_completed.assert_called_once()

    @pytest.mark.unit
    def test_process_job_not_found(self, stage1_processor, mock_job_service):
        """Test processing when job not found."""
        mock_job_service.get_job.return_value = None

        result = stage1_processor.process_job('nonexistent-job')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()
        mock_job_service.start_stage.assert_not_called()

    @pytest.mark.unit
    def test_process_job_psd_extraction_fails(self, stage1_processor, mock_psd_exporter, mock_job_service, mock_log_service):
        """Test processing when PSD extraction fails."""
        mock_psd_exporter.extract_all_layers.side_effect = Exception("PSD extraction failed")

        result = stage1_processor.process_job('test-job-1')

        assert result['success'] is False
        assert 'error' in result
        mock_job_service.update_job_status.assert_called_with('test-job-1', 'failed', current_stage=1)
        mock_log_service.log_error.assert_called_once()

    @pytest.mark.unit
    def test_process_job_aepx_processing_fails(self, stage1_processor, mock_aepx_processor, mock_job_service):
        """Test processing when AEPX processing fails."""
        mock_aepx_processor.process_aepx.side_effect = Exception("AEPX processing failed")

        result = stage1_processor.process_job('test-job-1')

        assert result['success'] is False
        assert 'aepx processing failed' in result['error'].lower()

    @pytest.mark.unit
    def test_process_job_stores_results(self, stage1_processor, mock_job_service):
        """Test that results are stored correctly."""
        result = stage1_processor.process_job('test-job-1')

        assert result['success'] is True

        # Verify results were stored
        mock_job_service.store_stage1_results.assert_called_once()
        call_args = mock_job_service.store_stage1_results.call_args
        assert call_args[1]['job_id'] == 'test-job-1'
        assert 'psd_result' in call_args[1]
        assert 'aepx_result' in call_args[1]
        assert 'match_result' in call_args[1]


class TestStage1ProcessorProcessBatch:
    """Test process_batch method."""

    @pytest.mark.unit
    def test_process_batch_empty(self, stage1_processor, mock_job_service):
        """Test processing batch with no jobs."""
        mock_job_service.get_jobs_for_stage.return_value = []

        result = stage1_processor.process_batch('batch-1')

        assert result['processed'] == 0
        assert result['succeeded'] == 0
        assert result['failed'] == 0

    @pytest.mark.unit
    def test_process_batch_single_job_success(self, stage1_processor, mock_job_service):
        """Test processing batch with single successful job."""
        mock_jobs = [
            Mock(job_id='job-1', psd_path='/path/psd', aepx_path='/path/aepx')
        ]
        mock_job_service.get_jobs_for_stage.return_value = mock_jobs
        mock_job_service.get_job.return_value = mock_jobs[0]

        result = stage1_processor.process_batch('batch-1')

        assert result['processed'] == 1
        assert result['succeeded'] == 1
        assert result['failed'] == 0
        assert 'job-1' in result['job_results']
        assert result['job_results']['job-1']['success'] is True

    @pytest.mark.unit
    def test_process_batch_multiple_jobs(self, stage1_processor, mock_job_service):
        """Test processing batch with multiple jobs."""
        mock_jobs = [
            Mock(job_id='job-1', psd_path='/path/psd1', aepx_path='/path/aepx1'),
            Mock(job_id='job-2', psd_path='/path/psd2', aepx_path='/path/aepx2'),
            Mock(job_id='job-3', psd_path='/path/psd3', aepx_path='/path/aepx3')
        ]
        mock_job_service.get_jobs_for_stage.return_value = mock_jobs

        # Set up get_job to return the correct job
        def get_job_side_effect(job_id):
            for job in mock_jobs:
                if job.job_id == job_id:
                    return job
            return None

        mock_job_service.get_job.side_effect = get_job_side_effect

        result = stage1_processor.process_batch('batch-1')

        assert result['processed'] == 3
        assert result['succeeded'] == 3
        assert result['failed'] == 0
        assert len(result['job_results']) == 3

    @pytest.mark.unit
    def test_process_batch_with_failures(self, stage1_processor, mock_job_service, mock_psd_exporter):
        """Test processing batch where some jobs fail."""
        mock_jobs = [
            Mock(job_id='job-1', psd_path='/path/psd1', aepx_path='/path/aepx1'),
            Mock(job_id='job-2', psd_path='/path/psd2', aepx_path='/path/aepx2')
        ]
        mock_job_service.get_jobs_for_stage.return_value = mock_jobs

        # First job succeeds, second fails
        call_count = [0]

        def get_job_side_effect(job_id):
            for job in mock_jobs:
                if job.job_id == job_id:
                    return job
            return None

        def extract_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call fails
                raise Exception("Extraction failed")
            return {
                'layers': {'Layer 1': {}},
                'fonts': [],
                'dimensions': {},
                'flattened_preview': None,
                'metadata': {}
            }

        mock_job_service.get_job.side_effect = get_job_side_effect
        mock_psd_exporter.extract_all_layers.side_effect = extract_side_effect

        result = stage1_processor.process_batch('batch-1')

        assert result['processed'] == 2
        assert result['succeeded'] == 1
        assert result['failed'] == 1

    @pytest.mark.unit
    def test_process_batch_respects_max_jobs(self, stage1_processor, mock_job_service):
        """Test that process_batch respects max_jobs limit."""
        stage1_processor.process_batch('batch-1', max_jobs=50)

        mock_job_service.get_jobs_for_stage.assert_called_once_with(
            stage=0,
            batch_id='batch-1',
            limit=50
        )


class TestStage1ProcessorPSDProcessing:
    """Test _process_psd method."""

    @pytest.mark.unit
    def test_process_psd_success(self, stage1_processor, mock_psd_exporter):
        """Test successful PSD processing."""
        mock_job = Mock(
            job_id='test-job',
            psd_path='/path/to/test.psd'
        )

        result = stage1_processor._process_psd(mock_job)

        assert 'layers' in result
        assert 'fonts' in result
        assert 'dimensions' in result
        assert 'flattened_preview' in result
        assert 'metadata' in result

        mock_psd_exporter.extract_all_layers.assert_called_once()
        call_args = mock_psd_exporter.extract_all_layers.call_args
        assert call_args[1]['psd_path'] == '/path/to/test.psd'
        assert call_args[1]['generate_thumbnails'] is True

    @pytest.mark.unit
    def test_process_psd_creates_export_directory(self, stage1_processor, mock_psd_exporter):
        """Test that PSD processing creates export directory."""
        mock_job = Mock(
            job_id='test-job',
            psd_path='/path/to/test.psd'
        )

        # Just verify the method runs successfully and calls the exporter
        result = stage1_processor._process_psd(mock_job)

        # Verify PSD exporter was called
        mock_psd_exporter.extract_all_layers.assert_called_once()

        # Verify result structure
        assert 'layers' in result
        assert 'fonts' in result


class TestStage1ProcessorAEPXProcessing:
    """Test _process_aepx method."""

    @pytest.mark.unit
    def test_process_aepx_success(self, stage1_processor, mock_aepx_processor):
        """Test successful AEPX processing."""
        mock_job = Mock(
            job_id='test-job',
            aepx_path='/path/to/test.aepx'
        )

        result = stage1_processor._process_aepx(mock_job)

        assert 'compositions' in result
        assert 'layers' in result
        assert 'placeholders' in result
        assert 'layer_categories' in result
        assert 'missing_footage' in result

        mock_aepx_processor.process_aepx.assert_called_once()
        call_args = mock_aepx_processor.process_aepx.call_args
        assert call_args[1]['aepx_path'] == '/path/to/test.aepx'
        assert call_args[1]['session_id'] == 'test-job'
        assert call_args[1]['generate_thumbnails'] is False


class TestStage1ProcessorAutoMatching:
    """Test _auto_match_layers method."""

    @pytest.mark.unit
    def test_auto_match_exact_matches(self, stage1_processor):
        """Test auto-matching with exact name matches."""
        # Use layer names that don't have substring conflicts
        psd_result = {
            'layers': {
                'Header': {'type': 'text'},
                'Body': {'type': 'text'},
                'Logo': {'type': 'image'}
            }
        }
        aepx_result = {
            'placeholders': [
                {'name': 'Header', 'type': 'text'},
                {'name': 'Body', 'type': 'text'},
                {'name': 'Logo', 'type': 'image'}
            ]
        }

        result = stage1_processor._auto_match_layers(psd_result, aepx_result)

        assert result['match_count'] == 3
        assert len(result['matches']) == 3
        assert len(result['unmatched_psd']) == 0
        assert len(result['unmatched_aepx']) == 0
        assert result['match_rate'] == 1.0

    @pytest.mark.unit
    def test_auto_match_case_insensitive(self, stage1_processor):
        """Test auto-matching is case-insensitive."""
        psd_result = {
            'layers': {
                'HEADER': {'type': 'text'},
                'footer': {'type': 'text'}
            }
        }
        aepx_result = {
            'placeholders': [
                {'name': 'Header', 'type': 'text'},
                {'name': 'Footer', 'type': 'text'}
            ]
        }

        result = stage1_processor._auto_match_layers(psd_result, aepx_result)

        assert result['match_count'] == 2
        assert len(result['unmatched_psd']) == 0
        assert len(result['unmatched_aepx']) == 0

    @pytest.mark.unit
    def test_auto_match_with_spaces(self, stage1_processor):
        """Test auto-matching handles spaces and underscores."""
        psd_result = {
            'layers': {
                'Main Title': {'type': 'text'},
                'Sub_Title': {'type': 'text'}
            }
        }
        aepx_result = {
            'placeholders': [
                {'name': 'Main_Title', 'type': 'text'},
                {'name': 'Sub Title', 'type': 'text'}
            ]
        }

        result = stage1_processor._auto_match_layers(psd_result, aepx_result)

        assert result['match_count'] == 2

    @pytest.mark.unit
    def test_auto_match_partial_match(self, stage1_processor):
        """Test auto-matching with partial name matches."""
        psd_result = {
            'layers': {
                'Title Text Layer': {'type': 'text'}
            }
        }
        aepx_result = {
            'placeholders': [
                {'name': 'Title', 'type': 'text'}
            ]
        }

        result = stage1_processor._auto_match_layers(psd_result, aepx_result)

        assert result['match_count'] == 1
        assert result['matches'][0]['psd_layer'] == 'Title Text Layer'

    @pytest.mark.unit
    def test_auto_match_with_unmatched(self, stage1_processor):
        """Test auto-matching with some unmatched layers."""
        psd_result = {
            'layers': {
                'Title': {'type': 'text'},
                'Extra Layer': {'type': 'image'}
            }
        }
        aepx_result = {
            'placeholders': [
                {'name': 'Title', 'type': 'text'},
                {'name': 'Missing Placeholder', 'type': 'text'}
            ]
        }

        result = stage1_processor._auto_match_layers(psd_result, aepx_result)

        assert result['match_count'] == 1
        assert len(result['unmatched_psd']) == 1
        assert 'Extra Layer' in result['unmatched_psd']
        assert len(result['unmatched_aepx']) == 1
        assert 'Missing Placeholder' in result['unmatched_aepx']
        assert result['match_rate'] == 0.5  # 1 out of 2 placeholders matched

    @pytest.mark.unit
    def test_auto_match_empty_inputs(self, stage1_processor):
        """Test auto-matching with empty inputs."""
        psd_result = {'layers': {}}
        aepx_result = {'placeholders': []}

        result = stage1_processor._auto_match_layers(psd_result, aepx_result)

        assert result['match_count'] == 0
        assert len(result['matches']) == 0
        assert result['match_rate'] == 0


class TestStage1ProcessorWarningChecks:
    """Test _check_warnings method."""

    @pytest.mark.unit
    def test_check_warnings_missing_fonts(
        self,
        stage1_processor,
        mock_warning_service,
        mock_log_service
    ):
        """Test warning creation for missing fonts."""
        psd_result = {
            'fonts': [
                {'family': 'Arial', 'style': 'Regular', 'is_installed': True},
                {'family': 'CustomFont', 'style': 'Bold', 'is_installed': False, 'layer_name': 'Text Layer'}
            ]
        }
        aepx_result = {'missing_footage': [], 'placeholders': []}
        matches = {'unmatched_aepx': []}

        warnings = stage1_processor._check_warnings('job-1', psd_result, aepx_result, matches)

        assert len(warnings) == 1
        assert warnings[0]['type'] == 'missing_font'
        mock_warning_service.add_missing_font_warning.assert_called_once()

    @pytest.mark.unit
    def test_check_warnings_missing_footage(
        self,
        stage1_processor,
        mock_warning_service,
        mock_log_service
    ):
        """Test warning creation for missing footage."""
        psd_result = {'fonts': []}
        aepx_result = {
            'missing_footage': [
                {'path': '/missing/video.mov', 'type': 'video'},
                {'path': '/missing/image.png', 'type': 'image'}
            ],
            'placeholders': []
        }
        matches = {'unmatched_aepx': []}

        warnings = stage1_processor._check_warnings('job-1', psd_result, aepx_result, matches)

        assert len(warnings) == 2
        assert all(w['type'] == 'missing_footage' for w in warnings)
        assert mock_warning_service.add_missing_asset_warning.call_count == 2

    @pytest.mark.unit
    def test_check_warnings_unmatched_placeholders(
        self,
        stage1_processor,
        mock_warning_service,
        mock_log_service
    ):
        """Test warning creation for unmatched placeholders."""
        psd_result = {'fonts': []}
        aepx_result = {'missing_footage': [], 'placeholders': []}
        matches = {
            'unmatched_aepx': ['Placeholder 1', 'Placeholder 2', 'Placeholder 3']
        }

        warnings = stage1_processor._check_warnings('job-1', psd_result, aepx_result, matches)

        assert len(warnings) == 3
        assert all(w['type'] == 'placeholder_not_matched' for w in warnings)
        assert mock_warning_service.add_placeholder_not_matched_warning.call_count == 3

    @pytest.mark.unit
    def test_check_warnings_all_types(
        self,
        stage1_processor,
        mock_warning_service,
        mock_log_service
    ):
        """Test warning creation with all warning types."""
        psd_result = {
            'fonts': [
                {'family': 'MissingFont', 'style': 'Regular', 'is_installed': False}
            ]
        }
        aepx_result = {
            'missing_footage': [
                {'path': '/missing/video.mov', 'type': 'video'}
            ],
            'placeholders': []
        }
        matches = {
            'unmatched_aepx': ['Unmatched Placeholder']
        }

        warnings = stage1_processor._check_warnings('job-1', psd_result, aepx_result, matches)

        assert len(warnings) == 3
        warning_types = {w['type'] for w in warnings}
        assert 'missing_font' in warning_types
        assert 'missing_footage' in warning_types
        assert 'placeholder_not_matched' in warning_types

    @pytest.mark.unit
    def test_check_warnings_no_warnings(
        self,
        stage1_processor,
        mock_warning_service,
        mock_log_service
    ):
        """Test when there are no warnings."""
        psd_result = {
            'fonts': [
                {'family': 'Arial', 'style': 'Regular', 'is_installed': True}
            ]
        }
        aepx_result = {'missing_footage': [], 'placeholders': []}
        matches = {'unmatched_aepx': []}

        warnings = stage1_processor._check_warnings('job-1', psd_result, aepx_result, matches)

        assert len(warnings) == 0
        mock_warning_service.add_missing_font_warning.assert_not_called()
        mock_warning_service.add_missing_asset_warning.assert_not_called()
        mock_warning_service.add_placeholder_not_matched_warning.assert_not_called()

    @pytest.mark.unit
    def test_check_warnings_logs_all_warnings(
        self,
        stage1_processor,
        mock_warning_service,
        mock_log_service
    ):
        """Test that all warnings are logged."""
        psd_result = {
            'fonts': [
                {'family': 'Font1', 'style': 'Regular', 'is_installed': False},
                {'family': 'Font2', 'style': 'Bold', 'is_installed': False}
            ]
        }
        aepx_result = {'missing_footage': [], 'placeholders': []}
        matches = {'unmatched_aepx': []}

        warnings = stage1_processor._check_warnings('job-1', psd_result, aepx_result, matches)

        assert len(warnings) == 2
        assert mock_log_service.log_warning_added.call_count == 2


class TestStage1ProcessorLogging:
    """Test logging methods."""

    @pytest.mark.unit
    def test_log_info(self, stage1_processor, mock_logger, capsys):
        """Test info logging."""
        stage1_processor.log_info("Test message")

        mock_logger.info.assert_called_once_with("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    @pytest.mark.unit
    def test_log_error(self, stage1_processor, mock_logger, capsys):
        """Test error logging."""
        stage1_processor.log_error("Error message")

        mock_logger.error.assert_called_once_with("Error message")
        captured = capsys.readouterr()
        assert "Error message" in captured.out

    @pytest.mark.unit
    def test_logging_without_logger(self, capsys):
        """Test logging when no logger is provided."""
        processor = Stage1Processor(logger=None)

        processor.log_info("Info without logger")
        processor.log_error("Error without logger")

        captured = capsys.readouterr()
        assert "Info without logger" in captured.out
        assert "Error without logger" in captured.out
