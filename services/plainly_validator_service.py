"""
Plainly Validator Service

Service wrapper for Plainly validation with Result pattern.
Provides logging and integration with the service container.
Includes auto-fix capabilities for common issues.
"""

from typing import Optional, Dict, List
from services.base_service import BaseService, Result
from modules.phase6.plainly_validator import PlainlyValidator, ValidationReport
from modules.phase6.plainly_auto_fixer import PlainlyAutoFixer, FixResult


class PlainlyValidatorService(BaseService):
    """Service for validating AEP files for Plainly compatibility with auto-fix"""

    def __init__(self, logger, enhanced_logging=None):
        super().__init__(logger, enhanced_logging)
        self.validator = PlainlyValidator()
        self.auto_fixer = PlainlyAutoFixer()

    def validate_aep(self, aep_path: str, aepx_data: Optional[Dict] = None) -> Result[ValidationReport]:
        """
        Validate AEP file for Plainly compatibility

        Args:
            aep_path: Path to AEP file
            aepx_data: Optional parsed AEPX data from aepx_service

        Returns:
            Result containing ValidationReport
        """
        try:
            self.log_info("=" * 70)
            self.log_info("PLAINLY VALIDATION STARTED")
            self.log_info("=" * 70)
            self.log_info(f"AEP path: {aep_path}")
            self.log_info(f"Has AEPX data: {aepx_data is not None}")

            # Run validation
            report = self.validator.validate_aep(aep_path, aepx_data)

            # Log results
            self.log_info(f"Validation complete:")
            self.log_info(f"  Score: {report.score:.1f}/100")
            self.log_info(f"  Grade: {report.grade}")
            self.log_info(f"  Valid: {report.is_valid}")
            self.log_info(f"  Plainly Ready: {report.plainly_ready}")
            self.log_info(f"  Issues: {report.summary['critical']} critical, "
                         f"{report.summary['warnings']} warnings, "
                         f"{report.summary['info']} info")

            # Log critical issues
            if report.summary['critical'] > 0:
                self.log_warning("CRITICAL ISSUES DETECTED:")
                for issue in report.issues:
                    if issue.severity.value == 'critical':
                        self.log_warning(f"  - {issue.message}: {issue.details}")

            self.log_info("=" * 70)

            return Result.success(report)

        except Exception as e:
            self.log_error(f"Validation error: {e}", exc_info=True)
            return Result.failure(f"Validation failed: {str(e)}")

    def get_validation_summary(self, report: ValidationReport) -> Dict:
        """
        Get a summary of validation results for UI display

        Args:
            report: ValidationReport

        Returns:
            Dictionary with summary information
        """
        return {
            'score': report.score,
            'grade': report.grade,
            'is_valid': report.is_valid,
            'plainly_ready': report.plainly_ready,
            'total_issues': report.summary['total_issues'],
            'critical_count': report.summary['critical'],
            'warning_count': report.summary['warnings'],
            'info_count': report.summary['info'],
            'status_message': self._get_status_message(report)
        }

    def _get_status_message(self, report: ValidationReport) -> str:
        """Generate user-friendly status message"""
        if report.plainly_ready:
            return "✅ Ready for Plainly deployment!"
        elif report.is_valid:
            return "⚠️ Valid but has warnings. Review before deployment."
        else:
            return "❌ Critical issues must be fixed before Plainly deployment."

    def get_critical_issues(self, report: ValidationReport) -> list:
        """Extract only critical issues from report"""
        return [issue for issue in report.issues if issue.severity.value == 'critical']

    def get_warning_issues(self, report: ValidationReport) -> list:
        """Extract only warning issues from report"""
        return [issue for issue in report.issues if issue.severity.value == 'warning']

    def get_info_issues(self, report: ValidationReport) -> list:
        """Extract only info issues from report"""
        return [issue for issue in report.issues if issue.severity.value == 'info']

    def apply_auto_fixes(self, aepx_data: Dict, report: ValidationReport) -> Result[FixResult]:
        """
        Automatically fix all fixable issues

        Args:
            aepx_data: Parsed AEPX data (will be modified in place)
            report: ValidationReport with issues to fix

        Returns:
            Result containing FixResult with details of changes made
        """
        try:
            self.log_info("==" * 35)
            self.log_info("AUTO-FIX STARTED")
            self.log_info("==" * 35)

            # Get fixable issues
            fixable_issues = [issue for issue in report.issues if self.auto_fixer.is_fixable(issue)]
            self.log_info(f"Found {len(fixable_issues)} fixable issues out of {len(report.issues)} total")

            if len(fixable_issues) == 0:
                self.log_info("No fixable issues found")
                return Result.success(FixResult(
                    success=True,
                    fixed_count=0,
                    message="No fixable issues found"
                ))

            # Apply fixes
            fix_result = self.auto_fixer.fix_all_issues(aepx_data, fixable_issues)

            # Log results
            self.log_info(f"Auto-fix complete:")
            self.log_info(f"  Fixed: {fix_result.fixed_count} issues")
            self.log_info(f"  Changes made: {len(fix_result.changes)}")

            if fix_result.errors:
                self.log_warning(f"  Errors encountered: {len(fix_result.errors)}")
                for error in fix_result.errors:
                    self.log_warning(f"    - {error}")

            # Log changes
            for change in fix_result.changes:
                self.log_info(f"  ✓ {change['type']}: {change['old_name']} → {change['new_name']}")

            self.log_info("==" * 35)

            return Result.success(fix_result)

        except Exception as e:
            self.log_error(f"Auto-fix error: {e}", exc_info=True)
            return Result.failure(f"Auto-fix failed: {str(e)}")

    def fix_single_issue(self, aepx_data: Dict, issue) -> Result[FixResult]:
        """
        Fix a single specific issue

        Args:
            aepx_data: Parsed AEPX data (will be modified in place)
            issue: ValidationIssue to fix

        Returns:
            Result containing FixResult for this specific fix
        """
        try:
            self.log_info(f"Fixing issue: {issue.message}")

            if not self.auto_fixer.is_fixable(issue):
                self.log_warning(f"Issue is not auto-fixable: {issue.category}")
                return Result.failure(f"Issue category '{issue.category}' cannot be automatically fixed")

            fix_result = self.auto_fixer.fix_single_issue(aepx_data, issue)

            if fix_result.success:
                self.log_info(f"Fix applied: {fix_result.message}")
                for change in fix_result.changes:
                    self.log_info(f"  ✓ {change['type']}: {change['old_name']} → {change['new_name']}")
            else:
                self.log_warning(f"Fix failed: {fix_result.message}")

            return Result.success(fix_result)

        except Exception as e:
            self.log_error(f"Fix error: {e}", exc_info=True)
            return Result.failure(f"Fix failed: {str(e)}")

    def get_fixable_issues(self, report: ValidationReport) -> List:
        """Get list of issues that can be automatically fixed"""
        return [issue for issue in report.issues if self.auto_fixer.is_fixable(issue)]

    def get_non_fixable_issues(self, report: ValidationReport) -> List:
        """Get list of issues that require manual intervention"""
        return [issue for issue in report.issues if not self.auto_fixer.is_fixable(issue)]
