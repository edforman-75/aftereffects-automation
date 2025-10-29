"""
AEPX Expression Writer

Modifies AEPX XML files to add expressions to layers.
This module reads AEPX project files, finds specific layers and properties,
and adds/modifies JavaScript expressions that make the layers dynamic.

Key Features:
- Add expressions to any layer property (text, opacity, scale, position, color)
- Batch add multiple expressions
- Remove expressions from layers
- Validate expression syntax (balanced braces, parentheses, valid JS)
- Find layers that have expressions
- Export expressions to JSON for debugging

Usage:
    >>> from modules.expression_system import AEPXExpressionWriter, ExpressionTarget
    >>> writer = AEPXExpressionWriter(logger, aepx_path="project.aepx")
    >>> result = writer.add_expression_to_layer(
    ...     comp_name="Main_Comp",
    ...     layer_name="homeTeamName",
    ...     target=ExpressionTarget.TEXT_SOURCE,
    ...     expression='comp("Hard_Card").layer("zhomeTeamName").text.sourceText'
    ... )
"""

import logging
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from services.base_service import Result


class ExpressionTarget(Enum):
    """
    Property types that can have expressions.

    Each enum value corresponds to an After Effects layer property
    that can be controlled via JavaScript expressions.

    Values:
        TEXT_SOURCE: Text layer content (sourceText)
        OPACITY: Layer opacity (0-100)
        SCALE: Layer scale (percentage)
        POSITION: Layer position (x, y pixels)
        COLOR: Fill color (RGBA values)
        ROTATION: Layer rotation (degrees)
        ANCHOR_POINT: Layer anchor point (x, y pixels)
    """
    TEXT_SOURCE = "sourceText"
    OPACITY = "opacity"
    SCALE = "scale"
    POSITION = "position"
    COLOR = "fillColor"
    ROTATION = "rotation"
    ANCHOR_POINT = "anchorPoint"


@dataclass
class LayerExpression:
    """
    Represents an expression applied to a layer property.

    Attributes:
        comp_name: Name of the composition containing the layer
        layer_name: Name of the layer
        target: Property type (from ExpressionTarget enum)
        expression: JavaScript expression code
        enabled: Whether the expression is active (default: True)

    Example:
        >>> expr = LayerExpression(
        ...     comp_name="Main_Comp",
        ...     layer_name="homeTeamName",
        ...     target=ExpressionTarget.TEXT_SOURCE,
        ...     expression='comp("Hard_Card").layer("zhomeTeamName").text.sourceText',
        ...     enabled=True
        ... )
    """
    comp_name: str
    layer_name: str
    target: ExpressionTarget
    expression: str
    enabled: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        return {
            'comp_name': self.comp_name,
            'layer_name': self.layer_name,
            'target': self.target.value,
            'expression': self.expression,
            'enabled': self.enabled
        }


class AEPXExpressionWriter:
    """
    Writes expressions to AEPX project files.

    This class provides methods to modify AEPX XML files, adding JavaScript
    expressions to layer properties. It can parse existing AEPX files,
    locate specific layers and properties, and insert/modify expression elements.

    The AEPX format is Adobe After Effects' XML-based project format.
    This implementation handles a simplified subset suitable for
    parametrized templates.

    Usage:
        >>> writer = AEPXExpressionWriter(logger, aepx_path="project.aepx")
        >>> writer.add_expression_to_layer(
        ...     comp_name="Main_Comp",
        ...     layer_name="teamName",
        ...     target=ExpressionTarget.TEXT_SOURCE,
        ...     expression='comp("Hard_Card").layer("zteamName").text.sourceText'
        ... )
    """

    def __init__(
        self,
        logger: logging.Logger,
        aepx_path: Optional[str] = None,
        aepx_xml: Optional[str] = None
    ):
        """
        Initialize the AEPX Expression Writer.

        Args:
            logger: Logger instance for logging operations
            aepx_path: Path to AEPX file to modify (optional)
            aepx_xml: AEPX XML string to modify (optional)

        Note: Must provide either aepx_path or aepx_xml
        """
        self.logger = logger
        self.aepx_path = aepx_path
        self.aepx_xml = aepx_xml
        self.tree = None
        self.root = None

        # XML namespace for After Effects
        self.namespace = {'ae': 'http://www.adobe.com/products/aftereffects'}
        self.ns_prefix = '{http://www.adobe.com/products/aftereffects}'

        # Track expressions for reporting
        self.expressions_added: List[LayerExpression] = []
        self.expressions_removed: List[Tuple[str, str, ExpressionTarget]] = []

        if aepx_path:
            self._load_from_file(aepx_path)
        elif aepx_xml:
            self._load_from_string(aepx_xml)

    def _load_from_file(self, path: str) -> None:
        """Load AEPX XML from file."""
        try:
            self.tree = ET.parse(path)
            self.root = self.tree.getroot()
            self.logger.info(f"Loaded AEPX file: {path}")
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse AEPX XML: {e}")
            raise
        except FileNotFoundError:
            self.logger.error(f"AEPX file not found: {path}")
            raise

    def _load_from_string(self, xml_string: str) -> None:
        """Load AEPX XML from string."""
        try:
            self.root = ET.fromstring(xml_string)
            self.tree = ET.ElementTree(self.root)
            self.logger.info("Loaded AEPX from XML string")
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse AEPX XML string: {e}")
            raise

    def _find_composition(self, comp_name: str) -> Optional[ET.Element]:
        """
        Find composition element by name.

        Args:
            comp_name: Name of composition to find

        Returns:
            Element if found, None otherwise
        """
        if self.root is None:
            return None

        # Search for Composition elements (with namespace)
        for comp in self.root.iter(f'{self.ns_prefix}Composition'):
            if comp.get('name') == comp_name:
                self.logger.debug(f"Found composition: {comp_name}")
                return comp

        # Also try without namespace for compatibility
        for comp in self.root.iter('Composition'):
            if comp.get('name') == comp_name:
                self.logger.debug(f"Found composition (no ns): {comp_name}")
                return comp

        self.logger.warning(f"Composition not found: {comp_name}")
        return None

    def _find_layer_in_comp(
        self,
        comp_element: ET.Element,
        layer_name: str
    ) -> Optional[ET.Element]:
        """
        Find layer element within a composition by name.

        Args:
            comp_element: Composition XML element
            layer_name: Name of layer to find

        Returns:
            Layer element if found, None otherwise
        """
        # Find Layers container (try with and without namespace)
        layers_container = comp_element.find(f'{self.ns_prefix}Layers')
        if layers_container is None:
            layers_container = comp_element.find('Layers')

        if layers_container is None:
            self.logger.warning("No Layers element in composition")
            return None

        # Search for Layer with matching name (try with namespace first)
        for layer in layers_container.findall(f'{self.ns_prefix}Layer'):
            if layer.get('name') == layer_name:
                self.logger.debug(f"Found layer: {layer_name}")
                return layer

        # Try without namespace
        for layer in layers_container.findall('Layer'):
            if layer.get('name') == layer_name:
                self.logger.debug(f"Found layer (no ns): {layer_name}")
                return layer

        self.logger.warning(f"Layer not found: {layer_name}")
        return None

    def _find_property_in_layer(
        self,
        layer_element: ET.Element,
        property_name: str
    ) -> Optional[ET.Element]:
        """
        Find property element within a layer by name.

        Args:
            layer_element: Layer XML element
            property_name: Name of property to find

        Returns:
            Property element if found, None otherwise
        """
        # Try with namespace first
        for prop in layer_element.findall(f'{self.ns_prefix}Property'):
            if prop.get('name') == property_name:
                self.logger.debug(f"Found property: {property_name}")
                return prop

        # Try without namespace
        for prop in layer_element.findall('Property'):
            if prop.get('name') == property_name:
                self.logger.debug(f"Found property (no ns): {property_name}")
                return prop

        self.logger.debug(f"Property not found: {property_name}")
        return None

    def _escape_expression_for_xml(self, expression: str) -> str:
        """
        Escape expression code for XML CDATA.

        Args:
            expression: JavaScript expression code

        Returns:
            XML-safe expression string
        """
        # Remove any existing CDATA markers
        expression = expression.replace('<![CDATA[', '').replace(']]>', '')

        # Wrap in CDATA section for XML safety
        return f'<![CDATA[{expression}]]>'

    def validate_expression_syntax(self, expression: str) -> Result:
        """
        Validate JavaScript expression syntax.

        Checks for common syntax errors:
        - Balanced braces {}
        - Balanced parentheses ()
        - Balanced brackets []
        - Valid variable declarations
        - No unterminated strings

        Args:
            expression: JavaScript expression to validate

        Returns:
            Result indicating success or syntax errors

        Example:
            >>> result = writer.validate_expression_syntax('var x = 5;')
            >>> result.is_success()
            True
            >>> result = writer.validate_expression_syntax('var x = 5;)')
            >>> result.is_success()
            False
        """
        errors = []

        # Check balanced braces
        brace_count = expression.count('{') - expression.count('}')
        if brace_count != 0:
            errors.append(f"Unbalanced braces: {brace_count} unclosed")

        # Check balanced parentheses
        paren_count = expression.count('(') - expression.count(')')
        if paren_count != 0:
            errors.append(f"Unbalanced parentheses: {paren_count} unclosed")

        # Check balanced brackets
        bracket_count = expression.count('[') - expression.count(']')
        if bracket_count != 0:
            errors.append(f"Unbalanced brackets: {bracket_count} unclosed")

        # Check for unterminated strings (basic check)
        # Count quotes not preceded by backslash
        single_quotes = len(re.findall(r"(?<!\\)'", expression))
        double_quotes = len(re.findall(r'(?<!\\)"', expression))

        if single_quotes % 2 != 0:
            errors.append("Unterminated single quote string")
        if double_quotes % 2 != 0:
            errors.append("Unterminated double quote string")

        # Check for valid variable declarations
        var_pattern = r'\bvar\s+\w+\s*='
        if 'var ' in expression:
            if not re.search(var_pattern, expression):
                errors.append("Invalid variable declaration syntax")

        # Report results
        if errors:
            self.logger.warning(f"Expression syntax validation failed: {errors}")
            return Result.failure({
                'errors': errors,
                'message': f"Syntax validation failed: {len(errors)} error(s)"
            })

        self.logger.debug("Expression syntax validation passed")
        return Result.success({'message': "Syntax validation passed"})

    def add_expression_to_layer(
        self,
        comp_name: str,
        layer_name: str,
        target: ExpressionTarget,
        expression: str,
        validate: bool = True
    ) -> Result:
        """
        Add expression to a specific layer property.

        Locates the layer within the composition and adds/updates
        the expression element for the specified property.

        Args:
            comp_name: Name of composition containing the layer
            layer_name: Name of layer to add expression to
            target: Property to add expression to (ExpressionTarget enum)
            expression: JavaScript expression code
            validate: Whether to validate syntax before adding (default: True)

        Returns:
            Result indicating success or failure

        Example:
            >>> result = writer.add_expression_to_layer(
            ...     comp_name="Main_Comp",
            ...     layer_name="teamName",
            ...     target=ExpressionTarget.TEXT_SOURCE,
            ...     expression='comp("Hard_Card").layer("zteamName").text.sourceText'
            ... )
        """
        if self.root is None:
            return Result.failure("No AEPX data loaded")

        # Validate expression syntax if requested
        if validate:
            validation_result = self.validate_expression_syntax(expression)
            if not validation_result.is_success():
                return Result.failure(
                    f"Expression syntax validation failed: {validation_result.error}"
                )

        # Find composition
        comp = self._find_composition(comp_name)
        if comp is None:
            return Result.failure(f"Composition not found: {comp_name}")

        # Find layer
        layer = self._find_layer_in_comp(comp, layer_name)
        if layer is None:
            return Result.failure(f"Layer not found: {layer_name} in {comp_name}")

        # Find or create property
        property_name = target.value
        prop = self._find_property_in_layer(layer, property_name)

        if prop is None:
            # Create new property element
            prop = ET.SubElement(layer, 'Property')
            prop.set('name', property_name)
            self.logger.debug(f"Created new property: {property_name}")

        # Add/update expression element
        expr_elem = prop.find('Expression')
        if expr_elem is None:
            expr_elem = ET.SubElement(prop, 'Expression')

        # Set expression text (wrapped in CDATA)
        expr_elem.text = self._escape_expression_for_xml(expression)

        # Track the addition
        layer_expr = LayerExpression(
            comp_name=comp_name,
            layer_name=layer_name,
            target=target,
            expression=expression,
            enabled=True
        )
        self.expressions_added.append(layer_expr)

        self.logger.info(
            f"Added expression to {comp_name}/{layer_name}/{property_name}"
        )

        return Result.success({
            'comp_name': comp_name,
            'layer_name': layer_name,
            'target': property_name,
            'message': f"Expression added successfully to {layer_name}"
        })

    def add_multiple_expressions(
        self,
        expressions: List[LayerExpression],
        validate: bool = True,
        stop_on_error: bool = False
    ) -> Result:
        """
        Add multiple expressions in batch.

        Args:
            expressions: List of LayerExpression objects to add
            validate: Whether to validate each expression (default: True)
            stop_on_error: Stop on first error or continue (default: False)

        Returns:
            Result with summary of successes and failures

        Example:
            >>> expressions = [
            ...     LayerExpression("Main", "team1", ExpressionTarget.TEXT_SOURCE, "..."),
            ...     LayerExpression("Main", "team2", ExpressionTarget.TEXT_SOURCE, "...")
            ... ]
            >>> result = writer.add_multiple_expressions(expressions)
        """
        if self.root is None:
            return Result.failure("No AEPX data loaded")

        successes = []
        failures = []

        for expr in expressions:
            result = self.add_expression_to_layer(
                comp_name=expr.comp_name,
                layer_name=expr.layer_name,
                target=expr.target,
                expression=expr.expression,
                validate=validate
            )

            if result.is_success():
                successes.append(expr.layer_name)
            else:
                failures.append({
                    'layer': expr.layer_name,
                    'error': result.error
                })
                if stop_on_error:
                    break

        # Report results
        if failures and stop_on_error:
            self.logger.error(
                f"Batch add stopped on error: {successes} succeeded, "
                f"{len(failures)} failed"
            )
            return Result.failure({
                'successes': successes,
                'failures': failures,
                'message': f"Stopped after {len(successes)} successes, 1 failure"
            })

        if failures:
            self.logger.warning(
                f"Batch add completed with errors: {len(successes)} succeeded, "
                f"{len(failures)} failed"
            )
            return Result.success({
                'successes': successes,
                'failures': failures,
                'message': f"{len(successes)} succeeded, {len(failures)} failed"
            })

        self.logger.info(f"Batch add completed: {len(successes)} expressions added")
        return Result.success({
            'successes': successes,
            'message': f"All {len(successes)} expressions added successfully"
        })

    def remove_expression_from_layer(
        self,
        comp_name: str,
        layer_name: str,
        target: ExpressionTarget
    ) -> Result:
        """
        Remove expression from a layer property.

        Args:
            comp_name: Name of composition
            layer_name: Name of layer
            target: Property to remove expression from

        Returns:
            Result indicating success or failure

        Example:
            >>> result = writer.remove_expression_from_layer(
            ...     comp_name="Main_Comp",
            ...     layer_name="teamName",
            ...     target=ExpressionTarget.TEXT_SOURCE
            ... )
        """
        if self.root is None:
            return Result.failure("No AEPX data loaded")

        # Find composition
        comp = self._find_composition(comp_name)
        if comp is None:
            return Result.failure(f"Composition not found: {comp_name}")

        # Find layer
        layer = self._find_layer_in_comp(comp, layer_name)
        if layer is None:
            return Result.failure(f"Layer not found: {layer_name}")

        # Find property
        property_name = target.value
        prop = self._find_property_in_layer(layer, property_name)

        if prop is None:
            return Result.failure(
                f"Property not found: {property_name} on layer {layer_name}"
            )

        # Find and remove expression
        expr_elem = prop.find('Expression')
        if expr_elem is None:
            return Result.failure(
                f"No expression found on {layer_name}/{property_name}"
            )

        prop.remove(expr_elem)

        # Track the removal
        self.expressions_removed.append((comp_name, layer_name, target))

        self.logger.info(
            f"Removed expression from {comp_name}/{layer_name}/{property_name}"
        )

        return Result.success({
            'comp_name': comp_name,
            'layer_name': layer_name,
            'target': property_name,
            'message': f"Expression removed from {layer_name}"
        })

    def find_layers_with_expressions(
        self,
        comp_name: Optional[str] = None
    ) -> Result:
        """
        Find all layers that have expressions.

        Args:
            comp_name: Optional composition name to search within.
                      If None, searches all compositions.

        Returns:
            Result containing list of layers with expressions

        Example:
            >>> result = writer.find_layers_with_expressions()
            >>> for layer_info in result.data['layers']:
            ...     print(f"{layer_info['comp']}/{layer_info['layer']}")
        """
        if self.root is None:
            return Result.failure("No AEPX data loaded")

        layers_with_expressions = []

        # Determine which compositions to search
        if comp_name:
            comps = [self._find_composition(comp_name)]
            if comps[0] is None:
                return Result.failure(f"Composition not found: {comp_name}")
        else:
            # Try with namespace first
            comps = list(self.root.iter(f'{self.ns_prefix}Composition'))
            if not comps:
                comps = list(self.root.iter('Composition'))

        # Search each composition
        for comp in comps:
            comp_name_found = comp.get('name', 'Unknown')

            # Find layers container (with or without namespace)
            layers_container = comp.find(f'{self.ns_prefix}Layers')
            if layers_container is None:
                layers_container = comp.find('Layers')

            if layers_container is None:
                continue

            # Check each layer (try with namespace first)
            layer_elements = list(layers_container.findall(f'{self.ns_prefix}Layer'))
            if not layer_elements:
                layer_elements = list(layers_container.findall('Layer'))

            for layer in layer_elements:
                layer_name = layer.get('name', 'Unknown')

                # Check each property for expressions (try with namespace first)
                prop_elements = list(layer.findall(f'{self.ns_prefix}Property'))
                if not prop_elements:
                    prop_elements = list(layer.findall('Property'))

                for prop in prop_elements:
                    # Find Expression element (try with namespace first)
                    expr = prop.find(f'{self.ns_prefix}Expression')
                    if expr is None:
                        expr = prop.find('Expression')

                    if expr is not None:
                        property_name = prop.get('name', 'Unknown')
                        expression_text = expr.text or ''

                        # Remove CDATA markers for readability
                        expression_text = expression_text.replace('<![CDATA[', '')
                        expression_text = expression_text.replace(']]>', '')

                        layers_with_expressions.append({
                            'comp': comp_name_found,
                            'layer': layer_name,
                            'property': property_name,
                            'expression': expression_text.strip()
                        })

        self.logger.info(
            f"Found {len(layers_with_expressions)} layers with expressions"
        )

        return Result.success({
            'count': len(layers_with_expressions),
            'layers': layers_with_expressions,
            'message': f"Found {len(layers_with_expressions)} layers with expressions"
        })

    def export_expressions_to_json(
        self,
        output_path: str,
        comp_name: Optional[str] = None
    ) -> Result:
        """
        Export all expressions to JSON file for debugging.

        Args:
            output_path: Path to output JSON file
            comp_name: Optional composition to export (None = all)

        Returns:
            Result indicating success or failure

        Example:
            >>> result = writer.export_expressions_to_json('expressions.json')
        """
        # Find all expressions
        find_result = self.find_layers_with_expressions(comp_name)

        if not find_result.is_success():
            return find_result

        # Get data from result
        data = find_result.get_data()
        if data is None:
            return Result.failure("No data returned from find_layers_with_expressions")

        # Write to JSON
        try:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"Exported expressions to {output_path}")
            return Result.success({
                'output_path': output_path,
                'count': data.get('count', 0),
                'message': f"Exported {data.get('count', 0)} expressions"
            })

        except Exception as e:
            self.logger.error(f"Failed to export expressions: {e}")
            return Result.failure(str(e))

    def save_to_file(self, output_path: Optional[str] = None) -> Result:
        """
        Save modified AEPX to file.

        Args:
            output_path: Path to save to. If None, overwrites original file.

        Returns:
            Result indicating success or failure

        Example:
            >>> writer.add_expression_to_layer(...)
            >>> writer.save_to_file('modified_project.aepx')
        """
        if self.tree is None or self.root is None:
            return Result.failure("No AEPX data loaded")

        # Determine output path
        save_path = output_path or self.aepx_path

        if save_path is None:
            return Result.failure("No output path specified and no original file path")

        try:
            # Write the tree to file
            self.tree.write(save_path, encoding='utf-8', xml_declaration=True)

            self.logger.info(f"Saved AEPX to {save_path}")
            return Result.success({
                'output_path': save_path,
                'message': f"Saved to {save_path}"
            })

        except Exception as e:
            self.logger.error(f"Failed to save AEPX: {e}")
            return Result.failure(str(e))

    def to_string(self) -> str:
        """
        Export modified AEPX as XML string.

        Returns:
            XML string representation
        """
        if self.tree is None or self.root is None:
            return ""

        return ET.tostring(self.root, encoding='unicode', method='xml')

    def get_statistics(self) -> Dict:
        """
        Get statistics about expressions added/removed.

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = writer.get_statistics()
            >>> print(f"Added: {stats['expressions_added']}")
        """
        return {
            'expressions_added': len(self.expressions_added),
            'expressions_removed': len(self.expressions_removed),
            'added_by_comp': self._group_by_comp(self.expressions_added),
            'removed_by_comp': self._group_by_comp_removed(self.expressions_removed)
        }

    def _group_by_comp(self, expressions: List[LayerExpression]) -> Dict[str, int]:
        """Group expressions by composition name."""
        grouped = {}
        for expr in expressions:
            grouped[expr.comp_name] = grouped.get(expr.comp_name, 0) + 1
        return grouped

    def _group_by_comp_removed(
        self,
        removals: List[Tuple[str, str, ExpressionTarget]]
    ) -> Dict[str, int]:
        """Group removals by composition name."""
        grouped = {}
        for comp_name, _, _ in removals:
            grouped[comp_name] = grouped.get(comp_name, 0) + 1
        return grouped
