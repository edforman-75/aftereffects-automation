"""
Plainly AEP Validator

Validates After Effects projects for Plainly compatibility.
Ensures files meet all Plainly requirements before deployment.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"  # Blocks deployment - will fail in Plainly
    WARNING = "warning"    # Allows deployment with confirmation - may cause issues
    INFO = "info"          # Suggestions only - best practice recommendations


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    severity: ValidationSeverity
    category: str
    message: str
    details: str
    fix_suggestion: str
    layer_name: Optional[str] = None
    composition_name: Optional[str] = None


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
    """
    Validates AEP files for Plainly compatibility

    Based on Plainly's documented requirements:
    - Critical: Non-English characters, .mp3 audio files
    - High Priority: Naming conventions, composition structure, effects usage
    - Best Practices: Performance optimization, asset management
    """

    # Validation patterns
    ENGLISH_ONLY_PATTERN = re.compile(r'^[A-Za-z0-9_\-\s.]+$')
    LAYER_PREFIX_PATTERN = re.compile(r'^(txt_|img_|vid_|audio_|color_)')
    RENDER_COMP_PATTERN = re.compile(r'^render_')

    def __init__(self):
        self.issues = []

    def validate_aep(self, aep_path: str, aepx_data: Optional[Dict] = None) -> ValidationReport:
        """
        Main validation entry point

        Args:
            aep_path: Path to AEP file
            aepx_data: Parsed AEPX data (from aepx_service)

        Returns:
            ValidationReport with all findings
        """
        self.issues = []

        # If we have AEPX data, perform detailed validation
        if aepx_data:
            # Critical checks (must pass)
            self._check_english_characters(aepx_data)
            self._check_audio_formats(aepx_data)

            # High priority checks (strongly recommended)
            self._check_layer_naming_conventions(aepx_data)
            self._check_render_composition(aepx_data)
            self._check_effects_usage(aepx_data)
            self._check_asset_formats(aepx_data)

            # Best practices (informational)
            self._check_performance_optimization(aepx_data)

        # Generate and return report
        return self._generate_report()

    def _check_english_characters(self, aepx_data: Dict):
        """
        CRITICAL: Check for non-English characters

        Plainly requirement: "Make sure that you don't add any non-English
        characters to layer/file names. This will cause failed renders."
        """
        # Check all layer names
        for layer in aepx_data.get('layers', []):
            name = layer.get('name', '')
            if name and not self.ENGLISH_ONLY_PATTERN.match(name):
                # Find the problematic characters
                non_english = ''.join([c for c in name if not re.match(r'[A-Za-z0-9_\-\s.]', c)])

                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="characters",
                    message="Non-English characters in layer name",
                    details=f"Layer '{name}' contains non-English characters: '{non_english}'",
                    fix_suggestion=f"Rename layer using only A-Z, a-z, 0-9, _, -, space, and period",
                    layer_name=name
                ))

        # Check composition names
        for comp in aepx_data.get('compositions', []):
            name = comp.get('name', '')
            if name and not self.ENGLISH_ONLY_PATTERN.match(name):
                non_english = ''.join([c for c in name if not re.match(r'[A-Za-z0-9_\-\s.]', c)])

                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="characters",
                    message="Non-English characters in composition name",
                    details=f"Composition '{name}' contains non-English characters: '{non_english}'",
                    fix_suggestion=f"Rename composition using only English characters",
                    composition_name=name
                ))

    def _check_audio_formats(self, aepx_data: Dict):
        """
        CRITICAL: Check audio file formats

        Plainly requirement: "Use .wav files; avoid .mp3 due to After Effects
        compatibility issues."
        """
        for layer in aepx_data.get('layers', []):
            layer_type = layer.get('type', '')
            source = layer.get('source', '')

            # Check if this is an audio layer
            if layer_type == 'audio' or source.lower().endswith(('.mp3', '.wav', '.aac', '.m4a')):
                if source.lower().endswith('.mp3'):
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="audio",
                        message="MP3 audio file detected",
                        details=f"Layer '{layer.get('name')}' uses MP3 audio which causes compatibility issues in Plainly",
                        fix_suggestion=f"Convert '{source}' to .wav format using audio conversion software",
                        layer_name=layer.get('name')
                    ))

    def _check_layer_naming_conventions(self, aepx_data: Dict):
        """
        WARNING: Check layer naming prefixes

        Plainly best practice: "Put a prefix in front of the layer name when
        naming layers that are planned to be dynamic."
        """
        # Map of layer types to expected prefixes
        prefix_map = {
            'text': 'txt_',
            'image': 'img_',
            'video': 'vid_',
            'audio': 'audio_'
        }

        for layer in aepx_data.get('layers', []):
            layer_type = layer.get('type', '').lower()
            name = layer.get('name', '')

            # Check if this is a dynamic layer type
            if layer_type in prefix_map:
                expected_prefix = prefix_map[layer_type]

                # Check if it has the expected prefix
                if not name.lower().startswith(expected_prefix.lower()):
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="naming",
                        message="Dynamic layer missing prefix",
                        details=f"Layer '{name}' is type '{layer_type}' but lacks '{expected_prefix}' prefix",
                        fix_suggestion=f"Rename to '{expected_prefix}{name}' to enable Plainly auto-parametrization",
                        layer_name=name
                    ))

    def _check_render_composition(self, aepx_data: Dict):
        """
        WARNING: Check render composition naming

        Plainly best practice: "Prefix rendering compositions with render_
        (example: render_final) to identify which composition Plainly uses
        for output."
        """
        compositions = aepx_data.get('compositions', [])
        render_comps = [c for c in compositions
                       if self.RENDER_COMP_PATTERN.match(c.get('name', ''))]

        if len(render_comps) == 0 and len(compositions) > 0:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="composition",
                message="No render composition found",
                details="No composition starts with 'render_' prefix. Plainly may not identify the output composition.",
                fix_suggestion="Rename your main output composition to 'render_final' or 'render_main'",
            ))
        elif len(render_comps) > 1:
            comp_names = ', '.join([c.get('name') for c in render_comps])
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="composition",
                message="Multiple render compositions found",
                details=f"Found {len(render_comps)} compositions with 'render_' prefix: {comp_names}",
                fix_suggestion="Ensure only your primary output composition is prefixed with 'render_'",
            ))

    def _check_effects_usage(self, aepx_data: Dict):
        """
        WARNING: Check effects usage

        Plainly best practice: "Effects destroy render times. If speed is
        important to you, try lowering the amount of effects/plugins to
        a minimum."
        """
        for layer in aepx_data.get('layers', []):
            effects = layer.get('effects', [])
            effect_count = len(effects)

            if effect_count > 10:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="effects",
                    message="Heavy effects usage detected",
                    details=f"Layer '{layer.get('name')}' has {effect_count} effects applied",
                    fix_suggestion="Consider pre-rendering this layer as .mp4 for better Plainly performance",
                    layer_name=layer.get('name')
                ))
            elif effect_count > 5:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="effects",
                    message="Moderate effects usage detected",
                    details=f"Layer '{layer.get('name')}' has {effect_count} effects",
                    fix_suggestion="Monitor render times. Pre-render as .mp4 if renders are slow.",
                    layer_name=layer.get('name')
                ))

    def _check_asset_formats(self, aepx_data: Dict):
        """
        WARNING: Check asset file formats

        Plainly best practice: "Convert Illustrator/Photoshop files to
        .png and .jpg formats."
        """
        unsupported_extensions = {
            '.ai': 'Adobe Illustrator',
            '.psd': 'Adobe Photoshop',
            '.eps': 'EPS'
        }

        for layer in aepx_data.get('layers', []):
            source = layer.get('source', '')
            if source:
                ext = Path(source).suffix.lower()

                if ext in unsupported_extensions:
                    format_name = unsupported_extensions[ext]
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="assets",
                        message=f"{format_name} file detected",
                        details=f"Layer '{layer.get('name')}' uses {ext} file: {source}",
                        fix_suggestion=f"Convert '{source}' to .png or .jpg format for better Plainly compatibility",
                        layer_name=layer.get('name')
                    ))

    def _check_performance_optimization(self, aepx_data: Dict):
        """
        INFO: Performance optimization suggestions

        Plainly best practices for performance optimization.
        """
        # Check total layer count
        layer_count = len(aepx_data.get('layers', []))
        if layer_count > 100:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="performance",
                message="High layer count detected",
                details=f"Composition has {layer_count} layers, which may impact render performance",
                fix_suggestion="Consider pre-composing related layers to reduce complexity and improve render times",
            ))

        # Check composition count
        comp_count = len(aepx_data.get('compositions', []))
        if comp_count > 20:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="performance",
                message="Many compositions detected",
                details=f"Project has {comp_count} compositions",
                fix_suggestion="Clean up unused pre-compositions to optimize project performance",
            ))

    def _generate_report(self) -> ValidationReport:
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

        # Ensure score doesn't go below 0
        score = max(0, score)

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

        # Determine validation status
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


def validate_aep_for_plainly(aep_path: str, aepx_data: Optional[Dict] = None) -> ValidationReport:
    """
    Convenience function to validate AEP file for Plainly compatibility

    Args:
        aep_path: Path to AEP file
        aepx_data: Optional parsed AEPX data

    Returns:
        ValidationReport with all findings
    """
    validator = PlainlyValidator()
    return validator.validate_aep(aep_path, aepx_data)
