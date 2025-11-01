"""
Plainly Auto-Fixer

Automatically fixes common Plainly compatibility issues in AEPX files.
"""

import re
import unicodedata
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class FixResult:
    """Result of an auto-fix operation"""
    success: bool
    fixed_count: int = 0
    changes: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    message: str = ""


class PlainlyAutoFixer:
    """
    Automatically fixes Plainly compatibility issues

    Capabilities:
    - Replaces non-English characters with English equivalents
    - Adds proper prefixes to layer names
    - Renames render compositions
    - Modifies AEPX data structure
    """

    # Character replacement map for common non-English characters
    CHAR_REPLACEMENTS = {
        # Latin Extended
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ý': 'y', 'ÿ': 'y',
        'ñ': 'n', 'ç': 'c',
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A',
        'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O', 'Ø': 'O',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
        'Ý': 'Y', 'Ÿ': 'Y',
        'Ñ': 'N', 'Ç': 'C',
        # Common symbols
        '–': '-', '—': '-', ''': "'", ''': "'", '"': '"', '"': '"',
        '…': '...',
        # Currency
        '€': 'EUR', '£': 'GBP', '¥': 'JPY',
    }

    # Layer type to prefix mapping
    LAYER_PREFIX_MAP = {
        'text': 'txt_',
        'image': 'img_',
        'video': 'vid_',
        'audio': 'audio_',
        'solid': 'color_'
    }

    def __init__(self):
        self.changes_made = []

    def fix_all_issues(self, aepx_data: Dict, issues: List[Any]) -> FixResult:
        """
        Fix all auto-fixable issues

        Args:
            aepx_data: Parsed AEPX data dictionary
            issues: List of ValidationIssue objects

        Returns:
            FixResult with summary of changes
        """
        self.changes_made = []
        total_fixed = 0
        errors = []

        # Group issues by category for efficient fixing
        critical_issues = [i for i in issues if i.severity.value == 'critical']
        warning_issues = [i for i in issues if i.severity.value == 'warning']

        # Fix critical issues first
        for issue in critical_issues:
            if issue.category == 'characters':
                result = self._fix_non_english_characters(aepx_data, issue)
                if result.success:
                    total_fixed += result.fixed_count
                    self.changes_made.extend(result.changes)
                else:
                    errors.extend(result.errors)

        # Fix warnings
        for issue in warning_issues:
            if issue.category == 'naming':
                result = self._fix_layer_naming(aepx_data, issue)
                if result.success:
                    total_fixed += result.fixed_count
                    self.changes_made.extend(result.changes)
                else:
                    errors.extend(result.errors)

            elif issue.category == 'composition':
                if 'No render composition found' in issue.message:
                    result = self._fix_render_composition(aepx_data)
                    if result.success:
                        total_fixed += result.fixed_count
                        self.changes_made.extend(result.changes)
                    else:
                        errors.extend(result.errors)

        return FixResult(
            success=len(errors) == 0,
            fixed_count=total_fixed,
            changes=self.changes_made,
            errors=errors,
            message=f"Fixed {total_fixed} issues" if total_fixed > 0 else "No fixable issues found"
        )

    def fix_single_issue(self, aepx_data: Dict, issue: Any) -> FixResult:
        """
        Fix a single specific issue

        Args:
            aepx_data: Parsed AEPX data dictionary
            issue: ValidationIssue object

        Returns:
            FixResult for this specific fix
        """
        self.changes_made = []

        if issue.category == 'characters':
            return self._fix_non_english_characters(aepx_data, issue)

        elif issue.category == 'naming':
            return self._fix_layer_naming(aepx_data, issue)

        elif issue.category == 'composition':
            if 'No render composition found' in issue.message:
                return self._fix_render_composition(aepx_data)

        return FixResult(
            success=False,
            message=f"Issue category '{issue.category}' is not auto-fixable"
        )

    def _fix_non_english_characters(self, aepx_data: Dict, issue: Any) -> FixResult:
        """Fix non-English characters in layer or composition names"""
        changes = []

        if issue.layer_name:
            # Fix layer name
            old_name = issue.layer_name
            new_name = self.sanitize_name(old_name)

            # Update in aepx_data
            for layer in aepx_data.get('layers', []):
                if layer.get('name') == old_name:
                    layer['name'] = new_name
                    changes.append({
                        'type': 'layer_rename',
                        'old_name': old_name,
                        'new_name': new_name,
                        'reason': 'Removed non-English characters'
                    })
                    break

        elif issue.composition_name:
            # Fix composition name
            old_name = issue.composition_name
            new_name = self.sanitize_name(old_name)

            # Update in aepx_data
            for comp in aepx_data.get('compositions', []):
                if comp.get('name') == old_name:
                    comp['name'] = new_name
                    changes.append({
                        'type': 'composition_rename',
                        'old_name': old_name,
                        'new_name': new_name,
                        'reason': 'Removed non-English characters'
                    })
                    break

        return FixResult(
            success=len(changes) > 0,
            fixed_count=len(changes),
            changes=changes,
            message=f"Fixed non-English characters: {changes[0]['old_name']} → {changes[0]['new_name']}" if changes else "No changes needed"
        )

    def _fix_layer_naming(self, aepx_data: Dict, issue: Any) -> FixResult:
        """Add proper prefix to layer name"""
        if not issue.layer_name:
            return FixResult(success=False, message="No layer name specified")

        changes = []
        old_name = issue.layer_name

        # Find the layer and its type
        for layer in aepx_data.get('layers', []):
            if layer.get('name') == old_name:
                layer_type = layer.get('type', '').lower()

                # Get appropriate prefix
                prefix = self.LAYER_PREFIX_MAP.get(layer_type, '')

                if prefix and not old_name.lower().startswith(prefix.lower()):
                    # Add prefix
                    new_name = prefix + old_name
                    layer['name'] = new_name

                    changes.append({
                        'type': 'layer_prefix_added',
                        'old_name': old_name,
                        'new_name': new_name,
                        'prefix': prefix,
                        'reason': f'Added {prefix} prefix for {layer_type} layer'
                    })
                    break

        return FixResult(
            success=len(changes) > 0,
            fixed_count=len(changes),
            changes=changes,
            message=f"Added prefix: {changes[0]['old_name']} → {changes[0]['new_name']}" if changes else "No changes needed"
        )

    def _fix_render_composition(self, aepx_data: Dict) -> FixResult:
        """Rename main composition to have render_ prefix"""
        changes = []
        compositions = aepx_data.get('compositions', [])

        if not compositions:
            return FixResult(success=False, message="No compositions found")

        # Find the first/main composition without render_ prefix
        for comp in compositions:
            name = comp.get('name', '')
            if not name.startswith('render_'):
                old_name = name
                new_name = f"render_{name}"
                comp['name'] = new_name

                changes.append({
                    'type': 'composition_rename',
                    'old_name': old_name,
                    'new_name': new_name,
                    'reason': 'Added render_ prefix for Plainly output identification'
                })
                break

        return FixResult(
            success=len(changes) > 0,
            fixed_count=len(changes),
            changes=changes,
            message=f"Renamed composition: {changes[0]['old_name']} → {changes[0]['new_name']}" if changes else "Already has render composition"
        )

    def sanitize_name(self, name: str) -> str:
        """
        Convert a name to use only English characters

        Args:
            name: Original name with potential non-English characters

        Returns:
            Sanitized name with only A-Z, a-z, 0-9, _, -, space, and .
        """
        # First pass: Replace known characters
        result = name
        for char, replacement in self.CHAR_REPLACEMENTS.items():
            result = result.replace(char, replacement)

        # Second pass: Use Unicode decomposition for remaining characters
        # This converts accented characters to base + accent, then we keep only base
        result = unicodedata.normalize('NFKD', result)
        result = ''.join([c for c in result if not unicodedata.combining(c)])

        # Third pass: Remove any remaining non-English characters
        # Keep only: A-Z, a-z, 0-9, _, -, space, .
        result = re.sub(r'[^A-Za-z0-9_\-\s.]', '', result)

        # Cleanup: Remove multiple spaces, trim
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    def get_fixable_categories(self) -> List[str]:
        """Return list of issue categories that can be auto-fixed"""
        return ['characters', 'naming', 'composition']

    def is_fixable(self, issue: Any) -> bool:
        """Check if an issue can be automatically fixed"""
        fixable_categories = self.get_fixable_categories()

        # Character issues are always fixable
        if issue.category == 'characters':
            return True

        # Naming issues are fixable if they're about missing prefixes
        if issue.category == 'naming':
            return 'prefix' in issue.message.lower()

        # Composition issues are fixable if it's about missing render comp
        if issue.category == 'composition':
            return 'no render composition' in issue.message.lower()

        # Audio format, effects, assets, performance are NOT auto-fixable
        # These require manual intervention (file conversion, pre-rendering, etc.)
        return False
