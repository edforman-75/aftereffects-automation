"""
Integration tests for stage route handlers.

Tests the complete API endpoints for stages 2, 4, 5, and 6 with in-memory database.
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database.models import Base, Job, Batch
from routes.stage2_routes import stage2_bp
from routes.stage4_routes import stage4_bp
from routes.stage5_routes import stage5_bp
from routes.stage6_routes import stage6_bp


@pytest.fixture(scope='function')
def test_app():
    """Create a Flask test app with in-memory database."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Register blueprints
    app.register_blueprint(stage2_bp)
    app.register_blueprint(stage4_bp)
    app.register_blueprint(stage5_bp)
    app.register_blueprint(stage6_bp)

    # Create in-memory database
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)

    # Inject session into app
    app.session = Session

    yield app

    # Cleanup
    Session.remove()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope='function')
def test_client(test_app):
    """Create a test client for the app."""
    return test_app.test_client()


@pytest.fixture(scope='function')
def test_db_session(test_app):
    """Get the test database session."""
    return test_app.session


@pytest.fixture
def sample_batch(test_db_session):
    """Create a sample batch for testing."""
    batch = Batch(
        batch_id='test-batch-1',
        name='Test Batch',
        created_at=datetime.utcnow()
    )
    test_db_session.add(batch)
    test_db_session.commit()
    return batch


@pytest.fixture
def sample_job_stage1(test_db_session, sample_batch):
    """Create a sample job in Stage 1 (completed)."""
    job = Job(
        job_id='job-stage1',
        batch_id=sample_batch.batch_id,
        psd_path='/path/to/test.psd',
        aepx_path='/path/to/template.aepx',
        current_stage=1,
        status='completed',
        stage1_results=json.dumps({
            'psd_layers': ['Layer 1', 'Layer 2'],
            'aepx_placeholders': ['Placeholder 1', 'Placeholder 2']
        }),
        stage1_started_at=datetime.utcnow(),
        stage1_completed_at=datetime.utcnow()
    )
    test_db_session.add(job)
    test_db_session.commit()
    return job


@pytest.fixture
def sample_job_stage2(test_db_session, sample_batch):
    """Create a sample job in Stage 2."""
    job = Job(
        job_id='job-stage2',
        batch_id=sample_batch.batch_id,
        psd_path='/path/to/test.psd',
        aepx_path='/path/to/template.aepx',
        current_stage=2,
        status='awaiting_review',
        stage1_results=json.dumps({
            'matches': [
                {'psd_layer': 'Layer 1', 'aepx_layer': 'Placeholder 1', 'confidence': 0.9}
            ]
        })
    )
    test_db_session.add(job)
    test_db_session.commit()
    return job


@pytest.fixture
def sample_job_stage4(test_db_session, sample_batch):
    """Create a sample job in Stage 4 with validation issues."""
    job = Job(
        job_id='job-stage4',
        batch_id=sample_batch.batch_id,
        psd_path='/path/to/test.psd',
        aepx_path='/path/to/template.aepx',
        current_stage=4,
        status='awaiting_approval',
        stage2_approved_matches=json.dumps([
            {'psd_layer': 'Layer 1', 'aepx_layer': 'Placeholder 1'}
        ]),
        stage3_validation_results=json.dumps({
            'has_critical_issues': True,
            'issues': [
                {'type': 'aspect_ratio_mismatch', 'severity': 'critical'}
            ]
        })
    )
    test_db_session.add(job)
    test_db_session.commit()
    return job


@pytest.fixture
def sample_job_stage5(test_db_session, sample_batch):
    """Create a sample job in Stage 5."""
    job = Job(
        job_id='job-stage5',
        batch_id=sample_batch.batch_id,
        psd_path='/path/to/test.psd',
        aepx_path='/path/to/template.aepx',
        current_stage=5,
        status='processing',
        stage2_approved_matches=json.dumps([
            {'psd_layer': 'Layer 1', 'aepx_layer': 'Placeholder 1'}
        ])
    )
    test_db_session.add(job)
    test_db_session.commit()
    return job


@pytest.fixture
def sample_job_stage6(test_db_session, sample_batch):
    """Create a sample job in Stage 6."""
    job = Job(
        job_id='job-stage6',
        batch_id=sample_batch.batch_id,
        psd_path='/path/to/test.psd',
        aepx_path='/path/to/template.aepx',
        current_stage=6,
        status='awaiting_approval',
        stage5_extendscript='var test = "script";',
        stage6_preview_video_path='/path/to/preview.mp4',
        stage6_psd_preview_path='/path/to/psd_preview.png'
    )
    test_db_session.add(job)
    test_db_session.commit()
    return job


class TestStage2Routes:
    """Test Stage 2 route handlers."""

    @pytest.mark.integration
    def test_approve_stage2_success(self, test_client, sample_job_stage2, test_db_session):
        """Test successful Stage 2 approval."""
        with patch('routes.stage2_routes.MatchValidationService') as mock_validator:
            with patch('routes.stage2_routes.transition_manager') as mock_transition:
                # Mock validation
                mock_validator_instance = Mock()
                mock_validator_instance.validate_job.return_value = {
                    'has_critical_issues': False,
                    'issues': []
                }
                mock_validator.return_value = mock_validator_instance

                # Mock transition
                mock_transition.transition_stage.return_value = {
                    'success': True,
                    'to_stage': 5
                }

                response = test_client.post(
                    f'/api/job/{sample_job_stage2.job_id}/approve-stage2',
                    json={
                        'matches': [
                            {'psd_layer': 'Layer 1', 'aepx_layer': 'Placeholder 1'}
                        ]
                    }
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True

    @pytest.mark.integration
    def test_approve_stage2_job_not_found(self, test_client):
        """Test Stage 2 approval with non-existent job."""
        response = test_client.post(
            '/api/job/nonexistent-job/approve-stage2',
            json={'matches': []}
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_approve_stage2_wrong_stage(self, test_client, sample_job_stage4):
        """Test Stage 2 approval when job is in wrong stage."""
        response = test_client.post(
            f'/api/job/{sample_job_stage4.job_id}/approve-stage2',
            json={'matches': []}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'not in stage 2' in data['error'].lower()

    @pytest.mark.integration
    def test_approve_stage2_missing_matches(self, test_client, sample_job_stage2):
        """Test Stage 2 approval with missing matches data."""
        response = test_client.post(
            f'/api/job/{sample_job_stage2.job_id}/approve-stage2',
            json={}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'matches' in data['error'].lower()


class TestStage4Routes:
    """Test Stage 4 route handlers."""

    @pytest.mark.integration
    def test_override_validation_success(self, test_client, sample_job_stage4, test_db_session):
        """Test successful validation override."""
        with patch('routes.stage4_routes.transition_manager') as mock_transition:
            mock_transition.transition_stage.return_value = {
                'success': True,
                'to_stage': 5
            }

            response = test_client.post(
                f'/api/job/{sample_job_stage4.job_id}/override-validation',
                json={
                    'reason': 'User confirmed dimensions are acceptable',
                    'user_id': 'user-123'
                }
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

            # Verify override was stored
            job = test_db_session.query(Job).filter_by(job_id=sample_job_stage4.job_id).first()
            assert job.stage4_override is True
            assert job.stage4_override_reason == 'User confirmed dimensions are acceptable'

    @pytest.mark.integration
    def test_override_validation_missing_reason(self, test_client, sample_job_stage4):
        """Test validation override without reason."""
        response = test_client.post(
            f'/api/job/{sample_job_stage4.job_id}/override-validation',
            json={'user_id': 'user-123'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'reason' in data['error'].lower()

    @pytest.mark.integration
    def test_return_to_matching_success(self, test_client, sample_job_stage4, test_db_session):
        """Test returning job to Stage 2 for re-matching."""
        with patch('routes.stage4_routes.transition_manager') as mock_transition:
            mock_transition.transition_stage.return_value = {
                'success': True,
                'to_stage': 2
            }

            response = test_client.post(
                f'/api/job/{sample_job_stage4.job_id}/return-to-matching',
                json={'user_id': 'user-123'}
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    @pytest.mark.integration
    def test_return_to_matching_wrong_stage(self, test_client, sample_job_stage2):
        """Test returning to matching when not in Stage 4."""
        response = test_client.post(
            f'/api/job/{sample_job_stage2.job_id}/return-to-matching',
            json={'user_id': 'user-123'}
        )

        assert response.status_code == 400


class TestStage5Routes:
    """Test Stage 5 route handlers."""

    @pytest.mark.integration
    def test_generate_extendscript_success(self, test_client, sample_job_stage5, test_db_session):
        """Test successful ExtendScript generation."""
        with patch('routes.stage5_routes.ExtendScriptService') as mock_service:
            mock_instance = Mock()
            mock_instance.generate_for_job.return_value = {
                'success': True,
                'extendscript': 'var test = "generated";'
            }
            mock_service.return_value = mock_instance

            response = test_client.post(
                f'/api/job/{sample_job_stage5.job_id}/generate-extendscript',
                json={'user_id': 'user-123'}
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    @pytest.mark.integration
    def test_generate_extendscript_wrong_stage(self, test_client, sample_job_stage2):
        """Test ExtendScript generation when not in Stage 5."""
        response = test_client.post(
            f'/api/job/{sample_job_stage2.job_id}/generate-extendscript',
            json={'user_id': 'user-123'}
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_extendscript_status_success(self, test_client, sample_job_stage5):
        """Test getting ExtendScript generation status."""
        # Set extendscript on job
        sample_job_stage5.stage5_extendscript = 'var test = "script";'

        response = test_client.get(
            f'/api/job/{sample_job_stage5.job_id}/extendscript-status'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'completed'
        assert data['has_extendscript'] is True

    @pytest.mark.integration
    def test_extendscript_status_not_ready(self, test_client, sample_job_stage5):
        """Test ExtendScript status when not yet generated."""
        sample_job_stage5.stage5_extendscript = None

        response = test_client.get(
            f'/api/job/{sample_job_stage5.job_id}/extendscript-status'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'processing'
        assert data['has_extendscript'] is False


class TestStage6Routes:
    """Test Stage 6 route handlers."""

    @pytest.mark.integration
    def test_get_preview_data_success(self, test_client, sample_job_stage6):
        """Test getting preview data."""
        response = test_client.get(
            f'/api/job/{sample_job_stage6.job_id}/preview-data'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['job_id'] == sample_job_stage6.job_id
        assert 'preview_video_path' in data
        assert 'psd_preview_path' in data

    @pytest.mark.integration
    def test_get_preview_data_job_not_found(self, test_client):
        """Test getting preview data for non-existent job."""
        response = test_client.get(
            '/api/job/nonexistent/preview-data'
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_preview_data_wrong_stage(self, test_client, sample_job_stage2):
        """Test getting preview data when not in Stage 6."""
        response = test_client.get(
            f'/api/job/{sample_job_stage2.job_id}/preview-data'
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_complete_job_success(self, test_client, sample_job_stage6, test_db_session):
        """Test completing a job from Stage 6."""
        with patch('routes.stage6_routes.transition_manager') as mock_transition:
            mock_transition.transition_stage.return_value = {
                'success': True
            }

            response = test_client.post(
                f'/api/job/{sample_job_stage6.job_id}/complete',
                json={
                    'approved': True,
                    'user_id': 'user-123'
                }
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

            # Verify approval was stored
            job = test_db_session.query(Job).filter_by(job_id=sample_job_stage6.job_id).first()
            assert job.stage6_approved is True

    @pytest.mark.integration
    def test_complete_job_rejection(self, test_client, sample_job_stage6, test_db_session):
        """Test rejecting a job in Stage 6."""
        response = test_client.post(
            f'/api/job/{sample_job_stage6.job_id}/complete',
            json={
                'approved': False,
                'rejection_reason': 'Preview quality not acceptable',
                'user_id': 'user-123'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify job was marked appropriately
        job = test_db_session.query(Job).filter_by(job_id=sample_job_stage6.job_id).first()
        assert job.stage6_approved is False

    @pytest.mark.integration
    def test_complete_job_missing_approval_status(self, test_client, sample_job_stage6):
        """Test completing job without approval status."""
        response = test_client.post(
            f'/api/job/{sample_job_stage6.job_id}/complete',
            json={'user_id': 'user-123'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'approved' in data['error'].lower()


class TestStageTransitionIntegration:
    """Test stage transitions through routes."""

    @pytest.mark.integration
    def test_full_stage2_to_stage5_flow(
        self,
        test_client,
        sample_job_stage2,
        test_db_session
    ):
        """Test complete flow from Stage 2 approval to Stage 5."""
        with patch('routes.stage2_routes.MatchValidationService') as mock_validator:
            with patch('routes.stage2_routes.transition_manager') as mock_transition:
                with patch('routes.stage5_routes.ExtendScriptService') as mock_es_service:
                    # Mock validation - no critical issues
                    mock_validator_instance = Mock()
                    mock_validator_instance.validate_job.return_value = {
                        'has_critical_issues': False,
                        'issues': []
                    }
                    mock_validator.return_value = mock_validator_instance

                    # Mock transition to Stage 5
                    mock_transition.transition_stage.return_value = {
                        'success': True,
                        'to_stage': 5
                    }

                    # Step 1: Approve Stage 2
                    response = test_client.post(
                        f'/api/job/{sample_job_stage2.job_id}/approve-stage2',
                        json={
                            'matches': [
                                {'psd_layer': 'Layer 1', 'aepx_layer': 'Placeholder 1'}
                            ]
                        }
                    )

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True

    @pytest.mark.integration
    def test_stage2_to_stage4_with_validation_issues(
        self,
        test_client,
        sample_job_stage2,
        test_db_session
    ):
        """Test flow from Stage 2 to Stage 4 when validation finds issues."""
        with patch('routes.stage2_routes.MatchValidationService') as mock_validator:
            with patch('routes.stage2_routes.transition_manager') as mock_transition:
                # Mock validation - has critical issues
                mock_validator_instance = Mock()
                mock_validator_instance.validate_job.return_value = {
                    'has_critical_issues': True,
                    'issues': [
                        {'type': 'aspect_ratio_mismatch', 'severity': 'critical'}
                    ]
                }
                mock_validator.return_value = mock_validator_instance

                # Mock transition to Stage 4
                mock_transition.transition_stage.return_value = {
                    'success': True,
                    'to_stage': 4
                }

                # Approve Stage 2
                response = test_client.post(
                    f'/api/job/{sample_job_stage2.job_id}/approve-stage2',
                    json={
                        'matches': [
                            {'psd_layer': 'Layer 1', 'aepx_layer': 'Placeholder 1'}
                        ]
                    }
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True


class TestConcurrentStageProcessing:
    """Test concurrent processing of multiple jobs."""

    @pytest.mark.integration
    def test_multiple_jobs_stage2_approval(
        self,
        test_client,
        test_db_session,
        sample_batch
    ):
        """Test approving multiple jobs in Stage 2 concurrently."""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = Job(
                job_id=f'job-concurrent-{i}',
                batch_id=sample_batch.batch_id,
                psd_path='/path/to/test.psd',
                aepx_path='/path/to/template.aepx',
                current_stage=2,
                status='awaiting_review',
                stage1_results=json.dumps({'matches': []})
            )
            test_db_session.add(job)
            jobs.append(job)

        test_db_session.commit()

        with patch('routes.stage2_routes.MatchValidationService'):
            with patch('routes.stage2_routes.transition_manager') as mock_transition:
                mock_transition.transition_stage.return_value = {'success': True}

                # Approve all jobs
                for job in jobs:
                    response = test_client.post(
                        f'/api/job/{job.job_id}/approve-stage2',
                        json={'matches': []}
                    )
                    assert response.status_code == 200

                # Verify all were processed
                assert mock_transition.transition_stage.call_count == 3
