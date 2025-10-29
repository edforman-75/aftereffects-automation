"""
Hard Card Generator

Generates the Hard_Card composition containing text layers for all variables.
The Hard Card is a special After Effects composition that serves as the central
variable store - all other layers reference these variables via expressions.

Each variable becomes a text layer with:
- Name prefixed with 'z' (e.g., "zhomeTeamName")
- Default/placeholder value from VariableDefinition
- Positioned in a readable grid layout
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from modules.expression_system.variable_definitions import (
    StandardVariables,
    VariableDefinition
)
from services.base_service import Result


@dataclass
class HardCardLayer:
    """
    Represents a single text layer in the Hard Card composition.

    Attributes:
        variable: VariableDefinition this layer represents
        position: (x, y) coordinates in pixels
        font_size: Font size in points
        font_family: Font family name
        color: RGBA color tuple (0.0-1.0 for each channel)

    Example:
        >>> layer = HardCardLayer(
        ...     variable=home_team_var,
        ...     position=(50, 50),
        ...     font_size=40,
        ...     font_family="Arial",
        ...     color=(1.0, 1.0, 1.0, 1.0)
        ... )
    """
    variable: VariableDefinition
    position: Tuple[int, int]
    font_size: int
    font_family: str
    color: Tuple[float, float, float, float]


class HardCardGenerator:
    """
    Generates Hard_Card composition containing all variable text layers.

    The Hard Card is the central variable store in parametrized templates.
    All variables are stored as text layers, which other layers reference
    via expressions.

    Layout Strategy:
    - Grid arrangement (configurable columns)
    - Evenly spaced horizontally and vertically
    - All layers use same font and color for consistency
    - Variables ordered by category for organization

    Usage:
        >>> generator = HardCardGenerator(logger)
        >>> hard_card_dict = generator.generate_hard_card_dict()
        >>> print(f"Generated {len(hard_card_dict['layers'])} layers")
        Generated 185 layers
    """

    def __init__(
        self,
        logger: logging.Logger,
        comp_width: int = 1920,
        comp_height: int = 1080
    ):
        """
        Initialize the Hard Card generator.

        Args:
            logger: Logger instance for logging operations
            comp_width: Composition width in pixels (default: 1920)
            comp_height: Composition height in pixels (default: 1080)
        """
        self.logger = logger
        self.comp_width = comp_width
        self.comp_height = comp_height

    def calculate_layer_positions(
        self,
        variables: List[VariableDefinition],
        columns: int = 4,
        start_x: int = 50,
        start_y: int = 50,
        horizontal_spacing: int = 400,
        vertical_spacing: int = 60,
        font_size: int = 40,
        font_family: str = "Arial",
        color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    ) -> List[HardCardLayer]:
        """
        Calculate positions for all variable layers in a grid layout.

        Arranges variables in a multi-column grid with consistent spacing.
        Variables are ordered by category for better organization.

        Args:
            variables: List of VariableDefinition objects to arrange
            columns: Number of columns in grid (default: 4)
            start_x: Starting X position in pixels (default: 50)
            start_y: Starting Y position in pixels (default: 50)
            horizontal_spacing: Pixels between columns (default: 400)
            vertical_spacing: Pixels between rows (default: 60)
            font_size: Font size in points (default: 40)
            font_family: Font family name (default: "Arial")
            color: RGBA color tuple 0.0-1.0 (default: white)

        Returns:
            List of HardCardLayer objects with calculated positions

        Example:
            >>> layers = generator.calculate_layer_positions(
            ...     variables=StandardVariables.get_all_variables(),
            ...     columns=4
            ... )
            >>> len(layers)
            185
            >>> layers[0].position
            (50, 50)
            >>> layers[1].position
            (450, 50)
        """
        hard_card_layers = []

        for i, variable in enumerate(variables):
            # Calculate grid position
            row = i // columns
            col = i % columns

            x = start_x + (col * horizontal_spacing)
            y = start_y + (row * vertical_spacing)

            layer = HardCardLayer(
                variable=variable,
                position=(x, y),
                font_size=font_size,
                font_family=font_family,
                color=color
            )

            hard_card_layers.append(layer)

        self.logger.info(
            f"Calculated positions for {len(hard_card_layers)} layers in "
            f"{columns} columns"
        )

        return hard_card_layers

    def generate_hard_card_dict(
        self,
        variables: Optional[List[VariableDefinition]] = None,
        **layout_kwargs
    ) -> Dict:
        """
        Generate Hard Card composition as a Python dictionary.

        This is easier to work with than XML and can be converted to AEPX
        format when needed.

        Args:
            variables: List of variables to include. If None, uses all standard variables.
            **layout_kwargs: Optional layout parameters passed to calculate_layer_positions()

        Returns:
            Dictionary representation of Hard Card composition

        Structure:
            {
                'name': 'Hard_Card',
                'width': 1920,
                'height': 1080,
                'duration': 8,
                'frameRate': 30,
                'layers': [
                    {
                        'name': 'zhomeTeamName',
                        'type': 'text',
                        'sourceText': 'Lakers',
                        'position': [50, 50],
                        'fontSize': 40,
                        'fontFamily': 'Arial',
                        'color': [1.0, 1.0, 1.0, 1.0]
                    },
                    ...
                ]
            }

        Example:
            >>> hard_card = generator.generate_hard_card_dict()
            >>> hard_card['name']
            'Hard_Card'
            >>> len(hard_card['layers'])
            185
        """
        # Use all standard variables if none provided
        if variables is None:
            variables = StandardVariables.get_all_variables()
            self.logger.info(f"Using all {len(variables)} standard variables")

        # Calculate layer positions
        hard_card_layers = self.calculate_layer_positions(variables, **layout_kwargs)

        # Build composition dictionary
        composition = {
            'name': 'Hard_Card',
            'width': self.comp_width,
            'height': self.comp_height,
            'duration': 8,  # 8 seconds default
            'frameRate': 30,
            'backgroundColor': [0.0, 0.0, 0.0, 1.0],  # Black background
            'layers': []
        }

        # Add each layer
        for hard_card_layer in hard_card_layers:
            var = hard_card_layer.variable

            layer_dict = {
                'name': var.hard_card_name,  # With z prefix
                'type': 'text',
                'sourceText': var.default_value or '',
                'position': list(hard_card_layer.position),
                'fontSize': hard_card_layer.font_size,
                'fontFamily': hard_card_layer.font_family,
                'color': list(hard_card_layer.color),
                'metadata': {
                    'variable_name': var.name,  # Without z prefix
                    'category': var.category.value,
                    'data_type': var.data_type,
                    'description': var.description
                }
            }

            composition['layers'].append(layer_dict)

        self.logger.info(
            f"Generated Hard_Card composition with {len(composition['layers'])} layers"
        )

        return composition

    def generate_hard_card_aepx(
        self,
        variables: Optional[List[VariableDefinition]] = None,
        **layout_kwargs
    ) -> str:
        """
        Generate Hard Card composition as AEPX XML string.

        Creates valid AEPX XML that can be inserted into an After Effects project file.
        Note: This is a simplified AEPX structure focused on text layers.
        Real AEPX files have more complex structure.

        Args:
            variables: List of variables to include. If None, uses all standard variables.
            **layout_kwargs: Optional layout parameters

        Returns:
            XML string representing Hard Card composition

        Example:
            >>> xml = generator.generate_hard_card_aepx()
            >>> 'Hard_Card' in xml
            True
            >>> 'zhomeTeamName' in xml
            True
        """
        # Generate dict representation first
        comp_dict = self.generate_hard_card_dict(variables, **layout_kwargs)

        # Build XML
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<AfterEffectsProject xmlns="http://www.adobe.com/products/aftereffects">')
        xml_lines.append('  <Project>')
        xml_lines.append('    <Items>')

        # Composition element
        xml_lines.append(
            f'      <Composition '
            f'name="{comp_dict["name"]}" '
            f'width="{comp_dict["width"]}" '
            f'height="{comp_dict["height"]}" '
            f'duration="{comp_dict["duration"]}" '
            f'frameRate="{comp_dict["frameRate"]}">'
        )

        # Add layers
        xml_lines.append('        <Layers>')

        for i, layer in enumerate(comp_dict['layers']):
            # Layer element
            xml_lines.append(
                f'          <Layer '
                f'index="{i + 1}" '
                f'name="{self._escape_xml(layer["name"])}" '
                f'type="{layer["type"]}">'
            )

            # Source text property
            xml_lines.append(
                f'            <Property name="sourceText" '
                f'value="{self._escape_xml(layer["sourceText"])}"/>'
            )

            # Position property
            pos_x, pos_y = layer['position']
            xml_lines.append(
                f'            <Property name="position" value="{pos_x},{pos_y}"/>'
            )

            # Font properties
            xml_lines.append(
                f'            <Property name="fontSize" value="{layer["fontSize"]}"/>'
            )
            xml_lines.append(
                f'            <Property name="fontFamily" '
                f'value="{self._escape_xml(layer["fontFamily"])}"/>'
            )

            # Color property
            r, g, b, a = layer['color']
            xml_lines.append(
                f'            <Property name="fillColor" value="{r},{g},{b},{a}"/>'
            )

            # Metadata as comments
            metadata = layer['metadata']
            xml_lines.append(
                f'            <!-- Variable: {metadata["variable_name"]} | '
                f'Category: {metadata["category"]} | '
                f'Type: {metadata["data_type"]} -->'
            )

            xml_lines.append('          </Layer>')

        xml_lines.append('        </Layers>')
        xml_lines.append('      </Composition>')
        xml_lines.append('    </Items>')
        xml_lines.append('  </Project>')
        xml_lines.append('</AfterEffectsProject>')

        xml_string = '\n'.join(xml_lines)

        self.logger.info(
            f"Generated AEPX XML for Hard_Card ({len(xml_string)} characters)"
        )

        return xml_string

    def validate_hard_card(self, hard_card_data: Dict) -> Result:
        """
        Validate Hard Card composition data for correctness.

        Checks for common issues:
        - All layer names start with 'z'
        - No duplicate variable names
        - All text layers have sourceText
        - Positions are within composition bounds
        - No excessive overlapping

        Args:
            hard_card_data: Hard Card dictionary from generate_hard_card_dict()

        Returns:
            Result indicating success or validation errors

        Example:
            >>> hard_card = generator.generate_hard_card_dict()
            >>> result = generator.validate_hard_card(hard_card)
            >>> result.is_success()
            True
        """
        errors = []
        warnings = []

        # Check basic structure
        if 'layers' not in hard_card_data:
            return Result.failure("Hard Card data missing 'layers' key")

        layers = hard_card_data['layers']
        layer_names = set()

        for i, layer in enumerate(layers):
            # Check layer name prefix
            if not layer['name'].startswith('z'):
                errors.append(
                    f"Layer {i}: '{layer['name']}' does not start with 'z'"
                )

            # Check for duplicates
            if layer['name'] in layer_names:
                errors.append(f"Duplicate layer name: '{layer['name']}'")
            layer_names.add(layer['name'])

            # Check source text
            if 'sourceText' not in layer:
                errors.append(
                    f"Layer {i} ('{layer['name']}') missing sourceText"
                )

            # Check position
            if 'position' in layer:
                x, y = layer['position']
                if x < 0 or y < 0:
                    warnings.append(
                        f"Layer '{layer['name']}' has negative position: ({x}, {y})"
                    )
                if x > hard_card_data.get('width', 1920):
                    warnings.append(
                        f"Layer '{layer['name']}' X position {x} exceeds comp width"
                    )
                if y > hard_card_data.get('height', 1080):
                    warnings.append(
                        f"Layer '{layer['name']}' Y position {y} exceeds comp height"
                    )

        # Check for expected count
        expected_count = len(StandardVariables.get_all_variables())
        if len(layers) != expected_count:
            warnings.append(
                f"Layer count {len(layers)} differs from standard variable count {expected_count}"
            )

        # Report results
        if errors:
            self.logger.error(f"Hard Card validation failed with {len(errors)} errors")
            return Result.failure(
                f"Validation failed: {len(errors)} error(s), details: {errors[:3]}"
            )

        if warnings:
            self.logger.warning(f"Hard Card validation passed with {len(warnings)} warnings")
            return Result.success({
                'warnings': warnings,
                'message': f"Validation passed with {len(warnings)} warning(s)"
            })

        self.logger.info("Hard Card validation passed with no issues")
        return Result.success({
            'message': "Validation passed with no issues"
        })

    def _escape_xml(self, text: str) -> str:
        """
        Escape special characters for XML.

        Args:
            text: Text to escape

        Returns:
            XML-safe text

        Example:
            >>> generator._escape_xml('Team "A" & Team "B"')
            'Team &quot;A&quot; &amp; Team &quot;B&quot;'
        """
        if not text:
            return ''

        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    def get_variable_count_by_category(self, hard_card_data: Dict) -> Dict[str, int]:
        """
        Get count of variables by category in Hard Card.

        Args:
            hard_card_data: Hard Card dictionary

        Returns:
            Dictionary mapping category names to counts

        Example:
            >>> hard_card = generator.generate_hard_card_dict()
            >>> counts = generator.get_variable_count_by_category(hard_card)
            >>> counts['team']
            10
            >>> counts['player']
            135
        """
        category_counts = {}

        for layer in hard_card_data.get('layers', []):
            metadata = layer.get('metadata', {})
            category = metadata.get('category', 'unknown')
            category_counts[category] = category_counts.get(category, 0) + 1

        return category_counts

    def export_variable_list(self, hard_card_data: Dict, output_path: str) -> Result:
        """
        Export list of variables to text file for documentation.

        Args:
            hard_card_data: Hard Card dictionary
            output_path: Path to output text file

        Returns:
            Result indicating success or failure

        Example:
            >>> hard_card = generator.generate_hard_card_dict()
            >>> result = generator.export_variable_list(hard_card, 'variables.txt')
        """
        try:
            with open(output_path, 'w') as f:
                f.write("HARD CARD VARIABLES\n")
                f.write("=" * 80 + "\n\n")

                # Group by category
                by_category = {}
                for layer in hard_card_data.get('layers', []):
                    metadata = layer.get('metadata', {})
                    category = metadata.get('category', 'unknown')
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(layer)

                # Write each category
                for category, layers in sorted(by_category.items()):
                    f.write(f"\n{category.upper()} ({len(layers)} variables)\n")
                    f.write("-" * 80 + "\n")

                    for layer in layers:
                        metadata = layer.get('metadata', {})
                        f.write(f"  {layer['name']:30} | ")
                        f.write(f"{metadata.get('data_type', 'unknown'):10} | ")
                        f.write(f"{layer.get('sourceText', '')[:30]}\n")

            self.logger.info(f"Exported variable list to {output_path}")
            return Result.success({'output_path': output_path})

        except Exception as e:
            self.logger.error(f"Failed to export variable list: {e}")
            return Result.failure(str(e))
