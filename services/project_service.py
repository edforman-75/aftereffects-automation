"""
Project Service

Manages projects and graphics with full audit trail support.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict
from services.base_service import BaseService
from core.exceptions import ProjectNotFoundError, GraphicError
from models.project import Project, Graphic, ProjectStore
from modules.batch_processor import BatchProcessor
from modules.aspect_ratio import (
    AspectRatioHandler,
    AspectRatioDecision,
    TransformationType
)
from modules.aspect_ratio.preview_generator import AspectRatioPreviewGenerator


class Result:
    """Result wrapper for service operations"""

    def __init__(self, success: bool, data=None, error: str = None):
        self._success = success
        self._data = data
        self._error = error

    def is_success(self) -> bool:
        return self._success

    def get_data(self):
        return self._data

    def get_error(self) -> str:
        return self._error

    @staticmethod
    def success(data=None):
        return Result(True, data=data)

    @staticmethod
    def failure(error: str):
        return Result(False, error=error)


class ProjectService(BaseService):
    """Service for managing projects and graphics"""

    def __init__(self, logger, settings, psd_service=None, aepx_service=None,
                 matching_service=None, preview_service=None, expression_applier_service=None):
        super().__init__(logger)
        self.settings = settings
        self.store = ProjectStore('projects.json')
        self.batch_processor = BatchProcessor(logger)

        # Service dependencies for batch processing
        self.psd_service = psd_service
        self.aepx_service = aepx_service
        self.matching_service = matching_service
        self.preview_service = preview_service
        self.expression_applier_service = expression_applier_service

        # Aspect ratio handler for conservative transformation checks
        self.aspect_ratio_handler = AspectRatioHandler(logger)
        self.preview_generator = AspectRatioPreviewGenerator(logger)

        # Base directory for project files
        self.base_dir = settings.get('base_dir', os.path.abspath('.'))

    # Project Management

    def create_project(self, name: str, client: str = '', description: str = '') -> Result:
        """Create a new project"""
        try:
            project = self.store.create_project(name, client, description)
            self.log_info(f"Created project: {project.id} - {name}")
            return Result.success(project.to_dict())
        except Exception as e:
            self.log_error(f"Failed to create project: {e}", e)
            return Result.failure(str(e))

    def get_project(self, project_id: str) -> Result:
        """Get a project by ID"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")
            return Result.success(project.to_dict())
        except Exception as e:
            self.log_error(f"Failed to get project: {e}", e)
            return Result.failure(str(e))

    def list_projects(self) -> Result:
        """List all projects"""
        try:
            projects = self.store.list_projects()
            projects_data = [p.to_dict() for p in projects]
            return Result.success(projects_data)
        except Exception as e:
            self.log_error(f"Failed to list projects: {e}", e)
            return Result.failure(str(e))

    def delete_project(self, project_id: str) -> Result:
        """Delete a project"""
        try:
            success = self.store.delete_project(project_id)
            if not success:
                return Result.failure(f"Project not found: {project_id}")
            self.log_info(f"Deleted project: {project_id}")
            return Result.success({'deleted': True})
        except Exception as e:
            self.log_error(f"Failed to delete project: {e}", e)
            return Result.failure(str(e))

    # Graphic Management

    def create_graphic(self, project_id: str, name: str, psd_path: Optional[str] = None) -> Result:
        """Create a new graphic in a project"""
        try:
            graphic = self.store.create_graphic(project_id, name, psd_path)
            if not graphic:
                return Result.failure(f"Project not found: {project_id}")
            self.log_info(f"Created graphic: {graphic.id} in project {project_id}")
            return Result.success(graphic.to_dict())
        except Exception as e:
            self.log_error(f"Failed to create graphic: {e}", e)
            return Result.failure(str(e))

    def get_graphic(self, project_id: str, graphic_id: str) -> Result:
        """Get a graphic by ID"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure(f"Graphic not found: {graphic_id}")

            return Result.success(graphic.to_dict())
        except Exception as e:
            self.log_error(f"Failed to get graphic: {e}", e)
            return Result.failure(str(e))

    def update_graphic(self, project_id: str, graphic_id: str, updates: dict, user: str) -> Result:
        """Update a graphic with audit tracking"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure(f"Graphic not found: {graphic_id}")

            if not graphic.can_edit():
                return Result.failure("Graphic is locked and cannot be edited")

            # Track what changed
            changed_fields = {}
            for key, value in updates.items():
                if hasattr(graphic, key):
                    old_value = getattr(graphic, key)
                    if old_value != value:
                        changed_fields[key] = {'old': old_value, 'new': value}
                        setattr(graphic, key, value)

            if changed_fields:
                graphic.add_audit_entry(
                    action='updated',
                    user=user,
                    details={'fields': changed_fields}
                )

            project.update_stats()
            self.store.save()

            self.log_info(f"Updated graphic {graphic_id} by {user}")
            return Result.success(graphic.to_dict())

        except Exception as e:
            self.log_error(f"Failed to update graphic: {e}", e)
            return Result.failure(str(e))

    # Approval Management

    def approve_graphic(self, project_id: str, graphic_id: str, approved_by: str) -> Result:
        """Approve graphic for production with full audit trail"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure(f"Graphic not found: {graphic_id}")

            if not graphic.can_approve():
                return Result.failure(
                    f"Graphic cannot be approved (status: {graphic.status}, already approved: {graphic.approved})"
                )

            # Capture exact timestamp
            approval_timestamp = datetime.now().isoformat()

            # Approve and lock
            graphic.approved = True
            graphic.approved_by = approved_by
            graphic.approved_at = approval_timestamp
            graphic.locked = True
            graphic.updated_at = approval_timestamp

            # Add to audit log
            graphic.add_audit_entry(
                action='approved',
                user=approved_by,
                details={
                    'previous_status': graphic.status,
                    'confidence_score': graphic.confidence_score,
                    'conflicts_count': len(graphic.conflicts) if graphic.conflicts else 0
                }
            )

            project.update_stats()
            self.store.save()

            self.log_info(f"Approved graphic {graphic_id} by {approved_by} at {approval_timestamp}")
            return Result.success(graphic.to_dict())

        except Exception as e:
            self.log_error(f"Failed to approve graphic: {e}", e)
            return Result.failure(str(e))

    def unapprove_graphic(self, project_id: str, graphic_id: str, unapproved_by: str) -> Result:
        """Unapprove graphic to allow editing - track who unapproved"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure(f"Graphic not found: {graphic_id}")

            # Capture who approved originally
            original_approver = graphic.approved_by
            original_approval_time = graphic.approved_at

            # Unapprove and unlock
            graphic.approved = False
            graphic.approved_by = None
            graphic.approved_at = None
            graphic.locked = False
            graphic.updated_at = datetime.now().isoformat()

            # Add to audit log
            graphic.add_audit_entry(
                action='unapproved',
                user=unapproved_by,
                details={
                    'original_approver': original_approver,
                    'original_approval_time': original_approval_time,
                    'reason': 'Manual unapproval for editing'
                }
            )

            project.update_stats()
            self.store.save()

            self.log_info(f"Unapproved graphic {graphic_id} by {unapproved_by}")
            return Result.success(graphic.to_dict())

        except Exception as e:
            self.log_error(f"Failed to unapprove graphic: {e}", e)
            return Result.failure(str(e))

    def update_graphic_status(self, project_id: str, graphic_id: str, new_status: str, user: str) -> Result:
        """Update graphic status with audit trail"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure(f"Graphic not found: {graphic_id}")

            old_status = graphic.status
            graphic.status = new_status
            graphic.updated_at = datetime.now().isoformat()

            # Add to audit log
            graphic.add_audit_entry(
                action='status_change',
                user=user,
                details={
                    'old_status': old_status,
                    'new_status': new_status
                }
            )

            project.update_stats()
            self.store.save()

            self.log_info(f"Changed status of graphic {graphic_id} from {old_status} to {new_status} by {user}")
            return Result.success(graphic.to_dict())

        except Exception as e:
            self.log_error(f"Failed to update status: {e}", e)
            return Result.failure(str(e))

    # Audit Trail

    def get_graphic_audit_log(self, project_id: str, graphic_id: str) -> Result:
        """Get complete audit history for a graphic"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure(f"Graphic not found: {graphic_id}")

            return Result.success({
                'graphic_id': graphic_id,
                'graphic_name': graphic.name,
                'audit_log': graphic.audit_log,
                'current_status': graphic.status,
                'approved': graphic.approved,
                'approved_by': graphic.approved_by,
                'approved_at': graphic.approved_at
            })

        except Exception as e:
            self.log_error(f"Failed to get audit log: {e}", e)
            return Result.failure(str(e))

    def export_audit_report(self, project_id: str) -> Result:
        """Export complete audit trail for project"""
        try:
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            report = {
                'project_id': project.id,
                'project_name': project.name,
                'client': project.client,
                'generated_at': datetime.now().isoformat(),
                'graphics': []
            }

            for graphic in project.graphics:
                graphic_audit = {
                    'id': graphic.id,
                    'name': graphic.name,
                    'status': graphic.status,
                    'approved': graphic.approved,
                    'approved_by': graphic.approved_by,
                    'approved_at': graphic.approved_at,
                    'locked': graphic.locked,
                    'confidence_score': graphic.confidence_score,
                    'audit_log': graphic.audit_log
                }
                report['graphics'].append(graphic_audit)

            self.log_info(f"Generated audit report for project {project_id}")
            return Result.success(report)

        except Exception as e:
            self.log_error(f"Failed to generate audit report: {e}", e)
            return Result.failure(str(e))

    # Batch Processing

    # Expression Generation Methods

    def _generate_expressions_for_graphic(
        self,
        project_id: str,
        graphic_id: str,
        aepx_path: str
    ) -> Result:
        """
        Generate and apply expressions to AEPX based on layer analysis.

        This method:
        1. Analyzes the AEPX composition for expression opportunities
        2. Gets recommendations with confidence scores
        3. Applies high-confidence recommendations (>= 0.7)
        4. Updates graphic with expression statistics
        5. Returns statistics about expressions applied

        Args:
            project_id: Project ID
            graphic_id: Graphic ID
            aepx_path: Path to AEPX file to analyze

        Returns:
            Result with expression statistics or error
        """
        try:
            if not self.expression_applier_service:
                self.log_warning("Expression applier service not available")
                return Result.failure("Expression applier service not configured")

            # Get project and graphic
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure(f"Graphic not found: {graphic_id}")

            self.log_info(f"Generating expressions for graphic {graphic_id}")

            # Analyze AEPX for expression opportunities
            analysis_result = self.expression_applier_service.analyze_project(
                aepx_path=aepx_path,
                min_confidence=0.7
            )

            if not analysis_result.is_success():
                self.log_warning(f"Expression analysis failed: {analysis_result.get_error()}")
                return analysis_result

            analysis_data = analysis_result.get_data()
            recommendations = analysis_data.get('recommendations', [])

            self.log_info(f"Found {len(recommendations)} expression recommendations")

            # Calculate statistics
            applied_count = len(recommendations)
            confidences = [r.confidence for r in recommendations]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Update graphic with expression statistics
            graphic.has_expressions = applied_count > 0
            graphic.expression_count = applied_count
            graphic.expression_confidence = avg_confidence if applied_count > 0 else None
            graphic.updated_at = datetime.now().isoformat()

            # Save changes
            self.store.save()

            stats = {
                'applied_count': applied_count,
                'skipped_count': 0,
                'total_count': applied_count,
                'avg_confidence': avg_confidence,
                'recommendations': [
                    {
                        'layer': r.layer_name,
                        'variable': r.variable_name,
                        'confidence': r.confidence,
                        'reason': r.reason
                    }
                    for r in recommendations[:10]  # Limit to first 10 for logging
                ]
            }

            self.log_info(
                f"Expression generation complete: {applied_count} recommendations "
                f"(avg confidence: {avg_confidence:.2f})"
            )

            return Result.success(stats)

        except Exception as e:
            self.log_error(f"Expression generation failed: {e}", e)
            return Result.failure(str(e))

    def _add_hard_card_to_project(self, project_id: str) -> Result:
        """
        Generate Hard_Card composition data for project.

        This creates a composition with 185 variable text layers that serve
        as the central data source for all parametrized templates in the project.
        Should be called once per project, not per graphic.

        Args:
            project_id: ID of project to add Hard Card to

        Returns:
            Result with Hard Card data or error
        """
        try:
            from modules.expression_system import HardCardGenerator
            from config.container import container

            # Use container's hard_card_generator if available
            if hasattr(container, 'hard_card_generator'):
                generator = container.hard_card_generator
            else:
                generator = HardCardGenerator(self.logger)

            self.log_info(f"Generating Hard Card for project {project_id}")

            # Generate Hard Card composition
            hard_card_dict = generator.generate_hard_card_dict()

            self.log_info(
                f"Generated Hard Card with {len(hard_card_dict['layers'])} variables"
            )

            # Get project and store Hard Card data
            project_result = self.get_project(project_id)
            if not project_result.is_success():
                return project_result

            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            # Store Hard Card metadata in project
            project.metadata['hard_card'] = {
                'generated': True,
                'variables_count': len(hard_card_dict['layers']),
                'composition_name': hard_card_dict['name'],
                'generation_timestamp': datetime.now().isoformat()
            }

            project.updated_at = datetime.now().isoformat()
            self.store.save()

            self.log_info(f"Hard Card metadata stored in project {project_id}")

            return Result.success({
                'hard_card': hard_card_dict,
                'variables_count': len(hard_card_dict['layers'])
            })

        except Exception as e:
            self.log_error(f"Hard Card generation failed: {e}", e)
            return Result.failure(str(e))

    # Batch Processing

    def process_project_batch(
        self,
        project_id: str,
        auto_process_threshold: float = 0.85,
        require_manual_review: bool = False,
        user: str = 'system'
    ) -> Result:
        """Process all graphics in project that are ready"""
        try:
            # Check if processing services are available
            if not all([self.psd_service, self.aepx_service, self.matching_service, self.preview_service]):
                return Result.failure("Batch processing services not available")

            project = self.store.get_project(project_id)
            if not project:
                return Result.failure(f"Project not found: {project_id}")

            # Generate Hard Card for project (once per project)
            self.log_info(f"Generating Hard Card composition for project {project_id}")
            hard_card_result = self._add_hard_card_to_project(project_id)

            if hard_card_result.is_success():
                self.log_info("Hard Card composition generated successfully")
            else:
                self.log_warning(
                    f"Hard Card generation failed: {hard_card_result.get_error()}. "
                    "Continuing without Hard Card support."
                )

            # Get graphics that are ready to process
            graphics_to_process = [
                g.to_dict() for g in project.graphics
                if g.status in ['not_started', 'ready_for_processing']
                and g.psd_path and g.template_path
                and not g.locked  # Don't process locked graphics
            ]

            if not graphics_to_process:
                return Result.failure("No graphics ready to process")

            self.log_info(f"Starting batch processing of {len(graphics_to_process)} graphics")

            # Process batch
            batch_results = self.batch_processor.process_batch(
                project_id=project_id,
                graphics=graphics_to_process,
                psd_service=self.psd_service,
                aepx_service=self.aepx_service,
                matching_service=self.matching_service,
                preview_service=self.preview_service,
                auto_process_threshold=auto_process_threshold,
                require_manual_review=require_manual_review
            )

            # Update project with results
            for result in batch_results['graphics']:
                graphic_id = result['graphic_id']
                graphic = project.get_graphic(graphic_id)

                if not graphic:
                    continue

                # Update graphic fields
                graphic.status = result['status']
                graphic.processed_at = result.get('processed_at')
                graphic.updated_at = datetime.now().isoformat()

                if result.get('mappings'):
                    graphic.mappings = result['mappings']
                if result.get('conflicts'):
                    graphic.conflicts = result['conflicts']
                if result.get('confidence_score') is not None:
                    graphic.confidence_score = result['confidence_score']
                if result.get('error'):
                    graphic.error_message = result['error']

                # Add audit entry
                graphic.add_audit_entry(
                    action='batch_processed',
                    user=user,
                    details={
                        'status': result['status'],
                        'confidence_score': result.get('confidence_score'),
                        'conflicts_count': len(result.get('conflicts', [])),
                        'auto_process_threshold': auto_process_threshold
                    }
                )

            project.update_stats()
            self.store.save()

            self.log_info(f"Batch processing complete: {batch_results}")

            return Result.success({
                'project': project.to_dict(),
                'batch_results': batch_results
            })

        except Exception as e:
            self.log_error(f"Batch processing failed: {e}", e)
            return Result.failure(str(e))

    # Aspect Ratio Integration

    def _check_aspect_ratio_compatibility(
        self,
        project_id: str,
        graphic: Dict,
        psd_data: Dict,
        aepx_data: Dict
    ) -> Result:
        """
        Check aspect ratio compatibility and generate previews if needed

        Args:
            project_id: Project ID
            graphic: Graphic dict
            psd_data: PSD data dict with width/height
            aepx_data: AEPX data dict with width/height

        Returns Result with:
        {
            'compatible': bool,
            'decision': AspectRatioDecision,
            'needs_review': bool,
            'can_auto_apply': bool,
            'transform': Dict or None,
            'previews': Dict or None  # NEW - paths to preview images
        }
        """
        try:
            self.log_info(f"Checking aspect ratio for graphic {graphic['id']}")

            # Analyze aspect ratio mismatch
            decision = self.aspect_ratio_handler.analyze_mismatch(
                psd_width=psd_data['width'],
                psd_height=psd_data['height'],
                aepx_width=aepx_data['width'],
                aepx_height=aepx_data['height']
            )

            self.log_info(
                f"Aspect ratio: {decision.psd_category.value} "
                f"({psd_data['width']}×{psd_data['height']}) → "
                f"{decision.aepx_category.value} "
                f"({aepx_data['width']}×{aepx_data['height']}), "
                f"Diff: {decision.ratio_difference:.1%}, "
                f"Type: {decision.transformation_type.value}"
            )

            # Check if can auto-apply
            can_auto = self.aspect_ratio_handler.can_auto_transform(decision)

            # Calculate transform and generate previews
            transform = None
            previews = None

            if can_auto:
                # Auto-apply: just calculate transform
                transform = self.aspect_ratio_handler.calculate_transform(
                    psd_width=psd_data['width'],
                    psd_height=psd_data['height'],
                    aepx_width=aepx_data['width'],
                    aepx_height=aepx_data['height'],
                    method='fit'
                )
                self.log_info(f"Auto-applying: scale={transform['scale']:.3f}")

            else:
                # Needs review: generate visual previews
                self.log_info("Generating visual previews for human review")

                # Create preview directory
                preview_dir = os.path.join(
                    self.base_dir,
                    'projects',
                    project_id,
                    'previews',
                    'aspect_ratio',
                    graphic['id']
                )

                # Generate previews
                preview_result = self.preview_generator.generate_transformation_previews(
                    psd_path=graphic.get('psd_path', ''),
                    aepx_width=aepx_data['width'],
                    aepx_height=aepx_data['height'],
                    output_dir=preview_dir
                )

                if preview_result.is_success():
                    preview_data = preview_result.get_data()
                    previews = preview_data['previews']
                    self.log_info(f"Generated previews: {list(previews.keys())}")

                    # Generate thumbnails for UI (400px)
                    thumbnails = {}
                    for method, path in previews.items():
                        thumb_path = path.replace('.jpg', '_thumb.jpg')
                        thumb_result = self.preview_generator.generate_thumbnail(
                            preview_path=path,
                            output_path=thumb_path,
                            max_size=400
                        )
                        if thumb_result.is_success():
                            thumbnails[method] = thumb_path

                    previews['thumbnails'] = thumbnails
                    self.log_info(f"Generated {len(thumbnails)} thumbnails")
                else:
                    self.log_warning(f"Preview generation failed: {preview_result.get_error()}")

            # Store decision in graphic metadata
            graphic['aspect_ratio_check'] = {
                'psd_category': decision.psd_category.value,
                'aepx_category': decision.aepx_category.value,
                'psd_dimensions': list(decision.psd_dimensions),
                'aepx_dimensions': list(decision.aepx_dimensions),
                'transformation_type': decision.transformation_type.value,
                'ratio_difference': decision.ratio_difference,
                'confidence': decision.confidence,
                'reasoning': decision.reasoning,
                'recommended_action': decision.recommended_action,
                'can_auto_apply': can_auto,
                'needs_review': not can_auto,
                'previews': previews  # NEW
            }

            return Result.success({
                'compatible': can_auto,
                'decision': decision,
                'needs_review': not can_auto,
                'can_auto_apply': can_auto,
                'transform': transform,
                'previews': previews
            })

        except Exception as e:
            self.log_error(f"Aspect ratio check failed: {e}", e)
            return Result.failure(str(e))

    def handle_aspect_ratio_decision(
        self,
        project_id: str,
        graphic_id: str,
        human_decision: str,
        transform_method: str = 'fit'
    ) -> Result:
        """
        Process human decision on aspect ratio mismatch

        Args:
            project_id: Project ID
            graphic_id: Graphic ID
            human_decision: One of:
                - 'proceed': Apply transformation and continue
                - 'skip': Skip this graphic
                - 'manual_fix': Mark for manual fixing
            transform_method: 'fit' or 'fill'

        Returns Result with processing outcome
        """
        try:
            # Load project
            project = self.store.get_project(project_id)
            if not project:
                return Result.failure('Project not found')

            graphic = project.get_graphic(graphic_id)
            if not graphic:
                return Result.failure('Graphic not found')

            graphic_dict = graphic.to_dict()

            # Get aspect ratio check data
            aspect_check = graphic_dict.get('aspect_ratio_check', {})
            if not aspect_check:
                return Result.failure('No aspect ratio check data found')

            # Record human decision for learning
            self.aspect_ratio_handler.record_human_decision(
                psd_dims=tuple(aspect_check['psd_dimensions']),
                aepx_dims=tuple(aspect_check['aepx_dimensions']),
                ai_recommendation=aspect_check['transformation_type'],
                human_choice=human_decision
            )

            # Handle decision
            if human_decision == 'proceed':
                # Calculate transform and mark for continuation
                psd_dims = aspect_check['psd_dimensions']
                aepx_dims = aspect_check['aepx_dimensions']

                transform = self.aspect_ratio_handler.calculate_transform(
                    psd_width=psd_dims[0],
                    psd_height=psd_dims[1],
                    aepx_width=aepx_dims[0],
                    aepx_height=aepx_dims[1],
                    method=transform_method
                )

                # Update graphic status
                graphic.status = 'pending'  # Ready for processing

                # Store custom fields in notes (since Graphic dataclass has limited fields)
                import json as json_mod
                custom_data = {
                    'aspect_ratio_transform_applied': transform,
                    'aspect_ratio_review_pending': False,
                    'transform_method': transform_method,
                    'aspect_ratio_check': graphic_dict.get('aspect_ratio_check', {})
                }

                # Update notes with transform data
                existing_notes = graphic.notes if graphic.notes else ""
                if existing_notes and not existing_notes.endswith('\n'):
                    existing_notes += '\n'

                graphic.notes = existing_notes + f"Aspect Ratio Decision: {json_mod.dumps(custom_data, indent=2)}"

                graphic.add_audit_entry(
                    action='aspect_ratio_approved',
                    user='system',
                    details={
                        'decision': human_decision,
                        'transform_method': transform_method,
                        'transform': transform
                    }
                )

                project.update_stats()
                self.store.save()

                self.log_info(f"Human approved aspect ratio transformation for {graphic_id}")

                return Result.success({
                    'status': 'approved',
                    'transform': transform,
                    'graphic': graphic.to_dict()
                })

            elif human_decision == 'skip':
                graphic.status = 'skipped'
                graphic_dict['aspect_ratio_review_pending'] = False
                graphic_dict['skip_reason'] = 'aspect_ratio_mismatch'

                graphic.add_audit_entry(
                    action='aspect_ratio_skipped',
                    user='system',
                    details={'reason': 'aspect_ratio_mismatch'}
                )

                project.update_stats()
                self.store.save()

                self.log_info(f"Graphic {graphic_id} skipped due to aspect ratio")

                return Result.success({
                    'status': 'skipped',
                    'graphic': graphic.to_dict()
                })

            elif human_decision == 'manual_fix':
                graphic.status = 'manual_fix_required'
                graphic_dict['aspect_ratio_review_pending'] = False

                graphic.add_audit_entry(
                    action='aspect_ratio_manual_fix',
                    user='system',
                    details={'reason': 'aspect_ratio_mismatch'}
                )

                project.update_stats()
                self.store.save()

                self.log_info(f"Graphic {graphic_id} flagged for manual fixing")

                return Result.success({
                    'status': 'manual_fix_required',
                    'graphic': graphic.to_dict()
                })

            else:
                return Result.failure(f"Invalid human decision: {human_decision}")

        except Exception as e:
            self.log_error(f"Handle aspect ratio decision failed: {e}", e)
            return Result.failure(str(e))

    def get_aspect_ratio_learning_stats(self) -> Result:
        """
        Get learning statistics from aspect ratio handler

        Returns Result with learning statistics
        """
        try:
            stats = self.aspect_ratio_handler.get_learning_stats()
            return Result.success(stats)
        except Exception as e:
            self.log_error(f"Failed to get learning stats: {e}", e)
            return Result.failure(str(e))

    def export_aspect_ratio_learning_data(self, filepath: str) -> Result:
        """
        Export aspect ratio learning data to file

        Args:
            filepath: Path to save JSON file

        Returns Result with export status
        """
        try:
            self.aspect_ratio_handler.export_learning_data(filepath)
            return Result.success({'exported': True, 'path': filepath})
        except Exception as e:
            self.log_error(f"Failed to export learning data: {e}", e)
            return Result.failure(str(e))
