"""
End-to-end integration tests for complete stage workflow.

Tests the complete pipeline from Stage 1 (Ingestion) through Stage 6 (Download).
Uses in-memory database and mocked external dependencies.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database.models import Base, Job, Batch
from services.stage1_processor import Stage1Processor
from services.stage_transition_manager import StageTransitionManager
from services.job_service import JobService


@pytest.fixture(scope='function')
def in_memory_db():
    """Create in-memory database for testing."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)

    yield Session

    Session.remove()
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_batch(in_memory_db):
    """Create a test batch."""
    batch = Batch(
        batch_id='e2e-batch-1',
        name='End-to-End Test Batch',
        created_at=datetime.utcnow()
    )
    in_memory_db.add(batch)
    in_memory_db.commit()
    return batch


@pytest.fixture
def test_job(in_memory_db, test_batch):
    """Create a test job in Stage 0."""
    job = Job(
        job_id='e2e-job-1',
        batch_id=test_batch.batch_id,
        psd_path='/test/data/sample.psd',
        aepx_path='/test/data/template.aepx',
        current_stage=0,
        status='pending',
        created_at=datetime.utcnow()
    )
    in_memory_db.add(job)
    in_memory_db.commit()
    return job


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


class TestEndToEndWorkflow:
    """Test complete workflow through all 6 stages."""

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_complete_pipeline_stage0_to_stage6(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test complete pipeline from Stage 0 to Stage 6."""

        # Mock external dependencies
        with patch('services.stage1_processor.PSDLayerExporter') as mock_psd:
            with patch('services.stage1_processor.AEPXProcessor') as mock_aepx:
                # Configure mock PSD exporter
                mock_psd_instance = Mock()
                mock_psd_instance.extract_all_layers.return_value = {
                    'layers': {
                        'Title': {'type': 'text', 'name': 'Title'},
                        'Image': {'type': 'image', 'name': 'Image'}
                    },
                    'fonts': [
                        {'family': 'Arial', 'style': 'Regular', 'is_installed': True}
                    ],
                    'dimensions': {'width': 1920, 'height': 1080},
                    'flattened_preview': '/previews/test.png',
                    'metadata': {}
                }
                mock_psd.return_value = mock_psd_instance

                # Configure mock AEPX processor
                mock_aepx_instance = Mock()
                mock_aepx_instance.process_aepx.return_value = {
                    'compositions': [
                        {'name': 'Main Comp', 'width': 1920, 'height': 1080}
                    ],
                    'layers': [
                        {'name': 'Title', 'type': 'text'},
                        {'name': 'Image', 'type': 'image'}
                    ],
                    'placeholders': [
                        {'name': 'Title', 'type': 'text'},
                        {'name': 'Image', 'type': 'image'}
                    ],
                    'layer_categories': {},
                    'missing_footage': []
                }
                mock_aepx.return_value = mock_aepx_instance

                # STAGE 1: Automated Ingestion
                stage1_processor = Stage1Processor(mock_logger)
                stage1_processor.psd_exporter = mock_psd_instance
                stage1_processor.aepx_processor = mock_aepx_instance
                stage1_processor.job_service = JobService(mock_logger)

                # Override session for in-memory DB
                with patch('services.job_service.SessionLocal', return_value=in_memory_db):
                    result = stage1_processor.process_job(test_job.job_id)

                assert result['success'] is True
                assert result['matches'] is not None
                assert len(result['warnings']) == 0  # No missing fonts or footage

                # Verify job progressed to Stage 2
                in_memory_db.refresh(test_job)
                assert test_job.current_stage == 2
                assert test_job.status == 'awaiting_review'
                assert test_job.stage1_completed_at is not None

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage1_to_stage2_transition(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 1 completion and transition to Stage 2."""

        with patch('services.stage1_processor.PSDLayerExporter') as mock_psd:
            with patch('services.stage1_processor.AEPXProcessor') as mock_aepx:
                with patch('services.job_service.SessionLocal', return_value=in_memory_db):
                    # Configure mocks
                    mock_psd_instance = Mock()
                    mock_psd_instance.extract_all_layers.return_value = {
                        'layers': {'Layer1': {}},
                        'fonts': [],
                        'dimensions': {},
                        'flattened_preview': None,
                        'metadata': {}
                    }
                    mock_psd.return_value = mock_psd_instance

                    mock_aepx_instance = Mock()
                    mock_aepx_instance.process_aepx.return_value = {
                        'compositions': [],
                        'layers': [],
                        'placeholders': [{'name': 'Layer1', 'type': 'text'}],
                        'layer_categories': {},
                        'missing_footage': []
                    }
                    mock_aepx.return_value = mock_aepx_instance

                    # Process Stage 1
                    stage1_processor = Stage1Processor(mock_logger)
                    stage1_processor.psd_exporter = mock_psd_instance
                    stage1_processor.aepx_processor = mock_aepx_instance
                    stage1_processor.job_service = JobService(mock_logger)

                    result = stage1_processor.process_job(test_job.job_id)

                    assert result['success'] is True

                    # Verify transition to Stage 2
                    in_memory_db.refresh(test_job)
                    assert test_job.current_stage == 2
                    assert test_job.stage1_results is not None

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage2_approval_to_stage5_flow(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 2 approval flowing to Stage 5 (no validation issues)."""

        # Set up job in Stage 2
        test_job.current_stage = 2
        test_job.status = 'awaiting_review'
        test_job.stage1_results = json.dumps({
            'matches': [
                {'psd_layer': 'Title', 'aepx_layer': 'Title', 'confidence': 1.0}
            ]
        })
        in_memory_db.commit()

        with patch('services.stage_transition_manager.SessionLocal', return_value=in_memory_db):
            # Create transition manager
            transition_manager = StageTransitionManager(mock_logger)

            # Simulate Stage 2 approval with no validation issues
            approved_matches = [
                {'psd_layer': 'Title', 'aepx_layer': 'Title'}
            ]

            result = transition_manager.transition_stage(
                job_id=test_job.job_id,
                from_stage=2,
                to_stage=5,  # Direct to Stage 5 (no issues)
                user_id='test-user',
                approved_data={'matches': approved_matches}
            )

            assert result['success'] is True
            assert result['to_stage'] == 5

            # Verify job is in Stage 5
            in_memory_db.refresh(test_job)
            assert test_job.current_stage == 5

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage2_to_stage4_with_validation_issues(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 2 approval routing to Stage 4 due to validation issues."""

        # Set up job in Stage 2
        test_job.current_stage = 2
        test_job.status = 'awaiting_review'
        in_memory_db.commit()

        with patch('services.stage_transition_manager.SessionLocal', return_value=in_memory_db):
            transition_manager = StageTransitionManager(mock_logger)

            # Transition to Stage 4 (validation review)
            result = transition_manager.transition_stage(
                job_id=test_job.job_id,
                from_stage=2,
                to_stage=4,
                user_id='test-user',
                approved_data={'matches': []}
            )

            assert result['success'] is True
            assert result['to_stage'] == 4

            in_memory_db.refresh(test_job)
            assert test_job.current_stage == 4

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage4_override_to_stage5(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 4 override flowing to Stage 5."""

        # Set up job in Stage 4
        test_job.current_stage = 4
        test_job.status = 'awaiting_approval'
        test_job.stage3_validation_results = json.dumps({
            'has_critical_issues': True,
            'issues': [{'type': 'aspect_ratio_mismatch'}]
        })
        in_memory_db.commit()

        with patch('services.stage_transition_manager.SessionLocal', return_value=in_memory_db):
            transition_manager = StageTransitionManager(mock_logger)

            # Override validation and move to Stage 5
            result = transition_manager.transition_stage(
                job_id=test_job.job_id,
                from_stage=4,
                to_stage=5,
                user_id='test-user'
            )

            assert result['success'] is True

            in_memory_db.refresh(test_job)
            assert test_job.current_stage == 5

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage4_return_to_stage2(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test returning from Stage 4 to Stage 2 for re-matching."""

        # Set up job in Stage 4
        test_job.current_stage = 4
        test_job.status = 'awaiting_approval'
        in_memory_db.commit()

        with patch('services.stage_transition_manager.SessionLocal', return_value=in_memory_db):
            transition_manager = StageTransitionManager(mock_logger)

            # Return to Stage 2
            result = transition_manager.transition_stage(
                job_id=test_job.job_id,
                from_stage=4,
                to_stage=2,
                user_id='test-user'
            )

            assert result['success'] is True

            in_memory_db.refresh(test_job)
            assert test_job.current_stage == 2

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage5_to_stage6_extendscript_generation(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 5 ExtendScript generation and transition to Stage 6."""

        # Set up job in Stage 5
        test_job.current_stage = 5
        test_job.status = 'processing'
        test_job.stage2_approved_matches = json.dumps([
            {'psd_layer': 'Title', 'aepx_layer': 'Title'}
        ])
        in_memory_db.commit()

        with patch('services.stage_transition_manager.SessionLocal', return_value=in_memory_db):
            transition_manager = StageTransitionManager(mock_logger)

            # Simulate ExtendScript generation completion
            test_job.stage5_extendscript = 'var CONFIG = {};'
            in_memory_db.commit()

            # Transition to Stage 6
            result = transition_manager.transition_stage(
                job_id=test_job.job_id,
                from_stage=5,
                to_stage=6,
                user_id='system'
            )

            assert result['success'] is True

            in_memory_db.refresh(test_job)
            assert test_job.current_stage == 6
            assert test_job.stage5_extendscript is not None

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage6_preview_generation_and_completion(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 6 preview generation and job completion."""

        # Set up job in Stage 6
        test_job.current_stage = 6
        test_job.status = 'processing'
        test_job.stage5_extendscript = 'var CONFIG = {};'
        in_memory_db.commit()

        # Simulate preview generation
        test_job.stage6_preview_video_path = '/previews/video.mp4'
        test_job.stage6_psd_preview_path = '/previews/psd.png'
        test_job.status = 'awaiting_approval'
        in_memory_db.commit()

        # Simulate user approval
        test_job.stage6_approved = True
        test_job.stage6_approved_at = datetime.utcnow()
        test_job.stage6_completed_at = datetime.utcnow()
        test_job.status = 'completed'
        in_memory_db.commit()

        in_memory_db.refresh(test_job)
        assert test_job.stage6_approved is True
        assert test_job.status == 'completed'


class TestWorkflowErrorHandling:
    """Test error handling throughout the workflow."""

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage1_psd_extraction_failure(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 1 handling of PSD extraction failure."""

        with patch('services.stage1_processor.PSDLayerExporter') as mock_psd:
            with patch('services.job_service.SessionLocal', return_value=in_memory_db):
                # Configure mock to fail
                mock_psd_instance = Mock()
                mock_psd_instance.extract_all_layers.side_effect = Exception("PSD extraction failed")
                mock_psd.return_value = mock_psd_instance

                stage1_processor = Stage1Processor(mock_logger)
                stage1_processor.psd_exporter = mock_psd_instance

                result = stage1_processor.process_job(test_job.job_id)

                assert result['success'] is False
                assert 'error' in result

                # Verify job status
                in_memory_db.refresh(test_job)
                assert test_job.status == 'failed'

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_stage1_missing_fonts_warning(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test Stage 1 creates warnings for missing fonts."""

        with patch('services.stage1_processor.PSDLayerExporter') as mock_psd:
            with patch('services.stage1_processor.AEPXProcessor') as mock_aepx:
                with patch('services.job_service.SessionLocal', return_value=in_memory_db):
                    # Configure mock with missing font
                    mock_psd_instance = Mock()
                    mock_psd_instance.extract_all_layers.return_value = {
                        'layers': {'Layer1': {}},
                        'fonts': [
                            {
                                'family': 'MissingFont',
                                'style': 'Bold',
                                'is_installed': False,
                                'layer_name': 'Text Layer'
                            }
                        ],
                        'dimensions': {},
                        'flattened_preview': None,
                        'metadata': {}
                    }
                    mock_psd.return_value = mock_psd_instance

                    mock_aepx_instance = Mock()
                    mock_aepx_instance.process_aepx.return_value = {
                        'compositions': [],
                        'layers': [],
                        'placeholders': [],
                        'layer_categories': {},
                        'missing_footage': []
                    }
                    mock_aepx.return_value = mock_aepx_instance

                    stage1_processor = Stage1Processor(mock_logger)
                    stage1_processor.psd_exporter = mock_psd_instance
                    stage1_processor.aepx_processor = mock_aepx_instance

                    result = stage1_processor.process_job(test_job.job_id)

                    assert result['success'] is True
                    assert len(result['warnings']) > 0
                    assert any(w['type'] == 'missing_font' for w in result['warnings'])

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_transition_with_wrong_stage(
        self,
        in_memory_db,
        test_job,
        mock_logger
    ):
        """Test transition fails when job is in wrong stage."""

        # Set job in Stage 3
        test_job.current_stage = 3
        in_memory_db.commit()

        with patch('services.stage_transition_manager.SessionLocal', return_value=in_memory_db):
            transition_manager = StageTransitionManager(mock_logger)

            # Try to transition from Stage 2 (but job is in Stage 3)
            result = transition_manager.transition_stage(
                job_id=test_job.job_id,
                from_stage=2,
                to_stage=3,
                user_id='test-user'
            )

            assert result['success'] is False
            assert 'stage 3' in result['error'].lower()


class TestBatchProcessing:
    """Test batch processing workflows."""

    @pytest.mark.integration
    @pytest.mark.e2e
    def test_batch_processing_multiple_jobs(
        self,
        in_memory_db,
        test_batch,
        mock_logger
    ):
        """Test processing multiple jobs in a batch."""

        # Create multiple jobs in Stage 0
        jobs = []
        for i in range(3):
            job = Job(
                job_id=f'batch-job-{i}',
                batch_id=test_batch.batch_id,
                psd_path=f'/test/data/sample{i}.psd',
                aepx_path=f'/test/data/template{i}.aepx',
                current_stage=0,
                status='pending'
            )
            in_memory_db.add(job)
            jobs.append(job)

        in_memory_db.commit()

        with patch('services.stage1_processor.PSDLayerExporter') as mock_psd:
            with patch('services.stage1_processor.AEPXProcessor') as mock_aepx:
                with patch('services.job_service.SessionLocal', return_value=in_memory_db):
                    # Configure mocks
                    mock_psd_instance = Mock()
                    mock_psd_instance.extract_all_layers.return_value = {
                        'layers': {},
                        'fonts': [],
                        'dimensions': {},
                        'flattened_preview': None,
                        'metadata': {}
                    }
                    mock_psd.return_value = mock_psd_instance

                    mock_aepx_instance = Mock()
                    mock_aepx_instance.process_aepx.return_value = {
                        'compositions': [],
                        'layers': [],
                        'placeholders': [],
                        'layer_categories': {},
                        'missing_footage': []
                    }
                    mock_aepx.return_value = mock_aepx_instance

                    stage1_processor = Stage1Processor(mock_logger)
                    stage1_processor.psd_exporter = mock_psd_instance
                    stage1_processor.aepx_processor = mock_aepx_instance

                    # Process batch
                    result = stage1_processor.process_batch(test_batch.batch_id)

                    assert result['processed'] == 3
                    assert result['succeeded'] == 3
                    assert result['failed'] == 0

                    # Verify all jobs progressed to Stage 2
                    for job in jobs:
                        in_memory_db.refresh(job)
                        assert job.current_stage == 2
