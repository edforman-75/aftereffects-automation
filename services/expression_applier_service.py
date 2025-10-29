"""
Expression Applier Service

Intelligently determines which expressions to apply to which layers based on
pattern detection, layer name analysis, and confidence scoring.

This service analyzes AEPX projects and recommends expressions for each layer
based on naming patterns, layer types, and standard variable definitions.

Key Features:
- Pattern matching for layer names (fuzzy and exact)
- Confidence scoring for expression recommendations
- Support for all standard variable types (team, score, event, player, media)
- Detection of conditional visibility patterns
- Player sequence detection
- Logo and image scaling recommendations
- Batch expression generation

Usage:
    >>> service = ExpressionApplierService(logger)
    >>> recommendations = service.analyze_project(aepx_path="project.aepx")
    >>> for rec in recommendations:
    ...     print(f"{rec.layer_name} -> {rec.variable_name} (confidence: {rec.confidence})")
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from enum import Enum
import xml.etree.ElementTree as ET

from services.base_service import BaseService, Result
from modules.expression_system import (
    StandardVariables,
    VariableDefinition,
    ExpressionGenerator,
    ExpressionTarget,
    LayerExpression
)


class LayerType(Enum):
    """Layer type classification."""
    TEXT = "text"
    SHAPE = "shape"
    IMAGE = "image"
    VIDEO = "video"
    SOLID = "solid"
    NULL = "null"
    UNKNOWN = "unknown"


class MatchConfidence(Enum):
    """Confidence level for expression recommendations."""
    EXACT = 1.0      # Perfect match
    HIGH = 0.9       # Very likely match
    GOOD = 0.75      # Likely match
    MEDIUM = 0.6     # Possible match
    LOW = 0.4        # Uncertain match


@dataclass
class ExpressionRecommendation:
    """
    Represents a recommended expression for a layer.

    Attributes:
        comp_name: Composition name
        layer_name: Layer name in composition
        layer_type: Type of layer (text, shape, image, etc.)
        variable_name: Matched standard variable name (without z prefix)
        variable: VariableDefinition object
        target: Expression target property
        expression: Generated expression code
        confidence: Confidence score (0.0-1.0)
        reason: Human-readable explanation of the match
    """
    comp_name: str
    layer_name: str
    layer_type: LayerType
    variable_name: str
    variable: VariableDefinition
    target: ExpressionTarget
    expression: str
    confidence: float
    reason: str

    def to_layer_expression(self) -> LayerExpression:
        """Convert to LayerExpression for AEPX writer."""
        return LayerExpression(
            comp_name=self.comp_name,
            layer_name=self.layer_name,
            target=self.target,
            expression=self.expression,
            enabled=True
        )


class ExpressionApplierService(BaseService):
    """
    Service for intelligently applying expressions to layers.

    Analyzes AEPX projects and recommends expressions based on:
    - Layer name pattern matching
    - Layer type detection
    - Standard variable definitions
    - Naming conventions and common patterns
    """

    def __init__(self, logger: logging.Logger, enhanced_logging=None):
        """
        Initialize the Expression Applier Service.

        Args:
            logger: Logger instance for logging operations
            enhanced_logging: EnhancedLoggingService instance (optional)
        """
        super().__init__(logger, enhanced_logging=enhanced_logging)
        self.expression_generator = ExpressionGenerator()
        self.all_variables = StandardVariables.get_all_variables()

        # Build lookup dictionaries
        self._build_variable_lookups()

        # Define common patterns
        self._define_patterns()

    def _build_variable_lookups(self):
        """Build lookup dictionaries for fast variable matching."""
        self.variable_by_name = {}
        self.variable_by_hard_card_name = {}

        for var in self.all_variables:
            self.variable_by_name[var.name.lower()] = var
            self.variable_by_hard_card_name[var.hard_card_name.lower()] = var

    def _define_patterns(self):
        """Define regex patterns for layer name matching."""
        # Team patterns
        self.team_patterns = [
            (r'^(home|away)Team(Name|Abbreviation|Rank|Color1|Color2)$', 1.0),
            (r'^(home|away)_?team_?(name|abbr|rank|color)s?$', 0.9),
            (r'^team[_\s]?(home|away)[_\s]?(name|abbr)?$', 0.8),
        ]

        # Score patterns
        self.score_patterns = [
            (r'^(home|away)TeamScore[1-5]?$', 1.0),
            (r'^(home|away)_?score[_\s]?[1-5]?$', 0.9),
            (r'^score[_\s]?(home|away)[_\s]?[1-5]?$', 0.8),
            (r'^(home|away)[_\s]?pts?[_\s]?[1-5]?$', 0.7),
        ]

        # Event patterns
        self.event_patterns = [
            (r'^event(Month|Day|Year|Time|City|State|Venue|Date).*$', 1.0),
            (r'^(date|time|city|state|venue|location)$', 0.8),
            (r'^game[_\s]?(date|time|city|venue)$', 0.8),
        ]

        # Player patterns (player1FirstName, player2LastName, etc.)
        self.player_patterns = [
            (r'^player(\d{1,2})(FirstName|LastName|FullName|Number|Position|Height|Weight|Year|Stats)$', 1.0),
            (r'^player[_\s]?(\d{1,2})[_\s]?(first|last|full)?[_\s]?(name|number|pos|stats?)$', 0.9),
            (r'^p(\d{1,2})[_\s]?(name|number|position)$', 0.8),
        ]

        # Status/control patterns
        self.status_patterns = [
            (r'^status(Text)?$', 1.0),
            (r'^(final|live|pregame)[_\s]?(badge|indicator|status)?$', 0.9),
            (r'^game[_\s]?status$', 0.8),
        ]

        # Logo patterns
        self.logo_patterns = [
            (r'^(home|away)TeamLogo(SingleColor)?$', 1.0),
            (r'^(home|away)[_\s]?logo[_\s]?(mono|single|color)?$', 0.9),
            (r'^(opponent|league)Logo$', 1.0),
            (r'^logo[_\s]?(home|away|opp|league)$', 0.8),
        ]

        # Image patterns
        self.image_patterns = [
            (r'^featuredImage[1-3]$', 1.0),
            (r'^featured[_\s]?image[_\s]?[1-3]?$', 0.9),
            (r'^hero[_\s]?image$', 0.7),
        ]

    def normalize_layer_name(self, name: str) -> str:
        """
        Normalize layer name for matching.

        Args:
            name: Original layer name

        Returns:
            Normalized name (lowercase, no special chars except underscore)
        """
        # Convert to lowercase
        normalized = name.lower()

        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(layer[_\s]?|txt[_\s]?|text[_\s]?|img[_\s]?)', '', normalized)
        normalized = re.sub(r'[_\s]?(copy|layer|txt|text)$', '', normalized)

        # Clean whitespace
        normalized = normalized.strip()

        return normalized

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using Levenshtein-like approach.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        if str1 == str2:
            return 1.0

        # Simple character-based similarity
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0

        # Count matching characters in order
        matches = 0
        i = j = 0
        while i < len(str1) and j < len(str2):
            if str1[i] == str2[j]:
                matches += 1
                i += 1
                j += 1
            elif len(str1) > len(str2):
                i += 1
            else:
                j += 1

        return matches / max_len

    def match_variable_exact(self, layer_name: str) -> Optional[Tuple[VariableDefinition, float]]:
        """
        Try exact match against variable names.

        Args:
            layer_name: Layer name to match

        Returns:
            Tuple of (VariableDefinition, confidence) or None
        """
        normalized = self.normalize_layer_name(layer_name)

        # Try exact match
        if normalized in self.variable_by_name:
            return (self.variable_by_name[normalized], MatchConfidence.EXACT.value)

        # Try with 'z' prefix (Hard Card name)
        if normalized in self.variable_by_hard_card_name:
            var = self.variable_by_hard_card_name[normalized]
            return (var, MatchConfidence.EXACT.value)

        return None

    def match_variable_fuzzy(self, layer_name: str) -> Optional[Tuple[VariableDefinition, float]]:
        """
        Try fuzzy match against variable names.

        Args:
            layer_name: Layer name to match

        Returns:
            Tuple of (VariableDefinition, confidence) or None
        """
        normalized = self.normalize_layer_name(layer_name)

        best_match = None
        best_score = 0.0

        # Try fuzzy matching against all variables
        for var in self.all_variables:
            similarity = self.calculate_similarity(normalized, var.name.lower())

            # Require at least 70% similarity
            if similarity > 0.7 and similarity > best_score:
                best_score = similarity
                best_match = var

        if best_match:
            # Scale confidence based on similarity
            if best_score >= 0.95:
                confidence = MatchConfidence.HIGH.value
            elif best_score >= 0.85:
                confidence = MatchConfidence.GOOD.value
            elif best_score >= 0.75:
                confidence = MatchConfidence.MEDIUM.value
            else:
                confidence = MatchConfidence.LOW.value

            return (best_match, confidence)

        return None

    def match_variable_pattern(self, layer_name: str) -> Optional[Tuple[VariableDefinition, float, str]]:
        """
        Try pattern-based matching.

        Args:
            layer_name: Layer name to match

        Returns:
            Tuple of (VariableDefinition, confidence, reason) or None
        """
        normalized = self.normalize_layer_name(layer_name)

        # Try team patterns
        for pattern, base_confidence in self.team_patterns:
            match = re.match(pattern, layer_name, re.IGNORECASE)
            if match:
                # Extract variable name from pattern
                var_name = layer_name[0].lower() + layer_name[1:]  # camelCase
                var = StandardVariables.get_by_name(var_name)
                if var:
                    return (var, base_confidence, f"Matched team pattern: {pattern}")

        # Try score patterns
        for pattern, base_confidence in self.score_patterns:
            match = re.match(pattern, layer_name, re.IGNORECASE)
            if match:
                var_name = layer_name[0].lower() + layer_name[1:]
                var = StandardVariables.get_by_name(var_name)
                if var:
                    return (var, base_confidence, f"Matched score pattern: {pattern}")

        # Try event patterns
        for pattern, base_confidence in self.event_patterns:
            match = re.match(pattern, layer_name, re.IGNORECASE)
            if match:
                var_name = layer_name[0].lower() + layer_name[1:]
                var = StandardVariables.get_by_name(var_name)
                if var:
                    return (var, base_confidence, f"Matched event pattern: {pattern}")

        # Try player patterns
        for pattern, base_confidence in self.player_patterns:
            match = re.match(pattern, layer_name, re.IGNORECASE)
            if match:
                var_name = layer_name[0].lower() + layer_name[1:]
                var = StandardVariables.get_by_name(var_name)
                if var:
                    return (var, base_confidence, f"Matched player pattern: {pattern}")

        return None

    def detect_layer_type(self, layer_element: ET.Element) -> LayerType:
        """
        Detect layer type from XML element.

        Args:
            layer_element: Layer XML element

        Returns:
            LayerType enum value
        """
        layer_type_str = layer_element.get('type', 'unknown').lower()

        type_mapping = {
            'text': LayerType.TEXT,
            'shape': LayerType.SHAPE,
            'image': LayerType.IMAGE,
            'video': LayerType.VIDEO,
            'solid': LayerType.SOLID,
            'null': LayerType.NULL,
        }

        return type_mapping.get(layer_type_str, LayerType.UNKNOWN)

    def determine_expression_target(
        self,
        layer_type: LayerType,
        variable: VariableDefinition
    ) -> ExpressionTarget:
        """
        Determine appropriate expression target based on layer type and variable.

        Args:
            layer_type: Type of layer
            variable: Variable definition

        Returns:
            ExpressionTarget enum value
        """
        # Text layers -> sourceText
        if layer_type == LayerType.TEXT:
            return ExpressionTarget.TEXT_SOURCE

        # Shape layers with color variables -> fillColor
        if layer_type == LayerType.SHAPE:
            if variable.data_type == 'color':
                return ExpressionTarget.COLOR
            else:
                # Status badges often use opacity for visibility
                return ExpressionTarget.OPACITY

        # Image/logo layers -> scale
        if layer_type in [LayerType.IMAGE, LayerType.VIDEO]:
            if variable.data_type in ['logo', 'image']:
                return ExpressionTarget.SCALE
            else:
                return ExpressionTarget.OPACITY

        # Default to opacity for visibility control
        return ExpressionTarget.OPACITY

    def generate_expression_for_match(
        self,
        variable: VariableDefinition,
        target: ExpressionTarget,
        layer_name: str
    ) -> str:
        """
        Generate appropriate expression for variable and target.

        Args:
            variable: Variable definition
            target: Expression target
            layer_name: Layer name (for context)

        Returns:
            Generated expression string
        """
        # Text source - simple link
        if target == ExpressionTarget.TEXT_SOURCE:
            return self.expression_generator.simple_text_link(variable_name=variable.name)

        # Scale for logos/images
        if target == ExpressionTarget.SCALE:
            if 'logo' in variable.name.lower():
                return self.expression_generator.logo_scaling_max_dimensions(500, 500)
            else:
                return self.expression_generator.image_scaling_fill_comp()

        # Color conversion
        if target == ExpressionTarget.COLOR:
            return self.expression_generator.hex_color_to_rgb(variable_name=variable.name)

        # Opacity for conditional visibility
        if target == ExpressionTarget.OPACITY:
            # Detect status-based visibility
            if 'final' in layer_name.lower():
                return self.expression_generator.conditional_visibility_text(
                    variable_name="statusText",
                    target_value="FINAL",
                    visible_when_match=True
                )
            elif 'live' in layer_name.lower():
                return self.expression_generator.conditional_visibility_text(
                    variable_name="statusText",
                    target_value="LIVE",
                    visible_when_match=True
                )
            else:
                # Default conditional visibility
                return self.expression_generator.conditional_visibility_text(
                    variable_name=variable.name,
                    target_value="",
                    visible_when_match=False
                )

        # Default: simple link (fallback)
        return self.expression_generator.simple_text_link(variable_name=variable.name)

    def analyze_layer(
        self,
        comp_name: str,
        layer_element: ET.Element
    ) -> Optional[ExpressionRecommendation]:
        """
        Analyze a single layer and recommend expression.

        Args:
            comp_name: Composition name
            layer_element: Layer XML element

        Returns:
            ExpressionRecommendation or None if no match found
        """
        layer_name = layer_element.get('name', '')
        if not layer_name:
            return None

        # Skip Hard_Card composition layers
        if comp_name == "Hard_Card":
            return None

        # Detect layer type
        layer_type = self.detect_layer_type(layer_element)

        # Try exact match first
        exact_match = self.match_variable_exact(layer_name)
        if exact_match:
            variable, confidence = exact_match
            target = self.determine_expression_target(layer_type, variable)
            expression = self.generate_expression_for_match(variable, target, layer_name)

            return ExpressionRecommendation(
                comp_name=comp_name,
                layer_name=layer_name,
                layer_type=layer_type,
                variable_name=variable.name,
                variable=variable,
                target=target,
                expression=expression,
                confidence=confidence,
                reason="Exact name match"
            )

        # Try pattern match
        pattern_match = self.match_variable_pattern(layer_name)
        if pattern_match:
            variable, confidence, reason = pattern_match
            target = self.determine_expression_target(layer_type, variable)
            expression = self.generate_expression_for_match(variable, target, layer_name)

            return ExpressionRecommendation(
                comp_name=comp_name,
                layer_name=layer_name,
                layer_type=layer_type,
                variable_name=variable.name,
                variable=variable,
                target=target,
                expression=expression,
                confidence=confidence,
                reason=reason
            )

        # Try fuzzy match
        fuzzy_match = self.match_variable_fuzzy(layer_name)
        if fuzzy_match:
            variable, confidence = fuzzy_match
            target = self.determine_expression_target(layer_type, variable)
            expression = self.generate_expression_for_match(variable, target, layer_name)

            return ExpressionRecommendation(
                comp_name=comp_name,
                layer_name=layer_name,
                layer_type=layer_type,
                variable_name=variable.name,
                variable=variable,
                target=target,
                expression=expression,
                confidence=confidence,
                reason=f"Fuzzy match (similarity: {confidence:.0%})"
            )

        # No match found
        return None

    def analyze_project(
        self,
        aepx_path: Optional[str] = None,
        aepx_xml: Optional[str] = None,
        min_confidence: float = 0.6
    ) -> Result:
        """
        Analyze entire AEPX project and recommend expressions for all layers.

        Args:
            aepx_path: Path to AEPX file
            aepx_xml: AEPX XML string
            min_confidence: Minimum confidence threshold (default: 0.6)

        Returns:
            Result containing list of ExpressionRecommendation objects

        Example:
            >>> service = ExpressionApplierService(logger)
            >>> result = service.analyze_project(aepx_path="project.aepx")
            >>> recommendations = result.get_data()['recommendations']
            >>> for rec in recommendations:
            ...     print(f"{rec.layer_name} -> {rec.variable_name}")
        """
        try:
            # Load AEPX
            if aepx_path:
                tree = ET.parse(aepx_path)
                root = tree.getroot()
            elif aepx_xml:
                root = ET.fromstring(aepx_xml)
            else:
                return Result.failure("Must provide either aepx_path or aepx_xml")

            # XML namespace
            ns_prefix = '{http://www.adobe.com/products/aftereffects}'

            recommendations = []

            # Find all compositions
            comps = list(root.iter(f'{ns_prefix}Composition'))
            if not comps:
                comps = list(root.iter('Composition'))

            self.logger.info(f"Analyzing {len(comps)} compositions")

            # Analyze each composition
            for comp in comps:
                comp_name = comp.get('name', 'Unknown')

                # Find layers container
                layers_container = comp.find(f'{ns_prefix}Layers')
                if layers_container is None:
                    layers_container = comp.find('Layers')

                if layers_container is None:
                    continue

                # Get all layers
                layer_elements = list(layers_container.findall(f'{ns_prefix}Layer'))
                if not layer_elements:
                    layer_elements = list(layers_container.findall('Layer'))

                # Analyze each layer
                for layer_element in layer_elements:
                    recommendation = self.analyze_layer(comp_name, layer_element)

                    if recommendation and recommendation.confidence >= min_confidence:
                        recommendations.append(recommendation)
                        self.logger.debug(
                            f"Recommended: {comp_name}/{recommendation.layer_name} -> "
                            f"{recommendation.variable_name} ({recommendation.confidence:.0%})"
                        )

            self.logger.info(
                f"Found {len(recommendations)} expression recommendations "
                f"(min confidence: {min_confidence:.0%})"
            )

            return Result.success({
                'recommendations': recommendations,
                'count': len(recommendations),
                'message': f"Found {len(recommendations)} recommendations"
            })

        except Exception as e:
            self.logger.error(f"Failed to analyze project: {e}")
            return Result.failure(str(e))

    def filter_recommendations(
        self,
        recommendations: List[ExpressionRecommendation],
        min_confidence: Optional[float] = None,
        layer_types: Optional[List[LayerType]] = None,
        comp_names: Optional[List[str]] = None
    ) -> List[ExpressionRecommendation]:
        """
        Filter recommendations by various criteria.

        Args:
            recommendations: List of recommendations to filter
            min_confidence: Minimum confidence threshold
            layer_types: List of layer types to include
            comp_names: List of composition names to include

        Returns:
            Filtered list of recommendations
        """
        filtered = recommendations

        if min_confidence is not None:
            filtered = [r for r in filtered if r.confidence >= min_confidence]

        if layer_types:
            filtered = [r for r in filtered if r.layer_type in layer_types]

        if comp_names:
            filtered = [r for r in filtered if r.comp_name in comp_names]

        return filtered

    def group_by_confidence(
        self,
        recommendations: List[ExpressionRecommendation]
    ) -> Dict[str, List[ExpressionRecommendation]]:
        """
        Group recommendations by confidence level.

        Args:
            recommendations: List of recommendations

        Returns:
            Dictionary mapping confidence levels to recommendations
        """
        groups = {
            'exact': [],
            'high': [],
            'good': [],
            'medium': [],
            'low': []
        }

        for rec in recommendations:
            if rec.confidence >= MatchConfidence.EXACT.value:
                groups['exact'].append(rec)
            elif rec.confidence >= MatchConfidence.HIGH.value:
                groups['high'].append(rec)
            elif rec.confidence >= MatchConfidence.GOOD.value:
                groups['good'].append(rec)
            elif rec.confidence >= MatchConfidence.MEDIUM.value:
                groups['medium'].append(rec)
            else:
                groups['low'].append(rec)

        return groups

    def export_recommendations_to_dict(
        self,
        recommendations: List[ExpressionRecommendation]
    ) -> List[Dict]:
        """
        Export recommendations to dictionary format.

        Args:
            recommendations: List of recommendations

        Returns:
            List of dictionaries
        """
        return [
            {
                'comp_name': rec.comp_name,
                'layer_name': rec.layer_name,
                'layer_type': rec.layer_type.value,
                'variable_name': rec.variable_name,
                'target': rec.target.value,
                'confidence': rec.confidence,
                'reason': rec.reason,
                'expression': rec.expression[:100] + '...' if len(rec.expression) > 100 else rec.expression
            }
            for rec in recommendations
        ]
