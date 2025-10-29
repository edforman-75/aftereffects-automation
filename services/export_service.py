"""
Export Service

Handle project export operations - create ZIP packages with all project deliverables.
"""

import os
import json
import zipfile
from datetime import datetime
from typing import Dict, List
from services.base_service import BaseService, Result
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


class ExportService(BaseService):
    """Handle project export operations"""

    def __init__(self, logger):
        super().__init__(logger)

    def export_project(
        self,
        project: Dict,
        output_dir: str = 'exports'
    ) -> Result:
        """
        Export complete project as ZIP file

        Args:
            project: Project data dict
            output_dir: Directory to save export

        Returns:
            Result with export path
        """
        try:
            # Validate all graphics are approved
            unapproved = [g for g in project['graphics'] if not g['approved']]
            if unapproved:
                return Result.failure(
                    f"{len(unapproved)} graphic(s) not approved. All graphics must be approved before export."
                )

            os.makedirs(output_dir, exist_ok=True)

            # Create export filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_name = project['name'].replace(' ', '_')
            zip_filename = f"{project_name}_{timestamp}.zip"
            zip_path = os.path.join(output_dir, zip_filename)

            self.log_info(f"Exporting project {project['name']} to {zip_path}")

            # Create manifest
            manifest = self._create_manifest(project)

            # Create summary PDF
            pdf_path = self._create_summary_pdf(project, output_dir)

            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add manifest
                zipf.writestr('manifest.json', json.dumps(manifest, indent=2))

                # Add summary PDF
                if pdf_path and os.path.exists(pdf_path):
                    zipf.write(pdf_path, 'PROJECT_SUMMARY.pdf')

                # Generate and add Hard Card composition
                self.log_info("Adding Hard Card composition to export")

                try:
                    # Check if project has hard card metadata
                    if project.get('metadata', {}).get('hard_card', {}).get('generated'):
                        hard_card_data = project['metadata']['hard_card']
                        self.log_info(f"Using existing Hard Card with {hard_card_data.get('variables_count', 0)} variables")

                        # Generate Hard Card dict
                        from modules.expression_system import HardCardGenerator
                        hard_card_generator = HardCardGenerator(self.logger)
                        hard_card_dict = hard_card_generator.generate_hard_card_dict()
                    else:
                        # Generate new Hard Card
                        from modules.expression_system import HardCardGenerator
                        hard_card_generator = HardCardGenerator(self.logger)
                        hard_card_dict = hard_card_generator.generate_hard_card_dict()
                        self.log_info(f"Generated new Hard Card with {len(hard_card_dict['layers'])} variables")

                    # Convert Hard Card dict to JSON
                    hard_card_json = json.dumps(hard_card_dict, indent=2)

                    # Add Hard Card to ZIP
                    zipf.writestr('Hard_Card.json', hard_card_json)
                    zipf.writestr('README_HARD_CARD.txt',
                        'This Hard_Card file contains 185 standardized variables that all graphics reference.\n'
                        'Import this into your After Effects project before opening individual graphics.\n'
                        'Modify values in the Hard_Card composition to update all graphics at once.'
                    )

                    self.log_info("Hard Card added to export successfully")

                except Exception as e:
                    self.log_warning(f"Failed to add Hard Card to export: {e}")
                    # Continue with export even if Hard Card fails

                # Add each graphic's files
                for graphic in project['graphics']:
                    if not graphic['approved']:
                        continue

                    graphic_name = graphic['name'].replace(' ', '_')

                    # Add populated AEPX file
                    if graphic.get('aepx_output_path') and os.path.exists(graphic['aepx_output_path']):
                        zipf.write(
                            graphic['aepx_output_path'],
                            f"aepx/{graphic_name}.aepx"
                        )

                    # Add ExtendScript file
                    if graphic.get('script_path') and os.path.exists(graphic['script_path']):
                        zipf.write(
                            graphic['script_path'],
                            f"scripts/{graphic_name}.jsx"
                        )

                    # Add preview if available
                    if graphic.get('preview_path') and os.path.exists(graphic['preview_path']):
                        preview_ext = os.path.splitext(graphic['preview_path'])[1]
                        zipf.write(
                            graphic['preview_path'],
                            f"previews/{graphic_name}{preview_ext}"
                        )

                    # Add original PSD
                    if graphic.get('psd_path') and os.path.exists(graphic['psd_path']):
                        zipf.write(
                            graphic['psd_path'],
                            f"psd_sources/{graphic_name}.psd"
                        )

            # Cleanup temp PDF
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)

            file_size = os.path.getsize(zip_path)

            self.log_info(f"Export complete: {zip_path} ({file_size} bytes)")

            return Result.success({
                'zip_path': zip_path,
                'zip_filename': zip_filename,
                'file_size': file_size,
                'graphics_count': len([g for g in project['graphics'] if g['approved']]),
                'manifest': manifest
            })

        except Exception as e:
            self.log_error(f"Export failed: {e}", e)
            return Result.failure(str(e))

    def _create_manifest(self, project: Dict) -> Dict:
        """Create manifest file with project metadata"""

        approved_graphics = [g for g in project['graphics'] if g['approved']]

        manifest = {
            'project': {
                'id': project['id'],
                'name': project['name'],
                'client': project['client'],
                'created_at': project['created_at'],
                'exported_at': datetime.now().isoformat()
            },
            'statistics': {
                'total_graphics': len(approved_graphics),
                'average_confidence': sum(
                    g.get('confidence_score', 0) for g in approved_graphics
                ) / len(approved_graphics) if approved_graphics else 0
            },
            'hard_card': self._get_hard_card_info(project),
            'graphics': []
        }

        for graphic in approved_graphics:
            # Handle None values for mappings and conflicts
            mappings = graphic.get('mappings') or []
            conflicts = graphic.get('conflicts') or []

            manifest['graphics'].append({
                'id': graphic['id'],
                'name': graphic['name'],
                'template': graphic.get('template_name'),
                'confidence_score': graphic.get('confidence_score'),
                'approved_by': graphic.get('approved_by'),
                'approved_at': graphic.get('approved_at'),
                'files': {
                    'aepx': f"aepx/{graphic['name'].replace(' ', '_')}.aepx",
                    'script': f"scripts/{graphic['name'].replace(' ', '_')}.jsx",
                    'preview': f"previews/{graphic['name'].replace(' ', '_')}.mp4"
                },
                'mappings_count': len(mappings),
                'conflicts_count': len(conflicts)
            })

        return manifest

    def _get_hard_card_info(self, project: Dict) -> Dict:
        """Extract Hard Card information from project metadata"""

        # Add Hard Card info to manifest
        if project.get('metadata', {}).get('hard_card', {}).get('generated'):
            return {
                'included': True,
                'variables_count': project['metadata']['hard_card'].get('variables_count', 185),
                'file': 'Hard_Card.json',
                'format': 'JSON (AEPX XML conversion pending)'
            }
        else:
            return {
                'included': False,
                'note': 'Hard Card not generated for this project'
            }

    def _create_summary_pdf(self, project: Dict, output_dir: str) -> str:
        """Create project summary PDF"""

        try:
            pdf_filename = f"temp_summary_{datetime.now().timestamp()}.pdf"
            pdf_path = os.path.join(output_dir, pdf_filename)

            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#007bff'),
                spaceAfter=30
            )
            story.append(Paragraph("Project Export Summary", title_style))
            story.append(Spacer(1, 0.2*inch))

            # Project Info
            story.append(Paragraph(f"<b>Project:</b> {project['name']}", styles['Normal']))
            story.append(Paragraph(f"<b>Client:</b> {project['client']}", styles['Normal']))
            story.append(Paragraph(
                f"<b>Exported:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles['Normal']
            ))
            story.append(Spacer(1, 0.3*inch))

            # Statistics
            approved_graphics = [g for g in project['graphics'] if g['approved']]
            stats = project.get('stats', {})

            story.append(Paragraph("<b>Project Statistics</b>", styles['Heading2']))
            avg_confidence = (sum(g.get('confidence_score', 0) for g in approved_graphics) / len(approved_graphics) * 100) if approved_graphics else 0

            stats_data = [
                ['Total Graphics', str(stats.get('total_graphics', len(project['graphics'])))],
                ['Approved', str(len(approved_graphics))],
                ['Completed', str(stats.get('completed', 0))],
                ['Average Confidence', f"{avg_confidence:.1f}%"]
            ]

            stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 0.3*inch))

            # Hard Card Information
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("<b>Parametrization System</b>", styles['Heading2']))

            if project.get('metadata', {}).get('hard_card', {}).get('generated'):
                hard_card_info = project['metadata']['hard_card']
                story.append(Paragraph(
                    f"This export includes a Hard_Card composition with "
                    f"{hard_card_info.get('variables_count', 185)} standardized variables. "
                    f"All graphics reference these variables via After Effects expressions, "
                    f"enabling batch rendering with different data.",
                    styles['Normal']
                ))

                # Expression statistics
                graphics_with_expressions = [g for g in approved_graphics if g.get('has_expressions', False)]
                if graphics_with_expressions:
                    avg_expr_confidence = sum(g.get('expression_confidence', 0) for g in graphics_with_expressions) / len(graphics_with_expressions)
                    total_expressions = sum(g.get('expression_count', 0) for g in graphics_with_expressions)

                    story.append(Spacer(1, 0.2*inch))
                    story.append(Paragraph(f"<b>Expression Statistics:</b>", styles['Normal']))
                    story.append(Paragraph(
                        f"• {len(graphics_with_expressions)} of {len(approved_graphics)} graphics have expressions<br/>"
                        f"• {total_expressions} total expressions generated<br/>"
                        f"• Average confidence: {avg_expr_confidence*100:.1f}%",
                        styles['Normal']
                    ))
            else:
                story.append(Paragraph(
                    "This project uses static values (no parametrization). "
                    "Graphics cannot be batch-rendered with different data.",
                    styles['Normal']
                ))

            # Graphics List
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("<b>Approved Graphics</b>", styles['Heading2']))

            # Modify the graphics table header
            graphics_data = [['Name', 'Template', 'Confidence', 'Expressions', 'Approved By']]

            for graphic in approved_graphics:
                expr_info = f"{graphic.get('expression_count', 0)} exprs" if graphic.get('has_expressions') else "Static"
                graphics_data.append([
                    graphic['name'],
                    graphic.get('template_name', 'N/A'),
                    f"{(graphic.get('confidence_score', 0) * 100):.0f}%",
                    expr_info,
                    graphic.get('approved_by', 'N/A')
                ])

            graphics_table = Table(graphics_data, colWidths=[2*inch, 1.5*inch, 0.8*inch, 0.8*inch, 1.4*inch])
            graphics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            story.append(graphics_table)

            # Build PDF
            doc.build(story)

            return pdf_path

        except Exception as e:
            self.log_error(f"Failed to create PDF: {e}", e)
            return None
