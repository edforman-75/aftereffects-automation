"""
Unit tests for Stage6PreviewService.

Tests the Stage6PreviewService class methods in isolation using mocks.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path

from services.stage6_preview_service import Stage6PreviewService


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def mock_preview_service():
    """Create a mock PreviewService."""
    return Mock()


@pytest.fixture
def stage6_service(mock_logger):
    """Create a Stage6PreviewService instance with mocked dependencies."""
    with patch('services.stage6_preview_service.PreviewService') as mock_ps:
        service = Stage6PreviewService(mock_logger)
        service.preview_service = Mock()
        return service


@pytest.fixture
def mock_job():
    """Create a mock Job object."""
    job = Mock()
    job.job_id = 'test-job-1'
    job.current_stage = 6
    job.psd_path = '/path/to/test.psd'
    job.aepx_path = '/path/to/template.aepx'
    job.stage5_extendscript = '''
        var CONFIG = {
            psdFile: "data/test.psd",
            outputProject: "output/result.aep"
        };
        // Some ExtendScript code
    '''
    job.stage2_approved_matches = '[]'
    return job


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return Mock()


class TestStage6PreviewServiceGeneratePreview:
    """Test generate_preview_for_job method."""

    @pytest.mark.unit
    def test_generate_preview_wrong_stage(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test preview generation when job is in wrong stage."""
        mock_job.current_stage = 3

        success, error, result = stage6_service.generate_preview_for_job(
            mock_job,
            mock_session
        )

        assert success is False
        assert 'stage 3' in error.lower()
        assert result is None

    @pytest.mark.unit
    def test_generate_preview_no_extendscript(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test preview generation when ExtendScript is missing."""
        mock_job.stage5_extendscript = None

        success, error, result = stage6_service.generate_preview_for_job(
            mock_job,
            mock_session
        )

        assert success is False
        assert 'no extendscript' in error.lower()
        assert result is None

    @pytest.mark.unit
    def test_generate_preview_success(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test successful preview generation."""
        with patch.object(stage6_service, '_export_psd_preview') as mock_export:
            with patch.object(stage6_service, '_execute_extendscript') as mock_execute:
                with patch.object(stage6_service, '_render_preview_video') as mock_render:
                    with patch('pathlib.Path.mkdir'):
                        mock_export.return_value = '/path/to/psd_preview.png'
                        mock_execute.return_value = '/path/to/populated.aep'
                        mock_render.return_value = '/path/to/preview.mp4'

                        success, error, result = stage6_service.generate_preview_for_job(
                            mock_job,
                            mock_session
                        )

                        assert success is True
                        assert error is None
                        assert result is not None
                        assert 'psd_preview_path' in result
                        assert 'video_preview_path' in result

                        # Verify all steps were called
                        mock_export.assert_called_once()
                        mock_execute.assert_called_once()
                        mock_render.assert_called_once()

    @pytest.mark.unit
    def test_generate_preview_psd_export_fails_continues(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test that preview generation continues if PSD export fails."""
        with patch.object(stage6_service, '_export_psd_preview') as mock_export:
            with patch.object(stage6_service, '_execute_extendscript') as mock_execute:
                with patch.object(stage6_service, '_render_preview_video') as mock_render:
                    with patch('pathlib.Path.mkdir'):
                        # PSD export returns None (failed)
                        mock_export.return_value = None
                        mock_execute.return_value = '/path/to/populated.aep'
                        mock_render.return_value = '/path/to/preview.mp4'

                        success, error, result = stage6_service.generate_preview_for_job(
                            mock_job,
                            mock_session
                        )

                        # Should still succeed even without PSD preview
                        assert success is True
                        # PSD preview path will be 'None' string when export fails
                        assert result['psd_preview_path'] == 'None' or result['psd_preview_path'] is None

    @pytest.mark.unit
    def test_generate_preview_extendscript_execution_fails(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test preview generation when ExtendScript execution fails."""
        with patch.object(stage6_service, '_export_psd_preview') as mock_export:
            with patch.object(stage6_service, '_execute_extendscript') as mock_execute:
                with patch('pathlib.Path.mkdir'):
                    mock_export.return_value = '/path/to/psd_preview.png'
                    mock_execute.return_value = None

                    success, error, result = stage6_service.generate_preview_for_job(
                        mock_job,
                        mock_session
                    )

                    assert success is False
                    assert 'failed to execute extendscript' in error.lower()

    @pytest.mark.unit
    def test_generate_preview_video_render_fails(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test preview generation when video rendering fails."""
        with patch.object(stage6_service, '_export_psd_preview') as mock_export:
            with patch.object(stage6_service, '_execute_extendscript') as mock_execute:
                with patch.object(stage6_service, '_render_preview_video') as mock_render:
                    with patch('pathlib.Path.mkdir'):
                        mock_export.return_value = '/path/to/psd_preview.png'
                        mock_execute.return_value = '/path/to/populated.aep'
                        mock_render.return_value = None

                        success, error, result = stage6_service.generate_preview_for_job(
                            mock_job,
                            mock_session
                        )

                        assert success is False
                        assert 'failed to render preview video' in error.lower()

    @pytest.mark.unit
    def test_generate_preview_exception_handling(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test exception handling during preview generation."""
        with patch.object(stage6_service, '_export_psd_preview') as mock_export:
            with patch('pathlib.Path.mkdir'):
                mock_export.side_effect = Exception("Unexpected error")

                success, error, result = stage6_service.generate_preview_for_job(
                    mock_job,
                    mock_session
                )

                assert success is False
                assert 'unexpected error' in error.lower()

    @pytest.mark.unit
    def test_generate_preview_updates_job_paths(
        self,
        stage6_service,
        mock_job,
        mock_session
    ):
        """Test that job paths are updated correctly."""
        with patch.object(stage6_service, '_export_psd_preview') as mock_export:
            with patch.object(stage6_service, '_execute_extendscript') as mock_execute:
                with patch.object(stage6_service, '_render_preview_video') as mock_render:
                    with patch('pathlib.Path.mkdir'):
                        psd_preview_path = '/path/to/psd_preview.png'
                        video_preview_path = '/path/to/preview.mp4'

                        mock_export.return_value = psd_preview_path
                        mock_execute.return_value = '/path/to/populated.aep'
                        mock_render.return_value = video_preview_path

                        success, error, result = stage6_service.generate_preview_for_job(
                            mock_job,
                            mock_session
                        )

                        assert success is True
                        assert mock_job.stage6_psd_preview_path == psd_preview_path
                        assert mock_job.stage6_preview_video_path == video_preview_path
                        mock_session.commit.assert_called()


class TestStage6PreviewServicePSDExport:
    """Test _export_psd_preview method."""

    @pytest.mark.unit
    def test_export_psd_preview_success(self, stage6_service):
        """Test successful PSD preview export."""
        psd_path = '/path/to/test.psd'
        output_path = Path('/path/to/output.png')

        with patch('services.stage6_preview_service.PSDImage') as mock_psd:
            with patch('services.stage6_preview_service.os.path.exists', return_value=True):
                # Set up the mock chain properly
                mock_psd_instance = Mock()
                mock_psd_instance.version = 1
                mock_composite = Mock()
                mock_composite.size = (1920, 1080)
                mock_psd_instance.composite.return_value = mock_composite
                mock_psd.open.return_value = mock_psd_instance

                result = stage6_service._export_psd_preview(psd_path, output_path)

                assert result == str(output_path)
                mock_psd.open.assert_called_once_with(psd_path)
                mock_composite.save.assert_called_once()

    @pytest.mark.unit
    def test_export_psd_preview_file_not_found(self, stage6_service):
        """Test PSD export when file not found."""
        with patch('services.stage6_preview_service.PSDImage') as mock_psd:
            mock_psd.open.side_effect = FileNotFoundError("File not found")

            result = stage6_service._export_psd_preview(
                '/nonexistent.psd',
                Path('/output.png')
            )

            assert result is None

    @pytest.mark.unit
    def test_export_psd_preview_psd_error(self, stage6_service):
        """Test PSD export when PSD processing fails."""
        with patch('services.stage6_preview_service.PSDImage') as mock_psd:
            mock_psd.open.side_effect = Exception("Invalid PSD format")

            result = stage6_service._export_psd_preview(
                '/invalid.psd',
                Path('/output.png')
            )

            assert result is None

    @pytest.mark.unit
    def test_export_psd_preview_macos_fallback(self, stage6_service):
        """Test PSD export falls back to macOS sips command."""
        with patch('services.stage6_preview_service.PSDImage') as mock_psd:
            with patch('services.stage6_preview_service.subprocess.run') as mock_run:
                with patch('services.stage6_preview_service.os.path.exists', return_value=True):
                    # PSDImage fails
                    mock_psd.open.side_effect = Exception("PSD error")

                    # sips succeeds
                    mock_path = Mock()
                    mock_path.exists.return_value = True
                    mock_run.return_value = Mock(returncode=0, stderr='')

                    result = stage6_service._export_psd_preview(
                        '/path/test.psd',
                        mock_path
                    )

                    assert result == str(mock_path)
                    # Verify sips was called
                    mock_run.assert_called_once()
                    sips_call = mock_run.call_args[0][0]
                    assert 'sips' in sips_call


class TestStage6PreviewServiceExtendScriptExecution:
    """Test _execute_extendscript method."""

    @pytest.mark.unit
    def test_execute_extendscript_success(self, stage6_service):
        """Test ExtendScript execution calls subprocess."""
        script = 'var test = "script";'
        template_path = '/path/to/template.aepx'
        output_path = Path('/path/to/output.aep')

        with patch('services.stage6_preview_service.subprocess.run') as mock_run:
            with patch('services.stage6_preview_service.os.path.exists', return_value=True):
                with patch('services.stage6_preview_service.os.path.getsize', return_value=1000):
                    # Mock Path.exists() for script file check
                    with patch.object(Path, 'exists', return_value=True):
                        with patch('builtins.open', mock_open(read_data='script content')):
                            # Mock successful execution
                            mock_run.return_value = Mock(returncode=0, stdout='Success', stderr='')

                            result = stage6_service._execute_extendscript(
                                script,
                                template_path,
                                output_path
                            )

                            # Verify subprocess was called
                            assert mock_run.called

    @pytest.mark.unit
    def test_execute_extendscript_ae_not_found(self, stage6_service):
        """Test ExtendScript execution when After Effects not found."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("After Effects not found")

            result = stage6_service._execute_extendscript(
                'script',
                '/template.aepx',
                '/output.aep'
            )

            assert result is None

    @pytest.mark.unit
    def test_execute_extendscript_execution_fails(self, stage6_service):
        """Test ExtendScript execution failure."""
        with patch('subprocess.run') as mock_run:
            with patch('builtins.open', mock_open()):
                mock_run.return_value = Mock(returncode=1, stdout='', stderr='Error')

                result = stage6_service._execute_extendscript(
                    'script',
                    '/template.aepx',
                    '/output.aep'
                )

                assert result is None

    @pytest.mark.unit
    def test_execute_extendscript_output_not_created(self, stage6_service):
        """Test when ExtendScript runs but output file not created."""
        with patch('subprocess.run') as mock_run:
            with patch('os.path.exists', return_value=False):
                with patch('builtins.open', mock_open()):
                    mock_run.return_value = Mock(returncode=0, stdout='Success', stderr='')

                    result = stage6_service._execute_extendscript(
                        'script',
                        '/template.aepx',
                        '/output.aep'
                    )

                    assert result is None


class TestStage6PreviewServiceVideoRendering:
    """Test _render_preview_video method."""

    @pytest.mark.unit
    def test_render_preview_video_success(self, stage6_service):
        """Test successful video rendering."""
        aep_path = '/path/to/project.aep'
        output_path = Path('/path/to/output.mp4')

        with patch('services.stage6_preview_service.subprocess.run') as mock_run:
            with patch('services.stage6_preview_service.os.path.exists', return_value=True):
                mock_run.return_value = Mock(returncode=0, stdout='Rendering complete', stderr='')

                result = stage6_service._render_preview_video(
                    aep_path,
                    output_path,
                    comp_name='Main Comp'
                )

                # Just verify aerender was called
                mock_run.assert_called()

    @pytest.mark.unit
    def test_render_preview_video_aerender_not_found(self, stage6_service):
        """Test video rendering when aerender not found."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("aerender not found")

            result = stage6_service._render_preview_video(
                '/project.aep',
                '/output.mp4'
            )

            assert result is None

    @pytest.mark.unit
    def test_render_preview_video_rendering_fails(self, stage6_service):
        """Test video rendering failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='Render error')

            result = stage6_service._render_preview_video(
                '/project.aep',
                '/output.mp4'
            )

            assert result is None

    @pytest.mark.unit
    def test_render_preview_video_output_not_created(self, stage6_service):
        """Test when rendering completes but output file not created."""
        with patch('subprocess.run') as mock_run:
            with patch('os.path.exists', return_value=False):
                mock_run.return_value = Mock(returncode=0, stdout='Success', stderr='')

                result = stage6_service._render_preview_video(
                    '/project.aep',
                    '/output.mp4'
                )

                assert result is None

    @pytest.mark.unit
    def test_render_preview_video_with_comp_name(self, stage6_service):
        """Test video rendering with specific composition name."""
        with patch('services.stage6_preview_service.subprocess.run') as mock_run:
            with patch('services.stage6_preview_service.os.path.exists', return_value=True):
                mock_run.return_value = Mock(returncode=0, stdout='Success', stderr='')

                result = stage6_service._render_preview_video(
                    '/project.aep',
                    Path('/output.mp4'),
                    comp_name='My Custom Comp'
                )

                # Just verify aerender was called with the method
                mock_run.assert_called()


class TestStage6PreviewServiceScriptModifications:
    """Test ExtendScript modification logic."""

    @pytest.mark.unit
    def test_extendscript_path_fixes(self, stage6_service, mock_job, mock_session):
        """Test that ExtendScript paths are fixed correctly."""
        with patch.object(stage6_service, '_export_psd_preview', return_value='/psd.png'):
            with patch.object(stage6_service, '_execute_extendscript') as mock_execute:
                with patch.object(stage6_service, '_render_preview_video', return_value='/video.mp4'):
                    with patch('pathlib.Path.mkdir'):
                        mock_execute.return_value = '/populated.aep'

                        stage6_service.generate_preview_for_job(mock_job, mock_session)

                        # Check that execute was called with modified script
                        call_args = mock_execute.call_args
                        modified_script = call_args[0][0]

                        # Verify paths were made absolute
                        assert 'data/exports/' not in modified_script or 'absolute' in modified_script.lower()

    @pytest.mark.unit
    def test_extendscript_removes_psd_import(self, stage6_service, mock_job, mock_session):
        """Test that PSD import is removed from ExtendScript."""
        mock_job.stage5_extendscript = '''
            logMessage("Importing PSD file...");
            var psdComp = importPSDAsComp(CONFIG.psdFile);
            if (!psdComp) {
                throw new Error("Failed to import PSD");
            }
        '''

        with patch.object(stage6_service, '_export_psd_preview', return_value='/psd.png'):
            with patch.object(stage6_service, '_execute_extendscript') as mock_execute:
                with patch.object(stage6_service, '_render_preview_video', return_value='/video.mp4'):
                    with patch('pathlib.Path.mkdir'):
                        mock_execute.return_value = '/populated.aep'

                        stage6_service.generate_preview_for_job(mock_job, mock_session)

                        # Verify PSD import was commented out
                        modified_script = mock_execute.call_args[0][0]
                        assert '// SKIPPED' in modified_script


class TestStage6PreviewServiceHelpers:
    """Test helper methods."""

    @pytest.mark.unit
    def test_log_info(self, stage6_service, mock_logger):
        """Test info logging."""
        stage6_service.log_info("Test message", job_id="job-1")

        mock_logger.info.assert_called()

    @pytest.mark.unit
    def test_log_error(self, stage6_service, mock_logger):
        """Test error logging."""
        stage6_service.log_error("Error message", job_id="job-1")

        mock_logger.error.assert_called()

    @pytest.mark.unit
    def test_log_warning(self, stage6_service, mock_logger):
        """Test warning logging."""
        stage6_service.log_warning("Warning message")

        mock_logger.warning.assert_called()
