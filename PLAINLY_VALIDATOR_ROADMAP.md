# Plainly Validator - Implementation Roadmap

## Executive Summary

This document outlines the complete implementation plan for the Plainly AEP Validator - the final quality control step in the PSD → After Effects → Plainly workflow.

---

## ✅ COMPLETED: Research Phase

### Documents Created:
1. **`PLAINLY_REQUIREMENTS_RESEARCH.md`** - Comprehensive requirements documentation
2. **`SESSION_SUMMARY_PLAINLY_VALIDATOR.md`** - Session summary and next steps
3. **`PLAINLY_VALIDATOR_ROADMAP.md`** - This implementation plan

### Key Findings:
- ❌ **CRITICAL:** No non-English characters (causes render failures)
- ❌ **CRITICAL:** Audio must be .wav (not .mp3)
- ⚠️ **HIGH PRIORITY:** Layer naming prefixes (`txt_`, `img_`, etc.)
- ⚠️ **HIGH PRIORITY:** Render compositions prefixed with `render_`
- ⚠️ **HIGH PRIORITY:** Dynamic elements in containers
- ⚠️ **HIGH PRIORITY:** Minimal effects (pre-render heavy ones)
- ℹ️ **BEST PRACTICE:** Asset optimization, expression simplification

### Additional Findings from Template Creation Docs:
- Composition selection is mandatory for rendering
- Plainly auto-detects parametrizable layers
- Prefix-based filtering available (default: "plainly")
- Layer exclusion options for adjustment/guide/disabled/shy layers

---

## 🚧 TODO: Implementation Phase

### Step 1: Core Validator Module (4-6 hours)

**File:** `modules/phase6/plainly_validator.py`

```python
"""
Plainly AEP Validator

Validates After Effects projects for Plainly compatibility.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels"""
    CRITICAL = "critical"  # Blocks deployment
    WARNING = "warning"    # Allows deployment with confirmation
    INFO = "info"          # Suggestions only


@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    category: str
    message: str
    details: str
    fix_suggestion: str
    layer_name: str = None
    composition_name: str = None


@dataclass
class ValidationReport:
    """Complete validation report"""
    is_valid: bool
    score: float
    grade: str
    issues: List[ValidationIssue] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    plainly_ready: bool = False


class PlainlyValidator:
    """Validates AEP files for Plainly compatibility"""

    # Validation patterns
    ENGLISH_ONLY_PATTERN = re.compile(r'^[A-Za-z0-9_\-\s.]+$')
    LAYER_PREFIX_PATTERN = re.compile(r'^(txt_|img_|vid_|audio_|color_)')
    RENDER_COMP_PATTERN = re.compile(r'^render_')

    def __init__(self):
        self.issues = []

    def validate_aep(self, aep_path: str, aepx_data: Dict = None) -> ValidationReport:
        """
        Main validation entry point

        Args:
            aep_path: Path to AEP file
            aepx_data: Parsed AEPX data (from aepx_service)

        Returns:
            ValidationReport
        """
        self.issues = []

        # If we have AEPX data, use it for validation
        if aepx_data:
            # Critical checks
            self.check_english_characters(aepx_data)
            self.check_audio_formats(aepx_data)

            # High priority checks
            self.check_layer_naming_conventions(aepx_data)
            self.check_render_composition(aepx_data)
            self.check_dynamic_element_containers(aepx_data)
            self.check_effects_usage(aepx_data)
            self.check_asset_formats(aepx_data)

            # Best practices
            self.check_performance_optimization(aepx_data)
            self.check_expression_complexity(aepx_data)

        # Generate report
        return self.generate_report()

    def check_english_characters(self, aepx_data: Dict):
        """CRITICAL: Check for non-English characters"""
        # Check layer names
        for layer in aepx_data.get('layers', []):
            name = layer.get('name', '')
            if not self.ENGLISH_ONLY_PATTERN.match(name):
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="characters",
                    message=f"Non-English characters in layer name",
                    details=f"Layer '{name}' contains non-English characters",
                    fix_suggestion=f"Rename layer using only A-Z, a-z, 0-9, _, -, space",
                    layer_name=name
                ))

        # Check composition names
        for comp in aepx_data.get('compositions', []):
            name = comp.get('name', '')
            if not self.ENGLISH_ONLY_PATTERN.match(name):
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="characters",
                    message=f"Non-English characters in composition name",
                    details=f"Composition '{name}' contains non-English characters",
                    fix_suggestion=f"Rename composition using only English characters",
                    composition_name=name
                ))

    def check_audio_formats(self, aepx_data: Dict):
        """CRITICAL: Check audio file formats"""
        for layer in aepx_data.get('layers', []):
            if layer.get('type') == 'audio':
                source = layer.get('source', '')
                if source.lower().endswith('.mp3'):
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="audio",
                        message=f"MP3 audio file detected",
                        details=f"Layer '{layer.get('name')}' uses MP3 audio which causes compatibility issues",
                        fix_suggestion=f"Convert {source} to .wav format",
                        layer_name=layer.get('name')
                    ))

    def check_layer_naming_conventions(self, aepx_data: Dict):
        """WARNING: Check layer naming prefixes"""
        dynamic_types = ['text', 'image', 'video', 'audio']

        for layer in aepx_data.get('layers', []):
            layer_type = layer.get('type')
            name = layer.get('name', '')

            if layer_type in dynamic_types:
                if not self.LAYER_PREFIX_PATTERN.match(name):
                    prefix_map = {
                        'text': 'txt_',
                        'image': 'img_',
                        'video': 'vid_',
                        'audio': 'audio_'
                    }
                    expected_prefix = prefix_map.get(layer_type, '')

                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="naming",
                        message=f"Dynamic layer missing prefix",
                        details=f"Layer '{name}' is type '{layer_type}' but lacks '{expected_prefix}' prefix",
                        fix_suggestion=f"Rename to '{expected_prefix}{name}'",
                        layer_name=name
                    ))

    def check_render_composition(self, aepx_data: Dict):
        """WARNING: Check render composition naming"""
        compositions = aepx_data.get('compositions', [])
        render_comps = [c for c in compositions if self.RENDER_COMP_PATTERN.match(c.get('name', ''))]

        if len(render_comps) == 0:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="composition",
                message=f"No render composition found",
                details=f"No composition starts with 'render_' prefix",
                fix_suggestion=f"Rename your main output composition to 'render_final' or 'render_main'",
            ))

    def check_dynamic_element_containers(self, aepx_data: Dict):
        """WARNING: Check if dynamic elements are in containers"""
        # This requires analyzing composition hierarchy
        # For now, provide general guidance
        pass

    def check_effects_usage(self, aepx_data: Dict):
        """WARNING: Check effects usage"""
        for layer in aepx_data.get('layers', []):
            effects = layer.get('effects', [])
            if len(effects) > 10:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="effects",
                    message=f"Heavy effects usage detected",
                    details=f"Layer '{layer.get('name')}' has {len(effects)} effects",
                    fix_suggestion=f"Consider pre-rendering this layer as .mp4 for better performance",
                    layer_name=layer.get('name')
                ))

    def check_asset_formats(self, aepx_data: Dict):
        """WARNING: Check asset file formats"""
        unsupported_extensions = ['.ai', '.psd']

        for layer in aepx_data.get('layers', []):
            source = layer.get('source', '')
            ext = Path(source).suffix.lower()

            if ext in unsupported_extensions:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="assets",
                    message=f"Unsupported asset format",
                    details=f"Layer '{layer.get('name')}' uses {ext} file",
                    fix_suggestion=f"Convert {source} to .png or .jpg format",
                    layer_name=layer.get('name')
                ))

    def check_performance_optimization(self, aepx_data: Dict):
        """INFO: Performance optimization suggestions"""
        # Check layer count
        layer_count = len(aepx_data.get('layers', []))
        if layer_count > 100:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="performance",
                message=f"High layer count detected",
                details=f"Composition has {layer_count} layers",
                fix_suggestion=f"Consider pre-composing related layers for better performance",
            ))

    def check_expression_complexity(self, aepx_data: Dict):
        """INFO: Expression complexity check"""
        # Placeholder for expression analysis
        pass

    def generate_report(self) -> ValidationReport:
        """Generate validation report with scoring"""
        # Calculate score
        score = 100.0
        critical_count = 0
        warning_count = 0
        info_count = 0

        for issue in self.issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 20
                critical_count += 1
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 5
                warning_count += 1
            elif issue.severity == ValidationSeverity.INFO:
                score -= 1
                info_count += 1

        score = max(0, score)  # Don't go below 0

        # Determine grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        # Determine if Plainly ready
        is_valid = critical_count == 0
        plainly_ready = critical_count == 0 and warning_count <= 2

        return ValidationReport(
            is_valid=is_valid,
            score=score,
            grade=grade,
            issues=self.issues,
            summary={
                'total_issues': len(self.issues),
                'critical': critical_count,
                'warnings': warning_count,
                'info': info_count
            },
            plainly_ready=plainly_ready
        )
```

---

### Step 2: Service Layer (2 hours)

**File:** `services/plainly_validator_service.py`

```python
"""
Plainly Validator Service

Service wrapper for Plainly validation with Result pattern.
"""

from services.base_service import BaseService, Result
from modules.phase6.plainly_validator import PlainlyValidator


class PlainlyValidatorService(BaseService):
    """Service for validating AEP files for Plainly compatibility"""

    def __init__(self, logger):
        super().__init__(logger)
        self.validator = PlainlyValidator()

    def validate_aep(self, aep_path: str, aepx_data: dict = None) -> Result:
        """
        Validate AEP file for Plainly compatibility

        Args:
            aep_path: Path to AEP file
            aepx_data: Optional parsed AEPX data

        Returns:
            Result containing ValidationReport
        """
        try:
            self.log_info(f"Validating AEP for Plainly: {aep_path}")

            # Run validation
            report = self.validator.validate_aep(aep_path, aepx_data)

            self.log_info(f"Validation complete - Score: {report.score}, Grade: {report.grade}")
            self.log_info(f"Issues: {report.summary['critical']} critical, {report.summary['warnings']} warnings, {report.summary['info']} info")

            if report.is_valid:
                return Result.success(report)
            else:
                return Result.success(report)  # Still success, but contains issues

        except Exception as e:
            self.log_error(f"Validation error: {e}", exc_info=True)
            return Result.failure(f"Validation failed: {str(e)}")
```

---

### Step 3: API Integration (1 hour)

**File:** `web_app.py` - Add endpoint

```python
@app.route('/validate-plainly', methods=['POST'])
def validate_plainly():
    """Validate AEP file for Plainly compatibility"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]

        # Get AEPX data from session
        aepx_data = session.get('aepx_data')
        aep_path = session.get('aepx_path')  # Actually the AEP/AEPX path

        container.main_logger.info(f"[VALIDATION] Starting Plainly validation for session {session_id}")

        # Import service
        from services.plainly_validator_service import PlainlyValidatorService

        # Validate
        validator_service = PlainlyValidatorService(container.main_logger)
        validation_result = validator_service.validate_aep(str(aep_path), aepx_data)

        if not validation_result.is_success():
            return jsonify({
                'success': False,
                'message': validation_result.get_error()
            }), 500

        report = validation_result.get_data()

        # Store in session
        session['validation_report'] = {
            'is_valid': report.is_valid,
            'score': report.score,
            'grade': report.grade,
            'plainly_ready': report.plainly_ready,
            'summary': report.summary
        }

        # Convert issues to serializable format
        issues_json = []
        for issue in report.issues:
            issues_json.append({
                'severity': issue.severity.value,
                'category': issue.category,
                'message': issue.message,
                'details': issue.details,
                'fix_suggestion': issue.fix_suggestion,
                'layer_name': issue.layer_name,
                'composition_name': issue.composition_name
            })

        return jsonify({
            'success': True,
            'report': {
                'is_valid': report.is_valid,
                'score': report.score,
                'grade': report.grade,
                'plainly_ready': report.plainly_ready,
                'issues': issues_json,
                'summary': report.summary
            }
        })

    except Exception as e:
        container.main_logger.error(f"Plainly validation error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Validation failed: {str(e)}'
        }), 500
```

---

### Step 4: Web UI (3-4 hours)

**Tasks:**
1. Add validation section HTML to `templates/index.html`
2. Add validation styles to `static/style.css`
3. Add JavaScript for validation API call
4. Display validation report with score/grade
5. Show issues breakdown by severity
6. Add action buttons (download report, deploy)

---

## 📊 VALIDATION SCORE CALCULATION

```python
Starting Score: 100

For each issue:
  - Critical: -20 points
  - Warning: -5 points
  - Info: -1 point

Final Score: max(0, score)

Grade:
  A: 90-100
  B: 80-89
  C: 70-79
  D: 60-69
  F: 0-59
```

---

## 🎯 SUCCESS METRICS

The validator is successful when:
- ✅ All critical Plainly requirements validated
- ✅ Clear actionable feedback for each issue
- ✅ Files graded "A" deploy successfully to Plainly
- ✅ Validation catches issues before production
- ✅ UI is intuitive and helpful
- ✅ Zero false positives on validated files

---

## 📝 TESTING PLAN

1. **Test with known-good AEP:**
   - Should score 90-100
   - Should be "Plainly Ready"
   - Should show minimal or no issues

2. **Test with non-English characters:**
   - Should show CRITICAL issues
   - Should NOT be "Plainly Ready"
   - Should provide clear fix suggestions

3. **Test with .mp3 audio:**
   - Should show CRITICAL issues
   - Should suggest conversion to .wav

4. **Test with poorly named layers:**
   - Should show WARNING issues
   - Should suggest proper prefixes

5. **Test with heavy effects:**
   - Should show WARNING/INFO issues
   - Should suggest pre-rendering

---

## 🚀 DEPLOYMENT PLAN

1. **Implement validator module**
2. **Test thoroughly**
3. **Integrate with container**
4. **Add API endpoint**
5. **Build UI**
6. **Test end-to-end**
7. **Deploy to production**
8. **Monitor validation results**
9. **Refine validation rules based on real usage**

---

## 📚 DOCUMENTATION TO CREATE

1. **Plainly Validation Guide** - User-facing documentation
2. **Validation Rules Reference** - Technical reference
3. **Common Issues & Fixes** - Troubleshooting guide
4. **API Documentation** - For programmatic validation

---

## ✨ FINAL DELIVERABLE

A complete, production-ready Plainly validator that:
- Validates AEP files against all Plainly requirements
- Provides actionable feedback with fix suggestions
- Assigns quality scores and grades
- Beautiful UI for reviewing validation reports
- Integrates seamlessly into existing workflow
- Prevents deployment of incompatible files
- Reduces Plainly render failures to near-zero

---

**Status:** Roadmap Complete ✅
**Next:** Begin Implementation 🚀
**ETA:** 12-16 hours
