"""
Stage 3: Match Validation Service

Validates approved layer matches for quality issues before ExtendScript generation.
Checks aspect ratios, resolutions, and compatibility.
"""

import json
from typing import Dict, List
from datetime import datetime
from database import db_session
from database.models import Job


class MatchValidationService:
    """
    Validates approved matches for potential issues.

    Validation Categories:
    - CRITICAL: Must be addressed or explicitly overridden  
    - WARNING: Should be reviewed but can proceed
    - INFO: Informational only
    """

    def __init__(self, logger):
        self.logger = logger

    def validate_job(self, job_id: str) -> Dict:
        """Run all validation checks on approved matches."""
        self.logger.info(f"Starting match validation for job {job_id}")

        try:
            # Get job data using ORM
            session = db_session()
            try:
                job = session.query(Job).filter_by(job_id=job_id).first()

                if not job:
                    raise ValueError(f"Job {job_id} not found")

                # JSON columns are auto-deserialized by SQLAlchemy
                stage1 = job.stage1_results if job.stage1_results else {}
                stage2 = job.stage2_approved_matches if job.stage2_approved_matches else {}
            finally:
                session.close()

            # Extract data
            psd_layers = stage1.get('psd', {}).get('layers', {})
            aepx_comp = stage1.get('aepx', {}).get('compositions', [{}])[0]
            matches = stage2.get('approved_matches', [])

            # Initialize results
            results = {
                "valid": True,
                "critical_issues": [],
                "warnings": [],
                "info": [],
                "job_id": job_id,
                "validated_at": datetime.utcnow().isoformat()
            }

            # Run checks
            results["critical_issues"].extend(
                self._check_aspect_ratios(psd_layers, aepx_comp, matches)
            )
            
            results["warnings"].extend(
                self._check_resolutions(psd_layers, aepx_comp, matches)
            )

            # Mark invalid if critical issues found
            if results["critical_issues"]:
                results["valid"] = False
                self.logger.warning(
                    f"Job {job_id} has {len(results['critical_issues'])} critical issues"
                )

            self.logger.info(
                f"Validation complete: {len(results['critical_issues'])} critical, "
                f"{len(results['warnings'])} warnings"
            )

            return results

        except Exception as e:
            self.logger.error(f"Error validating job {job_id}: {e}", exc_info=True)
            raise

    def _check_aspect_ratios(
        self, psd_layers: Dict, aepx_comp: Dict, matches: List
    ) -> List[Dict]:
        """Check for aspect ratio mismatches."""
        issues = []

        # Get comp dimensions
        comp_w = aepx_comp.get('width', 1920)
        comp_h = aepx_comp.get('height', 1080)
        comp_ratio = comp_w / comp_h if comp_h > 0 else 1.778

        for match in matches:
            psd_id = match.get('psd_layer_id', '')
            psd_name = psd_id.replace('psd_', '').replace('_', ' ')
            psd_layer = psd_layers.get(psd_name)

            if not psd_layer:
                continue

            # Get PSD dimensions
            size = psd_layer.get('size', [0, 0])
            if len(size) < 2 or size[0] == 0 or size[1] == 0:
                continue

            psd_w, psd_h = size[0], size[1]
            psd_ratio = psd_w / psd_h

            # Calculate difference
            ratio_diff = abs(psd_ratio - comp_ratio) / comp_ratio

            # Critical if > 10% different
            if ratio_diff > 0.10:
                orientation_psd = "portrait" if psd_ratio < 1 else "landscape"
                orientation_comp = "portrait" if comp_ratio < 1 else "landscape"

                issues.append({
                    "type": "aspect_ratio_mismatch",
                    "severity": "critical",
                    "psd_layer": psd_name,
                    "psd_dimensions": f"{int(psd_w)}×{int(psd_h)}",
                    "psd_orientation": orientation_psd,
                    "comp_dimensions": f"{int(comp_w)}×{int(comp_h)}",
                    "comp_orientation": orientation_comp,
                    "difference_percent": round(ratio_diff * 100, 1),
                    "message": (
                        f"Aspect ratio mismatch: '{psd_name}' "
                        f"({int(psd_w)}×{int(psd_h)}, {orientation_psd}) "
                        f"will be distorted in {orientation_comp} composition"
                    )
                })

        return issues

    def _check_resolutions(
        self, psd_layers: Dict, aepx_comp: Dict, matches: List
    ) -> List[Dict]:
        """Check for resolution issues (upscaling/downscaling)."""
        warnings = []

        comp_w = aepx_comp.get('width', 1920)
        comp_h = aepx_comp.get('height', 1080)

        for match in matches:
            psd_id = match.get('psd_layer_id', '')
            psd_name = psd_id.replace('psd_', '').replace('_', ' ')
            psd_layer = psd_layers.get(psd_name)

            if not psd_layer:
                continue

            size = psd_layer.get('size', [0, 0])
            if len(size) < 2 or size[0] == 0 or size[1] == 0:
                continue

            psd_w, psd_h = size[0], size[1]

            # Calculate scaling
            w_scale = comp_w / psd_w
            h_scale = comp_h / psd_h
            max_scale = max(w_scale, h_scale)

            # Critical upscaling > 200%
            if max_scale > 2.0:
                warnings.append({
                    "type": "resolution_critical",
                    "severity": "critical",
                    "psd_layer": psd_name,
                    "psd_dimensions": f"{int(psd_w)}×{int(psd_h)}",
                    "scale_percent": round(max_scale * 100, 0),
                    "message": (
                        f"Critical resolution issue: '{psd_name}' will be upscaled "
                        f"{round(max_scale * 100, 0)}%, causing pixelation"
                    )
                })

            # Moderate upscaling 100-200%
            elif max_scale > 1.0:
                warnings.append({
                    "type": "resolution_warning",
                    "severity": "warning",
                    "psd_layer": psd_name,
                    "scale_percent": round(max_scale * 100, 0),
                    "message": (
                        f"Resolution concern: '{psd_name}' will be upscaled "
                        f"{round(max_scale * 100, 0)}%, may reduce quality"
                    )
                })

        return warnings

    def save_validation_results(
        self, job_id: str, results: Dict, override: bool = False, reason: str = None
    ):
        """Save validation results to database."""
        try:
            # Use ORM to save validation results
            session = db_session()
            try:
                job = session.query(Job).filter_by(job_id=job_id).first()

                if not job:
                    raise ValueError(f"Job {job_id} not found")

                # Update job with validation results (JSON column auto-serializes)
                job.stage3_validation_results = results
                job.stage3_completed_at = datetime.utcnow()
                job.stage3_override = override
                job.stage3_override_reason = reason

                session.commit()
                self.logger.info(f"Saved validation results for job {job_id}")

            finally:
                session.close()

        except Exception as e:
            self.logger.error(f"Error saving validation: {e}", exc_info=True)
            raise
